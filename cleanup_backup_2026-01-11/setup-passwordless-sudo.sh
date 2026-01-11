#!/bin/bash
# Setup passwordless sudo for user singh
# Run this ONCE: bash setup-passwordless-sudo.sh

set -e

USERNAME="singh"
SUDOERS_FILE="/etc/sudoers.d/${USERNAME}-nopasswd"

echo "🔧 Configuring passwordless sudo for user: ${USERNAME}"
echo ""
echo "⚠️  WARNING: This will allow sudo commands without password"
echo "    Only do this on your personal development machine!"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

echo ""
echo "📝 Creating sudoers configuration..."

# Create the sudoers file with proper permissions
echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" | sudo tee "${SUDOERS_FILE}" > /dev/null

# Set correct permissions (required for sudoers files)
sudo chmod 0440 "${SUDOERS_FILE}"

# Validate the sudoers file
if sudo visudo -c -f "${SUDOERS_FILE}" 2>&1 | grep -q "parsed OK"; then
    echo "✅ Passwordless sudo configured successfully!"
    echo ""
    echo "🧪 Testing..."
    if sudo -n true 2>/dev/null; then
        echo "✅ Test passed! You can now use sudo without password"
        echo ""
        echo "💡 Try it: sudo apt update"
    else
        echo "⚠️  You may need to open a new terminal for changes to take effect"
    fi
else
    echo "❌ Configuration failed - syntax error"
    sudo rm -f "${SUDOERS_FILE}"
    exit 1
fi

echo ""
echo "📄 Configuration file created: ${SUDOERS_FILE}"
echo "   To revert: sudo rm ${SUDOERS_FILE}"

