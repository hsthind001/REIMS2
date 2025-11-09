#!/bin/bash
# PostgreSQL Backup Script
# Runs daily via cron

set -e

BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="reims2_backup_${TIMESTAMP}.sql"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform backup
echo "Starting PostgreSQL backup..."
pg_dump -h localhost -U postgres -d reims2_db > $BACKUP_DIR/$BACKUP_FILE

# Compress backup
gzip $BACKUP_DIR/$BACKUP_FILE

# Upload to MinIO
echo "Uploading to MinIO..."
mc cp $BACKUP_DIR/${BACKUP_FILE}.gz minio/backups/postgres/

# Cleanup old backups
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: ${BACKUP_FILE}.gz"

