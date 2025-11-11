# MinIO Persistence Guide

## ✅ MinIO Data Persistence is Now Fully Configured

Your MinIO setup now includes automatic bucket creation and data persistence across container restarts.

## 🎯 What's Been Configured

### 1. Named Volume for Data Persistence
```yaml
volumes:
  minio-data:
    driver: local
```

MinIO stores all data in the `minio-data` volume, which persists on your host system.

### 2. Automatic Bucket Initialization
A dedicated `minio-init` service ensures the `reims` bucket is:
- ✅ Created automatically on first startup
- ✅ Recreated if accidentally deleted
- ✅ Set to `download` policy for proper access

### 3. Service Dependencies
Services that use MinIO (backend, celery-worker) now wait for:
- MinIO service to be healthy
- MinIO bucket to be initialized

## 📦 How Data Persistence Works

### Volume Location
Docker stores the `minio-data` volume on your host system:

```bash
# Find volume location
docker volume inspect reims_minio-data

# Typical location:
# /var/lib/docker/volumes/reims_minio-data/_data
```

### What's Persisted
- ✅ All uploaded files
- ✅ All bucket configurations
- ✅ All folder structures
- ✅ All metadata and policies

### What Happens When You:

#### Restart Containers
```bash
docker compose restart minio
```
**Result:** All data remains intact ✅

#### Stop and Start Services
```bash
docker compose down
docker compose up -d
```
**Result:** All data remains intact ✅

#### Remove and Recreate Containers
```bash
docker compose down
docker compose up -d
```
**Result:** All data remains intact ✅
**Note:** Bucket is automatically recreated by `minio-init` service

#### Remove Volumes (⚠️ DESTRUCTIVE)
```bash
docker compose down -v
```
**Result:** ALL DATA IS DELETED ⚠️

## 🔍 Verify Persistence

### Check Volume Exists
```bash
docker volume ls | grep minio
# Should show: reims_minio-data
```

### Check Volume Details
```bash
docker volume inspect reims_minio-data
```

### Check Bucket Exists
```bash
# Access MinIO Console
firefox http://localhost:9001

# Login with:
# Username: minioadmin
# Password: minioadmin

# Or use mc (MinIO client)
docker run --rm --network reims_reims-network \
  minio/mc alias set myminio http://minio:9000 minioadmin minioadmin

docker run --rm --network reims_reims-network \
  minio/mc ls myminio
```

### List All Files in Bucket
```bash
docker run --rm --network reims_reims-network \
  minio/mc ls myminio/reims --recursive
```

## 📊 Monitor Storage Usage

### MinIO Console (Web UI)
```bash
# Open in browser
http://localhost:9001

# Features:
# - View all buckets
# - Browse files
# - Check storage usage
# - Manage access policies
# - View metrics
```

### Command Line
```bash
# Check bucket size
docker run --rm --network reims_reims-network \
  minio/mc du myminio/reims

# Count objects
docker run --rm --network reims_reims-network \
  minio/mc ls myminio/reims --recursive | wc -l
```

## 🗄️ Backup and Restore

### Backup Strategy 1: Volume Backup
```bash
# Create backup directory
mkdir -p ~/backups/minio

# Backup volume (while service is running)
docker run --rm \
  -v reims_minio-data:/data:ro \
  -v ~/backups/minio:/backup \
  ubuntu tar czf /backup/minio-backup-$(date +%Y%m%d).tar.gz -C /data .

# Result: ~/backups/minio/minio-backup-20251107.tar.gz
```

### Restore from Volume Backup
```bash
# Stop MinIO
docker compose stop minio minio-init backend celery-worker

# Restore backup
docker run --rm \
  -v reims_minio-data:/data \
  -v ~/backups/minio:/backup \
  ubuntu bash -c "cd /data && tar xzf /backup/minio-backup-20251107.tar.gz"

# Start services
docker compose up -d
```

### Backup Strategy 2: MinIO Mirror
```bash
# Mirror entire bucket to local directory
docker run --rm \
  --network reims_reims-network \
  -v ~/backups/minio-mirror:/backup \
  minio/mc mirror myminio/reims /backup/reims

# Restore from mirror
docker run --rm \
  --network reims_reims-network \
  -v ~/backups/minio-mirror:/backup \
  minio/mc mirror /backup/reims myminio/reims
```

