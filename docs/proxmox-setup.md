# Proxmox & Architecture Setup

## Complete Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  NEW Proxmox Server (192.168.30.100)                            │
│  Full isolation - ALL containers on this single Proxmox        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  VLAN 30: Tenant Network                                │   │
│  │  ├─ LXC 100: cyantula-tenant-portal                    │   │
│  │  │   └─ IP: 192.168.30.100                              │   │
│  │  │   └─ NGINX/Traefik reverse proxy                     │   │
│  │  │      ├─ cyantula.eu → portal                         │   │
│  │  │      └─ *.cyantula.eu → tenant LXCs                  │   │
│  │  │                                                       │   │
│  │  ├─ LXC 101: tenant-a.cyantula.eu                       │   │
│  │  │   └─ IP: 192.168.30.10                               │   │
│  │  │   └─ Cyantula instance                              │   │
│  │  │                                                       │   │
│  │  ├─ LXC 102: tenant-b.cyantula.eu                       │   │
│  │  │   └─ IP: 192.168.30.20                               │   │
│  │  │   └─ Cyantula instance                              │   │
│  │  │                                                       │   │
│  │  └─ LXC 103: tenant-c.cyantula.com                     │   │
│  │      └─ IP: 192.168.30.30                               │   │
│  │      └─ Cyantula instance                              │   │
│  │                                                           │   │
│  │  └─ Tenant isolation (no inter-tenant communication)   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Your forwarding rules
                              ▼
Internet
   │
   ├─ cyantula.eu → 192.168.30.100 (portal)
   └─ *.cyantula.eu → 192.168.30.100 (proxy routes to tenants)

EXISTING Server: 192.168.1.240 (NO CHANGES - production data)
```

## Network Isolation

```
VLAN 30 (192.168.30.0/24):
   ├── Portal (192.168.30.100) - reverse proxy + management
   ├── Tenant A (192.168.30.10) - isolated
   ├── Tenant B (192.168.30.20) - isolated
   └── Tenant C (192.168.30.30) - isolated
   
   └─ NO communication between tenants
   └─ NO access to production (192.168.1.0/24)
```

## Your Setup (From Your Network)

You need to configure forwarding:

```bash
# Your network → New Proxmox VLAN 30
cyantula.eu → 192.168.30.100
*.cyantula.eu → 192.168.30.100
```

The reverse proxy on the Proxmox then routes to the correct tenant LXC.

## Who Runs Where

| Component | Proxmox | VLAN | IP | Notes |
|-----------|---------|------|-----|-------|
| **Cyantula Tenant Portal** | New Proxmox | VLAN 30 | 192.168.30.100 | Reverse proxy + management |
| **Tenant A** | New Proxmox | VLAN 30 | 192.168.30.10 | Cyantula instance |
| **Tenant B** | New Proxmox | VLAN 30 | 192.168.30.20 | Cyantula instance |
| **Tenant C** | New Proxmox | VLAN 30 | 192.168.30.30 | Cyantula instance |
| **Production Data** | Existing Server | N/A | 192.168.1.240 | **NO CHANGES** |

## Key Benefits

1. **Complete isolation:** All containers on single Proxmox
2. **No production impact:** Existing server untouched
3. **Your control:** You configure forwarding from your network
4. **Simplified networking:** All on one Proxmox, one VLAN
5. **Security:** Tenants isolated from each other

## Implementation Steps

1. Install new Proxmox (192.168.30.100)
2. Configure VLAN 30 on Proxmox
3. Create LXC templates for Cyantula
4. Deploy cyantula-tenant-portal (with reverse proxy)
5. CI/CD creates tenant LXCs automatically
