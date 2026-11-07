# Proxmox Configuration for Cyantula Tenant Portal

## Infrastructure

```
Proxmox Host: 192.168.1.240 (VLAN 30)
Network: 192.168.30.0/24 (VLAN 30)
Gateway: 192.168.30.1
DNS: 192.168.1.53
```

## VM Configuration

### VM ID: 100
### Name: cyantula-portal
### Role: Central tenant portal (control plane)

**Hardware:**
- CPU: 4 vCPUs
- RAM: 8 GB
- Disk: 50 GB (SSD)
- Network: VM network on VLAN 30 (192.168.30.x)

**IP Address:** 192.168.30.100

**Purpose:**
- Tenant Portal API (FastAPI)
- Provisioning engine
- DNS manager (Cloudflare API)
- Email service (SMTP)
- Monitoring (Prometheus, Grafana)

---

### VM ID: 101-199
### Name: tenant-{slug}
### Role: Individual tenant instances

**Hardware per tenant:**
- CPU: 2 vCPUs
- RAM: 4 GB
- Disk: 20 GB (SSD)
- Network: VLAN 30 with isolated subnet

**Network isolation per tenant:**
```
Tenant A: 192.168.30.10/24
Tenant B: 192.168.30.20/24
Tenant C: 192.168.30.30/24
...
```

**Purpose:**
- Cyantula app (per tenant)
- Separate Docker Compose stack
- Isolated from other tenants

---

## Network Architecture

```
Internet
   │
   ▼
VLAN 30 (192.168.30.0/24)
   │
   ├─── 192.168.30.1 (gateway)
   │
   ├─── 192.168.30.100 (VM 100: cyantula-portal)
   │    ├── API: *.cyantula.eu, *.cyantula.com
   │    ├── Provisioning API
   │    ├── DNS Manager
   │    └── Email service
   │
   ├─── 192.168.30.10 (VM 101: tenant-a)
   │    └── Cyantula: tenant-a.cyantula.eu
   │
   ├─── 192.168.30.20 (VM 102: tenant-b)
   │    └── Cyantula: tenant-b.cyantula.eu
   │
   └─── 192.168.30.30 (VM 103: tenant-c)
        └── Cyantula: tenant-c.cyantula.com
```

---

## Proxmox Setup Steps

### 1. Install Proxmox on 192.168.1.240

```bash
# Download Proxmox ISO
wget https://enterprise.proxmox.com/debian/dsb/proxmox-ve_8.0-1.iso

# Install with VLAN 30
# During install:
# - Network: eth0.30 (VLAN 30)
# - IP: 192.168.30.100/24
# - Gateway: 192.168.30.1
```

### 2. Configure VLAN on Proxmox

```bash
# /etc/network/interfaces
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet manual

auto eth0.30
iface eth0.30 inet static
    address 192.168.30.100
    netmask 255.255.255.0
    gateway 192.168.30.1
    vlan-raw-device eth0

auto vmbr0
iface vmbr0 inet static
    address 192.168.30.100
    netmask 255.255.255.0
    bridge_ports eth0.30
    bridge_stp off
    bridge_fd 0
```

### 3. Create LXC Template for Tenants

```bash
# Download Ubuntu template
pveam download pve-focal-20.04-standard_20.04-1_amd64.tar.gz

# Create template VM
qm create 9000 --name cyantula-tenant-template --memory 4096 --cores 2
```

### 4. Provisioning Workflow

```python
# tenant_portal/provisioning/proxmox.py
import requests

class ProxmoxAPI:
    def __init__(self, host, user, password):
        self.base_url = f"https://{host}:8006/api2/json"
        self.token = self._authenticate(user, password)
    
    def _authenticate(self, user, password):
        response = requests.post(
            f"{self.base_url}/access/ticket",
            data={"username": user, "password": password}
        )
        return response.json()["data"]["ticket"]
    
    def create_lxc(self, vm_id, hostname, ip, subnet):
        """Create LXC container for new tenant"""
        # Create container
        response = requests.post(
            f"{self.base_url}/nodes/pve01/lxc",
            headers={"Cookie": f"PVEAuthCookie={self.token}"},
            data={
                "vmid": vm_id,
                "hostname": hostname,
                "ostemplate": "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.gz",
                "cores": 2,
                "memory": 4096,
                "net0": "name=eth0,bridge=vmbr0,ip=192.168.30.10/24,gw=192.168.30.1",
                "disk": "size=20G",
                "password": "temporary-password"
            }
        )
        return response.json()
    
    def start_lxc(self, vm_id):
        response = requests.post(
            f"{self.base_url}/nodes/pve01/lxc/{vm_id}/status/start",
            headers={"Cookie": f"PVEAuthCookie={self.token}"}
        )
        return response.json()
    
    def stop_lxc(self, vm_id):
        response = requests.post(
            f"{self.base_url}/nodes/pve01/lxc/{vm_id}/status/stop",
            headers={"Cookie": f"PVEAuthCookie={self.token}"}
        )
        return response.json()
    
    def delete_lxc(self, vm_id):
        response = requests.delete(
            f"{self.base_url}/nodes/pve01/lxc/{vm_id}",
            headers={"Cookie": f"PVEAuthCookie={self.token}"}
        )
        return response.json()
```

