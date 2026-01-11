#!/bin/bash
# REIMS 2.0 Restore Script
# Restores database, MinIO files, and Docker volumes from backup

set -e  # Exit on error

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh TIMESTAMP"
    echo "Example: ./restore.sh 20251112_231955"
    echo ""
    echo "Available backups:"
    ls -1 backups/database/reims_full_*.sql 2>/dev/null | sed 's/.*reims_full_/  /' | sed 's/.sql//' || echo "  No backups found"
    exit 1
fi

TIMESTAMP=$1
BACKUP_DIR="backups"

echo "🔄 Restoring REIMS 2.0 from backup: $TIMESTAMP..."
echo ""

# Check if backup files exist
if [ ! -f "$BACKUP_DIR/database/reims_full_${TIMESTAMP}.sql" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_DIR/database/reims_full_${TIMESTAMP}.sql"
    exit 1
fi

# Confirm before proceeding
read -p "⚠️  This will REPLACE all current data. Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""

# 1. Restore Database
echo "📊 Restoring PostgreSQL database..."
docker compose exec -T postgres psql -U reims -d reims < "$BACKUP_DIR/database/reims_full_${TIMESTAMP}.sql" > /dev/null 2>&1
echo "✅ Database restored"

# 2. Restore Docker Volumes (if backups exist)
if [ -f "$BACKUP_DIR/volumes/postgres-data_${TIMESTAMP}.tar.gz" ]; then
    echo "💾 Restoring postgres volume..."
    docker run --rm \
      -v reims2_postgres-data:/target \
      -v "$(pwd)/$BACKUP_DIR/volumes":/backup \
      alpine sh -c "cd /target && tar xzf /backup/postgres-data_${TIMESTAMP}.tar.gz" 2>/dev/null
    echo "✅ Postgres volume restored"
fi

if [ -f "$BACKUP_DIR/volumes/minio-data_${TIMESTAMP}.tar.gz" ]; then
    echo "💾 Restoring MinIO volume..."
    docker run --rm \
      -v reims2_minio-data:/target \
      -v "$(pwd)/$BACKUP_DIR/volumes":/backup \
      alpine sh -c "cd /target && tar xzf /backup/minio-data_${TIMESTAMP}.tar.gz" 2>/dev/null
    echo "✅ MinIO volume restored"
fi

if [ -f "$BACKUP_DIR/volumes/redis-data_${TIMESTAMP}.tar.gz" ]; then
    echo "💾 Restoring Redis volume..."
    docker run --rm \
      -v reims2_redis-data:/target \
      -v "$(pwd)/$BACKUP_DIR/volumes":/backup \
      alpine sh -c "cd /target && tar xzf /backup/redis-data_${TIMESTAMP}.tar.gz" 2>/dev/null
    echo "✅ Redis volume restored"
fi

echo ""
echo "🎉 Restore completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 Restored from: $BACKUP_DIR/ (timestamp: $TIMESTAMP)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  Restart services to apply changes:"
echo "   docker compose restart"

