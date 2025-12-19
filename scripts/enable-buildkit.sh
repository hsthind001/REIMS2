#!/bin/bash
# Enable Docker BuildKit for REIMS2
# This script enables BuildKit globally and for docker-compose

echo "🔧 Enabling Docker BuildKit for REIMS2..."

# Enable BuildKit for current session
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Add to ~/.bashrc if not already present
if ! grep -q "DOCKER_BUILDKIT=1" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# Docker BuildKit for REIMS2" >> ~/.bashrc
    echo "export DOCKER_BUILDKIT=1" >> ~/.bashrc
    echo "export COMPOSE_DOCKER_CLI_BUILD=1" >> ~/.bashrc
    echo "✅ Added BuildKit to ~/.bashrc"
else
    echo "ℹ️  BuildKit already in ~/.bashrc"
fi

# Verify BuildKit is enabled
if [ "$DOCKER_BUILDKIT" = "1" ]; then
    echo "✅ BuildKit enabled for current session"
    echo ""
    echo "To use in current shell, run:"
    echo "  source ~/.bashrc"
    echo ""
    echo "Or manually:"
    echo "  export DOCKER_BUILDKIT=1"
    echo "  export COMPOSE_DOCKER_CLI_BUILD=1"
else
    echo "❌ Failed to enable BuildKit"
    exit 1
fi

echo ""
echo "🚀 BuildKit is now enabled!"
echo "   - Faster builds with advanced caching"
echo "   - Parallel layer builds"
echo "   - Build secrets support"
echo ""
echo "Next steps:"
echo "  1. Restart your terminal or run: source ~/.bashrc"
echo "  2. Build with: docker compose build"
echo "  3. Enjoy faster builds! ⚡"

