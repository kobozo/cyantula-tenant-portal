"""Database models for tenants and custom domains."""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Tenant(Base):
    """Tenant configuration and LXC container information."""
    __tablename__ = "tenants"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default="gen_random_uuid()",
        comment="Unique identifier for the tenant"
    )
    
    name = Column(
        String(255),
        nullable=False,
        comment="Tenant display name"
    )
    
    slug = Column(
        String(255),
        unique=True,
        nullable=False,
        comment="Tenant URL slug (e.g., acme)"
    )
    
    base_domain = Column(
        String(255),
        nullable=True,
        comment="Base domain for tenant (e.g., acme.be)"
    )
    
    proxmox_ip = Column(
        String(15),
        nullable=False,
        comment="IP address of tenant's LXC container on VLAN 30"
    )
    
    proxmox_port = Column(
        Integer,
        default=443,
        comment="Port for tenant's LXC container (default: 443 for HTTPS)"
    )
    
    status = Column(
        String(50),
        default="provisioning",
        comment="Tenant status: provisioning, active, suspended, deleted"
    )
    
    setup_token = Column(
        String(255),
        nullable=True,
        comment="Token for initial setup flow"
    )
    
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        comment="When the tenant was created"
    )
    
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="When the tenant was last updated"
    )
    
    # Relationships
    custom_domains = relationship("CustomDomain", back_populates="tenant")


class CustomDomain(Base):
    """Custom domain configuration for a tenant."""
    __tablename__ = "tenant_custom_domains"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default="gen_random_uuid()",
        comment="Unique identifier for the custom domain"
    )
    
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        comment="Tenant that owns this custom domain"
    )
    
    hostname = Column(
        String(255),
        unique=True,
        nullable=False,
        comment="The custom domain hostname (e.g., portal.be)"
    )
    
    app_slug = Column(
        String(255),
        nullable=True,
        comment="App slug for per-app domains like <<app>>.be"
    )
    
    base_domain = Column(
        String(255),
        nullable=True,
        comment="Base domain if using wildcard pattern (e.g., acme.be)"
    )
    
    is_wildcard = Column(
        Boolean,
        default=False,
        comment="Whether this is a wildcard domain (*.base_domain)"
    )
    
    is_base_domain = Column(
        Boolean,
        default=False,
        comment="Whether this is a base domain registration"
    )
    
    verified = Column(
        Boolean,
        default=False,
        comment="Whether the domain has passed CNAME verification"
    )
    
    verified_at = Column(
        DateTime,
        nullable=True,
        comment="When the domain was verified"
    )
    
    cert_status = Column(
        String(50),
        default="pending",
        comment="Certificate status: pending, active, failed, skipped"
    )
    
    cf_hostname_id = Column(
        String(100),
        nullable=True,
        comment="Cloudflare hostname ID for certificate management"
    )
    
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        comment="When the domain was registered"
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="custom_domains")
