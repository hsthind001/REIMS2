#!/bin/bash
# REIMS 2.0 Backup Script
# Creates backups of database, MinIO files, and Docker volumes

set -e  # Exit on error

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🔄 Starting REIMS 2.0 backup at $TIMESTAMP..."

# Create backup directories
mkdir -p "$BACKUP_DIR/database"
mkdir -p "$BACKUP_DIR/minio"
mkdir -p "$BACKUP_DIR/volumes"

# 1. Database Backup
echo "📊 Backing up PostgreSQL database..."
docker compose exec -T postgres pg_dump -U reims -d reims --clean --if-exists > "$BACKUP_DIR/database/reims_full_${TIMESTAMP}.sql"
echo "✅ Database backup: $BACKUP_DIR/database/reims_full_${TIMESTAMP}.sql"

# 2. Data-only backup (for easier data migration)
echo "📊 Creating data-only backup..."
docker compose exec -T postgres pg_dump -U reims -d reims --data-only --inserts > "$BACKUP_DIR/database/reims_data_${TIMESTAMP}.sql" 2>/dev/null || echo "⚠️  Data backup completed with warnings"
echo "✅ Data backup: $BACKUP_DIR/database/reims_data_${TIMESTAMP}.sql"

# 3. MinIO file inventory
echo "📦 Creating MinIO file inventory..."
docker compose exec minio mc ls -r localminio/reims/ 2>/dev/null > "$BACKUP_DIR/minio/file_inventory_${TIMESTAMP}.txt"
FILE_COUNT=$(cat "$BACKUP_DIR/minio/file_inventory_${TIMESTAMP}.txt" | wc -l)
echo "✅ MinIO inventory: $FILE_COUNT files cataloged"

# 4. Docker volume backup
echo "💾 Backing up Docker volumes..."
docker run --rm \
  -v reims2_postgres-data:/source:ro \
  -v "$(pwd)/$BACKUP_DIR/volumes":/backup \
  alpine tar czf /backup/postgres-data_${TIMESTAMP}.tar.gz -C /source . 2>/dev/null

docker run --rm \
  -v reims2_minio-data:/source:ro \
  -v "$(pwd)/$BACKUP_DIR/volumes":/backup \
  alpine tar czf /backup/minio-data_${TIMESTAMP}.tar.gz -C /source . 2>/dev/null

docker run --rm \
  -v reims2_redis-data:/source:ro \
  -v "$(pwd)/$BACKUP_DIR/volumes":/backup \
  alpine tar czf /backup/redis-data_${TIMESTAMP}.tar.gz -C /source . 2>/dev/null

echo "✅ Docker volumes backed up"

# 5. Configuration backup
echo "⚙️  Backing up configuration files..."
cp docker-compose.yml "$BACKUP_DIR/docker-compose_${TIMESTAMP}.yml.bak"
[ -f .env ] && cp .env "$BACKUP_DIR/.env_${TIMESTAMP}.bak"
echo "✅ Configuration files backed up"

# Summary
echo ""
echo "🎉 Backup completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 Backup location: $BACKUP_DIR/"
echo "📊 Database: Full schema + data"
echo "📦 MinIO: $FILE_COUNT files inventoried"
echo "💾 Volumes: postgres, minio, redis"
echo "⚙️  Config: docker-compose.yml, .env"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To restore, run: ./restore.sh $TIMESTAMP"

