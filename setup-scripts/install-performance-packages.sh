#!/bin/bash
# Install performance tuning packages for REIMS2
# Run with: sudo bash install-performance-packages.sh

set -e

echo "📦 Installing performance tuning packages..."

apt-get update
apt-get install -y tuned earlyoom preload cpufrequtils htop

echo "✅ Packages installed successfully!"
echo ""
echo "Next steps:"
echo "1. Configure CPU governor: sudo bash setup-cpu-governor.sh"
echo "2. Apply sysctl settings: sudo sysctl -p /etc/sysctl.d/99-reims2-performance.conf"
echo "3. Configure Docker: sudo bash setup-docker-optimization.sh"

