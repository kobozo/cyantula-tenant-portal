"""Proxmox API client for LXC container management."""
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import requests
from urllib.parse import urljoin


@dataclass
class ProxmoxConfig:
    """Proxmox server configuration."""
    api_url: str = "https://192.168.3.211:8006"
    api_token_id: str = "root@pam!tenant-portal"
    api_token_secret: str = ""
    node: str = "pve"
    
    @classmethod
    def from_env(cls) -> "ProxmoxConfig":
        """Create config from environment variables."""
        return cls(
            api_url=os.getenv("PROXMOX_API_URL", "https://192.168.3.211:8006"),
            api_token_id=os.getenv("PROXMOX_API_TOKEN_ID", "root@pam!tenant-portal"),
            api_token_secret=os.getenv("PROXMOX_API_TOKEN_SECRET"),
            node=os.getenv("PROXMOX_NODE", "kb-pvecyantula01"),
        )


class ProxmoxClient:
    """Client for Proxmox VE API v2."""
    
    def __init__(self, config: Optional[ProxmoxConfig] = None):
        """Initialize the Proxmox client.
        
        Args:
            config: Proxmox configuration (defaults to env vars)
        """
        self.config = config or ProxmoxConfig.from_env()
        
        if not self.config.api_token_secret:
            raise ValueError("PROXMOX_API_TOKEN_SECRET environment variable is required")
    
    def _build_auth_header(self, method: str, path: str, data: Optional[Dict] = None) -> str:
        """Build the Authorization header for Proxmox API.
        
        Proxmox supports two auth methods:
        1. Simple token: PVEAPIToken={api_id}={api_token}
        2. HMAC-based: PVEAPIToken={api_id}={timestamp}:{nonce}:{hmac}
        
        Using simple token for now - works for API access.
        """
        return f"PVEAPIToken={self.config.api_token_id}={self.config.api_token_secret}"
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Make a request to the Proxmox API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., /nodes/{node}/lxc)
            data: Request body for POST/PUT
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            API response as dict
        """
        # Build URL with /api2/json prefix
        url = f"{self.config.api_url}/api2/json{endpoint}"
        
        # For auth signing, use full path with /api2/json prefix
        full_path = f"/api2/json{endpoint}"
        
        # Build auth header
        auth_header = self._build_auth_header(method, full_path, data)
        
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=data,
            timeout=timeout,
            verify=False,  # Proxmox uses self-signed certificates
        )
        
        response.raise_for_status()
        return response.json()
    
    # ── Node operations ──────────────────────────────────────────────────────
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """List all Proxmox nodes."""
        result = self._request("GET", "/nodes")
        return result.get("data", [])
    
    def get_node_status(self, node: str) -> Dict[str, Any]:
        """Get node status."""
        result = self._request("GET", f"/nodes/{node}")
        return result.get("data", {})
    
    # ── LXC container operations ─────────────────────────────────────────────
    
    def get_lxc_containers(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """List LXC containers.
        
        Args:
            node: Optional node name. If None, lists on default node.
        """
        target_node = node or self.config.node
        result = self._request("GET", f"/nodes/{target_node}/lxc")
        return result.get("data", [])
    
    def get_lxc_status(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get LXC container status."""
        result = self._request("GET", f"/nodes/{node}/lxc/{vmid}/status/current")
        return result.get("data") or {}
    
    def _run_pct_command(self, *args: str) -> str:
        """Run a pct command on the Proxmox host via SSH."""
        import subprocess
        
        # Build full shell command and execute via SSH with strict host key check disabled
        full_cmd = "pct " + " ".join(args)
        
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"root@{self.config.node}",
            full_cmd
        ]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"pct command failed: {result.stderr}")
        
        return result.stdout
    
    def create_lxc_container(
        self,
        vmid: int,
        hostname: str,
        storage: str = "local",
        cores: int = 1,
        memory: int = 1024,
        disk_size: int = 10,
        ostemplate: str = "debian-13-standard_13.6-1_amd64.tar.zst",
        password: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new LXC container using pct CLI (most reliable method).
        
        Args:
            vmid: Container ID (unique)
            hostname: Container hostname
            storage: Storage pool for rootfs
            cores: Number of CPU cores
            memory: Memory in MB
            disk_size: Disk size in GB
            ostemplate: Template name (must exist on storage)
            password: Root password (auto-generated if None)
            ip: Static IP address
            
        Returns:
            Task result dict
        """
        import secrets
        
        # Auto-generate root password if not provided
        if password is None:
            password = secrets.token_urlsafe(16)
        
        template = f"{storage}:vztmpl/{ostemplate}"
        
        # Run pct create command
        self._run_pct_command(
            "create", str(vmid),
            template,
            f"--hostname {hostname}",
            f"--cores {cores}",
            f"--memory {memory}",
            f"--rootfs {storage}-lvm:{disk_size}",
            f"--password {password}",
            "--net0 name=eth0,bridge=vmbr0,ip=dhcp",
            "--ostype debian",
        )
        
        return {"message": "Container creation completed"}
    
    def start_lxc_container(self, node: str, vmid: int) -> Dict[str, Any]:
        """Start an LXC container."""
        result = self._request("POST", f"/nodes/{node}/lxc/{vmid}/status/start")
        return result
    
    def stop_lxc_container(self, node: str, vmid: int) -> Dict[str, Any]:
        """Stop an LXC container."""
        result = self._request("POST", f"/nodes/{node}/lxc/{vmid}/status/stop")
        return result
    
    def delete_lxc_container(self, node: str, vmid: int) -> Dict[str, Any]:
        """Delete an LXC container."""
        result = self._request("DELETE", f"/nodes/{node}/lxc/{vmid}")
        return result
    
    def get_lxc_config(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get LXC container configuration."""
        result = self._request("GET", f"/nodes/{node}/lxc/{vmid}/config")
        return result.get("data", {})
    
    def update_lxc_config(
        self,
        node: str,
        vmid: int,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update LXC container configuration."""
        result = self._request("PUT", f"/nodes/{node}/lxc/{vmid}/config", data=config)
        return result
    
    # ── Template operations ──────────────────────────────────────────────────
    
    def get_templates(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available templates."""
        target_node = node or self.config.node
        result = self._request("GET", f"/nodes/{target_node}/storage/local-vztmpl/content")
        return result.get("data", [])
    
    # ── Utility methods ──────────────────────────────────────────────────────
    
    def find_next_vmid(self) -> int:
        """Find the next available VM ID."""
        containers = self.get_lxc_containers()
        used_ids = {c["vmid"] for c in containers}
        
        # Start from 100
        for vmid in range(100, 10000):
            if vmid not in used_ids:
                return vmid
        raise RuntimeError("No available VM IDs")
    
    def wait_for_container(
        self,
        node: str,
        vmid: int,
        status: str = "running",
        timeout: int = 120,
    ) -> bool:
        """Wait for a container to reach a specific status. Starts the container if needed.
        
        Args:
            node: Node name
            vmid: Container ID
            status: Target status (running, stopped)
            timeout: Timeout in seconds
             
        Returns:
            True if status reached, False on timeout
        """
        import time
        start_time = time.time()
        
        # Start container if not running
        if status == "running":
            current_status = self.get_lxc_status(node, vmid).get("status")
            if current_status != "running":
                self.start_lxc_container(node, vmid)
        
        while time.time() - start_time < timeout:
            container_status = self.get_lxc_status(node, vmid)
            current_status = container_status.get("status")
            
            if current_status == status:
                return True
            
            time.sleep(2)
        
        return False
