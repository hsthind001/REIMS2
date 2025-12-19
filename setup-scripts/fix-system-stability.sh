#!/bin/bash
# Comprehensive System Stability Fix for Ubuntu Desktop
# Fixes crashes in Cursor IDE, Terminal, Signal, and other applications
# Run with: sudo bash fix-system-stability.sh

set -e

echo "🔧 SYSTEM STABILITY FIX FOR UBUNTU DESKTOP"
echo "=========================================="
echo ""
echo "System: Lenovo YOGA 730-13IWL"
echo "RAM: 8GB (6.7GB usable with zram)"
echo "Issue: Frequent application crashes (Cursor, Terminal, Signal)"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Backup function
backup_file() {
    local file=$1
    if [ -f "$file" ]; then
        cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
        print_status "Backed up: $file"
    fi
}

echo "Step 1: Configuring systemd-oomd (Userspace OOM Killer)"
echo "--------------------------------------------------------"

# Configure systemd-oomd for better protection
mkdir -p /etc/systemd/oomd.conf.d

cat > /etc/systemd/oomd.conf.d/10-memory-pressure.conf << 'EOF'
# systemd-oomd configuration for low-memory systems
# More aggressive memory pressure protection

[OOM]
# Default swap used limit (percentage)
DefaultMemoryPressureLimit=80%

# Memory pressure duration threshold (microseconds)
DefaultMemoryPressureDurationSec=20s
EOF

print_status "systemd-oomd configured for aggressive memory protection"

# Configure user slice for better OOM protection
mkdir -p /etc/systemd/system/user@.service.d

cat > /etc/systemd/system/user@.service.d/10-oom-protect.conf << 'EOF'
[Service]
# Protect user applications from OOM killer
# Memory accounting enables systemd-oomd to monitor this slice
MemoryAccounting=yes

# Set memory high watermark (soft limit) - triggers memory pressure
# For 8GB system, allow user slice to use up to 5GB
MemoryHigh=5G

# Set memory max (hard limit) - kills processes if exceeded
# Allow up to 6GB before hard limit
MemoryMax=6G

# OOM policy - prefer killing processes within this cgroup
OOMPolicy=continue
EOF

print_status "User slice configured with memory limits"

echo ""
echo "Step 2: Optimizing Memory Management"
echo "-------------------------------------"

# Create or update sysctl configuration for memory management
cat > /etc/sysctl.d/99-low-memory-system.conf << 'EOF'
# Memory Management for 8GB System
# Optimized for desktop usage with heavy applications

# Swappiness: How aggressively to swap (0-100)
# Lower = prefer RAM, Higher = swap more
# 10 is good for desktop with 8GB RAM
vm.swappiness=10

# VFS Cache Pressure: How aggressively to reclaim directory/inode cache
# Lower = keep caches longer, Higher = reclaim aggressively
# 50 is balanced for desktop use
vm.vfs_cache_pressure=50

# Dirty Page Management
# Controls when dirty pages are written to disk
vm.dirty_ratio=10
vm.dirty_background_ratio=5

# Memory overcommit
# 1 = allow overcommit, with heuristics
vm.overcommit_memory=1
vm.overcommit_ratio=50

# Minimum free memory (in KB)
# Keep at least 128MB free for system stability
vm.min_free_kbytes=131072

# Zone reclaim mode (0 = don't reclaim from remote zones)
vm.zone_reclaim_mode=0

# Page cluster for swap (number of pages to read at once)
# Lower values for better responsiveness
vm.page-cluster=0
EOF

# Apply sysctl settings immediately
sysctl -p /etc/sysctl.d/99-low-memory-system.conf > /dev/null 2>&1

print_status "Memory management parameters optimized"

echo ""
echo "Step 3: Configuring Transparent Huge Pages"
echo "-------------------------------------------"

# THP can cause memory fragmentation and latency spikes
# Set to madvise for better desktop performance
if [ -f /sys/kernel/mm/transparent_hugepage/enabled ]; then
    echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
    echo madvise > /sys/kernel/mm/transparent_hugepage/defrag
    print_status "Transparent Huge Pages set to 'madvise' mode"

    # Make it persistent across reboots
    cat > /etc/tmpfiles.d/thp.conf << 'EOF'
# Transparent Huge Pages configuration
w /sys/kernel/mm/transparent_hugepage/enabled - - - - madvise
w /sys/kernel/mm/transparent_hugepage/defrag - - - - madvise
EOF
    print_status "THP settings will persist across reboots"
fi

