# Proxmox & Architecture Setup

## Physical Infrastructure

```
┌─────────────────────────────────────────────────────────────────┐
│  NEW Proxmox Server (192.168.30.100)                            │
│  VLAN 30 interface                                              │
│  ├─ LXC 100: cyantula-tenant-portal (management)              │
│  │   └─ IP: 192.168.30.100                                    │
│  ├─ LXC 101: tenant-a.cyantula.eu                              │
│  │   └─ IP: 192.168.30.10                                     │
│  ├─ LXC 102: tenant-b.cyantula.eu                              │
│  │   └─ IP: 192.168.30.20                                     │
│  └─ LXC 103: tenant-c.cyantula.com                            │
│      └─ IP: 192.168.30.30                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ VLAN 30
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  EXISTING Server (192.168.1.240) - PRODUCTION (NO CHANGES)     │
│  VLAN 30 interface (only for management access to new Proxmox) │
│  └─ Customer data stays here (unchanged)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Network Architecture

```
Internet
   │
   ▼
Firewall (OPNsense/router)
   │
   ├── VLAN 30: 192.168.30.0/24 (Tenant instances)
   │   ├── LXC 100: 192.168.30.100 (Portal - management)
   │   ├── LXC 101: 192.168.30.10 (Tenant A)
   │   ├── LXC 102: 192.168.30.20 (Tenant B)
   │   └── LXC 103: 192.168.30.30 (Tenant C)
   │
   └── VLAN 31: 192.168.31.0/24 (Management - optional)
       └─ LXC 100: 192.168.31.100 (Portal)
   
   └── VLAN 32: 192.168.1.0/24 (Production - EXISTING)
       └── 192.168.1.240 (Customer data - NO CHANGES)
```

## Firewall Rules

```bash
# Block tenant VLAN from accessing production
VLAN 30 → 192.168.1.0/24    DENY

# Block tenant-to-tenant communication
VLAN 30 → VLAN 30           DENY

# Allow portal to communicate with tenants (outbound only)
Portal (VLAN 30/31) → Tenants (VLAN 30)  ALLOW (management)
```

## Who Runs Where

| Component | Location | VM/LXC ID | IP | Notes |
|-----------|----------|-----------|-----|-------|
| **Cyantula Tenant Portal** | New Proxmox | LXC 100 | 192.168.30.100 | Management only |
| **Tenant A** | New Proxmox | LXC 101 | 192.168.30.10 | Cyantula instance |
| **Tenant B** | New Proxmox | LXC 102 | 192.168.30.20 | Cyantula instance |
| **Tenant C** | New Proxmox | LXC 103 | 192.168.30.30 | Cyantula instance |
| **Production Data** | Existing Server | N/A | 192.168.1.240 | **NO CHANGES** |

## Key Points

1. **ALL LXC containers run on the NEW Proxmox server**
2. **Existing server at 192.168.1.240 is untouched** - only has VLAN 30 interface for management access
3. **Tenant isolation:** VLAN 30 tenants cannot see each other
4. **Portal runs on NEW Proxmox** - not on production server

## VLAN 30 Communication Flow

```
Portal (192.168.30.100) ──outbound──► Tenant A (192.168.30.10)
Portal (192.168.30.100) ──outbound──► Tenant B (192.168.30.20)
Portal (192.168.30.100) ──outbound──► Tenant C (192.168.30.30)

Tenant A ──DENY──► Tenant B  (isolated)
Tenant B ──DENY──► Tenant C  (isolated)
```

## Implementation Steps

1. Install new Proxmox on VLAN 30 (192.168.30.100)
2. Configure firewall rules (block VLAN 30 → production)
3. Create LXC templates
4. Deploy cyantula-tenant-portal in LXC 100
5. CI/CD creates tenant LXCs as needed
