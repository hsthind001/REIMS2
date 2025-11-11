#!/bin/bash
# REIMS Daily Backup Script
# Backs up PostgreSQL database and MinIO files

# Configuration
BACKUP_DIR="/home/gurpyar/Documents/R/REIMS2/backend/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_BACKUP_FILE="$BACKUP_DIR/reims_backup_$TIMESTAMP.sql.gz"
MINIO_BACKUP_DIR="$BACKUP_DIR/minio_$TIMESTAMP"
RETENTION_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "🔄 Starting REIMS backup at $(date)"

# Backup PostgreSQL database
echo "📦 Backing up PostgreSQL database..."
docker exec reims-postgres pg_dump -U reims -d reims | gzip > "$DB_BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Database backed up to: $DB_BACKUP_FILE"
    echo "   Size: $(du -h "$DB_BACKUP_FILE" | cut -f1)"
else
    echo "❌ Database backup failed!"
    exit 1
fi

# Backup MinIO data
echo "📦 Backing up MinIO files..."
mkdir -p "$MINIO_BACKUP_DIR"
docker exec reims-minio mc mirror /data/reims /tmp/backup 2>/dev/null || true
docker cp reims-minio:/tmp/backup "$MINIO_BACKUP_DIR/" 2>/dev/null || true

if [ -d "$MINIO_BACKUP_DIR/backup" ]; then
    echo "✅ MinIO backed up to: $MINIO_BACKUP_DIR"
    echo "   Size: $(du -sh "$MINIO_BACKUP_DIR" | cut -f1)"
else
    echo "⚠️  MinIO backup may be empty or failed"
fi

# Clean up old backups
echo "🧹 Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "reims_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "minio_*" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null

echo "✅ Backup completed at $(date)"
echo ""
echo "To restore database:"
echo "  gunzip -c $DB_BACKUP_FILE | docker exec -i reims-postgres psql -U reims -d reims"
echo ""
echo "To restore MinIO:"
echo "  docker cp $MINIO_BACKUP_DIR/backup reims-minio:/data/reims/"

