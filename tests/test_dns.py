"""Tests for CNAME verification logic."""
import pytest
import asyncio
from dns.cname_check import (
    is_valid_hostname,
    is_valid_wildcard_hostname,
    normalize_hostname,
    extract_base_domain,
    check_cname
)


class TestCNAMEValidation:
    """Test hostname validation functions."""
    
    def test_normalize_hostname(self):
        """Test hostname normalization."""
        assert normalize_hostname("PORTAL.BE") == "portal.be"
        assert normalize_hostname("  portal.be  ") == "portal.be"
    
    def test_is_valid_hostname(self):
        """Test valid hostname detection."""
        assert is_valid_hostname("portal.be") is True
        assert is_valid_hostname("analytics.sintrembert.be") is True
        assert is_valid_hostname("app1.cyantula.eu") is True
        
        assert is_valid_hostname("") is False
        assert is_valid_hostname("invalid..hostname") is False
        assert is_valid_hostname("-invalid.be") is False
        assert is_valid_hostname("invalid-.be") is False
    
    def test_is_valid_wildcard_hostname(self):
        """Test wildcard hostname detection."""
        assert is_valid_wildcard_hostname("*.sintrembert.be") is True
        assert is_valid_wildcard_hostname("*.cyantula.eu") is True
        
        assert is_valid_wildcard_hostname("sintrembert.be") is False
        assert is_valid_wildcard_hostname("*.") is False
    
    def test_extract_base_domain(self):
        """Test base domain extraction."""
        # Returns last 2 parts (domain.tld)
        assert extract_base_domain("portal.be") == "portal.be"
        assert extract_base_domain("portal.sintrembert.be") == "sintrembert.be"
        assert extract_base_domain("analytics.sintrembert.be") == "sintrembert.be"
        assert extract_base_domain("*.sintrembert.be") == "sintrembert.be"
        
        assert extract_base_domain("invalid") is None
        assert extract_base_domain("a.b.c.d") == "c.d"


class TestCNAMECheck:
    """Test CNAME checking functionality."""
    
    @pytest.mark.asyncio
    async def test_check_cname_valid(self):
        """Test CNAME check with valid hostname."""
        result = await check_cname("portal.be", "portal.cyantula.eu")
        
        assert "ok" in result
        assert "detail" in result
        assert "actual_target" in result
    
    @pytest.mark.asyncio
    async def test_check_cname_invalid_hostname(self):
        """Test CNAME check with invalid hostname."""
        result = await check_cname("invalid..hostname", "portal.cyantula.eu")
        
        assert result["ok"] is False
        assert "Invalid" in result["detail"]
    
    @pytest.mark.asyncio
    async def test_verify_custom_domain_success(self):
        """Test custom domain verification."""
        result = await check_cname("portal.be", "portal.cyantula.eu")
        
        assert "ok" in result
        assert "detail" in result
