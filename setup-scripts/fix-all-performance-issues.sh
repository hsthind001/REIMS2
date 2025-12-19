#!/bin/bash
# Fix all performance optimization issues
# Run with: sudo bash fix-all-performance-issues.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Fixing REIMS2 Performance Optimization Issues"
echo "================================================"
echo ""

# Step 1: Fix Docker daemon configuration
echo "🐳 Step 1/4: Fixing Docker daemon configuration..."
if [ -f /etc/docker/daemon.json ]; then
    # Backup existing config
    BACKUP_FILE="/etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)"
    cp /etc/docker/daemon.json "$BACKUP_FILE"
    echo "   📋 Backed up existing config to $BACKUP_FILE"
fi

# Create safe Docker daemon configuration
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

echo "   ✅ Docker daemon.json updated (using safe configuration)"

# Restart Docker
echo "   🔄 Restarting Docker service..."
if systemctl restart docker; then
    sleep 3
    if docker info > /dev/null 2>&1; then
        echo "   ✅ Docker is running successfully!"
    else
        echo "   ⚠️  Docker restarted but may have issues"
    fi
else
    echo "   ❌ Failed to restart Docker"
    echo "   Check logs: sudo journalctl -xeu docker.service --no-pager | tail -30"
fi
echo ""

# Step 2: Enable and start tuned
echo "🎯 Step 2/4: Configuring tuned service..."
if command -v tuned-adm &> /dev/null; then
    systemctl enable tuned 2>/dev/null || true
    systemctl start tuned 2>/dev/null || true
    sleep 1
    if systemctl is-active tuned > /dev/null 2>&1; then
        tuned-adm profile throughput-performance 2>/dev/null || true
        echo "   ✅ Tuned service is active"
    else
        echo "   ⚠️  Tuned service failed to start"
    fi
else
    echo "   ⚠️  tuned-adm not found (tuned may not be installed)"
fi
echo ""

# Step 3: Enable and start earlyoom
echo "🛡️  Step 3/4: Configuring earlyoom service..."
if command -v earlyoom &> /dev/null; then
    # Ensure config file exists
    if [ -f "$SCRIPT_DIR/earlyoom.conf" ]; then
        cp "$SCRIPT_DIR/earlyoom.conf" /etc/default/earlyoom
    fi
    
    systemctl enable earlyoom 2>/dev/null || true
    systemctl restart earlyoom 2>/dev/null || true
    sleep 1
    if systemctl is-active earlyoom > /dev/null 2>&1; then
        echo "   ✅ EarlyOOM service is active"
    else
        echo "   ⚠️  EarlyOOM service failed to start"
        echo "   Check logs: sudo journalctl -xeu earlyoom.service --no-pager | tail -20"
    fi
else
    echo "   ⚠️  earlyoom not found (may not be installed)"
fi
echo ""

# Step 4: Verify CPU governor
echo "⚡ Step 4/4: Verifying CPU governor..."
if command -v cpufreq-info &> /dev/null; then
    # Check if performance governor is set
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        if [ -f "$cpu" ]; then
            CURRENT_GOV=$(cat "$cpu" 2>/dev/null || echo "unknown")
            if [ "$CURRENT_GOV" != "performance" ]; then
                echo "   ⚠️  CPU $(basename $(dirname $(dirname $cpu))) governor: $CURRENT_GOV (should be 'performance')"
                # Try to set it
                echo "performance" | sudo tee "$cpu" > /dev/null 2>&1 || true
            fi
        fi
    done
    echo "   ✅ CPU governor check complete"
else
    echo "   ⚠️  cpufrequtils not available"
fi
echo ""

echo "================================================"
echo "✅ All fixes applied!"
echo ""
echo "Next steps:"
echo "1. Run performance check: bash setup-scripts/reims2-performance-check.sh"
echo "2. If Docker is working, start REIMS2: cd /home/hsthind/Documents/GitHub/REIMS2 && docker compose up -d"

