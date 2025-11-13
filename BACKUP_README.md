# REIMS 2.0 Backup & Restore Guide

## Quick Start

### Create Backup
```bash
./backup.sh
```

### Restore Backup
```bash
./restore.sh TIMESTAMP
```

Example:
```bash
./restore.sh 20251112_232124
```

---

## What Gets Backed Up

### 1. **PostgreSQL Database** (Full Schema + Data)
- Location: `backups/database/reims_full_TIMESTAMP.sql`
- Size: ~1.7 MB
- Contains: Tables, views, indexes, constraints, and all data
- Format: SQL dump with `--clean --if-exists`

### 2. **PostgreSQL Data Only** (Insert Statements)
- Location: `backups/database/reims_data_TIMESTAMP.sql`
- Size: ~2.6 MB  
- Contains: Only data with INSERT statements
- Format: Portable SQL inserts
- Use: For migrating data to existing schema

### 3. **MinIO File Storage**
- Inventory: `backups/minio/file_inventory_TIMESTAMP.txt`
- Volume Backup: `backups/volumes/minio-data_TIMESTAMP.tar.gz`
- Size: ~430 KB
- Contains: All uploaded PDF documents (28 files)

### 4. **Docker Volumes**
- Postgres: `backups/volumes/postgres-data_TIMESTAMP.tar.gz` (~14 MB)
- MinIO: `backups/volumes/minio-data_TIMESTAMP.tar.gz` (~430 KB)
- Redis: `backups/volumes/redis-data_TIMESTAMP.tar.gz` (~4 KB)

### 5. **Configuration Files**
- Docker Compose: `backups/docker-compose_TIMESTAMP.yml.bak`
- Environment: `backups/.env_TIMESTAMP.bak` (if exists)

---

## Backup Schedule Recommendations

### Development Environment
```bash
# Daily backups (cron)
0 2 * * * cd /home/singh/REIMS2 && ./backup.sh >> backups/backup.log 2>&1
```

### Production Environment
```bash
# Hourly during business hours
0 9-17 * * 1-5 cd /path/to/reims2 && ./backup.sh >> backups/backup.log 2>&1

# Plus full backup at midnight
0 0 * * * cd /path/to/reims2 && ./backup.sh >> backups/backup.log 2>&1
```

---

## Restoration Process

### Full System Restore
1. **Stop services**: `docker compose down`
2. **Run restore**: `./restore.sh TIMESTAMP`
3. **Start services**: `docker compose up -d`

### Database Only Restore
```bash
# Restore to running database
docker compose exec -T postgres psql -U reims -d reims < backups/database/reims_full_TIMESTAMP.sql
```

### Volume Only Restore
```bash
# Restore specific volume
docker run --rm \
  -v reims2_postgres-data:/target \
  -v "$(pwd)/backups/volumes":/backup \
  alpine sh -c "cd /target && tar xzf /backup/postgres-data_TIMESTAMP.tar.gz"
```

---

## Backup Retention

### Keep Strategy
- **Last 7 daily backups** (1 week)
- **Last 4 weekly backups** (1 month)
- **Last 12 monthly backups** (1 year)

### Cleanup Old Backups
```bash
# Keep only last 7 backups
cd backups/database
ls -t reims_full_*.sql | tail -n +8 | xargs rm -f
```

---

## Disaster Recovery

### Scenario 1: Database Corruption
```bash
./restore.sh LATEST_TIMESTAMP
docker compose restart postgres backend
```

### Scenario 2: Lost MinIO Files
```bash
# Extract volume backup
docker run --rm \
  -v reims2_minio-data:/target \
  -v "$(pwd)/backups/volumes":/backup \
  alpine sh -c "cd /target && tar xzf /backup/minio-data_TIMESTAMP.tar.gz"

docker compose restart minio backend
```

### Scenario 3: Complete System Loss
1. Clone repository
2. Copy backup files to project
3. Run: `docker compose up -d`
4. Run: `./restore.sh TIMESTAMP`
5. Restart: `docker compose restart`

---

## Backup Verification

```bash
# Check backup file size
ls -lh backups/database/reims_full_*.sql

# Verify backup can be parsed
docker compose exec -T postgres psql -U reims -d postgres -f backups/database/reims_full_TIMESTAMP.sql --dry-run

# Check MinIO file count
cat backups/minio/file_inventory_TIMESTAMP.txt | wc -l
```

---

## Current Backup Status

**Latest Backup**: `20251112_232124`

### Contents:
- ✅ Database: 34 document uploads (28 active, 6 inactive versions)
- ✅ MinIO: 28 PDF files
- ✅ Alerts: 13 active alerts
- ✅ Anomalies: 5 detected anomalies
- ✅ Alert Rules: 10 configured rules
- ✅ Financial Metrics: Calculated for all documents
- ✅ Validation Results: 27 validation checks

### Database Stats:
- **Properties**: 4 (ESP001, HMND001, TCSH001, WEND001)
- **Financial Periods**: 12 periods across properties
- **Balance Sheets**: 8 documents
- **Income Statements**: 8 documents
- **Cash Flows**: 8 documents
- **Rent Rolls**: 4 documents (April 2025)
- **Extracted Records**: 3,000+ line items
- **Storage**: PostgreSQL + MinIO + Redis

---

## Notes

- Backups are stored locally in `backups/` directory
- For production, configure off-site backup storage (S3, NAS, etc.)
- Test restore process regularly
- Monitor backup script execution via `backups/backup.log`
- Volume backups capture the exact state including indexes and cache

