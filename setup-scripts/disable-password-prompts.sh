#!/bin/bash
# Disable Password Prompts for Applications and Sudo
# ⚠️ WARNING: This reduces system security significantly
# Run with: sudo bash disable-password-prompts.sh

set -e

echo "⚠️  PASSWORD PROMPT REMOVAL SCRIPT"
echo "=================================="
echo ""
echo "This script will:"
echo "1. Fix the keyring unlock prompt (safe)"
echo "2. Enable passwordless sudo (REDUCES SECURITY)"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Get the actual user
if [ "$SUDO_USER" ]; then
    ACTUAL_USER=$SUDO_USER
    ACTUAL_HOME=$(eval echo ~$SUDO_USER)
else
    ACTUAL_USER=$USER
    ACTUAL_HOME=$HOME
fi

echo "User: $ACTUAL_USER"
echo ""

# PART 1: Fix Keyring
echo "Part 1: Fixing Keyring Unlock Prompt"
echo "-------------------------------------"

KEYRING_DIR="$ACTUAL_HOME/.local/share/keyrings"
if [ -d "$KEYRING_DIR" ]; then
    print_warning "Backing up existing keyring..."
    [ -f "$KEYRING_DIR/login.keyring" ] && mv "$KEYRING_DIR/login.keyring" "$KEYRING_DIR/login.keyring.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    [ -f "$KEYRING_DIR/Default.keyring" ] && mv "$KEYRING_DIR/Default.keyring" "$KEYRING_DIR/Default.keyring.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    print_status "Keyrings backed up"
fi

# Disable keyring via PAM
if [ -f /etc/pam.d/gdm-password ]; then
    cp /etc/pam.d/gdm-password /etc/pam.d/gdm-password.backup.$(date +%Y%m%d_%H%M%S)
    sed -i 's/^auth.*pam_gnome_keyring.so$/#&/' /etc/pam.d/gdm-password 2>/dev/null || true
    sed -i 's/^session.*pam_gnome_keyring.so.*auto_start$/#&/' /etc/pam.d/gdm-password 2>/dev/null || true
    print_status "GDM PAM configuration updated"
fi

if [ -f /etc/pam.d/gdm-autologin ]; then
    cp /etc/pam.d/gdm-autologin /etc/pam.d/gdm-autologin.backup.$(date +%Y%m%d_%H%M%S)
    sed -i 's/^auth.*pam_gnome_keyring.so$/#&/' /etc/pam.d/gdm-autologin 2>/dev/null || true
    sed -i 's/^session.*pam_gnome_keyring.so.*auto_start$/#&/' /etc/pam.d/gdm-autologin 2>/dev/null || true
    print_status "GDM autologin PAM updated"
fi

mkdir -p "$ACTUAL_HOME/.config/autostart"
cat > "$ACTUAL_HOME/.config/autostart/gnome-keyring-ssh.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=SSH Key Agent
Hidden=true
EOF
chown $ACTUAL_USER:$ACTUAL_USER "$ACTUAL_HOME/.config/autostart/gnome-keyring-ssh.desktop"
print_status "Keyring disabled for user session"

echo ""

# PART 2: Passwordless Sudo
echo "Part 2: Configuring Passwordless Sudo"
echo "--------------------------------------"
print_warning "⚠️  This SIGNIFICANTLY reduces system security"
echo ""

SUDOERS_FILE="/etc/sudoers.d/99-passwordless-sudo-$ACTUAL_USER"
[ -f "$SUDOERS_FILE" ] && cp "$SUDOERS_FILE" "${SUDOERS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

cat > "$SUDOERS_FILE" << EOF
# Passwordless sudo for user: $ACTUAL_USER
# ⚠️ WARNING: Allows ALL commands as root without password
$ACTUAL_USER ALL=(ALL) NOPASSWD: ALL
EOF

chmod 0440 "$SUDOERS_FILE"

if visudo -c -f "$SUDOERS_FILE" 2>/dev/null; then
    print_status "Passwordless sudo configured"
else
    echo "ERROR: Sudoers validation failed"
    rm -f "$SUDOERS_FILE"
    exit 1
fi

echo ""

# PART 3: PolicyKit
echo "Part 3: Configuring PolicyKit"
echo "------------------------------"

mkdir -p /etc/polkit-1/rules.d
cat > /etc/polkit-1/rules.d/49-nopasswd-for-user.rules << EOF
/* Disable password prompts for: $ACTUAL_USER */
polkit.addRule(function(action, subject) {
    if (subject.user == "$ACTUAL_USER") {
        return polkit.Result.YES;
    }
});
EOF

print_status "PolicyKit configured"
echo ""

echo "=========================================="
echo "✅ CONFIGURATION COMPLETE"
echo "=========================================="
echo ""
echo "Changes:"
echo "1. ✅ Keyring unlock disabled"
echo "2. ✅ Passwordless sudo enabled"
echo "3. ✅ PolicyKit prompts disabled"
echo ""
echo "⚠️  SECURITY WARNING: System is now less secure"
echo ""
echo "Next Steps:"
echo "1. LOG OUT and LOG BACK IN for changes to take effect"
echo "2. Test: sudo whoami (should not ask password)"
echo ""
echo "To Revert:"
echo "  sudo rm $SUDOERS_FILE"
echo "  sudo rm /etc/polkit-1/rules.d/49-nopasswd-for-user.rules"
echo ""
