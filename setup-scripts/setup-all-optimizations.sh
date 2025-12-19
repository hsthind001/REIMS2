#!/bin/bash
# Master script to apply all REIMS2 performance optimizations
# Run with: sudo bash setup-all-optimizations.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 REIMS2 Performance Optimization Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Step 1: Install packages
echo "📦 Step 1/8: Installing performance packages..."
bash "$SCRIPT_DIR/install-performance-packages.sh"
echo ""

# Step 2: Configure CPU governor
echo "⚡ Step 2/8: Configuring CPU governor..."
bash "$SCRIPT_DIR/setup-cpu-governor.sh"
echo ""

# Step 3: Apply memory optimizations
echo "💾 Step 3/8: Applying memory optimizations..."
cp "$SCRIPT_DIR/99-reims2-performance.conf" /etc/sysctl.d/
sysctl -p /etc/sysctl.d/99-reims2-performance.conf > /dev/null
echo "✅ Memory optimizations applied"
echo ""

# Step 4: Apply kernel optimizations
echo "🔧 Step 4/8: Applying kernel optimizations..."
cp "$SCRIPT_DIR/99-reims2-kernel.conf" /etc/sysctl.d/
sysctl -p /etc/sysctl.d/99-reims2-kernel.conf > /dev/null
echo "✅ Kernel optimizations applied"
echo ""

# Step 5: Configure Docker
echo "🐳 Step 5/8: Configuring Docker optimization..."
bash "$SCRIPT_DIR/setup-docker-optimization.sh"
echo ""

# Step 6: Configure tuned
echo "🎯 Step 6/8: Configuring tuned service..."
bash "$SCRIPT_DIR/setup-tuned.sh"
echo ""

# Step 7: Configure earlyoom
echo "🛡️  Step 7/8: Configuring earlyoom service..."
bash "$SCRIPT_DIR/setup-earlyoom.sh"
echo ""

# Step 8: Configure systemd limits
echo "⚙️  Step 8/8: Configuring systemd limits..."
bash "$SCRIPT_DIR/setup-systemd-limits.sh"
systemctl daemon-reload
echo "✅ Systemd limits configured"
echo ""

echo "=========================================="
echo "✅ All optimizations applied successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Reboot the system for all changes to take full effect:"
echo "   sudo reboot"
echo ""
echo "2. After reboot, verify optimizations:"
echo "   bash $SCRIPT_DIR/reims2-performance-check.sh"
echo ""
echo "3. Start REIMS2 services:"
echo "   cd /home/hsthind/Documents/GitHub/REIMS2"
echo "   docker compose up -d"
echo ""

