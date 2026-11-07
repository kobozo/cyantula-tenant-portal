# API Endpoints

## Organisations

### Create Organisation
**POST** `/api/organisations`

```json
{
  "name": "Organisatie Naam",
  "admin_email": "admin@example.com"
}
```

**Response:** 201 Created
```json
{
  "id": "uuid",
  "name": "Organisatie Naam",
  "slug": "organisatie-naam",
  "admin_email": "admin@example.com",
  "status": "provisioning"
}
```

### Get Organisation
**GET** `/api/organisations/{id}`

**Response:** 200 OK
```json
{
  "id": "uuid",
  "name": "Organisatie Naam",
  "slug": "organisatie-naam",
  "admin_email": "admin@example.com",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Generate Setup Token
**POST** `/api/organisations/{id}/setup-token`

**Response:** 200 OK
```json
{
  "token": "random-generated-token",
  "expires_at": "2024-01-02T00:00:00Z"
}
```

### Get Provisioning Logs
**GET** `/api/organisations/{id}/logs`

**Response:** 200 OK
```json
[
  {
    "step": "creating_docker",
    "status": "success",
    "started_at": "2024-01-01T00:00:00Z",
    "completed_at": "2024-01-01T00:01:00Z"
  },
  {
    "step": "registering_dns",
    "status": "pending",
    "started_at": "2024-01-01T00:01:00Z",
    "completed_at": null
  }
]
```

## DNS

### Register DNS
**POST** `/api/dns/register`

```json
{
  "slug": "organisatie-slug",
  "cluster_ip": "192.168.1.10"
}
```

**Response:** 200 OK
```json
{
  "success": true,
  "dns_name": "organisatie-slug.apps.example.com"
}
```

### Unregister DNS
**DELETE** `/api/dns/register/{slug}`

**Response:** 200 OK
```json
{
  "success": true
}
```

## Health

### Health Check
**GET** `/health`

**Response:** 200 OK
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Email

### Send Setup Email
**POST** `/api/email/setup`

```json
{
  "organisation_id": "uuid",
  "token": "setup-token"
}
```

**Response:** 200 OK
```json
{
  "success": true
}
```
