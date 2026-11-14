"""Tests for tenant provisioning endpoints, with Proxmox faked."""
import pytest
from fastapi.testclient import TestClient

import api.tenants as tenants
from main import app

client = TestClient(app)


class FakeProxmox:
    class config:
        node = "test-node"

    def __init__(self, existing=None, fail_install=False, token="realtoken123"):
        self.existing = existing or []
        self.fail_install = fail_install
        self.token = token

    def get_lxc_containers(self):
        return self.existing

    def find_next_vmid(self):
        return 200

    def create_lxc_container(self, **kwargs):
        self.created = kwargs

    def wait_for_container(self, node, vmid, status="running"):
        return True

    def install_cyantula(self, node, vmid):
        if self.fail_install:
            raise RuntimeError("pct command failed: secret internals")

    def get_container_ip(self, vmid):
        return "192.168.3.70"

    def get_setup_token(self, vmid):
        return {"token": self.token, "url": f"http://192.168.3.70:8080/setup?token={self.token}"}


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    tenants.tenants_db.clear()
    yield
    tenants.tenants_db.clear()


def use(monkeypatch, fake):
    monkeypatch.setattr(tenants, "_proxmox_client", fake)
    return fake


def test_create_tenant_returns_cyantula_token_and_ip(monkeypatch):
    use(monkeypatch, FakeProxmox())
    r = client.post("/api/tenants", json={"name": "Acme", "slug": "acme"})
    assert r.status_code == 200
    body = r.json()
    assert body["setup_token"] == "realtoken123"
    assert body["setup_url"] == "http://192.168.3.70:8080/setup?token=realtoken123"
    assert body["proxmox_ip"] == "192.168.3.70"


def test_create_tenant_rejects_existing_slug(monkeypatch):
    use(monkeypatch, FakeProxmox(existing=[{"vmid": 150, "status": "running", "name": "acme-tenant"}]))
    r = client.post("/api/tenants", json={"name": "Acme", "slug": "acme"})
    assert r.status_code == 400


def test_create_tenant_failure_hides_internals(monkeypatch):
    use(monkeypatch, FakeProxmox(fail_install=True))
    r = client.post("/api/tenants", json={"name": "Acme", "slug": "acme"})
    assert r.status_code == 500
    detail = r.json()["detail"]
    assert "pct" not in detail and "Traceback" not in detail
    assert "acme" not in tenants.tenants_db


def test_create_tenant_fails_without_setup_token(monkeypatch):
    use(monkeypatch, FakeProxmox(token=None))
    r = client.post("/api/tenants", json={"name": "Acme", "slug": "acme"})
    assert r.status_code == 500


def test_refresh_setup_token_reads_from_container(monkeypatch):
    fake = use(monkeypatch, FakeProxmox())
    client.post("/api/tenants", json={"name": "Acme", "slug": "acme"})
    fake.token = "rotated456"
    r = client.post("/api/tenants/acme/setup-token")
    assert r.status_code == 200
    assert r.json()["setup_token"] == "rotated456"
    assert client.get("/api/tenants/setup-token/rotated456").status_code == 200
