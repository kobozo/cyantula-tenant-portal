#!/bin/bash
# Install Cyantula on LXC container
# Uses official install script from releases

set -e

echo "=== Installing Cyantula on LXC ==="

# Install Docker first (required)
apt-get update
apt-get install -y docker.io

# Start Docker
systemctl start docker
systemctl enable docker

# Install Cyantula using official script
curl -fsSL https://github.com/kobozo/cyantula-releases/releases/latest/download/install.sh | sudo bash

echo "=== Cyantula installation complete ==="
echo "Check status: systemctl status cyantula"
echo "View logs: journalctl -u cyantula -f"
