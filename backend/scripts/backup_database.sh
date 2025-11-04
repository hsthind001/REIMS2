#!/bin/bash
#
# Database Backup Script
# 
# Creates a compressed backup of the REIMS PostgreSQL database
# Automatically rotates backups, keeping only the last 7
#
# Usage:
#   ./scripts/backup_database.sh
#

set -e

# Configuration
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="reims_backup_${TIMESTAMP}.sql.gz"
KEEP_BACKUPS=7

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting database backup..."
echo "Timestamp: $TIMESTAMP"

# Create backup
docker exec reims-postgres pg_dump -U reims reims | gzip > "$BACKUP_DIR/$BACKUP_FILE"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    echo "  File: $BACKUP_DIR/$BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"
else
    echo "✗ Backup failed"
    exit 1
fi

# Rotate backups - keep only last N backups
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/reims_backup_*.sql.gz 2>/dev/null | wc -l)

if [ "$BACKUP_COUNT" -gt "$KEEP_BACKUPS" ]; then
    echo "Rotating backups (keeping last $KEEP_BACKUPS)..."
    ls -t "$BACKUP_DIR"/reims_backup_*.sql.gz | tail -n +$(($KEEP_BACKUPS + 1)) | xargs -r rm
    echo -e "${YELLOW}Removed old backups${NC}"
fi

echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/reims_backup_*.sql.gz 2>/dev/null | awk '{print "  "$9" ("$5")"}'

echo ""
echo -e "${GREEN}Backup complete!${NC}"

