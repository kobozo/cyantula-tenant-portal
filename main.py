"""Main application entry point."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.custom_domains import router as custom_domains_router
from api.tenants import router as tenants_router
from database.models import Base

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/cyantula_tenant")

# Create FastAPI app
app = FastAPI(
    title="Cyantula Tenant Portal API",
    description="Multi-tenant portal for Cyantula - handles organisation onboarding, provisioning, and DNS routing",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Cyantula Tenant Portal",
        "version": "0.1.0",
        "description": "Multi-tenant portal for Cyantula"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup():
    """Startup hook."""
    # Database initialization would go here
    # e.g., create tables, connect to database
    print("Starting Cyantula Tenant Portal...")


@app.on_event("shutdown")
async def shutdown():
    """Shutdown hook."""
    print("Shutting down Cyantula Tenant Portal...")


# Include routers
app.include_router(custom_domains_router)
app.include_router(tenants_router)