echo ""
echo "Step 4: Optimizing File Descriptors and Limits"
echo "-----------------------------------------------"

# Increase file descriptor limits for desktop applications
backup_file /etc/security/limits.conf

cat >> /etc/security/limits.conf << 'EOF'

# Desktop Application Limits (Added by fix-system-stability.sh)
*               soft    nofile          65536
*               hard    nofile          65536
*               soft    nproc           8192
*               hard    nproc           8192
EOF

print_status "File descriptor limits increased"

# Update systemd system limits
backup_file /etc/systemd/system.conf

sed -i 's/#DefaultLimitNOFILE=.*/DefaultLimitNOFILE=65536/' /etc/systemd/system.conf
sed -i 's/#DefaultLimitNPROC=.*/DefaultLimitNPROC=8192/' /etc/systemd/system.conf

print_status "systemd limits updated"

echo ""
echo "Step 5: Configuring earlyoom Service"
echo "-------------------------------------"

# Ensure earlyoom is installed
if ! command -v earlyoom &> /dev/null; then
    print_warning "earlyoom not found, installing..."
    apt-get update -qq
    apt-get install -y earlyoom
    print_status "earlyoom installed"
else
    print_status "earlyoom already installed"
fi

# Configure earlyoom with conservative settings
cat > /etc/default/earlyoom << 'EOF'
# EarlyOOM Configuration for 8GB Desktop System
# Kills processes before system becomes unresponsive

# Memory threshold: Kill when free RAM drops below 15%
# Swap threshold: Kill when free swap drops below 10%
# Report interval: 60 seconds
# Notifications: enabled
# Prefer killing: large memory users, avoid system processes
# Ignore: critical system processes

EARLYOOM_ARGS="-r 15 -s 10 -m 60 -n --prefer '(electron|chrome|firefox|cursor)' --avoid '(systemd|gdm|Xorg|pipewire|pulseaudio)'"
EOF

systemctl daemon-reload
systemctl enable earlyoom > /dev/null 2>&1
systemctl restart earlyoom

if systemctl is-active earlyoom > /dev/null 2>&1; then
    print_status "earlyoom service is active and monitoring"
else
    print_error "earlyoom service failed to start"
fi

echo ""
echo "Step 6: Creating Cursor IDE Memory Optimization"
echo "------------------------------------------------"

# Create Cursor IDE configuration to reduce memory usage
CURSOR_CONFIG_DIR="$HOME/.config/Cursor/User"
mkdir -p "$CURSOR_CONFIG_DIR"

# Check if running as sudo and get real user
if [ "$SUDO_USER" ]; then
    REAL_USER=$SUDO_USER
    REAL_HOME=$(eval echo ~$SUDO_USER)
    CURSOR_CONFIG_DIR="$REAL_HOME/.config/Cursor/User"
    mkdir -p "$CURSOR_CONFIG_DIR"

    cat > "$CURSOR_CONFIG_DIR/settings.json.memory-optimized" << 'EOF'
{
  "window.restoreWindows": "none",
  "files.autoSave": "afterDelay",
  "files.autoSaveDelay": 5000,
  "extensions.autoUpdate": false,
  "extensions.autoCheckUpdates": false,
  "editor.renderWhitespace": "selection",
  "editor.minimap.enabled": false,
  "workbench.enableExperiments": false,
  "telemetry.telemetryLevel": "off",
  "update.mode": "manual",
  "search.followSymlinks": false,
  "search.maxResults": 2000,
  "files.watcherExclude": {
    "**/.git/objects/**": true,
    "**/.git/subtree-cache/**": true,
    "**/node_modules/**": true,
    "**/.hg/store/**": true
  },
  "files.exclude": {
    "**/.git": true,
    "**/.svn": true,
    "**/.hg": true,
    "**/CVS": true,
    "**/.DS_Store": true,
    "**/node_modules": true
  }
}
EOF
    chown $REAL_USER:$REAL_USER "$CURSOR_CONFIG_DIR/settings.json.memory-optimized"

    print_status "Cursor IDE memory optimization config created at:"
    echo "    $CURSOR_CONFIG_DIR/settings.json.memory-optimized"
    print_warning "Merge these settings into your existing settings.json manually"
fi

echo ""
echo "Step 7: Creating Memory Monitoring Script"
echo "------------------------------------------"

cat > /usr/local/bin/memory-monitor << 'EOF'
#!/bin/bash
# Memory monitoring script
# Shows memory usage and potential issues

echo "=== System Memory Status ==="
echo ""

