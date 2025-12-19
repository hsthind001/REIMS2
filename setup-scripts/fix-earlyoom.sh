#!/bin/bash
# Fix earlyoom service configuration
# Run with: sudo bash fix-earlyoom.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🛡️  Fixing EarlyOOM service configuration..."
echo ""

# Check if earlyoom is installed
if ! command -v earlyoom &> /dev/null; then
    echo "⚠️  earlyoom not installed. Installing..."
    apt-get update
    apt-get install -y earlyoom
fi

# Create a simpler, validated configuration
cat > /etc/default/earlyoom << 'EOF'
# EarlyOOM Configuration for REIMS2
# Free memory threshold: 10%
# Free swap threshold: 5%
# Memory report interval: 60 seconds
# Show notifications: yes

EARLYOOM_ARGS="-r 10 -s 5 -m 60 -n --prefer '(dockerd|containerd|postgres|systemd)' --avoid '(dockerd|containerd|postgres|systemd|kernel)'"
EOF

echo "✅ EarlyOOM configuration updated"

# Reload systemd and restart earlyoom
echo "🔄 Restarting EarlyOOM service..."
systemctl daemon-reload
systemctl enable earlyoom 2>/dev/null || true
systemctl restart earlyoom

sleep 2

# Check status
if systemctl is-active earlyoom > /dev/null 2>&1; then
    echo "✅ EarlyOOM service is now active!"
    echo ""
    echo "EarlyOOM status:"
    systemctl status earlyoom --no-pager -l | head -15
else
    echo "⚠️  EarlyOOM service still not active"
    echo ""
    echo "Checking logs:"
    journalctl -xeu earlyoom.service --no-pager | tail -20
    echo ""
    echo "Trying manual start to see error:"
    earlyoom --version || true
fi

