# Custom Domain Routing Design

## Architecture Overview

Cyantula has **two types of portals**:

### 1. Main Portal (Shared)
- URL: `portal.cyantula.eu`
- Purpose: Shared admin/user interface for ALL tenants
- Sign-in, app management, dashboard (shared across platform)

### 2. Tenant Apps (Per Tenant)
- Each tenant can have multiple apps
- Apps accessed via: `<<appname>>.<<tenantdomain>>.be`
- Custom domains point to specific apps

## Scenario

Customer domain: `acme.be`

Tenant wants:
- Portal app: `portal.acme.be` (their main branded entry point)
- Analytics app: `analytics.acme.be`
- CRM app: `crm.acme.be`

## DNS Setup

**Option 1: Per-app CNAME (Current Cyantula pattern)**

```
Customer DNS:
portal.be       CNAME    → portal.acme.cyantula.eu
analytics.be    CNAME    → analytics.acme.cyantula.eu
crm.be          CNAME    → crm.acme.cyantula.eu

Proxmox DNS:
portal.acme.cyantula.eu       A    → Tunnel
analytics.acme.cyantula.eu    A    → Tunnel
crm.acme.cyantula.eu          A    → Tunnel
```

**Option 2: Base Domain Wildcard**

```
Customer DNS:
*.acme.be    CNAME    → acme.cyantula.eu

Proxmox DNS:
acme.cyantula.eu    A    → Tunnel
```

## Architecture

```
Internet
   │
   ▼
Cloudflare Tunnel (cloudflared on Proxmox)
   │
   ├── portal.cyantula.eu → Main Portal UI (shared)
   │
   └── *.cyantula.eu → Reverse Proxy
       │
       └── Routes to tenant LXCs based on Host header
           ├── portal.be → 192.168.30.10:443 (Tenant A, "portal" app)
           ├── portal.acme.be → 192.168.30.10:443 (Tenant A, "portal" app)
           ├── analytics.be → 192.168.30.10:443 (Tenant A, "analytics" app)
           ├── analytics.acme.be → 192.168.30.10:443 (Tenant A, "analytics" app)
           └── *.cyantula.eu → Tenant routing
```

## How It Works

### Custom Domain per App

```
1. Tenant creates app named "portal"
2. Tenant adds custom domain: portal.be
3. System creates: portal.be → portal.acme.cyantula.eu
4. Customer adds DNS: portal.be CNAME portal.acme.cyantula.eu
5. Traffic: portal.be → Tenant A's "portal" app
```

### Base Domain Wildcard

```
1. Tenant registers acme.be as base domain
2. System creates: *.acme.be → acme.cyantula.eu
3. Customer adds DNS: *.acme.be CNAME acme.cyantula.eu
4. All subdomains route to tenant (app selection via path or subdomain routing)
```

## Reverse Proxy Logic

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
    
    # Extract app/tenant from host
    set $tenant_slug "";
    set $app_slug "";
    
    # Pattern 1: <<app>>.be (custom domain per app)
    if ($host ~* ^(.+)\.be$) {
        set $app_slug $1;
        set $tenant_slug $1;  # Same as app for this pattern
    }
    
    # Pattern 2: <<app>>.acme.be (custom subdomain)
    if ($host ~* ^(.+)\.acme\.be$) {
        set $app_slug $1;
        set $tenant_slug "acme";  # Base domain tenant
    }
    
    # Pattern 3: <<tenant>>.cyantula.eu (default)
    if ($host ~* ^(.+)\.cyantula\.eu$) {
        set $tenant_slug $1;
    }
    
    # Route to tenant
    location @route_tenant {
        # Database lookup: SELECT ip FROM tenants WHERE slug = $tenant_slug
        proxy_pass https://$tenant_ip;
        proxy_set_header Host $host;
    }
}
```

## Database Schema

```sql
CREATE TABLE tenant_custom_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    hostname VARCHAR(255) UNIQUE NOT NULL,
    app_slug VARCHAR(255),  # For per-app domains like <<app>>.be
    base_domain VARCHAR(255),  # For base domains like acme.be
    is_base_domain BOOLEAN DEFAULT FALSE,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    cert_status VARCHAR(50),
    cf_hostname_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenant_custom_domain_base ON tenant_custom_domains(base_domain);
```

## Portal API

```python
# /api/tenants/:id/custom-domains
POST   # Add custom domain
GET    # List custom domains
DELETE # Remove custom domain
POST   # Check CNAME verification

# For per-app domain:
{
  "hostname": "portal.be",
  "type": "CNAME",
  "target": "portal.acme.cyantula.eu",
  "record": "portal.be  CNAME  portal.acme.cyantula.eu"
}

# For base domain:
{
  "hostname": "acme.be",
  "type": "CNAME",
  "target": "acme.cyantula.eu",
  "is_base_domain": true,
  "record": "*.acme.be  CNAME  acme.cyantula.eu"
}
```

## Routing Examples

| Host Header | Tenant Slug | App Slug | Tenant IP | Description |
|-------------|-------------|----------|-----------|-------------|
| `portal.be` | `portal` | `portal` | 192.168.30.10 | Tenant A's portal app |
| `portal.acme.be` | `acme` | `portal` | 192.168.30.20 | Tenant B's portal app |
| `analytics.acme.be` | `acme` | `analytics` | 192.168.30.20 | Tenant B's analytics app |
| `portal.cyantula.eu` | `portal` | `portal` | 192.168.30.100 | Main shared portal UI |
| `analytics.be` | `analytics` | `analytics` | 192.168.30.10 | Tenant A's analytics app |

## Benefits

1. **Simple DNS**: Customer adds CNAME (per-app or wildcard)
2. **Cert automation**: Individual or wildcard certificates via Cloudflare/Let's Encrypt
3. **Same pattern as Cyantula**: Uses existing custom domain mechanism
4. **Session handling**: `/__spin/claim` for cookies
5. **No special routing**: Custom domains point to apps - same as existing

## Security

- CNAME verification ensures domain ownership
- Session forwarding via `/__spin/claim` for cookies
- Reverse proxy only routes verified domains
- TLS termination before tenant app

## Implementation Steps

1. Tenant onboards → creates LXC container
2. Tenant creates apps (portal, analytics, etc.)
3. Tenant adds custom domains for each app
4. Portal verifies CNAMEs and registers with Cloudflare
5. Reverse proxy routes based on Host header
6. Traffic reaches correct app in tenant LXC
