#!/bin/bash
# Configure systemd service limits
# Run with: sudo bash setup-systemd-limits.sh

set -e

echo "⚙️  Configuring systemd service limits..."

# Backup existing system.conf
if [ -f /etc/systemd/system.conf ]; then
    cp /etc/systemd/system.conf /etc/systemd/system.conf.backup.$(date +%Y%m%d_%H%M%S)
fi

# Check if limits are already set
if grep -q "^DefaultLimitNOFILE=" /etc/systemd/system.conf; then
    echo "⚠️  DefaultLimitNOFILE already set, updating..."
    sed -i 's/^DefaultLimitNOFILE=.*/DefaultLimitNOFILE=65536/' /etc/systemd/system.conf
else
    echo "DefaultLimitNOFILE=65536" >> /etc/systemd/system.conf
fi

if grep -q "^DefaultLimitNPROC=" /etc/systemd/system.conf; then
    echo "⚠️  DefaultLimitNPROC already set, updating..."
    sed -i 's/^DefaultLimitNPROC=.*/DefaultLimitNPROC=32768/' /etc/systemd/system.conf
else
    echo "DefaultLimitNPROC=32768" >> /etc/systemd/system.conf
fi

echo "✅ Systemd limits configured!"
echo ""
echo "⚠️  Note: These changes require a system reboot to take full effect."
echo "   You can reload systemd with: sudo systemctl daemon-reload"

