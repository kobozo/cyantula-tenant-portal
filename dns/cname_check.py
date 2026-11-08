"""CNAME verification for custom domains."""
import asyncio
import re
from typing import Optional
import aiohttp


# Regex patterns for hostname validation
HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
WILDCARD_RE = re.compile(r"^\*\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2,}$")


def normalize_hostname(hostname: str) -> str:
    """Normalize a hostname to lowercase."""
    return hostname.lower().strip()


def is_valid_hostname(hostname: str) -> bool:
    """Check if a hostname is valid."""
    hostname = normalize_hostname(hostname)
    return bool(HOSTNAME_RE.match(hostname) or WILDCARD_RE.match(hostname))


def is_valid_wildcard_hostname(hostname: str) -> bool:
    """Check if a hostname is a valid wildcard domain."""
    hostname = normalize_hostname(hostname)
    return bool(WILDCARD_RE.match(hostname))


def extract_base_domain(hostname: str) -> Optional[str]:
    """Extract the base domain from a hostname.
    
    Examples:
        portal.be -> be
        portal.sintrembert.be -> sintrembert.be
        *.sintrembert.be -> sintrembert.be
    """
    hostname = normalize_hostname(hostname)
    
    if is_valid_wildcard_hostname(hostname):
        # Remove the *.
        hostname = hostname[2:]
    
    parts = hostname.split(".")
    if len(parts) < 2:
        return None
    
    # Return last two parts (domain.tld) or more for subdomains
    # For sintrembert.be -> sintrembert.be
    # For portal.sintrembert.be -> sintrembert.be
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    
    return None


async def check_cname(
    hostname: str,
    expected_target: str,
    timeout: float = 10.0
) -> dict:
    """Check if a hostname has the correct CNAME record.
    
    Args:
        hostname: The hostname to check (e.g., portal.be)
        expected_target: The expected CNAME target (e.g., portal.cyantula.eu)
        timeout: DNS lookup timeout in seconds
        
    Returns:
        dict with keys:
            - ok: bool - Whether the CNAME check passed
            - detail: str - Detailed result message
            - actual_target: Optional[str] - Actual CNAME target if found
    """
    hostname = normalize_hostname(hostname)
    
    if not is_valid_hostname(hostname):
        return {
            "ok": False,
            "detail": "Invalid hostname format",
            "actual_target": None
        }
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            # For now, simulate DNS lookup
            # In production, use asyncio.loop.get_event_loop().resolve() or dns.resolver
            # Or use a library like aiodnspython
            
            # Simulate checking if hostname points to expected target
            # This would be the actual DNS lookup in production
            actual_target = await resolve_cname(hostname)
            
            if actual_target is None:
                return {
                    "ok": False,
                    "detail": f"No CNAME record found for {hostname}",
                    "actual_target": None
                }
            
            # Check if the actual target matches expected
            if normalize_hostname(actual_target) == normalize_hostname(expected_target):
                return {
                    "ok": True,
                    "detail": f"CNAME record matches: {hostname} -> {actual_target}",
                    "actual_target": actual_target
                }
            else:
                return {
                    "ok": False,
                    "detail": f"CNAME mismatch: expected {expected_target}, got {actual_target}",
                    "actual_target": actual_target
                }
                
    except asyncio.TimeoutError:
        return {
            "ok": False,
            "detail": f"DNS lookup timed out for {hostname}",
            "actual_target": None
        }
    except Exception as e:
        return {
            "ok": False,
            "detail": f"DNS lookup failed: {str(e)}",
            "actual_target": None
        }


async def resolve_cname(hostname: str) -> Optional[str]:
    """Resolve the CNAME record for a hostname.
    
    Args:
        hostname: The hostname to resolve
        
    Returns:
        The CNAME target or None if not found
    """
    # For production, use aiodnspython:
    # import aiodns
    # resolver = aiodns.DNSResolver()
    # result = await resolver.query(hostname, 'CNAME')
    # return str(result.cname) if result else None
    
    # For now, simulate
    # This would do actual DNS lookup in production
    return None


async def verify_custom_domain(
    hostname: str,
    tenant_id: str,
    expected_target: Optional[str] = None
) -> dict:
    """Verify a custom domain by checking CNAME and setting up certificate.
    
    Args:
        hostname: The custom domain hostname
        tenant_id: The tenant identifier
        expected_target: The expected CNAME target (auto-generated if not provided)
        
    Returns:
        dict with verification result
    """
    if expected_target is None:
        expected_target = f"{tenant_id}.cyantula.eu"
    
    result = await check_cname(hostname, expected_target)
    
    if result["ok"]:
        return {
            "success": True,
            "hostname": hostname,
            "verified": True,
            "cert_status": "pending",
            "cf_hostname_id": None,
            "detail": result["detail"]
        }
    else:
        return {
            "success": False,
            "hostname": hostname,
            "verified": False,
            "cert_status": "pending",
            "cf_hostname_id": None,
            "detail": result["detail"]
        }
