# Deployment Guide - Cyantula Multi-Tenant

## Overview

This guide covers deploying the multi-tenant infrastructure for Cyantula.

## Architecture

```
Productivity Server (192.168.1.240)
  ├── Cybera / existing apps
  └── VLAN 30 interface

Proxmox Server (192.168.3.211) - VLAN 30
  ├── Tenant API (port 8000)
  │   └── Cloudflare Tunnel → api.cyantula.eu
  └── LXC Containers (VM IDs 100+)
      ├── Tenant A (192.168.3.101)
      ├── Tenant B (192.168.3.102)
      └── ...
```

## Pre-requisites

- Proxmox server (192.168.3.211) with VLAN 30 configured
- Cloudflare account with `cyantula.eu` zone
- SSH access to Proxmox server
- Docker access to Cyantula server

## Steps

### 1. Tenant API Deployment

The Tenant API is already deployed on the Proxmox server:
- Service: `tenant-api.service`
- API: `http://192.168.3.211:8000`
- Tunnel: `https://api.cyantula.eu`

### 2. Cyantula Server Setup

```bash
# On Cyantula server
cd /home/yannick/cyantula/server

# Generate Prisma client
npx -y prisma@6 generate

# Create and run migration
npx -y prisma@6 migrate dev --name add_tenant_support
npx -y prisma@6 migrate deploy
```

### 3. Add Proxmox Server to Cyantula

```sql
-- In Cyantula database
INSERT INTO "Server" (
  id, name, type, status, address, port, acceptsNew, createdAt, updatedAt,
  proxmoxNode, proxmoxApiUrl, lxcVmidBase
) VALUES (
  gen_random_uuid(),
  'kb-pvecyantula01',
  'PROXMOX_LXC',
  'ONLINE',
  '192.168.3.211',
  8006,
  true,
  NOW(),
  NOW(),
  'pve',
  'https://192.168.3.211:8006',
  100
);
```

### 4. Test Tenant Creation

```bash
curl -X POST https://api.cyantula.eu/api/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Tenant",
    "slug": "test123",
    "base_domain": "cyantula.eu"
  }'
```

### 5. Verify LXC Container

```bash
# On Proxmox server
pct list
# Should show: 10X - test123-tenant - RUNNING
```

## Troubleshooting

### Tenant API not starting

```bash
# Check service status
systemctl status tenant-api

# View logs
journalctl -u tenant-api -f
```

### Cloudflare Tunnel issues

```bash
# Check tunnel status
systemctl status cloudflared

# Restart tunnel
systemctl restart cloudflared
```

### LXC container creation fails

```bash
# Check Proxmox API
curl -k https://192.168.3.211:8006/api2/json/version \
  -H "Authorization: PVEAPIToken=root@pam!tenant-portal-full=06ef9479-3581-4386-beab-88291ff68584"

# Check SSH access
ssh root@192.168.3.211 'pct list'
```

## Cleanup

```bash
# Delete tenant (removes LXC container)
curl -X DELETE https://api.cyantula.eu/api/tenants/{slug}
```
