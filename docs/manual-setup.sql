-- Manual Tenant Setup in Cybera Database
-- Run this after creating a tenant via the Tenant API

-- Step 1: Get the tenant info from Tenant API first:
-- curl https://api.cyantula.eu/api/tenants/{slug}
-- Note the tenant ID, slug, and Proxmox VMID

-- Step 2: Insert the Proxmox server record
INSERT INTO "Server" (
  id, name, type, status, address, port, "acceptsNew", "createdAt", "updatedAt",
  "proxmoxNode", "proxmoxApiUrl", "lxcVmidBase"
)
SELECT
  gen_random_uuid(),
  'Cybera Tenant Server',
  'PROXMOX_LXC',
  'ONLINE',
  '192.168.3.211',
  8006,
  true,
  NOW(),
  NOW(),
  'pve',
  'https://192.168.3.211:8006',
  100
WHERE NOT EXISTS (
  SELECT 1 FROM "Server" WHERE name = 'Cybera Tenant Server'
);

-- Step 3: Get the server ID
-- Run: SELECT id FROM "Server" WHERE name = 'Cybera Tenant Server';

-- Step 4: Insert the tenant record (replace server_id with actual ID from step 3)
INSERT INTO "Tenant" (
  id, name, slug, "baseDomain", status, "setupTokenHash", "setupTokenExpiresAt", "serverId",
  "appCountLimit", "memoryLimit", "storageLimit", "createdAt", "updatedAt", "lastActiveAt"
)
VALUES (
  gen_random_uuid(),
  'Cybera',
  'cybera',
  'cyantula.eu',
  'ACTIVE',
  '',
  NULL,
  '<server_id_from_step_3>',
  10,
  '4g',
  '20g',
  NOW(),
  NOW(),
  NULL
);

-- Step 5: Verify
SELECT t.*, s.name as server_name, s.address as server_address
FROM "Tenant" t
JOIN "Server" s ON t."serverId" = s.id
WHERE t.slug = 'cybera';
