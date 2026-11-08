"""API endpoints for custom domain management."""
import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/api/custom-domains", tags=["custom-domains"])


# Pydantic models for requests/responses
class CustomDomainCreate(BaseModel):
    hostname: str = Field(..., description="The custom domain hostname (e.g., portal.be or *.sintrembert.be)")
    tenant_id: str = Field(..., description="Tenant identifier")
    base_domain: Optional[str] = Field(None, description="Base domain if using wildcard pattern")
    is_wildcard: bool = Field(default=False, description="Whether this is a wildcard domain")

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: str) -> str:
        # Basic hostname validation
        hostname_pattern = r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
        wildcard_pattern = r"^\*\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2,}$"
        
        if not re.match(hostname_pattern, v) and not re.match(wildcard_pattern, v):
            raise ValueError("Invalid hostname format")
        return v.lower()


class CustomDomainResponse(BaseModel):
    id: str
    hostname: str
    tenant_id: str
    base_domain: Optional[str]
    is_wildcard: bool
    verified: bool
    verified_at: Optional[str]
    cert_status: str
    cf_hostname_id: Optional[str]
    created_at: str


class DnsRecord(BaseModel):
    hostname: str
    type: str = "CNAME"
    target: str
    record: str


class CustomDomainInstructions(BaseModel):
    hostname: str
    type: str
    target: str
    accepted_targets: list[str]
    record: str


# Dummy database (will be replaced with actual DB later)
custom_domains_db: dict[str, dict] = {}


@router.post("", response_model=CustomDomainResponse)
async def create_custom_domain(data: CustomDomainCreate):
    """Create a new custom domain for a tenant."""
    domain_id = f"dom_{data.tenant_id}_{data.hostname.replace('.', '_')}"
    
    custom_domains_db[domain_id] = {
        "id": domain_id,
        "hostname": data.hostname,
        "tenant_id": data.tenant_id,
        "base_domain": data.base_domain,
        "is_wildcard": data.is_wildcard,
        "verified": False,
        "verified_at": None,
        "cert_status": "pending",
        "cf_hostname_id": None,
        "created_at": "2026-11-08T00:00:00Z",
    }
    
    return custom_domains_db[domain_id]


@router.get("", response_model=list[CustomDomainResponse])
async def list_custom_domains(tenant_id: Optional[str] = None):
    """List custom domains, optionally filtered by tenant."""
    if tenant_id:
        return [
            domain for domain in custom_domains_db.values()
            if domain["tenant_id"] == tenant_id
        ]
    return list(custom_domains_db.values())


@router.get("/{domain_id}", response_model=CustomDomainResponse)
async def get_custom_domain(domain_id: str):
    """Get a specific custom domain."""
    if domain_id not in custom_domains_db:
        raise HTTPException(status_code=404, detail="Custom domain not found")
    return custom_domains_db[domain_id]


@router.delete("/{domain_id}")
async def delete_custom_domain(domain_id: str):
    """Delete a custom domain."""
    if domain_id not in custom_domains_db:
        raise HTTPException(status_code=404, detail="Custom domain not found")
    del custom_domains_db[domain_id]
    return {"message": "Custom domain deleted"}


@router.post("/{domain_id}/verify", response_model=CustomDomainResponse)
async def verify_custom_domain(domain_id: str):
    """Verify a custom domain by checking CNAME."""
    if domain_id not in custom_domains_db:
        raise HTTPException(status_code=404, detail="Custom domain not found")
    
    domain = custom_domains_db[domain_id]
    
    # Simulate verification (will be replaced with actual CNAME check)
    # In production: check CNAME against cloudflared tunnel hostname
    domain["verified"] = True
    domain["verified_at"] = "2026-11-08T00:00:00Z"
    domain["cert_status"] = "active"
    
    return domain


@router.get("/{domain_id}/instructions", response_model=CustomDomainInstructions)
async def get_dns_instructions(domain_id: str):
    """Get DNS configuration instructions for a custom domain."""
    if domain_id not in custom_domains_db:
        raise HTTPException(status_code=404, detail="Custom domain not found")
    
    domain = custom_domains_db[domain_id]
    
    # Generate target hostname based on tenant
    tenant_id = domain["tenant_id"]
    target = f"{tenant_id}.cyantula.eu"
    
    return CustomDomainInstructions(
        hostname=domain["hostname"],
        type="CNAME",
        target=target,
        accepted_targets=[target],
        record=f"{domain['hostname']}  CNAME  {target}",
    )
