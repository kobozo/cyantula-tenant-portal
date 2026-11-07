# Proxmox Setup Instructions

## Architecture

```
Existing Production Server: 192.168.1.240 (NO CHANGES - data safe)
   │
   └── VLAN 30 interface → New Proxmox Server (192.168.30.x)
          │
          ├── LXC 100: cyantula-tenant-portal (192.168.30.100)
          │    ├── Tenant Portal API
          │    ├── Provisioning engine
          │    ├── CI/CD runner (templates, release)
          │    └── Auto-update for tenant apps
          │
          └── LXC 101-199: Tenant Cyantula instances
               └── Per tenant Cyantula app
```

## What NOT to Do

⚠️ **DO NOT** touch the existing server at 192.168.1.240
- Production data stays intact
- No reinstallation
- No changes to existing services

## New Setup

### 1. Separate Proxmox Server

Set up a **NEW** Proxmox server on VLAN 30 (different machine or separate VLAN interface).

**Network (VLAN 30):**
- Proxmox: 192.168.30.100
- Network: 192.168.30.0/24
- Gateway: 192.168.30.1
- DNS: 192.168.1.53

### 2. cyantula-tenant-portal

The app we're building will run in an LXC container on this new Proxmox:

**LXC 100:**
- IP: 192.168.30.100
- CPU: 4 vCPUs
- RAM: 8 GB
- Disk: 50 GB SSD

**Functies:**
- Tenant Portal API
- Provisioning engine (creates LXC for tenants)
- Template generator (CI/CD)
- Release management
- Auto-update tenant apps

### 3. Communication Flow

```
Internet
   │
   ▼
192.168.1.240 (production - unchanged)
   │
   └── VLAN 30 → 192.168.30.100 (cyantula-tenant-portal)
          │
          ├── API: Create organisation → LXC provisioning
          ├── Provisioning: Create LXC → tenant instance
          └── CI/CD: Build templates → publish updates
```

## VLAN 30 Configuration

### On the existing server (192.168.1.240)

Add VLAN 30 interface for communication to new Proxmox:

```bash
# /etc/network/interfaces (on 192.168.1.240)
auto eth0.30
iface eth0.30 inet static
    address 192.168.1.240  # unchanged - existing IP
    # VLAN 30 bridge for new Proxmox
```

### On the new Proxmox server

```bash
# /etc/network/interfaces (on new Proxmox)
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

## What I Should Create

**In cyantula-tenant-portal repo:**
- API endpoints for tenant onboarding
- Provisioning logic (Proxmox API client)
- Template generation scripts
- Release management
- Auto-update mechanism

**What CI does:**
- Build packages
- Publish templates
- Update tenant instances

## Summary

| Component | Location | Action |
|-----------|----------|--------|
| Existing server | 192.168.1.240 | **NO CHANGES** |
| New Proxmox | New machine/VLAN 30 | Install Proxmox |
| cyantula-tenant-portal | LXC on new Proxmox | Build app + code |
| Tenant LXCs | On new Proxmox | Created by portal |
