# Proxmox & Architecture Setup

## Cloudflare Tunnel Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  NEW Proxmox Server (192.168.30.100)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Cloudflare Tunnel (cloudflared)                        │   │
│  │  ├─ portal.cyantula.eu → 192.168.30.100:443            │   │
│  │  └─ *.cyantula.eu → 192.168.30.100:443 (Proxy)         │   │
│  │                                                           │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │  VLAN 30: Tenant Network                          │  │   │
│  │  │  ├─ LXC 100: Portal (192.168.30.100)              │  │   │
│  │  │  │   └─ NGINX/Traefik reverse proxy               │  │   │
│  │  │  │      └─ Routes *.cyantula.eu to tenant LXCs    │  │   │
│  │  │  │                                                 │  │   │
│  │  │  ├─ LXC 101: tenant-a.cyantula.eu (192.168.30.10) │  │   │
│  │  │  │   └─ Cyantula instance                         │  │   │
│  │  │  │                                                 │  │   │
│  │  │  ├─ LXC 102: tenant-b.cyantula.eu (192.168.30.20) │  │   │
│  │  │  │   └─ Cyantula instance                         │  │   │
│  │  │  │                                                 │  │   │
│  │  │  └─ LXC 103: tenant-c.cyantula.com (192.168.30.30)│  │   │
│  │  │      └─ Cyantula instance                         │  │   │
│  │  │                                                     │  │   │
│  │  │  └─ Tenant isolation (no inter-tenant comm)       │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

Internet
   │
   ▼
Cloudflare (DNS + Argo Tunnel)
   │
   ├── portal.cyantula.eu → Tunnel → 192.168.30.100
   │
   └── *.cyantula.eu → Tunnel → 192.168.30.100
       │
       └── Reverse proxy routes to tenant LXCs
```

## Your Setup (Minimal)

### 1. Cloudflare Tunnel on Proxmox

Install `cloudflared` on the Proxmox server (192.168.30.100):

```bash
# Install cloudflared
curl -L --cloudflare-access https://bin.equinox.io/c/bNyj1mQVY4c/cloudflared-linux-amd64.tar.gz -o cloudflared.tar.gz
tar xzvf cloudflared.tar.gz
sudo cp cloudflared /usr/local/bin/

# Login to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create cyantula-portal
```

### 2. Tunnel Configuration

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: cyantula-portal
credentials-file: /home/user/.cloudflared/cyantula-portal.json

ingress:
  - hostname: portal.cyantula.eu
    service: http://127.0.0.1:8000  # Portal API
  
  - hostname: "*.cyantula.eu"
    service: http://127.0.0.1:8080  # Reverse proxy
  
  - service: http_status:404
```

### 3. Run Tunnel

```bash
cloudflared tunnel run cyantula-portal
```

### 4. DNS in Cloudflare

```
portal.cyantula.eu    A    (tunnel)
*.cyantula.eu         A    (tunnel)
```

## Reverse Proxy on Proxmox

NGINX/Traefik routes to tenant LXCs:

```nginx
# NGINX config
upstream tenant_a {
    server 192.168.30.10:443;
}

upstream tenant_b {
    server 192.168.30.20:443;
}

server {
    listen 8080;
    server_name ~^(?<tenant>.+)\.cyantula\.eu$;
    
    location / {
        proxy_pass http://$tenant;
    }
}
```

## Benefits

1. **Zero network changes** - No port forwarding needed
2. **Cloudflare handles TLS** - Auto SSL certificates
3. **Full isolation** - All on one Proxmox, VLAN 30 only
4. **Secure** - Traffic stays within Cloudflare network
5. **Easy** - Just run `cloudflared tunnel`

## Who Runs Where

| Component | Proxmox | VLAN | IP | Access |
|-----------|---------|------|-----|--------|
| **Cloudflare Tunnel** | New Proxmox | VLAN 30 | 192.168.30.100 | portal.cyantula.eu, *.cyantula.eu |
| **Cyantula Portal** | New Proxmox | VLAN 30 | 192.168.30.100 | Internal: 8000 |
| **Reverse Proxy** | New Proxmox | VLAN 30 | 192.168.30.100 | Internal: 8080 |
| **Tenant A** | New Proxmox | VLAN 30 | 192.168.30.10 | 192.168.30.10:443 |
| **Tenant B** | New Proxmox | VLAN 30 | 192.168.30.20 | 192.168.30.20:443 |

## Implementation Steps

1. Install new Proxmox (192.168.30.100)
2. Install cloudflared on Proxmox
3. Create tunnel and configure DNS
4. Configure reverse proxy for tenant routing
5. Deploy cyantula-tenant-portal
6. CI/CD creates tenant LXCs
