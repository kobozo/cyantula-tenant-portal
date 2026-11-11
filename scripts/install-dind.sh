#!/bin/bash
# Install Docker-in-Docker for Cyantula tenant
# This creates an isolated Docker environment for the tenant

set -e

echo "=== Installing Docker-in-Docker for Cyantula ==="

# Update system
apt-get update
apt-get install -y docker.io docker-compose curl

# Create Docker data directory
mkdir -p /var/lib/docker-tenant
mkdir -p /etc/docker-tenant

# Create Docker daemon config for tenant isolation
cat > /etc/docker-tenant/daemon.json << EOF
{
  "data-root": "/var/lib/docker-tenant",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "bip": "172.20.0.1/24",
  "fixed-cidr": "172.20.0.0/24"
}
EOF

# Start Docker daemon for tenant
systemctl stop docker || true
systemctl disable docker || true

# Create tenant-specific Docker service
cat > /etc/systemd/system/docker-tenant.service << EOF
[Unit]
Description=Docker Application Container Engine (Tenant)
After=network.target

[Service]
Type=docker
ExecStart=/usr/bin/dockerd --config-file=/etc/docker-tenant/daemon.json
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Start tenant Docker
systemctl daemon-reload
systemctl start docker-tenant
systemctl enable docker-tenant

# Allow tenant user to use Docker
useradd -m -s /bin/bash tenant 2>/dev/null || true
usermod -aG docker-tenant tenant

# Create SSH key for tenant access
su - tenant -c "ssh-keygen -t ed25519 -f /home/tenant/.ssh/id_ed25519 -N ''" 2>/dev/null || true

echo "=== Docker-in-Docker installation complete ==="
echo "Docker daemon running on: 172.20.0.1"
echo "Tenant user created for access"
