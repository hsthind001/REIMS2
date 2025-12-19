#!/bin/bash
# Configure Docker daemon for optimal performance
# Run with: sudo bash setup-docker-optimization.sh

set -e

echo "🐳 Configuring Docker daemon optimization..."

# Backup existing daemon.json if it exists
if [ -f /etc/docker/daemon.json ]; then
    echo "📋 Backing up existing /etc/docker/daemon.json..."
    cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
fi

# Copy new configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/docker-daemon.json" /etc/docker/daemon.json

echo "✅ Docker daemon.json configured!"
echo ""
echo "⚠️  Validating Docker configuration..."
if ! docker info > /dev/null 2>&1; then
    echo "⚠️  Docker is not running. Testing configuration syntax..."
    dockerd --validate --config-file /etc/docker/daemon.json 2>&1 || {
        echo "❌ Docker daemon.json has syntax errors. Restoring backup..."
        if [ -f /etc/docker/daemon.json.backup.* ]; then
            RESTORE_FILE=$(ls -t /etc/docker/daemon.json.backup.* 2>/dev/null | head -1)
            if [ -n "$RESTORE_FILE" ]; then
                cp "$RESTORE_FILE" /etc/docker/daemon.json
                echo "✅ Restored backup configuration"
            fi
        fi
        exit 1
    }
fi

echo "⚠️  Restarting Docker service (this will restart all containers)..."
if systemctl restart docker; then
    echo "✅ Docker restarted with new configuration!"
    sleep 2
    echo ""
    echo "Verifying Docker configuration:"
    docker info 2>/dev/null | grep -E "(Memory|CPUs|Storage Driver|Logging Driver)" | head -5 || echo "Docker is starting up..."
else
    echo "❌ Failed to restart Docker. Checking logs..."
    echo "Run: sudo journalctl -xeu docker.service --no-pager | tail -30"
    echo "If needed, restore backup: sudo cp /etc/docker/daemon.json.backup.* /etc/docker/daemon.json"
    exit 1
fi

