"""Reverse proxy configuration generator."""
from typing import Optional
from dataclasses import dataclass
from jinja2 import Template


@dataclass
class Upstream:
    """Represents a tenant upstream server."""
    tenant_id: str
    ip: str
    port: int = 443
    protocol: str = "https"
    
    @property
    def name(self) -> str:
        return f"tenant_{self.tenant_id}"
    
    @property
    def address(self) -> str:
        return f"{self.ip}:{self.port}"


@dataclass
class Route:
    """Represents a routing rule."""
    hostname: str
    tenant_id: str
    app_slug: Optional[str] = None
    
    @property
    def slug(self) -> str:
        """Extract the slug from hostname."""
        if self.app_slug:
            return self.app_slug
        
        # Extract from hostname
        # portal.be -> portal
        # portal.sintrembert.be -> portal
        parts = self.hostname.split(".")
        return parts[0] if parts else "portal"


class ReverseProxyConfig:
    """Generate reverse proxy configuration."""
    
    NGINX_TEMPLATE = """
# Upstream definitions
{% for upstream in upstreams %}
upstream {{ upstream.name }} {
    server {{ upstream.address }};
}
{% endfor %}

server {
    listen {{ port }};
    server_name _;
    
    # Route to tenant based on Host header
    set $tenant_slug "";
    set $app_slug "";
    
    # Pattern 1: <<app>>.be (custom domain per app)
    if ($host ~* ^(.+)\.be$) {
        set $app_slug $1;
        set $tenant_slug $1;
    }
    
    # Pattern 2: <<app>>.sintrembert.be (custom subdomain)
    if ($host ~* ^(.+)\.{{ base_domain }}$) {
        set $app_slug $1;
        set $tenant_slug "{{ tenant_id }}";
    }
    
    # Pattern 3: <<tenant>>.cyantula.eu (default)
    if ($host ~* ^(.+)\.cyantula\.eu$) {
        set $tenant_slug $1;
    }
    
    # Pattern 4: portal.cyantula.eu (main portal)
    if ($host == "portal.cyantula.eu") {
        set $tenant_slug "portal";
    }
    
    # Route to tenant
    location @route_tenant {
        # Database lookup would happen here
        # For now, use static mapping
        {% for upstream in upstreams %}
        {% if loop.first %}if ($tenant_slug = "{{ upstream.tenant_id }}") {% endif %}
            proxy_pass {{ upstream.protocol }}://{{ upstream.address }};
        {% endif %}
        {% endfor %}
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_ssl_verify off;
        proxy_ssl_server_name on;
    }
    
    location / {
        proxy_pass http://127.0.0.1:{{ portal_port }};
        proxy_set_header Host $host;
    }
}
"""
    
    def __init__(
        self,
        base_domain: str = "cyantula.eu",
        portal_port: int = 8000,
        port: int = 8080
    ):
        """Initialize the reverse proxy config generator.
        
        Args:
            base_domain: The base domain for tenant routing
            portal_port: Port for the main portal
            port: Port for the reverse proxy
        """
        self.base_domain = base_domain
        self.portal_port = portal_port
        self.port = port
        self.upstreams: list[Upstream] = []
        self.routes: list[Route] = []
    
    def add_upstream(self, tenant_id: str, ip: str, port: int = 443):
        """Add a tenant upstream server.
        
        Args:
            tenant_id: The tenant identifier
            ip: The IP address of the tenant's LXC container
            port: The port (default: 443 for HTTPS)
        """
        upstream = Upstream(tenant_id=tenant_id, ip=ip, port=port)
        self.upstreams.append(upstream)
    
    def add_route(self, hostname: str, tenant_id: str, app_slug: Optional[str] = None):
        """Add a routing rule.
        
        Args:
            hostname: The hostname to route (e.g., portal.be)
            tenant_id: The tenant identifier
            app_slug: Optional app slug (if different from tenant)
        """
        route = Route(hostname=hostname, tenant_id=tenant_id, app_slug=app_slug)
        self.routes.append(route)
    
    def generate_nginx_config(self) -> str:
        """Generate NGINX configuration."""
        template = Template(self.NGINX_TEMPLATE)
        return template.render(
            upstreams=self.upstreams,
            base_domain=self.base_domain,
            tenant_id=self.base_domain.split(".")[0] if "." in self.base_domain else self.base_domain,
            portal_port=self.portal_port,
            port=self.port
        )
    
    def generate_caddy_config(self) -> str:
        """Generate Caddy configuration (alternative to NGINX)."""
        caddy_template = """
{
    admin off
}

{
    base_domain} {
    # Reverse proxy for tenant domains
    @tenants {
        host *.{{ base_domain }}
    }
    
    route @tenants {
        reverse_proxy {match:
            # Extract tenant from Host header
            {{ # Each upstream }}
            {{# each upstreams }}
            {{ hostname }} {{ protocol }}://{{ address }}
            {{/ each }}
        }
    }
    
    :{{ portal_port }} {
        respond "Portal not configured"
    }
}
"""
        template = Template(caddy_template)
        return template.render(
            base_domain=self.base_domain,
            portal_port=self.portal_port,
            upstreams=self.upstreams
        )


# Example usage
if __name__ == "__main__":
    config = ReverseProxyConfig(base_domain="cyantula.eu", portal_port=8000, port=8080)
    
    # Add tenants
    config.add_upstream("tenant_a", "192.168.30.10")
    config.add_upstream("tenant_b", "192.168.30.20")
    
    # Add routes
    config.add_route("portal.be", "tenant_a")
    config.add_route("analytics.be", "tenant_a")
    config.add_route("portal.sintrembert.be", "tenant_b")
    
    # Generate NGINX config
    nginx_config = config.generate_nginx_config()
    print("NGINX Configuration:")
    print(nginx_config)
