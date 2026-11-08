# Custom Domain Routing Brainstorm

## Scenario

Customer has their own domain: `acme.be`

Goal: `acme.be` → Customer's tenant instance (acme.cyantula.eu)

## Options

### Option 1: DNS CNAME
```
acme.be  CNAME  → acme.cyantula.eu
```
-Pros: Simple, Cloudflare handles it
-Cons: Browser shows acme.cyantula.eu (unless proxying)

### Option 2: HTTPS Proxy
```
acme.be → Reverse Proxy → acme.cyantula.eu → Tenant
```
-Pros: Clean URL, SSL works
-Cons: More complex, two hops

### Option 3: Cloudflare Tunnel per custom domain
-Pros: Direct, no proxy needed
-Cons: Many tunnels, management overhead

### Option 4: SSL Termination at Reverse Proxy
-Pros: SSL works for custom domains
-Cons: Need to handle certificates

## Recommended Approach

### DNS Setup
```
Customer DNS:
acme.be    A      → Cloudflare IP (via CNAME to portal.cyantula.eu)

Or:
acme.be    CNAME  → acme.cyantula.eu
```

### Reverse Proxy with Custom Domains
```
server {
    listen 443 ssl;
    server_name acme.be www.acme.be;
    
    ssl_certificate /etc/ssl/custom/acme.be.crt;
    ssl_certificate_key /etc/ssl/custom/acme.be.key;
    
    location / {
        proxy_pass https://192.168.30.10;
        proxy_set_header Host $host;
    }
}
```

## Best Practice

1. **DNS CNAME** to tenant's subdomain
2. **SSL certificates** via Cloudflare or Let's Encrypt
3. **Reverse proxy** handles routing and SSL termination
4. **Portal** manages domain registration and SSL certs

## Implementation

The portal should:
1. Accept custom domain registration
2. Generate SSL certificates (Let's Encrypt or Cloudflare)
3. Configure reverse proxy automatically
4. Verify domain ownership (DNS check)
