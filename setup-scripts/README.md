# REIMS2 Performance Optimization Setup Scripts

This directory contains scripts to optimize Ubuntu system performance for running REIMS2 efficiently.

## Quick Start

Run all optimizations in order:

```bash
cd /home/hsthind/Documents/GitHub/REIMS2/setup-scripts

# 1. Install required packages
sudo bash install-performance-packages.sh

# 2. Configure CPU governor
sudo bash setup-cpu-governor.sh

# 3. Apply memory optimizations
sudo cp 99-reims2-performance.conf /etc/sysctl.d/
sudo sysctl -p /etc/sysctl.d/99-reims2-performance.conf

# 4. Apply kernel optimizations
sudo cp 99-reims2-kernel.conf /etc/sysctl.d/
sudo sysctl -p /etc/sysctl.d/99-reims2-kernel.conf

# 5. Configure Docker
sudo bash setup-docker-optimization.sh

# 6. Configure tuned service
sudo bash setup-tuned.sh

# 7. Configure earlyoom
sudo bash setup-earlyoom.sh

# 8. Configure systemd limits
sudo bash setup-systemd-limits.sh
sudo systemctl daemon-reload

# 9. Verify all optimizations
bash reims2-performance-check.sh
```

## Individual Scripts

### install-performance-packages.sh
Installs required packages:
- `tuned` - System performance tuning
- `earlyoom` - Early OOM killer
- `preload` - Application preloading
- `cpufrequtils` - CPU frequency management
- `htop` - Process monitoring

### setup-cpu-governor.sh
Sets CPU governor to `performance` mode for maximum CPU speed. Creates a systemd service to persist the setting across reboots.

### 99-reims2-performance.conf
Memory management optimizations:
- Swappiness: 10 (reduced from 60)
- vfs_cache_pressure: 50 (optimized)
- Dirty page ratios optimized
- Memory overcommit settings

### 99-reims2-kernel.conf
Kernel parameter optimizations:
- Network connection limits
- TCP optimizations
- File descriptor limits

### setup-docker-optimization.sh
Configures Docker daemon with:
- File descriptor limits
- Log rotation (10MB max, 3 files)
- OOM score adjustment
- Storage driver optimizations

### setup-tuned.sh
Configures `tuned` service with `throughput-performance` profile for optimal system performance.

### setup-earlyoom.sh
Configures earlyoom to prevent system crashes:
- Triggers at 10% free RAM
- Triggers at 5% free swap
- Protects critical processes (Docker, PostgreSQL)

### setup-systemd-limits.sh
Increases systemd default limits:
- DefaultLimitNOFILE: 65536
- DefaultLimitNPROC: 32768

### reims2-performance-check.sh
Validation script that checks:
- CPU governor status
- sysctl settings
- Docker configuration
- Service status
- System resources

## Docker Compose Resource Limits

The `docker-compose.yml` has been updated with resource limits for all services:

| Service | Memory Limit | CPU Limit | Memory Reservation | CPU Reservation |
|---------|-------------|-----------|-------------------|----------------|
| PostgreSQL | 1.5GB | 2.0 cores | 512MB | 0.5 cores |
| Redis | 512MB | 1.0 core | 256MB | 0.25 cores |
| Backend | 2GB | 2.0 cores | 512MB | 0.5 cores |
| Celery Worker | 1.5GB | 2.0 cores | 512MB | 0.5 cores |
| Frontend | 512MB | 1.0 core | 256MB | 0.25 cores |
| MinIO | 512MB | 1.0 core | 256MB | 0.25 cores |
| pgAdmin | 512MB | 1.0 core | 256MB | 0.25 cores |
| Flower | 512MB | 0.5 cores | 128MB | 0.1 cores |

**Total Memory Limits:** ~7.5GB (fits within 7GB RAM + swap)
**Total CPU Limits:** ~10 cores (fits within 8 cores with some headroom)

## Notes

- Some changes require a system reboot to take full effect (sysctl, systemd limits)
- Docker daemon restart will restart all containers
- CPU governor changes are immediate but require persistence setup
- All scripts create backups before modifying system files

## Troubleshooting

If you encounter issues:

1. Check script output for errors
2. Run `reims2-performance-check.sh` to verify settings
3. Check system logs: `journalctl -xe`
4. Restore backups if needed (scripts create timestamped backups)

## Reverting Changes

To revert optimizations:

1. Restore Docker daemon.json backup: `sudo cp /etc/docker/daemon.json.backup.* /etc/docker/daemon.json`
2. Remove sysctl files: `sudo rm /etc/sysctl.d/99-reims2-*.conf`
3. Disable services: `sudo systemctl disable tuned earlyoom cpu-governor`
4. Restore system.conf: `sudo cp /etc/systemd/system.conf.backup.* /etc/systemd/system.conf`

