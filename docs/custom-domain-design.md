# Custom Domain Routing Design

## Scenario

Customer has domain: `sintrembert.be`

Apps are accessed via: `<<appname>>.sintrembert.be`

Examples:
- `portal.sintrembert.be`
- `analytics.sintrembert.be`
- `dashboard.sintrembert.be`

## Existing Cyantula Pattern

Cyantula already supports this pattern:

```
1. Customer creates wildcard CNAME:
   *.sintrembert.be  CNAME  → cyantula.eu (or portal.cyantula.eu)

2. Cyantula checks CNAME for <<appname>>.sintrembert.be

3. Certificate automation:
   - Cloudflare: API-based wildcard certificate
   - Caddy: Let's Encrypt on-demand

4. Session forwarding via /__spin/claim for cookies
```

## Tenant Portal Implementation

### DNS Setup

```
Customer DNS (at any DNS host):
*.sintrembert.be    CNAME    → tenant-a.cyantula.eu

Cloudflare Tunnel DNS:
tenant-a.cyantula.eu    A    → Tunnel
```

### Architecture

```
Internet
   │
   ▼
Cloudflare Tunnel (cloudflared on Proxmox)
   │
   ├── portal.cyantula.eu → Portal API
   │
   └── *.cyantula.eu → Reverse Proxy
       │
       └── Routes to tenant LXCs based on Host header
           ├── portal.sintrembert.be → 192.168.30.10:443 (Tenant A)
           ├── analytics.sintrembert.be → 192.168.30.10:443 (Tenant A)
           ├── app1.sintrembert.be → 192.168.30.10:443 (Tenant A)
           └── tenant-b.cyantula.eu → 192.168.30.20:443 (Tenant B)
```

### Reverse Proxy Logic

NGINX config:

```nginx
# Reverse proxy on port 8080
upstream tenant_a {
    server 192.168.30.10:443;
}

upstream tenant_b {
    server 192.168.30.20:443;
}

server {
    listen 8080;
    
    # Extract tenant from Host header
    # portal.sintrembert.be → tenant_a
    # analytics.sintrembert.be → tenant_a
    # app1.sintrembert.be → tenant_a
    set $tenant_slug $host;
    
    # Remove .sintrembert.be to get tenant identifier
    if ($host ~* ^(.+)\.sintrembert\.be$) {
        set $tenant_slug $1;
    }
    
    # Map tenant slug to IP
    location @tenant_route {
        proxy_pass https://$tenant_ip;
        proxy_set_header Host $host;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### Portal Database

```sql
CREATE TABLE tenant_custom_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    base_domain VARCHAR(255) NOT NULL,  -- sintrembert.be
    wildcard_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    cert_status VARCHAR(50),
    cf_hostname_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenant_custom_domain_base ON tenant_custom_domains(base_domain);
```

### Portal API

```python
# /api/tenants/:id/custom-domains
POST   # Add custom domain (base domain)
GET    # List custom domains
DELETE # Remove custom domain
POST   # Check CNAME verification

# Instructions for customer:
{
  "hostname": "*.sintrembert.be",
  "type": "CNAME",
  "target": "tenant-a.cyantula.eu",
  "record": "*.sintrembert.be  CNAME  tenant-a.cyantula.eu"
}
```

## How It Works

1. **Customer registers domain**: `sintrembert.be` in portal
2. **Portal creates wildcard CNAME**: `*.sintrembert.be` → `tenant-a.cyantula.eu`
3. **Customer adds DNS**: `*.sintrembert.be` CNAME record
4. **Portal verifies**: CNAME check for any `*.sintrembert.be`
5. **Certificate**: Wildcard cert for `*.sintrembert.be`
6. **Traffic routing**:
   - `portal.sintrembert.be` → Tenant A LXC
   - `analytics.sintrembert.be` → Tenant A LXC
   - `app1.sintrembert.be` → Tenant A LXC

## Reverse Proxy Logic (Detailed)

```nginx
server {
    listen 8080;
    
    # Extract tenant from host
    set $tenant_slug "";
    
    # Pattern 1: *.cyantula.eu (tenant subdomain)
    if ($host ~* ^(.+)\.cyantula\.eu$) {
        set $tenant_slug $1;
    }
    
    # Pattern 2: *.sintrembert.be (custom domain)
    if ($host ~* ^(.+)\.sintrembert\.be$) {
        set $tenant_slug $1;
    }
    
    # Lookup tenant IP from database based on slug
    location @route_tenant {
        # Database lookup: SELECT ip FROM tenants WHERE slug = $tenant_slug
        proxy_pass https://$tenant_ip;
        proxy_set_header Host $host;
    }
}
```

## Portal Workflow

1. Tenant registers `sintrembert.be`
2. Portal stores `base_domain = sintrembert.be`
3. Portal generates instructions for `*.sintrembert.be` CNAME
4. Customer adds DNS record
5. Portal verifies CNAME (any subdomain works)
6. Portal registers wildcard with Cloudflare API
7. Reverse proxy routes all `*.sintrembert.be` to tenant

## Benefits

1. **Wildcard DNS**: One CNAME for all apps
2. **Same pattern as Cyantula**: Customer familiar with this
3. **Cert automation**: Wildcard certificate for base domain
4. **Flexible routing**: Portal controls which tenant handles which host
5. **Verification**: CNAME check ensures domain ownership

## Security

- CNAME verification for `*.domain` ensures ownership
- Session forwarding via `/__spin/claim` for cookies
- Reverse proxy only routes verified domains
- TLS termination before tenant app
