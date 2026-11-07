# Proxmox API Client

"""Proxmox API integration for tenant provisioning."""

import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProxmoxConfig:
    """Proxmox configuration."""
    host: str = "192.168.30.100"
    port: int = 8006
    user: str = "root@pam"
    password: str = ""
    verify_ssl: bool = False


class ProxmoxClient:
    """Client for Proxmox VE API."""
    
    def __init__(self, config: ProxmoxConfig):
        self.config = config
        self.base_url = f"https://{config.host}:{config.port}/api2/json"
        self.session = requests.Session()
        self.session.verify = config.verify_ssl
        self._ticket: Optional[str] = None
        self._csrf: Optional[str] = None
    
    def _authenticate(self) -> None:
        """Authenticate with Proxmox API."""
        response = self.session.post(
            f"{self.base_url}/access/ticket",
            data={
                "username": self.config.user,
                "password": self.config.password
            },
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        self._ticket = data["data"]["ticket"]
        self._csrf = data["data"]["CSRFPreventionToken"]
        
        # Set cookie
        self.session.cookies.set("PVEAuthCookie", self._ticket)
    
    def _ensure_authenticated(self) -> None:
        """Ensure we're authenticated, authenticate if not."""
        if not self._ticket:
            self._authenticate()
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers with CSRF token."""
        self._ensure_authenticated()
        return {
            "CSRFPreventionToken": self._csrf,
            "Content-Type": "application/x-www-form-urlencoded"
        }
    
    def get_nodes(self) -> list:
        """List all nodes in cluster."""
        response = self.session.get(
            f"{self.base_url}/nodes",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()["data"]
    
    def get_lxc_list(self, node: str = "pve") -> list:
        """List all LXC containers on a node."""
        response = self.session.get(
            f"{self.base_url}/nodes/{node}/lxc",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()["data"]
    
    def create_lxc(
        self,
        node: str,
        vm_id: int,
        hostname: str,
        ostemplate: str,
        cores: int = 2,
        memory: int = 4096,
        disk_size: int = 20,
        ip_address: str = "",
        gateway: str = "",
        password: str = "",
        nameserver: str = "",
        searchdomain: str = "",
        ssh_public_keys: str = "",
        unused: str = ""
    ) -> Dict[str, Any]:
        """Create a new LXC container."""
        self._ensure_authenticated()
        
        data = {
            "vmid": vm_id,
            "hostname": hostname,
            "ostemplate": f"local:vztmpl/{ostemplate}",
            "cores": cores,
            "memory": memory,
            "disk": f"size={disk_size}G",
        }
        
        if ip_address:
            data["net0"] = f"name=eth0,bridge=vmbr0,ip={ip_address}/24,gw={gateway}"
        
        if password:
            data["password"] = password
        
        if nameserver:
            data["nameserver"] = nameserver
        
        if searchdomain:
            data["searchdomain"] = searchdomain
        
        if ssh_public_keys:
            data["sshpublickeys"] = ssh_public_keys
        
        if unused:
            data["unused0"] = unused
        
        response = self.session.post(
            f"{self.base_url}/nodes/{node}/lxc",
            headers=self._headers(),
            data=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["data"]
    
    def start_lxc(self, node: str, vm_id: int) -> Dict[str, Any]:
        """Start an LXC container."""
        self._ensure_authenticated()
        
        response = self.session.post(
            f"{self.base_url}/nodes/{node}/lxc/{vm_id}/status/start",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()["data"]
    
    def stop_lxc(self, node: str, vm_id: int) -> Dict[str, Any]:
        """Stop an LXC container."""
        self._ensure_authenticated()
        
        response = self.session.post(
            f"{self.base_url}/nodes/{node}/lxc/{vm_id}/status/stop",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()["data"]
    
    def delete_lxc(self, node: str, vm_id: int) -> Dict[str, Any]:
        """Delete an LXC container."""
        self._ensure_authenticated()
        
        response = self.session.delete(
            f"{self.base_url}/nodes/{node}/lxc/{vm_id}",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()["data"]
    
    def get_lxc_status(self, node: str, vm_id: int) -> Dict[str, Any]:
        """Get LXC container status."""
        response = self.session.get(
            f"{self.base_url}/nodes/{node}/lxc/{vm_id}/status/current",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()["data"]
    
    def get_templates(self, node: str = "pve", storage: str = "local") -> list:
        """List available templates."""
        response = self.session.get(
            f"{self.base_url}/nodes/{node}/storage/{storage}/content",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()["data"]
    
    def get_vm_next_id(self, node: str = "pve") -> int:
        """Get next available VM ID."""
        response = self.session.get(
            f"{self.base_url}/cluster/nextid",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return int(response.json()["data"])
    
    def clone_lxc(
        self,
        node: str,
        vm_id: int,
        new_id: int,
        new_hostname: str,
        full: int = 1
    ) -> Dict[str, Any]:
        """Clone an existing LXC container."""
        self._ensure_authenticated()
        
        response = self.session.post(
            f"{self.base_url}/nodes/{node}/lxc/{vm_id}/clone",
            headers=self._headers(),
            data={
                "vmid": new_id,
                "hostname": new_hostname,
                "full": full
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["data"]
    
    def update_lxc_config(
        self,
        node: str,
        vm_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Update LXC container configuration."""
        self._ensure_authenticated()
        
        response = self.session.put(
            f"{self.base_url}/nodes/{node}/lxc/{vm_id}/config",
            headers=self._headers(),
            data=kwargs,
            timeout=10
        )
        response.raise_for_status()
        return response.json()["data"]
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get cluster information."""
        response = self.session.get(
            f"{self.base_url}/cluster/status",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()["data"]


# Convenience function
def get_proxmox_client(
    host: str = "192.168.30.100",
    password: str = ""
) -> ProxmoxClient:
    """Create a Proxmox client with default configuration."""
    config = ProxmoxConfig(
        host=host,
        password=password
    )
    return ProxmoxClient(config)