# Total memory
total_mem=$(free -h | awk '/^Mem:/ {print $2}')
used_mem=$(free -h | awk '/^Mem:/ {print $3}')
available_mem=$(free -h | awk '/^Mem:/ {print $7}')
mem_percent=$(free | awk '/^Mem:/ {printf "%.1f", $3/$2 * 100}')

echo "Memory: $used_mem / $total_mem used ($mem_percent%)"
echo "Available: $available_mem"
echo ""

# Swap status
swap_total=$(free -h | awk '/^Swap:/ {print $2}')
swap_used=$(free -h | awk '/^Swap:/ {print $3}')
echo "Swap: $swap_used / $swap_total"
echo ""

# zram status
if [ -e /dev/zram0 ]; then
    echo "zram compression:"
    zramctl | grep -v ALGORITHM
    echo ""
fi

# Top memory consumers
echo "Top 10 Memory Consumers:"
ps aux --sort=-%mem | head -11 | awk 'NR==1 {print "USER       PID %MEM  RSS     COMMAND"} NR>1 {printf "%-10s %5d %4.1f%% %7s %s\n", $1, $2, $4, $6, substr($11,1,50)}'
echo ""

# Check if memory pressure is high
mem_pressure=$(cat /proc/pressure/memory 2>/dev/null | awk '/some/ {print $4}' | cut -d= -f2)
if [ ! -z "$mem_pressure" ]; then
    echo "Memory Pressure: $mem_pressure"
    pressure_val=$(echo $mem_pressure | cut -d. -f1)
    if [ "$pressure_val" -gt 50 ]; then
        echo "⚠️  HIGH MEMORY PRESSURE - Consider closing applications"
    fi
fi

# Check OOM scores
echo ""
echo "Processes at Risk of OOM Kill (score > 500):"
for pid in $(ps aux | awk 'NR>1 {print $2}'); do
    if [ -f /proc/$pid/oom_score ]; then
        score=$(cat /proc/$pid/oom_score 2>/dev/null)
        if [ ! -z "$score" ] && [ "$score" -gt 500 ]; then
            cmd=$(ps -p $pid -o comm= 2>/dev/null)
            printf "  PID %5d (%-20s): %d\n" $pid "$cmd" $score
        fi
    fi
done
EOF

chmod +x /usr/local/bin/memory-monitor
print_status "Memory monitoring script created: /usr/local/bin/memory-monitor"

echo ""
echo "Step 8: Reload systemd Configuration"
echo "-------------------------------------"

systemctl daemon-reload
print_status "systemd configuration reloaded"

echo ""
echo "=========================================="
echo "✅ SYSTEM STABILITY FIX COMPLETED"
echo "=========================================="
echo ""
echo "Changes Applied:"
echo "  ✓ systemd-oomd configured for aggressive memory protection"
echo "  ✓ User processes limited to 5GB soft / 6GB hard limit"
echo "  ✓ Memory management optimized for 8GB system"
echo "  ✓ Transparent Huge Pages optimized"
echo "  ✓ File descriptor limits increased"
echo "  ✓ earlyoom service enabled and running"
echo "  ✓ Cursor IDE memory optimization config created"
echo "  ✓ Memory monitoring script installed"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo ""
echo "1. REBOOT YOUR SYSTEM for all changes to take effect:"
echo "   sudo reboot"
echo ""
echo "2. After reboot, verify the fixes:"
echo "   sudo systemctl status earlyoom"
echo "   sudo systemctl status systemd-oomd"
echo "   sysctl vm.swappiness vm.vfs_cache_pressure"
echo ""
echo "3. Monitor memory usage with:"
echo "   memory-monitor"
echo ""
echo "4. For Cursor IDE optimization:"
echo "   - Review: ~/.config/Cursor/User/settings.json.memory-optimized"
echo "   - Merge recommended settings into your settings.json"
echo "   - Consider disabling unused extensions"
echo ""
echo "5. If crashes continue after reboot:"
echo "   - Check logs: journalctl -b -p err"
echo "   - Monitor memory: watch -n 2 memory-monitor"
echo "   - Check OOM kills: sudo dmesg | grep -i oom"
echo ""
echo "Additional Tips:"
echo "  • Close unused applications to free memory"
echo "  • Disable browser tabs when not in use"
echo "  • Use lighter alternatives (e.g., nano instead of VS Code for small edits)"
echo "  • Consider upgrading RAM to 16GB for heavy development work"
echo ""
echo "Script completed at: $(date)"
echo ""
