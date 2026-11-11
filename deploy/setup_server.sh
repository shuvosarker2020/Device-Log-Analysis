#!/usr/bin/env bash
# ==============================================================================
# NetLogIQ - Production Server Automated Setup Script (Ubuntu / Debian)
# ==============================================================================
set -e

echo "=================================================="
echo " Starting NetLogIQ Production Server Installation"
echo "=================================================="

# 1. Update and install prerequisites
echo "[1/6] Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git curl ufw libcap2-bin

# 2. Setup directory and user
echo "[2/6] Preparing /opt/netlogiq and user..."
sudo id -u netlogiq &>/dev/null || sudo useradd -r -s /bin/false -d /opt/netlogiq netlogiq
sudo mkdir -p /opt/netlogiq

# Determine current source location
CURRENT_DIR="$(pwd)"
if [ "$CURRENT_DIR" != "/opt/netlogiq" ] && [ -f "$CURRENT_DIR/run.py" ]; then
    echo "Copying repository files from $CURRENT_DIR to /opt/netlogiq..."
    sudo cp -r "$CURRENT_DIR"/* /opt/netlogiq/
elif [ ! -f "/opt/netlogiq/run.py" ]; then
    echo "Cloning fresh repository to /opt/netlogiq..."
    sudo git clone https://github.com/shuvosarker2020/Device-Log-Analysis.git /opt/netlogiq
fi

sudo mkdir -p /opt/netlogiq/data

# 3. Setup Python Virtual Environment
echo "[3/6] Setting up Python virtual environment..."
cd /opt/netlogiq
if [ ! -d "/opt/netlogiq/venv" ]; then
    sudo python3 -m venv /opt/netlogiq/venv
fi

sudo /opt/netlogiq/venv/bin/pip install --upgrade pip
sudo /opt/netlogiq/venv/bin/pip install -r /opt/netlogiq/requirements.txt

# 4. Set directory permissions
echo "[4/6] Configuring file permissions..."
sudo chown -R netlogiq:netlogiq /opt/netlogiq
sudo chmod 750 /opt/netlogiq

# 5. Setup Systemd Service
echo "[5/6] Installing and starting systemd service..."
sudo cp /opt/netlogiq/deploy/netlogiq.service /etc/systemd/system/netlogiq.service
sudo systemctl daemon-reload
sudo systemctl enable netlogiq
sudo systemctl restart netlogiq

# 6. Configure Firewall (UFW)
echo "[6/6] Configuring firewall rules..."
if command -v ufw &>/dev/null; then
    sudo ufw allow 8000/tcp comment 'NetLogIQ Web Dashboard' || true
    sudo ufw allow 514/udp comment 'Syslog UDP Port' || true
    sudo ufw allow 514/tcp comment 'Syslog TCP Port' || true
fi

echo "=================================================="
echo " Installation Complete!"
echo " Service Status:"
sudo systemctl status netlogiq --no-pager
echo "=================================================="
echo " Web Dashboard: http://$(hostname -I | awk '{print $1}'):8000"
echo " Syslog UDP/TCP Port: 514"
echo "=================================================="
