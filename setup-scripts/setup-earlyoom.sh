#!/bin/bash
# Configure earlyoom service
# Run with: sudo bash setup-earlyoom.sh

set -e

echo "🛡️  Configuring earlyoom service..."

# Install earlyoom if not already installed
if ! command -v earlyoom &> /dev/null; then
    apt-get update
    apt-get install -y earlyoom
fi

# Copy configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/earlyoom.conf" /etc/default/earlyoom

# Enable and start earlyoom service
systemctl enable earlyoom
systemctl restart earlyoom

echo "✅ EarlyOOM service configured and started!"
echo ""
echo "EarlyOOM status:"
systemctl status earlyoom --no-pager -l | head -10

