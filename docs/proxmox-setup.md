# Proxmox & Architecture Setup

## Cloudflare Tunnel Architecture

```
Internet
   │
   ▼
Cloudflare (DNS + Argo Tunnel)
   │
   ├── cyantula.eu ──────┐
   │                     │
   ├── portal.cyantula.eu ──────────→ Tunnel → 192.168.30.100:8000 (Portal API)
   │
   ├── *.cyantula.eu ────────────────→ Tunnel → 192.168.30.100:8080 (Reverse Proxy)
   │                                 │
   │                                 └── Routes to tenant LXCs
   │                                     ├── tenant-a.cyantula.eu → 192.168.30.10:443
   │                                     └── tenant-b.cyantula.eu → 192.168.30.20:443
   │
   └── www.cyantula.eu ──────────────→ existing-website.com (geen tunnel, oude website)
```

## Cloudflare DNS Setup

```dns
cyantula.eu           CNAME   → portal.cyantula.eu (tunnel)
www.cyantula.eu       A       → existing-website-ip (geen tunnel)
portal.cyantula.eu    A       → Tunnel
*.cyantula.eu         A       → Tunnel
```

## Cloudflare Tunnel Configuration

Install `cloudflared` on Proxmox (192.168.30.100):

```bash
# Install
curl -L https://bin.equinox.io/c/bNyj1mQVY4c/cloudflared-linux-amd64.tar.gz -o cloudflared.tar.gz
tar xzvf cloudflared.tar.gz
sudo cp cloudflared /usr/local/bin/

# Login
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create cyantula-portal
```

### Tunnel Config (`~/.cloudflared/config.yml`)

```yaml
tunnel: cyantula-portal
credentials-file: /home/user/.cloudflared/cyantula-portal.json

ingress:
  # www.cyantula.eu → existing website (geen tunnel)
  - hostname: www.cyantula.eu
    service: https://existing-website-ip:443
  
  # cyantula.eu en portal.cyantula.eu → portal
  - hostname: cyantula.eu
    service: http://127.0.0.1:8000
  - hostname: portal.cyantula.eu
    service: http://127.0.0.1:8000
  
  # *.cyantula.eu → reverse proxy
  - hostname: "*.cyantula.eu"
    service: http://127.0.0.1:8080
  
  - service: http_status:404
```

### Run Tunnel

```bash
cloudflared tunnel run cyantula-portal
```

## Reverse Proxy Configuration

NGINX op Proxmox (192.168.30.100) op poort 8080:

```nginx
upstream tenant_a {
    server 192.168.30.10:443;
}

upstream tenant_b {
    server 192.168.30.20:443;
}

server {
    listen 8080;
    
    # Tenant routing
    location ~ ^/(?<tenant>.+)\.cyantula\.eu(/.*)?$ {
        proxy_pass https://$tenant;
        proxy_set_header Host $host;
        proxy_ssl_verify off;
    }
    
    # Default to portal
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

## Complete Flow

```
User visits:
├─ cyantula.eu → Cloudflare Tunnel → 192.168.30.100:8000 → Portal
├─ portal.cyantula.eu → Cloudflare Tunnel → 192.168.30.100:8000 → Portal
├─ tenant-a.cyantula.eu → Cloudflare Tunnel → 192.168.30.100:8080 → 192.168.30.10:443
└─ www.cyantula.eu → existing website (geen tunnel)

Port numbers:
├─ Portal API: 8000 (internal)
├─ Reverse Proxy: 8080 (internal)
└─ Tenant instances: 443 (HTTPS)
```

## Benefits

1. **www.cyantula.eu** blijft bestaande website
2. **cyantula.eu/portal** → nieuwe portal
3. **Tenants** → `*.cyantula.eu` routing
4. **Geen forwarding** - Cloudflare regelt alles
5. **Volledige isolatie** - VLAN 30

## DNS in Cloudflare (samenvatting)

| Record | Type | Value | Purpose |
|--------|------|-------|---------|
| cyantula.eu | CNAME | portal.cyantula.eu | Portal main domain |
| www.cyantula.eu | A | existing-website-ip | Oude website |
| portal.cyantula.eu | A | Tunnel | Portal API |
| *.cyantula.eu | A | Tunnel | Tenant routing |

## Implementation Steps

1. Proxmox installeren (192.168.30.100)
2. cloudflared installeren en tunnel configureren
3. DNS records aanmaken in Cloudflare
4. Reverse proxy configureren
5. Portal en CI/CD deployen