### 5. Tenant Onboarding with Proxmox

```python
# tenant_portal/provisioning/tenant_onboarding.py
from .proxmox import ProxmoxAPI
from .dns import DNSManager
from .email import EmailService

class TenantOnboarding:
    def __init__(self):
        self.proxmox = ProxmoxAPI(
            host="192.168.30.100",
            user="root@pam",
            password="your-proxmox-password"
        )
        self.dns = DNSManager()
        self.email = EmailService()
    
    def onboard_tenant(self, organisation):
        """Full tenant onboarding flow"""
        # 1. Get next available VM ID
        vm_id = self._get_next_vm_id()
        
        # 2. Create LXC container
        self.proxmox.create_lxc(
            vm_id=vm_id,
            hostname=organisation.slug,
            ip=f"192.168.30.{vm_id}/24",
            subnet="192.168.30.0/24"
        )
        
        # 3. Start container
        self.proxmox.start_lxc(vm_id)
        
        # 4. Register DNS
        dns_name = f"{organisation.slug}.cyantula.eu"
        self.dns.register(dns_name, f"192.168.30.{vm_id}")
        
        # 5. Generate setup token
        token = self._generate_setup_token(organisation.id)
        
        # 6. Send setup email
        self.email.send_setup_email(organisation, token)
        
        return {
            "vm_id": vm_id,
            "ip": f"192.168.30.{vm_id}",
            "dns": dns_name,
            "token": token
        }
    
    def deprovision_tenant(self, organisation):
        """Remove tenant resources"""
        vm_id = self._get_vm_id_for_organisation(organisation.id)
        
        # 1. Stop container
        self.proxmox.stop_lxc(vm_id)
        
        # 2. Delete container
        self.proxmox.delete_lxc(vm_id)
        
        # 3. Remove DNS
        dns_name = f"{organisation.slug}.cyantula.eu"
        self.dns.unregister(dns_name)
        
        return {"success": True}
```

### 6. Isolation Hardening

```bash
# /etc/pve/lxc/101.conf (Tenant A)
# Namespace isolation
lxc.namespace.pivot: on
lxc.namespace.clone: yes

# Network isolation (separate MAC)
lxc.net0: type=veth,bridge=vmbr0,hwaddr=02:00:00:AA:BB:01,ip=192.168.30.10/24,gw=192.168.30.1

# Resource limits (cgroups)
lxc.cgroup2.memory.max: 4294967296
lxc.cgroup2.cpu.weight: 100
lxc.cgroup2.cpu.max: 200000

# Filesystem isolation
lxc.mount.entry: none mnt tmpfs defaults,bind,ro 0 0
lxc.mount.entry: none dev tmpfs defaults,bind,ro 0 0

# Seccomp profile
lxc.apparmor.profile: unconfined

# No shared mounts
lxc.mount.auto: cgroup:rw proc:rw sys:rw
```

### 7. Monitoring

```bash
# Install Prometheus on portal VM
# scrape_targets.yml
scrape_configs:
  - job_name: 'proxmox'
    static_configs:
      - targets: ['192.168.30.100']
  
  - job_name: 'tenants'
    static_configs:
      - targets: ['192.168.30.10']
      - targets: ['192.168.30.20']
      - targets: ['192.168.30.30']
```

---

## Summary

| Component | Location | IP | Purpose |
|-----------|----------|-----|---------|
| Proxmox Host | 192.168.1.240 | 192.168.30.100 | Control plane |
| Tenant Portal VM | Proxmox | 192.168.30.100 | API, provisioning, DNS, email |
| Tenant LXC 1 | Proxmox | 192.168.30.10 | Cyantula instance A |
| Tenant LXC 2 | Proxmox | 192.168.30.20 | Cyantula instance B |
| ... | ... | ... | ... |

**Key:** VLAN 30 voor alle communicatie, Proxmox API voor provisioning, LXC isolatie per tenant.

Wil je dat ik dit nu in de repo zet als spec + code?