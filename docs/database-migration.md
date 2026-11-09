# Database Migration Guide

This document describes how to migrate the Cyantula database to support multi-tenant architecture.

## Prerequisites

1. Access to Cyantula PostgreSQL database
2. Prisma CLI installed (`npx -y prisma@6`)

## Migration Steps

### 1. Update Prisma Schema

The schema has been updated in `/home/yannick/cyantula/server/prisma/schema.prisma` with:

- **Tenant model**: Stores tenant information
- **TenantAccess model**: Manages user access to tenants
- **TenantInvitation model**: Handles tenant invitations
- **ServerType enum**: Added `PROXMOX_LXC` type

### 2. Generate Prisma Client

```bash
cd /home/yannick/cyantula/server
npx -y prisma@6 generate
```

### 3. Create Migration

```bash
npx -y prisma@6 migrate dev --name add_tenant_support
```

### 4. Apply Migration to Database

```bash
# If using Docker:
docker exec -it cyantula-server sh -c "npx -y prisma@6 migrate deploy"

# Or directly:
npx -y prisma@6 migrate deploy
```

### 5. Verify Migration

```bash
npx -y prisma@6 studio
```

## Database Schema Changes

### New Models

#### Tenant
```prisma
model Tenant {
  id            String    @id @default(uuid())
  name          String
  slug          String    @unique
  baseDomain    String?
  status        TenantStatus @default(ACTIVE)
  setupToken    String?
  setupTokenExpiry DateTime?
  servers       Server[]
  users         TenantAccess[]
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
}
```

#### TenantAccess
```prisma
model TenantAccess {
  id        String   @id @default(uuid())
  userId    String
  tenantId  String
  role      TenantRole @default(MEMBER)
  user      User     @relation(fields: [userId], references: [id])
  tenant    Tenant   @relation(fields: [tenantId], references: [id])
  createdAt DateTime @default(now())
  
  @@unique([userId, tenantId])
}
```

#### TenantInvitation
```prisma
model TenantInvitation {
  id        String   @id @default(uuid())
  tenantId  String
  inviterId String
  email     String
  role      TenantRole
  token     String   @unique
  expiresAt DateTime
  accepted  Boolean  @default(false)
  createdAt DateTime @default(now())
}
```

### Modified Models

#### User
```prisma
model User {
  // ... existing fields
  tenantAccess TenantAccess[]
  // ... other fields
}
```

#### App
```prisma
model App {
  // ... existing fields
  tenantId String?
  tenant   Tenant? @relation(fields: [tenantId], references: [id])
  // ... other fields
}
```

#### Server
```prisma
model Server {
  // ... existing fields
  type           ServerType    @default(DOCKER)
  proxmoxNode    String?
  proxmoxApiUrl  String?
  lxcVmidBase    Int?          @default(100)
  tenantId       String?
  tenant         Tenant?       @relation(fields: [tenantId], references: [id])
  // ... other fields
}
```

### New Enums

```prisma
enum ServerType {
  DOCKER
  PROXMOX_LXC
}

enum TenantRole {
  OWNER
  ADMIN
  MEMBER
}

enum TenantStatus {
  ACTIVE
  INACTIVE
  SUSPENDED
}
```

## Post-Migration Tasks

1. **Restart Cyantula server** to use new Prisma client
2. **Update deployment pipeline** to handle Proxmox LXC servers
3. **Update cluster placement logic** to route apps to correct server type

## Rollback

If issues occur:

```bash
npx -y prisma@6 migrate reset --skip-seed
```

Or apply previous migration:

```bash
npx -y prisma@6 migrate resolve --applied <previous_migration_name>
```
