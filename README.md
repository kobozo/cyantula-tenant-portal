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
   ├── DNS routing
   └── Email service
   
   ├───▶ Cyantula Installatie A (voor Organisatie X)
   ├───▶ Cyantula Installatie B (voor Organisatie Y)
   └───▶ Cyantula Shared (demo's, fallback)
```

## Features

- ✅ Organisation onboarding
- ✅ Automatic provisioning per tenant
- ✅ DNS-based routing
- ✅ Setup token generation
- ✅ Email notifications
- ✅ Observability (logging, metrics)

## Tech Stack

- **Backend:** Python 3.12+, FastAPI
- **Database:** PostgreSQL
- **Provisioning:** Docker Compose, Docker SDK
- **DNS:** Cloudflare API (configurable)
- **Email:** SMTP (configurable)
- **Monitoring:** Prometheus, Structlog

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Repository Structure

```
cyantula-tenant-portal/
├── api/              # FastAPI endpoints
├── provisioning/     # Docker Compose provisioning
├── dns/              # DNS registration
├── email/            # Email service
├── observability/    # Logging, metrics
├── database/         # Database models
├── tests/            # Integration tests
├── docker-compose.yml
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
```

## License

MIT
