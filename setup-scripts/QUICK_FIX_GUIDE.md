# Quick System Stability Fix Guide

## TL;DR - What Was Done

Your Ubuntu system with 8GB RAM was experiencing crashes because:
- No memory protection was active
- Applications (especially Cursor IDE) were consuming all available RAM
- System had no way to prevent Out-Of-Memory crashes

**Solution:** Implemented 3-layer memory protection + optimized memory management.

---

## What You Need to Do NOW

### 1. REBOOT YOUR SYSTEM (Required)

```bash
sudo reboot
```

**Why:** Many kernel and systemd changes require a reboot to activate.

### 2. After Reboot - Verify (30 seconds)

```bash
# Should show both services as "active (running)"
sudo systemctl status earlyoom systemd-oomd
```

### 3. Monitor Your System (Optional but Recommended)

```bash
# Check memory status anytime
memory-monitor

# Watch in real-time (Ctrl+C to exit)
watch -n 2 memory-monitor
```

---

## Quick Reference Commands

### Check if Protection is Working
```bash
# Service status
sudo systemctl status earlyoom

# Memory settings
sysctl vm.swappiness vm.vfs_cache_pressure

# Current memory usage
free -h
```

### Monitor Memory Usage
```bash
# Simple view
memory-monitor

# Live monitoring
watch -n 2 memory-monitor

# Top memory users
ps aux --sort=-%mem | head -10
```

### Check for Problems
```bash
# Recent errors
sudo journalctl -b -p err | tail -20

# OOM kill events
sudo dmesg | grep -i oom

# Application crashes
sudo journalctl -b | grep -i "killed\|crash" | tail -20
```

### Restart Protection Services
```bash
# If needed
sudo systemctl restart earlyoom systemd-oomd
```

---

## What Changed

### Protection Services (Main Fix)

1. **earlyoom** - Kills apps before system crashes
   - Triggers at 15% free RAM or 10% free swap
   - Prefers killing: Cursor, Chrome, Firefox, Electron apps
   - Protects: System services, terminals, core apps

2. **systemd-oomd** - Enhanced memory pressure monitoring
   - Triggers at 80% memory pressure for 20+ seconds
   - Complements earlyoom with different detection strategy

3. **Process Limits** - Prevents memory hogging
   - Users limited to 5GB soft / 6GB hard limit
   - Automatic enforcement by systemd

### Memory Optimization

- **vm.swappiness = 10** (prefer RAM, minimal swap)
- **vm.vfs_cache_pressure = 50** (balanced caching)
- **Transparent Huge Pages = madvise** (reduce fragmentation)
- **File descriptors increased** (65536 limit)

---

## Expected Behavior

### Before Fix
- Applications crash randomly
- System freezes/becomes unresponsive
- No warning when memory runs low

### After Fix
- System stays responsive
- Apps may be killed when memory is critically low (you'll get notification)
- System protects itself from total crashes

### You Might See
- Desktop notifications: "earlyoom killed [application]"
- Applications closing when memory < 15%
- System remaining stable instead of freezing

**This is NORMAL and EXPECTED** - it's better to lose one app than crash the whole system.

---

## Cursor IDE Optimization (Optional)

A template config was created at:
`~/.config/Cursor/User/settings.json.memory-optimized`

**To apply:**
1. Open Cursor Settings (Ctrl+,)
2. Click "Open Settings (JSON)" in top-right
3. Review and merge settings from `.memory-optimized` file
4. Restart Cursor

**Key optimizations:**
- Disable minimap
- Limit search results
- Turn off auto-updates
- Reduce file watchers
- Disable telemetry

---

## Troubleshooting

### "Applications still crashing after reboot"

1. Verify services are running:
   ```bash
   sudo systemctl status earlyoom systemd-oomd
   ```

2. Check what's using memory:
   ```bash
   memory-monitor
   ```

3. Check logs for OOM kills:
   ```bash
   sudo journalctl -u earlyoom -n 30
   ```

### "earlyoom is killing apps too often"

If earlyoom is too aggressive, adjust thresholds:

```bash
sudo nano /etc/default/earlyoom
# Change: -r 15 -s 10  to  -r 10 -s 5
# (Lower numbers = less aggressive)

sudo systemctl restart earlyoom
```

### "System is slower after fix"

The protection has minimal overhead. If you notice slowness:

1. Check memory usage: `memory-monitor`
2. Check swap usage: `free -h`
3. If swap usage is high, you need more RAM or to close apps

---

## Long-Term Solution

**Your system has 8GB RAM** - this is minimal for modern desktop development work with:
- Cursor IDE (Electron-based, memory-heavy)
- Web browsers
- Docker containers (if running REIMS2)

**Recommended:** Upgrade to **16GB RAM** (~$40-80)
- Would eliminate most memory pressure
- Lenovo YOGA 730-13IWL supports up to 16GB
- Much more cost-effective than managing limited memory

---

## Files and Locations

### Configuration Files
- `/etc/default/earlyoom` - earlyoom config
- `/etc/systemd/oomd.conf.d/10-memory-pressure.conf` - oomd config
- `/etc/sysctl.d/99-low-memory-system.conf` - kernel memory settings
- `/etc/systemd/system/user@.service.d/10-oom-protect.conf` - process limits

### Scripts and Tools
- `/usr/local/bin/memory-monitor` - Memory monitoring tool
- `~/Documents/GitHub/REIMS2/setup-scripts/fix-system-stability.sh` - Main fix script
- `~/Documents/GitHub/REIMS2/setup-scripts/SYSTEM_STABILITY_FIX_SUMMARY.md` - Full documentation

### Backups
All modified system files were backed up with timestamp:
- `/etc/security/limits.conf.backup.TIMESTAMP`
- `/etc/systemd/system.conf.backup.TIMESTAMP`

---

## Revert If Needed

If you want to undo changes (not recommended):

```bash
# Stop services
sudo systemctl stop earlyoom systemd-oomd
sudo systemctl disable earlyoom

# Remove configs (keeps backups)
sudo rm /etc/sysctl.d/99-low-memory-system.conf
sudo rm -rf /etc/systemd/oomd.conf.d/10-memory-pressure.conf
sudo rm -rf /etc/systemd/system/user@.service.d/10-oom-protect.conf

# Reboot
sudo reboot
```

---

## Summary Checklist

- [ ] Read this guide
- [ ] **REBOOT SYSTEM** (most important!)
- [ ] After reboot: Check services are active
- [ ] Test: Open your normal applications
- [ ] Monitor: Run `memory-monitor` periodically
- [ ] Optional: Merge Cursor IDE settings
- [ ] Optional: Consider RAM upgrade for long-term

---

**Questions or Issues?**

1. Check full documentation: `SYSTEM_STABILITY_FIX_SUMMARY.md`
2. Run diagnostics: `memory-monitor`
3. Check logs: `sudo journalctl -b -p err`

**System is now protected from memory-related crashes!**
**Remember to REBOOT for changes to take full effect.**

---
*Created: 2025-12-18*
*System: Lenovo YOGA 730-13IWL, 8GB RAM, Ubuntu 25.10*
