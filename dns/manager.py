# DNS Manager for Cloudflare integration

"""DNS management for tenant routing."""

import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class DNSConfig:
    """DNS configuration."""
    provider: str = "cloudflare"
    api_token: str = ""
    zone_id: str = ""
    base_domain: str = "cyantula.eu"
    ttl: int = 300  # DNS record TTL in seconds


class DNSManager:
    """Manager for DNS records using Cloudflare API."""
    
    def __init__(self, config: DNSConfig = DNSConfig()):
        self.config = config
        self.base_url = "https://api.cloudflare.com/client/v4"
    
    def _headers(self) -> Dict[str, str]:
        """Get Cloudflare API headers."""
        return {
            "Authorization": f"Bearer {self.config.api_token}",
            "Content-Type": "application/json"
        }
    
    def _get_zone_id(self) -> Optional[str]:
        """Get zone ID for base domain if not configured."""
        if self.config.zone_id:
            return self.config.zone_id
        
        # Fetch zone ID from Cloudflare
        response = requests.get(
            f"{self.base_url}/zones?name={self.config.base_domain}",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        
        zones = response.json()["result"]
        if zones:
            self.config.zone_id = zones[0]["id"]
            return self.config.zone_id
        
        return None
    
    def register(self, subdomain: str, ip_address: str) -> Dict[str, Any]:
        """Register DNS record for tenant."""
        zone_id = self._get_zone_id()
        if not zone_id:
            raise ValueError("Zone ID not found or configured")
        
        dns_name = f"{subdomain}.{self.config.base_domain}"
        
        # Check if record exists
        existing = self._get_record(zone_id, dns_name)
        if existing:
            print(f"[DNS] Record already exists, updating: {dns_name}")
            return self._update_record(zone_id, existing["id"], dns_name, ip_address)
        
        # Create new record
        print(f"[DNS] Creating record: {dns_name} -> {ip_address}")
        return self._create_record(zone_id, dns_name, ip_address)
    
    def unregister(self, subdomain: str) -> Dict[str, Any]:
        """Remove DNS record for tenant."""
        zone_id = self._get_zone_id()
        if not zone_id:
            raise ValueError("Zone ID not found or configured")
        
        dns_name = f"{subdomain}.{self.config.base_domain}"
        
        # Find and delete record
        existing = self._get_record(zone_id, dns_name)
        if existing:
            print(f"[DNS] Deleting record: {dns_name}")
            return self._delete_record(zone_id, existing["id"])
        
        print(f"[DNS] Record not found: {dns_name}")
        return {"success": True, "message": "Record not found"}
    
    def _get_record(self, zone_id: str, dns_name: str) -> Optional[Dict[str, Any]]:
        """Get DNS record by name."""
        response = requests.get(
            f"{self.base_url}/zones/{zone_id}/dns_records?name={dns_name}&type=A",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        
        records = response.json()["result"]
        return records[0] if records else None
    
    def _create_record(
        self,
        zone_id: str,
        dns_name: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """Create new DNS record."""
        response = requests.post(
            f"{self.base_url}/zones/{zone_id}/dns_records",
            headers=self._headers(),
            json={
                "type": "A",
                "name": dns_name,
                "content": ip_address,
                "ttl": self.config.ttl,
                "proxied": False  # Don't proxy through Cloudflare (direct to tenant)
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def _update_record(
        self,
        zone_id: str,
        record_id: str,
        dns_name: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """Update existing DNS record."""
        response = requests.put(
            f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}",
            headers=self._headers(),
            json={
                "type": "A",
                "name": dns_name,
                "content": ip_address,
                "ttl": self.config.ttl,
                "proxied": False
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def _delete_record(
        self,
        zone_id: str,
        record_id: str
    ) -> Dict[str, Any]:
        """Delete DNS record."""
        response = requests.delete(
            f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def get_record(self, subdomain: str) -> Optional[Dict[str, Any]]:
        """Get DNS record for subdomain."""
        zone_id = self._get_zone_id()
        if not zone_id:
            return None
        
        dns_name = f"{subdomain}.{self.config.base_domain}"
        return self._get_record(zone_id, dns_name)
    
    def list_records(self) -> list:
        """List all DNS records."""
        zone_id = self._get_zone_id()
        if not zone_id:
            return []
        
        response = requests.get(
            f"{self.base_url}/zones/{zone_id}/dns_records",
            headers=self._headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()["result"]
    
    def verify_domain_ownership(self, domain: str) -> bool:
        """Verify domain ownership via DNS."""
        # This would check for a verification token in DNS
        # For now, assume ownership is verified
        return True


# Convenience function
def create_dns_manager(
    api_token: str,
    zone_id: str = "",
    base_domain: str = "cyantula.eu"
) -> DNSManager:
    """Create DNS manager with configuration."""
    config = DNSConfig(
        api_token=api_token,
        zone_id=zone_id,
        base_domain=base_domain
    )
    return DNSManager(config)
