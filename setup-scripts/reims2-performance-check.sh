#!/bin/bash
# REIMS2 Performance Optimization Validation Script
# Run with: bash reims2-performance-check.sh

echo "🔍 REIMS2 Performance Optimization Check"
echo "========================================"
echo ""

# Check CPU Governor
echo "1. CPU Governor Status:"
if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    CURRENT_GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "unknown")
    if [ "$CURRENT_GOV" = "performance" ]; then
        echo "   ✅ CPU Governor: $CURRENT_GOV (optimal)"
    else
        echo "   ⚠️  CPU Governor: $CURRENT_GOV (should be 'performance')"
    fi
elif command -v cpufreq-info &> /dev/null; then
    CURRENT_GOV=$(cpufreq-info -c 0 -p 2>/dev/null | grep -oP 'governor: \K\w+' || echo "unknown")
    if [ "$CURRENT_GOV" = "performance" ]; then
        echo "   ✅ CPU Governor: $CURRENT_GOV (optimal)"
    else
        echo "   ⚠️  CPU Governor: $CURRENT_GOV (should be 'performance')"
    fi
else
    echo "   ⚠️  Cannot determine CPU governor (cpufrequtils not installed or no access)"
fi
echo ""

# Check sysctl settings
echo "2. Memory Management Settings:"
SWAPPINESS=$(cat /proc/sys/vm/swappiness 2>/dev/null || echo "N/A")
VFS_CACHE=$(cat /proc/sys/vm/vfs_cache_pressure 2>/dev/null || echo "N/A")

if [ "$SWAPPINESS" = "10" ]; then
    echo "   ✅ Swappiness: $SWAPPINESS (optimal)"
else
    echo "   ⚠️  Swappiness: $SWAPPINESS (should be 10)"
fi

if [ "$VFS_CACHE" = "50" ]; then
    echo "   ✅ vfs_cache_pressure: $VFS_CACHE (optimal)"
else
    echo "   ⚠️  vfs_cache_pressure: $VFS_CACHE (should be 50)"
fi
echo ""

# Check Docker configuration
echo "3. Docker Configuration:"
if [ -f /etc/docker/daemon.json ]; then
    echo "   ✅ Docker daemon.json exists"
    if grep -q "oom-score-adjust" /etc/docker/daemon.json; then
        echo "   ✅ OOM score adjustment configured"
    else
        echo "   ⚠️  OOM score adjustment not found"
    fi
else
    echo "   ⚠️  Docker daemon.json not found"
fi
echo ""

# Check services
echo "4. Performance Services Status:"
for service in tuned earlyoom preload; do
    if systemctl list-unit-files | grep -q "^${service}.service"; then
        ENABLED=$(systemctl is-enabled $service 2>/dev/null || echo "disabled")
        STATUS=$(systemctl is-active $service 2>/dev/null || echo "inactive")
        if [ "$STATUS" = "active" ] && [ "$ENABLED" != "disabled" ]; then
            echo "   ✅ $service: active (enabled)"
        else
            echo "   ⚠️  $service: $STATUS (enabled: $ENABLED)"
        fi
    else
        echo "   ⚠️  $service: not installed"
    fi
done
echo ""

# Check system resources
echo "5. System Resources:"
echo "   Memory:"
free -h | grep -E "(Mem|Swap)" | sed 's/^/      /'
echo ""
echo "   CPU Cores: $(nproc)"
echo "   Disk Space:"
df -h / | tail -1 | awk '{print "      Root: " $4 " free of " $2 " (" $5 " used)"}'
echo ""

# Check Docker containers
echo "6. Docker Containers Resource Usage:"
if command -v docker &> /dev/null && docker ps &> /dev/null; then
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | head -10 || echo "   No containers running"
else
    echo "   Docker not available or no permission"
fi
echo ""

echo "========================================"
echo "✅ Performance check complete!"

