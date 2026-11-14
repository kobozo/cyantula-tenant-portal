"""API endpoints for tenant management."""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database.models import Tenant, CustomDomain, Base
from proxmox.client import ProxmoxClient, ProxmoxConfig

router = APIRouter(prefix="/api/tenants", tags=["tenants"])

# Database session (will be properly injected later)
def get_db():
    """Get database session."""
    # This will be properly implemented with dependency injection
    raise NotImplementedError("Database session not yet configured")

# Proxmox client singleton
_proxmox_client: Optional[ProxmoxClient] = None

def get_proxmox_client() -> ProxmoxClient:
    """Get or create Proxmox client."""
    global _proxmox_client
    if _proxmox_client is None:
        _proxmox_client = ProxmoxClient(ProxmoxConfig.from_env())
    return _proxmox_client


# Pydantic models
class TenantCreate(BaseModel):
    """Request model for creating a tenant."""
    name: str = Field(..., description="Tenant display name")
    slug: str = Field(..., description="URL slug (unique, lowercase, hyphens only)")
    base_domain: Optional[str] = Field(None, description="Base domain (e.g., acme.org)")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format."""
        import re
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", v):
            raise ValueError("Slug must be lowercase, start/end with alphanumeric, allow hyphens")
        return v


class TenantResponse(BaseModel):
    """Response model for tenant."""
    id: str
    name: str
    slug: str
    base_domain: Optional[str]
    proxmox_ip: Optional[str]
    status: str
    setup_token: Optional[str]
    created_at: str


class SetupTokenResponse(BaseModel):
    """Response for setup token."""
    setup_token: str
    expires_at: str


class LXCConfig(BaseModel):
    """LXC container configuration."""
    vmid: int
    hostname: str
    cores: int = 2
    memory: int = 2048
    disk_size: int = 10
    password: Optional[str] = None
    ip: Optional[str] = None


# In-memory store for now (will be replaced with DB)
tenants_db: dict[str, dict] = {}


@router.post("", response_model=TenantResponse)
async def create_tenant(data: TenantCreate):
    """Create a new tenant with Proxmox LXC container."""
    # Check if slug already exists in Proxmox
    proxmox = get_proxmox_client()
    containers = proxmox.get_lxc_containers()
    for c in containers:
        if c.get("hostname") == f"{data.slug}-tenant":
            raise HTTPException(status_code=400, detail="Tenant with this slug already exists")
    
    # Find next available VM ID from Proxmox
    containers = proxmox.get_lxc_containers()
    vmid = proxmox.find_next_vmid()
    print(f"DEBUG: Found {len(containers)} containers, next VMID: {vmid}")
    
    # Generate setup token
    setup_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Create LXC container
    try:
        import traceback
        hostname = f"{data.slug}-tenant"
        result = proxmox.create_lxc_container(
            vmid=vmid,
            hostname=hostname,
            cores=data.slug.count("") % 4 + 1,  # Simple core allocation
            memory=2048,
            disk_size=10,
            password=secrets.token_hex(8),  # Use hex instead of urlsafe for simpler passwords
        )
        
        # Wait for container to start
        proxmox.wait_for_container(proxmox.config.node, vmid, status="running")
        
        # Install Cyantula in the container
        proxmox.install_cyantula(proxmox.config.node, vmid)
        
        # Get container IP
        config = proxmox.get_lxc_config(proxmox.config.node, vmid)
        net0 = config.get("net0", "")
        
        # Parse IP from net0 (format: name=eth0,bridge=vmbr0,ip=dhcp,gw=192.168.3.1)
        ip = None
        if "ip=" in net0:
            ip_part = net0.split("ip=")[1].split(",")[0]
            if ip_part != "dhcp":
                ip = ip_part
        
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create LXC container: {str(e)}\n\nTraceback:\n{tb}")
    
    # Store tenant
    tenant_id = f"tenant_{secrets.token_hex(8)}"
    
    # Get the actual IP address from the container
    if ip is None:
        config = proxmox.get_lxc_config(proxmox.config.node, vmid)
        net0 = config.get("net0", "")
        if "ip=" in net0:
            ip_part = net0.split("ip=")[1].split(",")[0]
            if ip_part != "dhcp":
                ip = ip_part
            else:
                # DHCP - need to check the actual IP from container
                # This will be populated later when the app is deployed
                ip = None
    
    tenant_data = {
        "id": tenant_id,
        "name": data.name,
        "slug": data.slug,
        "base_domain": data.base_domain,
        "proxmox_ip": ip,
        "proxmox_vmid": vmid,
        "status": "active",
        "setup_token": setup_token,
        "setup_token_expiry": expires_at.isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }
    
    tenants_db[data.slug] = tenant_data
    
    return tenant_data


@router.get("", response_model=list[TenantResponse])
async def list_tenants():
    """List all tenants."""
    return list(tenants_db.values())


@router.get("/{slug}", response_model=TenantResponse)
async def get_tenant(slug: str):
    """Get a specific tenant."""
    if slug not in tenants_db:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenants_db[slug]


@router.post("/{slug}/setup-token", response_model=SetupTokenResponse)
async def generate_setup_token(slug: str):
    """Generate a new setup token for a tenant."""
    if slug not in tenants_db:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant = tenants_db[slug]
    new_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    tenant["setup_token"] = new_token
    tenant["setup_token_expiry"] = expires_at.isoformat()
    
    return {"setup_token": new_token, "expires_at": expires_at.isoformat()}


@router.get("/setup-token/{token}")
async def validate_setup_token(token: str):
    """Validate a setup token and return tenant info."""
    for slug, tenant in tenants_db.items():
        if tenant.get("setup_token") == token:
            expires_at = datetime.fromisoformat(tenant["setup_token_expiry"])
            if datetime.utcnow() > expires_at:
                raise HTTPException(status_code=400, detail="Setup token has expired")
            return {
                "valid": True,
                "tenant_id": tenant["id"],
                "slug": tenant["slug"],
                "name": tenant["name"],
                "expires_at": tenant["setup_token_expiry"],
                "proxmox_ip": tenant.get("proxmox_ip"),
                "proxmox_vmid": tenant.get("proxmox_vmid"),
            }
    raise HTTPException(status_code=404, detail="Invalid setup token")


@router.delete("/{slug}")
async def delete_tenant(slug: str):
    """Delete a tenant and their LXC container."""
    if slug not in tenants_db:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant = tenants_db[slug]
    proxmox = get_proxmox_client()
    
    # Delete LXC container
    vmid = tenant.get("proxmox_vmid")
    if vmid:
        try:
            proxmox.delete_lxc_container(proxmox.config.node, vmid)
        except Exception as e:
            # Log warning but continue with deletion
            print(f"Warning: Failed to delete LXC {vmid}: {str(e)}")
    
    # Delete tenant
    del tenants_db[slug]
    
    return {"message": "Tenant deleted"}
