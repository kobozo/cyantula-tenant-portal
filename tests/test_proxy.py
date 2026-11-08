"""Tests for reverse proxy configuration."""
import pytest
from proxy.config import ReverseProxyConfig, Upstream, Route


class TestReverseProxyConfig:
    """Test reverse proxy configuration generation."""
    
    def test_add_upstream(self):
        """Test adding upstream servers."""
        config = ReverseProxyConfig()
        config.add_upstream("tenant_a", "192.168.30.10")
        
        assert len(config.upstreams) == 1
        assert config.upstreams[0].tenant_id == "tenant_a"
        assert config.upstreams[0].ip == "192.168.30.10"
    
    def test_add_route(self):
        """Test adding routing rules."""
        config = ReverseProxyConfig()
        config.add_route("portal.be", "tenant_a")
        config.add_route("analytics.be", "tenant_a")
        
        assert len(config.routes) == 2
        assert config.routes[0].hostname == "portal.be"
        assert config.routes[1].hostname == "analytics.be"
    
    def test_slug_extraction(self):
        """Test slug extraction from hostnames."""
        route1 = Route(hostname="portal.be", tenant_id="tenant_a")
        route2 = Route(hostname="analytics.be", tenant_id="tenant_a")
        route3 = Route(hostname="portal.acme.be", tenant_id="tenant_b")
        
        assert route1.slug == "portal"
        assert route2.slug == "analytics"
        assert route3.slug == "portal"
    
    def test_upstream_name(self):
        """Test upstream name generation."""
        upstream = Upstream(tenant_id="tenant_a", ip="192.168.30.10")
        assert upstream.name == "tenant_tenant_a"
        assert upstream.address == "192.168.30.10:443"
    
    def test_generate_nginx_config(self):
        """Test NGINX configuration generation."""
        config = ReverseProxyConfig()
        config.add_upstream("tenant_a", "192.168.30.10")
        config.add_upstream("tenant_b", "192.168.30.20")
        config.add_route("portal.be", "tenant_a")
        config.add_route("portal.acme.be", "tenant_b")
        
        nginx_config = config.generate_nginx_config()
        
        assert "upstream" in nginx_config
        assert "proxy_pass" in nginx_config
        assert "tenant_a" in nginx_config
        assert "tenant_b" in nginx_config
    
    def test_generate_caddy_config(self):
        """Test Caddy configuration generation."""
        config = ReverseProxyConfig()
        config.add_upstream("tenant_a", "192.168.30.10")
        
        caddy_config = config.generate_caddy_config()
        
        assert "reverse_proxy" in caddy_config
        assert "tenant_a" in caddy_config
