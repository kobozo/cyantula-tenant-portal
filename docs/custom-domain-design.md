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

Customer domain: `sintrembert.be`

Tenant wants:
- Portal app: `portal.sintrembert.be` (their main branded entry point)
- Analytics app: `analytics.sintrembert.be`
- CRM app: `crm.sintrembert.be`

## DNS Setup

**Option 1: Per-app CNAME (Current Cyantula pattern)**

```
Customer DNS:
portal.be       CNAME    → portal.sintrembert.cyantula.eu
analytics.be    CNAME    → analytics.sintrembert.cyantula.eu
crm.be          CNAME    → crm.sintrembert.cyantula.eu

Proxmox DNS:
portal.sintrembert.cyantula.eu       A    → Tunnel
analytics.sintrembert.cyantula.eu    A    → Tunnel
crm.sintrembert.cyantula.eu          A    → Tunnel
```

**Option 2: Base Domain Wildcard**

```
Customer DNS:
*.sintrembert.be    CNAME    → sintrembert.cyantula.eu

Proxmox DNS:
sintrembert.cyantula.eu    A    → Tunnel
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
           ├── portal.sintrembert.be → 192.168.30.10:443 (Tenant A, "portal" app)
           ├── analytics.be → 192.168.30.10:443 (Tenant A, "analytics" app)
           ├── analytics.sintrembert.be → 192.168.30.10:443 (Tenant A, "analytics" app)
           └── *.cyantula.eu → Tenant routing
```

## How It Works

### Custom Domain per App

```
1. Tenant creates app named "portal"
2. Tenant adds custom domain: portal.be
3. System creates: portal.be → portal.sintrembert.cyantula.eu
4. Customer adds DNS: portal.be CNAME portal.sintrembert.cyantula.eu
5. Traffic: portal.be → Tenant A's "portal" app
```

### Base Domain Wildcard

```
1. Tenant registers sintrembert.be as base domain
2. System creates: *.sintrembert.be → sintrembert.cyantula.eu
3. Customer adds DNS: *.sintrembert.be CNAME sintrembert.cyantula.eu
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
    
    # Pattern 2: <<app>>.sintrembert.be (custom subdomain)
    if ($host ~* ^(.+)\.sintrembert\.be$) {
        set $app_slug $1;
        set $tenant_slug "sintrembert";  # Base domain tenant
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
    base_domain VARCHAR(255),  # For base domains like sintrembert.be
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
  "target": "portal.sintrembert.cyantula.eu",
  "record": "portal.be  CNAME  portal.sintrembert.cyantula.eu"
}

# For base domain:
{
  "hostname": "sintrembert.be",
  "type": "CNAME",
  "target": "sintrembert.cyantula.eu",
  "is_base_domain": true,
  "record": "*.sintrembert.be  CNAME  sintrembert.cyantula.eu"
}
```

## Routing Examples

| Host Header | Tenant Slug | App Slug | Tenant IP | Description |
|-------------|-------------|----------|-----------|-------------|
| `portal.be` | `portal` | `portal` | 192.168.30.10 | Tenant A's portal app |
| `portal.sintrembert.be` | `sintrembert` | `portal` | 192.168.30.20 | Tenant B's portal app |
| `analytics.sintrembert.be` | `sintrembert` | `analytics` | 192.168.30.20 | Tenant B's analytics app |
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
