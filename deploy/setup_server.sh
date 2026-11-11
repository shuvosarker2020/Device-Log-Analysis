#!/usr/bin/env bash
# ==============================================================================
# NetLogIQ - Production Server Automated Setup Script (Ubuntu / Debian)
# ==============================================================================
set -e

echo "=================================================="
echo " Starting NetLogIQ Production Server Installation"
echo "=================================================="

# 1. Update and install prerequisites
echo "[1/7] Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git curl ufw libcap2-bin

# 2. Create service user and directory
echo "[2/7] Creating service user and directory..."
sudo id -u netlogiq &>/dev/null || sudo useradd -r -s /bin/false -d /opt/netlogiq netlogiq
sudo mkdir -p /opt/netlogiq
sudo cp -r . /opt/netlogiq/
sudo mkdir -p /opt/netlogiq/data

# 3. Setup Python Virtual Environment
echo "[3/7] Setting up Python virtual environment..."
cd /opt/netlogiq
sudo python3 -m venv venv
sudo /opt/netlogiq/venv/bin/pip install --upgrade pip
sudo /opt/netlogiq/venv/bin/pip install -r requirements.txt

# 4. Set directory permissions
echo "[4/7] Configuring file permissions..."
sudo chown -R netlogiq:netlogiq /opt/netlogiq
sudo chmod 750 /opt/netlogiq

# 5. Setup Systemd Service
echo "[5/7] Installing systemd service..."
sudo cp /opt/netlogiq/deploy/netlogiq.service /etc/systemd/system/netlogiq.service
sudo systemctl daemon-reload
sudo systemctl enable netlogiq
sudo systemctl restart netlogiq

# 6. Configure Firewall (UFW)
echo "[6/7] Configuring firewall rules..."
sudo ufw allow 8000/tcp comment 'NetLogIQ Web Dashboard'
sudo ufw allow 514/udp comment 'Syslog UDP Port'
sudo ufw allow 514/tcp comment 'Syslog TCP Port'

echo "=================================================="
echo " Installation Complete!"
echo " Service Status:"
sudo systemctl status netlogiq --no-pager
echo "=================================================="
echo " Web Dashboard: http://<SERVER_IP>:8000"
echo " Syslog UDP/TCP Port: 514"
echo "=================================================="
