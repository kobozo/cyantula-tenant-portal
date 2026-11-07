# Tenant provisioning manager using Proxmox

"""Tenant onboarding and provisioning logic."""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .proxmox_client import ProxmoxClient, ProxmoxConfig
from .dns import DNSManager
from .email import EmailService
from database.models import Organisation, SetupToken


@dataclass
class TenantConfig:
    """Tenant instance configuration."""
    vm_id: int = 101
    cores: int = 2
    memory: int = 4096  # MB
    disk_size: int = 20  # GB
    network_base: str = "192.168.30"  # Base IP
    gateway: str = "192.168.30.1"
    nameserver: str = "192.168.1.53"
    searchdomain: str = "cyantula.eu"
    template: str = "ubuntu-22.04-standard_22.04-1_amd64.tar.gz"


class TenantProvisioner:
    """Manager for tenant provisioning using Proxmox LXC."""
    
    def __init__(
        self,
        proxmox: ProxmoxClient,
        dns_manager: DNSManager,
        email_service: EmailService,
        config: TenantConfig = TenantConfig()
    ):
        self.proxmox = proxmox
        self.dns = dns_manager
        self.email = email_service
        self.config = config
        self.node = "pve"  # Default Proxmox node
    
    def _generate_token(self, organisation_id: str) -> str:
        """Generate secure setup token."""
        token = secrets.token_hex(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Store token hash in database
        expiry = datetime.now() + timedelta(hours=24)
        
        # This would typically be done via ORM
        # setup_token = SetupToken(
        #     organisation_id=organisation_id,
        #     token_hash=token_hash,
        #     expires_at=expiry
        # )
        # db.session.add(setup_token)
        # db.session.commit()
        
        return token
    
    def _get_next_vm_id(self) -> int:
        """Get next available VM ID from Proxmox."""
        return self.proxmox.get_vm_next_id(self.node)
    
    def _get_tenant_ip(self, vm_id: int) -> str:
        """Get IP address for tenant based on VM ID."""
        # Use last octet of VM ID for IP assignment
        return f"{self.config.network_base}.{vm_id % 256}"
    
    def _isolate_lxc_config(self, vm_id: int, hostname: str, ip: str) -> dict:
        """Generate isolated LXC configuration for security."""
        return {
            # Namespace isolation
            "lxc.namespace.pivot": "on",
            "lxc.namespace.clone": "yes",
            
            # Network isolation (unique MAC)
            "lxc.net0": f"name=eth0,bridge=vmbr0,hwaddr=02:00:00:{vm_id:02x}:{vm_id:02x}:{vm_id:02x},ip={ip}/24,gw={self.config.gateway}",
            
            # Resource limits (cgroups)
            "lxc.cgroup2.memory.max": str(self.config.memory * 1024 * 1024),
            "lxc.cgroup2.cpu.weight": "100",
            "lxc.cgroup2.cpu.max": "200000",
            
            # Filesystem isolation
            "lxc.mount.entry": "none mnt tmpfs defaults,bind,ro 0 0",
            
            # AppArmor (unconfined for flexibility, can be hardened later)
            "lxc.apparmor.profile": "unconfined",
            
            # No shared mounts
            "lxc.mount.auto": "cgroup:rw proc:rw sys:rw",
        }
    
    def onboard_tenant(
        self,
        organisation: Organisation
    ) -> Dict[str, Any]:
        """Full tenant onboarding flow."""
        print(f"[ONBOARD] Starting onboarding for {organisation.name}")
        
        try:
            # 1. Get next available VM ID
            vm_id = self._get_next_vm_id()
            print(f"[ONBOARD] Assigned VM ID: {vm_id}")
            
            # 2. Create LXC container
            ip = self._get_tenant_ip(vm_id)
            print(f"[ONBOARD] Creating LXC container with IP: {ip}")
            
            self.proxmox.create_lxc(
                node=self.node,
                vm_id=vm_id,
                hostname=organisation.slug,
                ostemplate=self.config.template,
                cores=self.config.cores,
                memory=self.config.memory,
                disk_size=self.config.disk_size,
                ip_address=ip,
                gateway=self.config.gateway,
                password=secrets.token_hex(16),
                nameserver=self.config.nameserver,
                searchdomain=self.config.searchdomain
            )
            print(f"[ONBOARD] LXC container created")
            
            # 3. Start container
            print(f"[ONBOARD] Starting LXC container")
            self.proxmox.start_lxc(self.node, vm_id)
            print(f"[ONBOARD] LXC container started")
            
            # 4. Wait for container to be ready
            import time
            max_wait = 60
            for i in range(max_wait):
                status = self.proxmox.get_lxc_status(self.node, vm_id)
                if status.get("status") == "running":
                    print(f"[ONBOARD] LXC container is running")
                    break
                time.sleep(1)
            else:
                raise Exception(f"Container failed to start within {max_wait} seconds")
            
            # 5. Register DNS
            dns_name = f"{organisation.slug}.cyantula.eu"
            print(f"[ONBOARD] Registering DNS: {dns_name} -> {ip}")
            self.dns.register(dns_name, ip)
            print(f"[ONBOARD] DNS registered")
            
            # 6. Generate setup token
            token = self._generate_token(organisation.id)
            print(f"[ONBOARD] Setup token generated")
            
            # 7. Send setup email
            print(f"[ONBOARD] Sending setup email to {organisation.admin_email}")
            self.email.send_setup_email(organisation, token)
            print(f"[ONBOARD] Setup email sent")
            
            return {
                "success": True,
                "vm_id": vm_id,
                "ip": ip,
                "dns": dns_name,
                "token": token,
                "status": "completed"
            }
            
        except Exception as e:
            print(f"[ONBOARD] Failed: {str(e)}")
            # Cleanup on failure
            self._cleanup_failed_provisioning(vm_id)
            raise
    
    def _cleanup_failed_provisioning(self, vm_id: Optional[int]) -> None:
        """Cleanup resources if provisioning fails."""
        if vm_id:
            try:
                # Stop container if it was started
                status = self.proxmox.get_lxc_status(self.node, vm_id)
                if status.get("status") == "running":
                    self.proxmox.stop_lxc(self.node, vm_id)
                
                # Delete container
                self.proxmox.delete_lxc(self.node, vm_id)
                print(f"[CLEANUP] Cleaned up VM {vm_id}")
            except Exception as cleanup_error:
                print(f"[CLEANUP] Cleanup error: {cleanup_error}")
    
    def deprovision_tenant(
        self,
        organisation: Organisation,
        vm_id: int
    ) -> Dict[str, Any]:
        """Remove tenant resources."""
        print(f"[DEPROVISION] Starting deprovisioning for {organisation.name}")
        
        try:
            # 1. Stop container
            print(f"[DEPROVISION] Stopping LXC container {vm_id}")
            self.proxmox.stop_lxc(self.node, vm_id)
            print(f"[DEPROVISION] LXC container stopped")
            
            # 2. Delete container
            print(f"[DEPROVISION] Deleting LXC container {vm_id}")
            self.proxmox.delete_lxc(self.node, vm_id)
            print(f"[DEPROVISION] LXC container deleted")
            
            # 3. Remove DNS
            dns_name = f"{organisation.slug}.cyantula.eu"
            print(f"[DEPROVISION] Removing DNS: {dns_name}")
            self.dns.unregister(dns_name)
            print(f"[DEPROVISION] DNS removed")
            
            return {
                "success": True,
                "vm_id": vm_id,
                "status": "completed"
            }
            
        except Exception as e:
            print(f"[DEPROVISION] Failed: {str(e)}")
            raise
    
    def get_tenant_status(self, vm_id: int) -> Dict[str, Any]:
        """Get status of tenant container."""
        status = self.proxmox.get_lxc_status(self.node, vm_id)
        return {
            "vm_id": vm_id,
            "status": status.get("status", "unknown"),
            "uptime": status.get("uptime", 0),
            "cpus": status.get("cpus", 0),
            "memory": status.get("memory", {}),
            "disk": status.get("disk", {})
        }
    
    def restart_tenant(self, vm_id: int) -> Dict[str, Any]:
        """Restart tenant container."""
        self.proxmox.stop_lxc(self.node, vm_id)
        time.sleep(5)
        self.proxmox.start_lxc(self.node, vm_id)
        return {"success": True, "vm_id": vm_id}


# Convenience function
def create_provisioner(
    proxmox_password: str,
    dns_api_token: str,
    smtp_password: str
) -> TenantProvisioner:
    """Create a fully configured provisioner."""
    # Proxmox client
    proxmox_config = ProxmoxConfig(
        host="192.168.30.100",
        password=proxmox_password
    )
    proxmox = ProxmoxClient(proxmox_config)
    
    # DNS manager (Cloudflare example)
    dns_manager = DNSManager(
        provider="cloudflare",
        api_token=dns_api_token,
        base_domain="cyantula.eu"
    )
    
    # Email service
    email_service = EmailService(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="noreply@cyantula.eu",
        smtp_password=smtp_password
    )
    
    return TenantProvisioner(proxmox, dns_manager, email_service)
