# Cyantula Tenant Portal - Implementation Plan

## Current State

### ✅ Completed:
- Custom domain API endpoints (FastAPI)
- Database models (Tenant, CustomDomain)
- DNS registration (Cloudflare API)
- CNAME verification logic
- Reverse proxy config generation (NGINX/Caddy)
- Tests (23 passing)

### ⚠️ Partially Completed:
- Setup token field in Tenant model (but no implementation)
- Base domain field in Tenant model (but no implementation)

### ❌ Not Started:
- Proxmox API integration (LXC creation)
- Tenant onboarding flow
- Setup token generation & validation
- Email service
- Database migrations (Alembic)
- Reverse proxy deployment automation
- CI/CD pipeline

## Implementation Priority

### Phase 1: MVP Core (Critical) - **START HERE**

| Feature | Priority | Est. Time | Dependencies | Status |
|---------|----------|-----------|--------------|--------|
| Proxmox API client | Critical | 2 days | None | ❌ Not started |
| LXC provisioning | Critical | 2 days | Proxmox client | ❌ Not started |
| Tenant onboarding API | Critical | 1 day | LXC provisioning | ❌ Not started |
| Setup token generation | Critical | 1 day | None | ⚠️ Model exists, not implemented |
| Database migrations (Alembic) | Critical | 1 day | None | ❌ Not started |

**Total Phase 1:** 7 days

### Phase 2: DNS & Security (High Priority)

| Feature | Priority | Est. Time | Dependencies | Status |
|---------|----------|-----------|--------------|--------|
| Cloudflare DNS automation | High | 1 day | Cloudflare client | ✅ Client exists |
| SSL certificate management | High | 2 days | DNS automation | ❌ Not started |
| Reverse proxy deployment | High | 2 days | LXC + DNS | ❌ Not started |
| Email notifications | High | 1 day | None | ❌ Not started |
| Health check endpoints | High | 0.5 day | None | ❌ Not started |

**Total Phase 2:** 6.5 days

### Phase 3: Production Ready (Medium Priority)

| Feature | Priority | Est. Time | Dependencies | Status |
|---------|----------|-----------|--------------|--------|
| CI/CD pipeline | Medium | 3 days | None | ❌ Not started |
| Observability (logging/metrics) | Medium | 1 day | None | ❌ Not started |
| Environment configuration | Medium | 0.5 day | None | ⚠️ Partial (.env.example exists) |
| Documentation | Medium | 1 day | None | ⚠️ README exists, needs expansion |

**Total Phase 3:** 5.5 days

### Phase 4: Advanced Features (Nice to Have)

| Feature | Priority | Est. Time | Dependencies | Status |
|---------|----------|-----------|--------------|--------|
| Multi-region support | Low | 3 days | Phase 3 | ❌ Not started |
| Analytics dashboard | Low | 2 days | Phase 3 | ❌ Not started |
| API rate limiting | Low | 1 day | Phase 2 | ❌ Not started |
| Custom branding per tenant | Low | 2 days | Phase 3 | ❌ Not started |

**Total Phase 4:** 8 days

## Timeline Summary

| Phase | Duration | Deliverables | Risk Level |
|-------|----------|--------------|------------|
| Phase 1 (MVP) | 7 days | Working tenant onboarding + LXC creation | 🔴 High |
| Phase 2 (DNS/Security) | 6.5 days | Full DNS + SSL + email | 🟡 Medium |
| Phase 3 (Production) | 5.5 days | CI/CD + monitoring | 🟢 Low |
| Phase 4 (Advanced) | 8 days | Advanced features | 🟢 Low |

**Total MVP (Phases 1-2):** 13.5 days
**Total Production (Phases 1-3):** 19 days

## Technical Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Tenant Portal API                    │
│              (FastAPI - port 8000)                      │
│  - Tenant registration                                  │
│  - Setup token generation                               │
│  - Custom domain management                             │
│  - DNS record creation                                  │
└───────────────────────────────┬─────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │               PostgreSQL Database             │
        │           (tenants, custom_domains)           │
        └───────────────────────┬───────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │         Proxmox API (VLAN 30)                 │
        │      Create LXC containers (192.168.30.x)     │
        └───────────────────────┬───────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │          Cloudflare Tunnel                    │
        │         (cloudflared)                         │
        │  Routes: *.cyantula.eu → Tenant LXCs         │
        └───────────────────────────────────────────────┘
```

## Critical Path Analysis

### Risk 1: Proxmox API Integration (HIGH)
**Issue:** No Proxmox client exists yet
**Mitigation:** 
- Use `requests` library for API calls
- Create simple wrapper for LXC operations
- Test against dev Proxmox instance first

### Risk 2: LXC Network Configuration (HIGH)
**Issue:** VLAN 30 setup, network isolation
**Mitigation:**
- Pre-configure VLAN on Proxmox host
- Use Proxmox API for network device addition
- Document network requirements clearly

### Risk 3: SSL Certificate Management (MEDIUM)
**Issue:** Let's Encrypt rate limits, wildcard certs
**Mitigation:**
- Use Cloudflare SSL if possible
- Implement certificate caching
- Add retry logic with exponential backoff

### Risk 4: Setup Flow Complexity (MEDIUM)
**Issue:** Connecting LXC creation → setup token → tenant setup
**Mitigation:**
- Simple token-based setup first
- No complex validation until MVP works
- Incremental improvements after MVP

## Next Steps (Recommended Order)

1. **Week 1: Phase 1 Core**
   - [ ] Set up Alembic for migrations
   - [ ] Implement Proxmox API client
   - [ ] Create LXC provisioning endpoint
   - [ ] Implement setup token generation

2. **Week 2: Phase 2 DNS & Security**
   - [ ] Cloudflare DNS automation
   - [ ] SSL certificate management
   - [ ] Email notifications
   - [ ] Health check endpoints

3. **Week 3: Testing & Polish**
   - [ ] End-to-end test (tenant onboarding)
   - [ ] Error handling & edge cases
   - [ ] Documentation
   - [ ] CI/CD pipeline

## Open Questions

1. **Proxmox API authentication:** Token-based (recommended) vs password?
2. **Database migrations:** Alembic vs SQLAlchemy create_all() for MVP?
3. **Email provider:** SMTP relay vs SendGrid vs Mailgun?
4. **Reverse proxy:** NGINX (manual) vs Caddy (auto-SSL) vs Traefik?
5. **LXC template:** Use Proxmox template or create custom one?

## Recommended Initial Action

**Start with Proxmox API client + basic LXC provisioning:**
```python
# New file: proxmox/client.py
import requests

class ProxmoxClient:
    def __init__(self, api_url: str, token: str):
        self.api_url = api_url
        self.headers = {"Authorization": f"PVEAPIToken={token}"}
    
    def create_lxc(self, node: str, vmid: int, config: dict):
        # POST /nodes/{node}/lxc
        pass
    
    def start_lxc(self, node: str, vmid: int):
        # POST /nodes/{node}/lxc/{vmid}/status/start
        pass
```

Then build the onboarding flow around it.