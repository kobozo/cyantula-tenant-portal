# Proxmox Setup Instructions

## Infrastructure

```
Proxmox Host: 192.168.1.240 (VLAN 30)
Network: 192.168.30.0/24
Gateway: 192.168.30.1
DNS: 192.168.1.53
```

## Architectuur

```
Internet
   │
   ▼
VLAN 30 (192.168.30.0/24)
   │
   ├─── 192.168.30.100 (LXC 100: cyantula-portal)
   │    ├── Tenant Portal API
   │    ├── Provisioning engine
   │    ├── Template generator (via CI)
   │    ├── Release management
   │    └── Auto-update voor tenant apps
   │
   ├─── 192.168.30.101-199 (LXC: tenant instances)
   │    └── Cyantula per tenant
   │
   └─── 192.168.30.200 (LXC: cyantula-app)
        ├── Template generator
        ├── Release builder (CI)
        └── Package publisher
```

## Proxmox Installatie

### 1. Installatie

Install Proxmox VE op 192.168.1.240 met VLAN 30 support.

### 2. Netwerk Configuratie

Bewerk `/etc/network/interfaces`:

```bash
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet manual

# VLAN 30
auto eth0.30
iface eth0.30 inet static
    address 192.168.30.100
    netmask 255.255.255.0
    gateway 192.168.30.1
    vlan-raw-device eth0

# Bridge voor LXC/VMs
auto vmbr0
iface vmbr0 inet static
    address 192.168.30.100
    netmask 255.255.255.0
    bridge_ports eth0.30
    bridge_stp off
    bridge_fd 0
```

### 3. Proxmox Updaten

```bash
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve-install-repo.list
wget -O- https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg
apt update && apt full-upgrade -y
```

### 4. DNS

```bash
nameserver 192.168.1.53
search cyantula.eu
```

## LXC Containers

### Cyantula Portal (LXC 100)

Deze LXC draait de tenant portal en de CI/CD pipeline.

**Hardware:**
- CPU: 4 vCPUs
- RAM: 8 GB
- Disk: 50 GB SSD

**Network:**
- IP: 192.168.30.100/24
- Gateway: 192.168.30.1

**Functies:**
- Tenant Portal API (FastAPI)
- Provisioning engine
- Template generator (via CI)
- Release management
- Auto-update tenant apps

### Tenant LXC Containers (LXC 101-199)

Elke tenant krijgt een eigen LXC container.

**Hardware per tenant:**
- CPU: 2 vCPUs
- RAM: 4 GB
- Disk: 20 GB SSD

**Network:**
- Elke tenant heeft eigen IP in 192.168.30.x/24 subnet
- Volledige isolatie tussen tenants

**Functies:**
- Cyantula app per tenant
- Auto-update via portal
- Gedeclareerd bij template update

## CI/CD Pipeline

De cyantula-app in LXC doet:

1. **Template Generator**: Genereert LXC templates voor tenants
2. **Release Builder**: Buildt nieuwe Cyantula versies
3. **Package Publisher**: Publiceert packages voor auto-update

## Volgende Stappen

Na Proxmox installatie:
1. LXC 100 aanmaken voor cyantula-portal
2. Cyantula app installeren in LXC 100
3. CI/CD pipeline configureren
4. Template generator opstarten
5. Tenant onboarding flow testen
