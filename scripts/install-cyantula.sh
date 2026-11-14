#!/bin/bash
# Install Cyantula on LXC container
# Run this script inside the LXC container

set -e

echo "=== Installing Cyantula ==="

# Update system
apt-get update
apt-get install -y curl git wget

# Install Docker
curl -fsSL https://get.docker.com -o /tmp/install-docker.sh
bash /tmp/install-docker.sh

# Start Docker
systemctl start docker
systemctl enable docker

# Clone Cyantula
cd /opt
git clone https://github.com/kobozo/cyantula.git
cd cyantula

# Build and install
make build
make install

# Create data directory
mkdir -p /var/lib/cyantula
chown -R cyantula:cyantula /var/lib/cyantula

# Setup environment
cat > /etc/cyantula.env << EOF
# Cyantula Configuration
DATABASE_URL=postgresql://cyantula:password@localhost:5432/cyantula
REDIS_URL=redis://localhost:6379
CLUSTER_HOST=0.0.0.0
CLUSTER_PORT=7443
CLUSTER_CERT_FILE=/etc/cyantula/cert.pem
CLUSTER_KEY_FILE=/etc/cyantula/key.pem
EOF

# Setup SSL certificates
mkdir -p /etc/cyantula
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/cyantula/key.pem \
  -out /etc/cyantula/cert.pem \
  -subj "/CN=$(hostname)"

# Start Cyantula
systemctl start cyantula
systemctl enable cyantula

echo "=== Cyantula installation complete ==="
echo "Access via: https://$(hostname).cyantula.eu"
