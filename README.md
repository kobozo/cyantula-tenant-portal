# Cyantula Tenant Portal

Multi-tenant portal for Cyantula - handles organisation onboarding, provisioning, and DNS routing.

## Architecture

```
Internet
   │
   ▼
 Tenant Portal (NEW - Python/FastAPI)
    ├── Organisation onboarding
    ├── Provisioning (Docker Compose)
    ├── DNS routing (Cloudflare API)
    ├── Custom domain management
    └── Email service
    
    ├───▶ Tenant A (LXC on VLAN 30 - 192.168.30.10)
    ├───▶ Tenant B (LXC on VLAN 30 - 192.168.30.20)
    └─▶ Shared Portal (portal.cyantula.eu)
```

## Features

- ✅ Organisation onboarding
- ✅ Automatic LXC provisioning on Proxmox VLAN 30
- ✅ Custom domain management (<<app>>.be → <<app>>.tenant.cyantula.eu)
- ✅ Base domain wildcard support (*.tenant.be)
- ✅ DNS registration via Cloudflare API
- ✅ CNAME verification for domain ownership
- ✅ SSL certificate management
- ✅ Reverse proxy configuration generation
- ✅ Email notifications
- ✅ Observability (logging, metrics)

## Tech Stack

- **Backend:** Python 3.12+, FastAPI
- **Database:** PostgreSQL
- **Provisioning:** Docker SDK, Proxmox API
- **DNS:** Cloudflare API (configurable)
- **Email:** SMTP (configurable)
- **Monitoring:** Prometheus, Structlog
- **Proxy:** NGINX/Caddy (configurable)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run with Docker Compose
docker-compose up --build
```

## Custom Domain Routing

The portal supports two routing patterns:

### Pattern 1: Per-App Custom Domains

```
Customer domain: acme.be

Apps accessed via:
- portal.be → Tenant A's portal app (192.168.30.10)
- analytics.be → Tenant A's analytics app (192.168.30.10)
- crm.be → Tenant A's CRM app (192.168.30.10)

DNS setup:
portal.be       CNAME → portal.acme.cyantula.eu
analytics.be    CNAME → analytics.acme.cyantula.eu
crm.be          CNAME → crm.acme.cyantula.eu
```

### Pattern 2: Base Domain Wildcard

```
Customer domain: acme.be

Apps accessed via:
- portal.acme.be → Tenant A (192.168.30.10)
- analytics.acme.be → Tenant A (192.168.30.10)

DNS setup:
*.acme.be    CNAME → acme.cyantula.eu
```

## API Endpoints

### Custom Domains

- `POST /api/custom-domains` - Create a new custom domain
- `GET /api/custom-domains` - List all custom domains
- `GET /api/custom-domains/{domain_id}` - Get a specific custom domain
- `DELETE /api/custom-domains/{domain_id}` - Delete a custom domain
- `POST /api/custom-domains/{domain_id}/verify` - Verify CNAME record
- `GET /api/custom-domains/{domain_id}/instructions` - Get DNS configuration instructions

## Repository Structure

```
cyantula-tenant-portal/
├── api/              # FastAPI endpoints
│   ├── __init__.py
│   └── custom_domains.py
├── database/         # Database models and schema
│   ├── __init__.py
│   └── models.py
├── dns/              # DNS registration and verification
│   ├── __init__.py
│   ├── cname_check.py
│   └── cloudflare.py
├── proxy/            # Reverse proxy configuration
│   ├── __init__.py
│   └── config.py
├── email/            # Email service
├── observability/    # Logging, metrics
├── tests/            # Integration tests
├── docker-compose.yml
├── Dockerfile
├── main.py
└── README.md
```

## Development

```bash
# Run tests
pytest

# Lint
ruff check .

# Format
ruff format .

# Type check
mypy .
```

## License

MIT
