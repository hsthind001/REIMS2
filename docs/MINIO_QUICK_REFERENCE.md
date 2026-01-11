# MinIO Quick Reference Card

## 🚀 Quick Start

```bash
cd /home/gurpyar/Documents/R/REIMS2

# Start everything (MinIO bucket auto-created)
docker compose up -d

# Verify bucket exists
docker run --rm --network reims_reims-network \
  minio/mc alias set myminio http://minio:9000 minioadmin minioadmin && \
  docker run --rm --network reims_reims-network \
  minio/mc ls myminio/reims
```

## 🔗 Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **MinIO API** | http://localhost:9000 | minioadmin / minioadmin |
| **Backend API** | http://localhost:8000/docs | - |

## 📦 Key Information

- **Bucket Name:** `reims`
- **Volume:** `reims_minio-data` (persistent)
- **Policy:** `download` (public read)
- **Auto-Created:** ✅ Yes (on every startup if missing)

## 🧪 Test Persistence

```bash
# Run automated test
./test_minio_persistence.sh
```

## 📁 Common Commands

### List Files
```bash
docker run --rm --network reims_reims-network \
  minio/mc ls myminio/reims --recursive
```

### Upload File
```bash
docker run --rm --network reims_reims-network \
  -v $(pwd):/data \
  minio/mc cp /data/myfile.pdf myminio/reims/
```

### Download File
```bash
docker run --rm --network reims_reims-network \
  -v $(pwd):/data \
  minio/mc cp myminio/reims/myfile.pdf /data/
```

### Check Bucket Size
```bash
docker run --rm --network reims_reims-network \
  minio/mc du myminio/reims
```

## 💾 Backup & Restore

### Backup
```bash
docker run --rm \
  -v reims_minio-data:/data:ro \
  -v ~/backups:/backup \
  ubuntu tar czf /backup/minio-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore
```bash
docker compose stop minio backend celery-worker
docker run --rm \
  -v reims_minio-data:/data \
  -v ~/backups:/backup \
  ubuntu bash -c "cd /data && tar xzf /backup/minio-YYYYMMDD.tar.gz"
docker compose up -d
```

## 🔧 Troubleshooting

### Bucket Not Found
```bash
docker compose up -d minio-init
docker compose logs minio-init
```

### Check Volume
```bash
docker volume inspect reims_minio-data
```

### View Logs
```bash
docker compose logs minio
docker compose logs minio-init
docker compose logs backend | grep -i minio
```

## ⚠️ Important Notes

✅ **Data persists across:**
- Container restarts
- `docker compose down` + `docker compose up`
- Container recreation
- System reboots

❌ **Data is deleted with:**
- `docker compose down -v` (includes `-v` flag)
- `docker volume rm reims_minio-data`

## 📚 Full Documentation

- **[MINIO_PERSISTENCE.md](MINIO_PERSISTENCE.md)** - Complete guide
- **[MINIO_PERSISTENCE_IMPLEMENTATION.md](MINIO_PERSISTENCE_IMPLEMENTATION.md)** - What was changed
- **[backend/MINIO_README.md](backend/MINIO_README.md)** - API usage

## 🎯 What Changed

1. ✅ Added `minio-init` service (auto-creates bucket)
2. ✅ Improved health checks (faster startup)
3. ✅ Updated service dependencies
4. ✅ Created test script
5. ✅ Added comprehensive documentation

---

**Status:** ✅ Production Ready  
**Last Updated:** November 7, 2025

