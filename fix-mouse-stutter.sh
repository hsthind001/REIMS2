#!/bin/bash

# Mouse/Touchpad Stutter Fix for Acer Predator PHN16-73
# Ubuntu 24.04 LTS - Intel Core Ultra 9 275HX
# Date: 2026-01-03

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Mouse/Touchpad Stutter Fix${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run this script as root or with sudo${NC}"
    exit 1
fi

echo -e "${YELLOW}Detected Touchpad: FTCS1012:00 2808:0352${NC}"
echo ""

# Fix 1: Disable PSR (Panel Self Refresh) - Common cause of stuttering on Intel GPUs
echo -e "${YELLOW}Fix 1: Disabling Intel PSR (Panel Self Refresh)...${NC}"
if [ ! -f /etc/modprobe.d/i915.conf ]; then
    echo "options i915 enable_psr=0" | sudo tee /etc/modprobe.d/i915.conf > /dev/null
    echo -e "${GREEN}✓ Created /etc/modprobe.d/i915.conf${NC}"
else
    if ! grep -q "enable_psr=0" /etc/modprobe.d/i915.conf; then
        echo "options i915 enable_psr=0" | sudo tee -a /etc/modprobe.d/i915.conf > /dev/null
        echo -e "${GREEN}✓ Updated /etc/modprobe.d/i915.conf${NC}"
    else
        echo -e "${GREEN}✓ PSR already disabled${NC}"
    fi
fi
echo ""

# Fix 2: Optimize I2C HID polling
echo -e "${YELLOW}Fix 2: Optimizing I2C HID polling rate...${NC}"
if [ ! -f /etc/modprobe.d/i2c-hid.conf ]; then
    cat << 'EOF' | sudo tee /etc/modprobe.d/i2c-hid.conf > /dev/null
# Reduce I2C HID polling interval for better responsiveness
options i2c_hid poll_mode=1
EOF
    echo -e "${GREEN}✓ Created /etc/modprobe.d/i2c-hid.conf${NC}"
else
    echo -e "${GREEN}✓ i2c-hid.conf already exists${NC}"
fi
echo ""

# Fix 3: Disable USB autosuspend for input devices
echo -e "${YELLOW}Fix 3: Disabling USB autosuspend for input devices...${NC}"
if [ ! -f /etc/udev/rules.d/99-disable-usb-autosuspend.rules ]; then
    cat << 'EOF' | sudo tee /etc/udev/rules.d/99-disable-usb-autosuspend.rules > /dev/null
# Disable USB autosuspend for input devices (prevents stuttering)
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="2808", ATTR{idProduct}=="0352", ATTR{power/control}="on"
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/control", ATTR{power/control}="on"
EOF
    echo -e "${GREEN}✓ Created USB autosuspend rules${NC}"
else
    echo -e "${GREEN}✓ USB autosuspend rules already exist${NC}"
fi
echo ""

# Fix 4: Optimize touchpad settings with libinput
echo -e "${YELLOW}Fix 4: Optimizing touchpad acceleration...${NC}"
xinput set-prop "FTCS1012:00 2808:0352 Touchpad" "libinput Accel Speed" 0.3
echo -e "${GREEN}✓ Set touchpad acceleration to 0.3${NC}"
echo ""

# Fix 5: Disable "Disable While Typing" if it's too aggressive
echo -e "${YELLOW}Fix 5: Adjusting 'Disable While Typing' setting...${NC}"
xinput set-prop "FTCS1012:00 2808:0352 Touchpad" "libinput Disable While Typing Enabled" 0
echo -e "${GREEN}✓ Disabled 'Disable While Typing' (can re-enable if preferred)${NC}"
echo ""

# Fix 6: Create persistent xinput settings
echo -e "${YELLOW}Fix 6: Creating persistent touchpad settings...${NC}"
mkdir -p ~/.config/autostart
cat << 'EOF' > ~/.config/autostart/touchpad-settings.desktop
[Desktop Entry]
Type=Application
Name=Touchpad Settings
Exec=sh -c 'xinput set-prop "FTCS1012:00 2808:0352 Touchpad" "libinput Accel Speed" 0.3; xinput set-prop "FTCS1012:00 2808:0352 Touchpad" "libinput Disable While Typing Enabled" 0'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
echo -e "${GREEN}✓ Created autostart desktop entry${NC}"
echo ""

# Fix 7: Update initramfs
echo -e "${YELLOW}Fix 7: Updating initramfs with new kernel parameters...${NC}"
sudo update-initramfs -u
echo -e "${GREEN}✓ Initramfs updated${NC}"
echo ""

# Fix 8: Install additional touchpad utilities (optional)
echo -e "${YELLOW}Fix 8: Checking for touchpad utilities...${NC}"
if ! command -v libinput &> /dev/null; then
    sudo apt install -y libinput-tools
    echo -e "${GREEN}✓ Installed libinput-tools${NC}"
else
    echo -e "${GREEN}✓ libinput-tools already installed${NC}"
fi
echo ""

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Diagnostic Information${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

echo -e "${YELLOW}Current Touchpad Settings:${NC}"
xinput list-props "FTCS1012:00 2808:0352 Touchpad" | grep -E "Device Enabled|Accel Speed|Disable While Typing"
echo ""

echo -e "${YELLOW}I2C HID Devices:${NC}"
ls -la /sys/bus/i2c/devices/ | grep FTCS || echo "No FTCS devices found in sysfs"
echo ""

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Additional Troubleshooting${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

echo -e "${YELLOW}If stuttering persists, try these additional steps:${NC}"
echo ""
echo "1. Check CPU frequency scaling:"
echo "   sudo apt install cpufrequtils"
echo "   cpufreq-info"
echo ""
echo "2. Disable C-States (power saving that can cause stuttering):"
echo "   Edit /etc/default/grub and add: intel_idle.max_cstate=1"
echo "   sudo update-grub"
echo ""
echo "3. Monitor touchpad events:"
echo "   libinput debug-events --device /dev/input/event4"
echo ""
echo "4. Check for firmware updates:"
echo "   sudo fwupdmgr refresh"
echo "   sudo fwupdmgr get-updates"
echo "   sudo fwupdmgr update"
echo ""
echo "5. Try Wayland instead of X11 (if using X11):"
echo "   Log out and select 'Ubuntu on Wayland' at login screen"
echo ""

echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}✓ Fix Applied!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: Please REBOOT your system for all changes to take effect!${NC}"
echo ""
echo -e "${YELLOW}After reboot, test the touchpad/mouse.${NC}"
echo -e "${YELLOW}If stuttering persists, run: libinput debug-events${NC}"
echo ""
echo "To reboot now: sudo reboot"
echo ""
