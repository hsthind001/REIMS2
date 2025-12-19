#!/bin/bash
# Fix Docker configuration if it failed
# Run with: sudo bash fix-docker-config.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Fixing Docker configuration..."

# Check if there's a backup
if ls /etc/docker/daemon.json.backup.* > /dev/null 2>&1; then
    RESTORE_FILE=$(ls -t /etc/docker/daemon.json.backup.* | head -1)
    echo "📋 Found backup: $RESTORE_FILE"
    echo "Restoring backup..."
    cp "$RESTORE_FILE" /etc/docker/daemon.json
    echo "✅ Backup restored"
else
    echo "⚠️  No backup found. Creating minimal valid configuration..."
    cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
    echo "✅ Created minimal configuration"
fi

# Try to restart Docker
echo ""
echo "🔄 Restarting Docker..."
if systemctl restart docker; then
    sleep 2
    if docker info > /dev/null 2>&1; then
        echo "✅ Docker is running successfully!"
        echo ""
        echo "Docker info:"
        docker info | grep -E "(Memory|CPUs|Storage Driver|Logging Driver)" | head -5
    else
        echo "⚠️  Docker restarted but not responding. Check status:"
        echo "   sudo systemctl status docker"
    fi
else
    echo "❌ Failed to restart Docker. Check logs:"
    echo "   sudo journalctl -xeu docker.service --no-pager | tail -30"
    exit 1
fi


