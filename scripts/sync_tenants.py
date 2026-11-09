#!/usr/bin/env python3
"""Sync tenants from Tenant API to Cybera database."""

import asyncio
import json
import os
import sys
import asyncpg
import httpx

# Tenant API URL
TENANT_API_URL = os.environ.get("TENANT_API_URL", "http://192.168.3.211:8000")
TENANT_API_TOKEN = os.environ.get("TENANT_API_TOKEN")

# Cybera database config
CYANTULA_DB_URL = os.environ.get("CYANTULA_DB_URL", "postgresql://postgres:postgres@192.168.1.240:5432/cyantula")

async def get_tenants_from_api():
    """Get all tenants from Tenant API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{TENANT_API_URL}/api/tenants")
        response.raise_for_status()
        return response.json()

async def get_existing_slugs(pool):
    """Get all tenant slugs from Cybera database."""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT slug FROM "Tenant"')
        return {row['slug'] for row in rows}

async def create_tenant_in_db(pool, tenant_data):
    """Create a tenant record in Cybera database."""
    async with pool.acquire() as conn:
        # First, create the Proxmox server for this tenant
        server_id = await conn.fetchval(
            '''INSERT INTO "Server" (id, name, type, status, address, port, "acceptsNew", "createdAt", "updatedAt", "proxmoxNode", "proxmoxApiUrl", "lxcVmidBase")
               VALUES (gen_random_uuid(), $1, 'PROXMOX_LXC', 'ONLINE', $2, 8006, true, NOW(), NOW(), 'pve', $3, 100)
               RETURNING id''',
            tenant_data['name'],
            '192.168.3.211',
            'https://192.168.3.211:8006'
        )
        
        # Then create the tenant
        await conn.execute(
            '''INSERT INTO "Tenant" (id, name, slug, "baseDomain", status, "setupTokenHash", "setupTokenExpiresAt", "serverId", "appCountLimit", memory_limit, storage_limit, "createdAt", "updatedAt", "lastActiveAt")
               VALUES (gen_random_uuid(), $1, $2, $3, 'ACTIVE', '', NULL, $4, 10, '4g', '20g', NOW(), NOW(), NULL)''',
            tenant_data['name'],
            tenant_data['slug'],
            tenant_data.get('base_domain', 'cyantula.eu'),
            server_id
        )
        
        print(f"✓ Created tenant: {tenant_data['slug']}")

async def sync_tenants():
    """Sync tenants from Tenant API to Cybera database."""
    print("Fetching tenants from Tenant API...")
    tenants = await get_tenants_from_api()
    print(f"Found {len(tenants)} tenants in API")
    
    # Parse database URL: postgresql://user:password@host:port/database
    if CYANTULA_DB_URL.startswith("postgresql://"):
        import urllib.parse
        parsed = urllib.parse.urlparse(CYANTULA_DB_URL)
        pool = await asyncpg.create_pool(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            user=parsed.username or 'postgres',
            password=parsed.password or 'postgres',
            database=parsed.path.lstrip('/') or 'cyantula'
        )
    else:
        print(f"Invalid DB URL format: {CYANTULA_DB_URL}")
        return
    
    try:
        existing_slugs = await get_existing_slugs(pool)
        print(f"Found {len(existing_slugs)} existing tenants in Cybera")
        
        for tenant in tenants:
            if tenant['slug'] not in existing_slugs:
                print(f"Syncing tenant: {tenant['slug']}")
                await create_tenant_in_db(pool, tenant)
            else:
                print(f"Skipped (already exists): {tenant['slug']}")
        
        print("\nSync complete!")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(sync_tenants())
