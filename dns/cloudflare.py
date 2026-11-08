"""Cloudflare API client for DNS management."""
import os
from typing import Optional
import aiohttp


class CloudflareClient:
    """Client for Cloudflare API v4."""
    
    API_BASE_URL = "https://api.cloudflare.com/client/v4"
    
    def __init__(self, api_token: Optional[str] = None, email: Optional[str] = None):
        """Initialize the Cloudflare client.
        
        Args:
            api_token: Cloudflare API token (required)
            email: Cloudflare account email (optional, for legacy API keys)
        """
        self.api_token = api_token or os.getenv("CLOUDFLARE_API_TOKEN")
        self.email = email or os.getenv("CLOUDFLARE_EMAIL")
        
        if not self.api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN environment variable is required")
    
    @property
    def headers(self) -> dict:
        """Build request headers."""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        if self.email:
            headers["X-Cloud-User-Email"] = self.email
        return headers
    
    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[dict] = None,
        params: Optional[dict] = None
    ) -> dict:
        """Make a request to the Cloudflare API."""
        url = f"{self.API_BASE_URL}/{path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                json=json,
                params=params,
                headers=self.headers
            ) as response:
                data = await response.json()
                
                if not data.get("success"):
                    raise CloudflareError(
                        message=data.get("errors", [{}])[0].get("message", "Unknown error"),
                        code=data.get("errors", [{}])[0].get("code", 0)
                    )
                
                return data
    
    async def list_zones(self, name: Optional[str] = None) -> list:
        """List zones (domains) in the account.
        
        Args:
            name: Filter by zone name
            
        Returns:
            List of zones
        """
        params = {}
        if name:
            params["name"] = name
        
        response = await self._request("GET", "zones", params=params)
        return response.get("result", [])
    
    async def get_zone(self, zone_id: str) -> dict:
        """Get zone details.
        
        Args:
            zone_id: The zone identifier
            
        Returns:
            Zone details
        """
        response = await self._request("GET", f"zones/{zone_id}")
        return response.get("result", {})
    
    async def create_dns_record(
        self,
        zone_id: str,
        hostname: str,
        target: str,
        record_type: str = "CNAME",
        ttl: int = 1
    ) -> dict:
        """Create a DNS record.
        
        Args:
            zone_id: The zone identifier
            hostname: The hostname (e.g., portal.be)
            target: The CNAME target (e.g., portal.cyantula.eu)
            record_type: DNS record type (default: CNAME)
            ttl: Time to live in seconds (1 = auto)
            
        Returns:
            Created DNS record
        """
        data = {
            "type": record_type,
            "name": hostname,
            "content": target,
            "ttl": ttl,
            "proxied": True  # Route through Cloudflare
        }
        
        response = await self._request("POST", f"zones/{zone_id}/dns_records", json=data)
        return response.get("result", {})
    
    async def update_dns_record(
        self,
        zone_id: str,
        record_id: str,
        hostname: str,
        target: str,
        record_type: str = "CNAME"
    ) -> dict:
        """Update an existing DNS record.
        
        Args:
            zone_id: The zone identifier
            record_id: The DNS record identifier
            hostname: The hostname
            target: The new CNAME target
            record_type: DNS record type (default: CNAME)
            
        Returns:
            Updated DNS record
        """
        data = {
            "type": record_type,
            "name": hostname,
            "content": target,
            "ttl": 1,
            "proxied": True
        }
        
        response = await self._request(
            "PATCH",
            f"zones/{zone_id}/dns_records/{record_id}",
            json=data
        )
        return response.get("result", {})
    
    async def delete_dns_record(self, zone_id: str, record_id: str) -> bool:
        """Delete a DNS record.
        
        Args:
            zone_id: The zone identifier
            record_id: The DNS record identifier
            
        Returns:
            True if successful
        """
        await self._request("DELETE", f"zones/{zone_id}/dns_records/{record_id}")
        return True
    
    async def list_dns_records(
        self,
        zone_id: str,
        name: Optional[str] = None,
        type_: Optional[str] = None
    ) -> list:
        """List DNS records in a zone.
        
        Args:
            zone_id: The zone identifier
            name: Filter by hostname
            type_: Filter by record type
            
        Returns:
            List of DNS records
        """
        params = {}
        if name:
            params["name"] = name
        if type_:
            params["type"] = type_
        
        response = await self._request("GET", f"zones/{zone_id}/dns_records", params=params)
        return response.get("result", [])
    
    async def get_or_create_dns_record(
        self,
        zone_id: str,
        hostname: str,
        target: str,
        record_type: str = "CNAME"
    ) -> dict:
        """Get existing DNS record or create a new one.
        
        Args:
            zone_id: The zone identifier
            hostname: The hostname
            target: The CNAME target
            record_type: DNS record type (default: CNAME)
            
        Returns:
            DNS record (existing or newly created)
        """
        records = await self.list_dns_records(zone_id, name=hostname, type_=record_type)
        
        if records:
            # Record exists, update it
            record = records[0]
            if record.get("content") != target:
                return await self.update_dns_record(zone_id, record["id"], hostname, target, record_type)
            return record
        
        # Record doesn't exist, create it
        return await self.create_dns_record(zone_id, hostname, target, record_type)
    
    async def register_hostname(self, hostname: str, tenant_id: str) -> dict:
        """Register a hostname with Cloudflare for certificate management.
        
        This creates the DNS record and sets up the hostname for certificate issuance.
        
        Args:
            hostname: The hostname to register (e.g., portal.be)
            tenant_id: The tenant identifier
            
        Returns:
            Registration result with hostname_id
        """
        # Extract base domain from hostname
        # For portal.be -> base domain is be
        # For portal.acme.be -> base domain is acme.be
        parts = hostname.split(".")
        
        if len(parts) < 2:
            raise ValueError(f"Invalid hostname: {hostname}")
        
        # Try to find the zone
        base_domain = ".".join(parts[-2:])
        
        zones = await self.list_zones(name=base_domain)
        
        if not zones:
            raise ValueError(f"No zone found for {base_domain}")
        
        zone = zones[0]
        zone_id = zone["id"]
        
        # Create or update the DNS record
        target = f"{tenant_id}.cyantula.eu"
        record = await self.get_or_create_dns_record(zone_id, hostname, target)
        
        # Register hostname for certificate management
        # This would be done via the Cloudflare API for certificate assignment
        return {
            "hostname": hostname,
            "zone_id": zone_id,
            "dns_record_id": record["id"],
            "target": target,
            "verified": record["status"] == "active"
        }


class CloudflareError(Exception):
    """Error from Cloudflare API."""
    
    def __init__(self, message: str, code: int):
        self.message = message
        self.code = code
        super().__init__(f"Cloudflare API error {code}: {message}")