### Automated Daily Backups
Add to your crontab:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /home/gurpyar/Documents/R/REIMS2 && docker run --rm -v reims_minio-data:/data:ro -v ~/backups/minio:/backup ubuntu tar czf /backup/minio-backup-$(date +\%Y\%m\%d).tar.gz -C /data . > /dev/null 2>&1

# Keep only last 7 days of backups
0 3 * * * find ~/backups/minio -name "minio-backup-*.tar.gz" -mtime +7 -delete > /dev/null 2>&1
```

## 🔧 Troubleshooting

### Bucket Not Found Error
```bash
# Check if bucket exists
docker exec reims-minio mc ls /data

# Manually create bucket
docker exec reims-minio mc mb /data/reims --ignore-existing

# Or restart minio-init
docker compose up -d minio-init
```

### Files Disappear After Restart
This shouldn't happen with proper volume configuration. Check:

```bash
# 1. Verify volume exists
docker volume inspect reims_minio-data

# 2. Check mount point in container
docker inspect reims-minio | grep -A 10 Mounts

# 3. Verify data directory
docker exec reims-minio ls -la /data
```

### Permission Issues
```bash
# Check MinIO data ownership
docker exec reims-minio ls -la /data

# Should be owned by user running MinIO (usually root or minio)
```

### Volume Full
```bash
# Check disk space
df -h

# Check volume size
docker system df -v

# Clean up unused data
docker volume prune  # ⚠️ WARNING: Only removes unused volumes
```

## 🚀 Testing Persistence

### Quick Test
```bash
# 1. Upload a test file via API or console

# 2. List files
docker run --rm --network reims_reims-network \
  minio/mc ls myminio/reims --recursive

# 3. Restart MinIO
docker compose restart minio

# 4. List files again - should still be there!
docker run --rm --network reims_reims-network \
  minio/mc ls myminio/reims --recursive

# 5. Remove and recreate containers
docker compose down
docker compose up -d

# 6. List files again - still there!
docker run --rm --network reims_reims-network \
  minio/mc ls myminio/reims --recursive
```

## 📝 Best Practices

1. **Never use `-v` flag with `docker compose down`** unless you want to delete all data
2. **Set up regular backups** using cron jobs
3. **Monitor storage usage** via MinIO Console
4. **Test restore procedures** periodically
5. **Keep backup rotation** to save disk space
6. **Document custom policies** if you modify bucket permissions

## 🎓 Understanding MinIO Persistence

### Docker Volume vs Bind Mount

Your setup uses a **named volume** (`minio-data`):

**Pros:**
- ✅ Managed by Docker
- ✅ Survives container removal
- ✅ Easy to backup with `docker run`
- ✅ Portable across systems

**Cons:**
- ❌ Less obvious location on host
- ❌ Requires Docker commands to access

**Alternative: Bind Mount**
If you prefer a specific local directory:

```yaml
volumes:
  - /home/gurpyar/minio-data:/data
```

### When Data is Lost

Data is ONLY lost when:
1. You run `docker compose down -v`
2. You manually delete the volume: `docker volume rm reims_minio-data`
3. You run `docker system prune --volumes` (nuclear option)
4. Disk failure (make backups!)

### When Data is NOT Lost

Data persists through:
- ✅ Container restarts
- ✅ Container removal and recreation
- ✅ Docker daemon restarts
- ✅ System reboots
- ✅ Upgrading MinIO image
- ✅ Changing container configuration

## 🔗 Related Documentation

- [MinIO Official Docs](https://min.io/docs/minio/linux/index.html)
- [Docker Volumes Guide](https://docs.docker.com/storage/volumes/)
- [MINIO_README.md](backend/MINIO_README.md) - API usage guide
- [DOCKER_COMPOSE_README.md](DOCKER_COMPOSE_README.md) - Stack overview

## ✅ Summary

Your MinIO setup is now **production-ready** with:

1. ✅ **Persistent storage** via named volume
2. ✅ **Automatic bucket creation** via init container
3. ✅ **Health checks** ensuring service reliability
4. ✅ **Proper dependencies** preventing startup issues
5. ✅ **Public download policy** for file access
6. ✅ **Web console** at http://localhost:9001
7. ✅ **API endpoint** at http://localhost:9000

**Your data will persist across all normal operations!** 🎉

