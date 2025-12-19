#!/bin/bash
# Configure tuned service for performance
# Run with: sudo bash setup-tuned.sh

set -e

echo "🎯 Configuring tuned service..."

# Install tuned if not already installed
if ! command -v tuned-adm &> /dev/null; then
    apt-get update
    apt-get install -y tuned
fi

# Enable and start tuned service
systemctl enable tuned
systemctl start tuned

# Set to throughput-performance profile
tuned-adm profile throughput-performance

echo "✅ Tuned service configured with throughput-performance profile!"
echo ""
echo "Current tuned profile:"
tuned-adm active

