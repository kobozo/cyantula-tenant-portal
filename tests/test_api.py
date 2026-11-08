"""Tests for custom domain API endpoints."""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestCustomDomainEndpoints:
    """Test custom domain API endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint returns expected response."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Cyantula Tenant Portal"
        assert "version" in data
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_create_custom_domain(self):
        """Test creating a custom domain."""
        domain_data = {
            "hostname": "portal.be",
            "tenant_id": "test_tenant_123",
            "base_domain": "sintrembert.be",
            "is_wildcard": False
        }
        
        response = client.post("/api/custom-domains", json=domain_data)
        assert response.status_code == 200
        data = response.json()
        assert data["hostname"] == "portal.be"
        assert data["tenant_id"] == "test_tenant_123"
        assert data["verified"] is False
        assert "id" in data
    
    def test_list_custom_domains(self):
        """Test listing custom domains."""
        response = client.get("/api/custom-domains")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_custom_domains_filtered(self):
        """Test listing custom domains filtered by tenant."""
        response = client.get("/api/custom-domains", params={"tenant_id": "test_tenant_123"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_custom_domain_not_found(self):
        """Test getting a non-existent custom domain."""
        response = client.get("/api/custom-domains/nonexistent_id")
        assert response.status_code == 404
    
    def test_delete_custom_domain(self):
        """Test deleting a custom domain."""
        # First create a domain
        domain_data = {
            "hostname": "delete-me.be",
            "tenant_id": "test_tenant_123"
        }
        create_response = client.post("/api/custom-domains", json=domain_data)
        domain_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(f"/api/custom-domains/{domain_id}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_verify_custom_domain(self):
        """Test verifying a custom domain."""
        # First create a domain
        domain_data = {
            "hostname": "verify-me.be",
            "tenant_id": "test_tenant_123"
        }
        create_response = client.post("/api/custom-domains", json=domain_data)
        domain_id = create_response.json()["id"]
        
        # Verify it
        response = client.post(f"/api/custom-domains/{domain_id}/verify")
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is True
        assert data["cert_status"] == "active"
    
    def test_get_dns_instructions(self):
        """Test getting DNS configuration instructions."""
        # First create a domain
        domain_data = {
            "hostname": "instructions.be",
            "tenant_id": "test_tenant_123"
        }
        create_response = client.post("/api/custom-domains", json=domain_data)
        domain_id = create_response.json()["id"]
        
        # Get instructions
        response = client.get(f"/api/custom-domains/{domain_id}/instructions")
        assert response.status_code == 200
        data = response.json()
        assert "hostname" in data
        assert "record" in data
        assert "CNAME" in data["record"]
    
    def test_invalid_hostname_format(self):
        """Test validation of hostname format."""
        domain_data = {
            "hostname": "invalid..hostname",
            "tenant_id": "test_tenant_123"
        }
        
        response = client.post("/api/custom-domains", json=domain_data)
        assert response.status_code == 422  # Validation error
