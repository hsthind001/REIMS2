#!/bin/bash
# REIMS2 Automated Backup Script
# Backs up PostgreSQL database and MinIO storage volumes

set -e

# Configuration
BACKUP_DIR="/home/singh/REIMS2/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7  # Keep backups for 7 days

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== REIMS2 Backup Script ===${NC}"
echo "Starting backup at $(date)"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Function to check if container is running
check_container() {
    if ! docker ps --format '{{.Names}}' | grep -q "^$1$"; then
        echo -e "${RED}Error: Container $1 is not running${NC}"
        return 1
    fi
    return 0
}

# === PostgreSQL Backup ===
echo -e "${YELLOW}[1/3] Backing up PostgreSQL database...${NC}"

if check_container "reims-postgres"; then
    POSTGRES_BACKUP="$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz"
    
    docker exec reims-postgres pg_dump -U reims -d reims | gzip > "$POSTGRES_BACKUP"
    
    if [ -f "$POSTGRES_BACKUP" ]; then
        SIZE=$(du -h "$POSTGRES_BACKUP" | cut -f1)
        echo -e "${GREEN}✓ PostgreSQL backup complete: $POSTGRES_BACKUP ($SIZE)${NC}"
    else
        echo -e "${RED}✗ PostgreSQL backup failed${NC}"
        exit 1
    fi
else
    exit 1
fi

echo ""

# === MinIO Backup ===
echo -e "${YELLOW}[2/3] Backing up MinIO storage...${NC}"

if check_container "reims-minio"; then
    MINIO_BACKUP="$BACKUP_DIR/minio_${TIMESTAMP}"
    mkdir -p "$MINIO_BACKUP"
    
    # Export MinIO data using mc (MinIO Client)
    docker run --rm \
        --network reims2_reims-network \
        -v "$MINIO_BACKUP:/backup" \
        --entrypoint sh \
        minio/mc:latest \
        -c "mc alias set myminio http://minio:9000 minioadmin minioadmin && mc mirror myminio/reims /backup/reims" > /dev/null 2>&1
    
    if [ -d "$MINIO_BACKUP/reims" ]; then
        SIZE=$(du -sh "$MINIO_BACKUP" | cut -f1)
        FILECOUNT=$(find "$MINIO_BACKUP" -type f | wc -l)
        echo -e "${GREEN}✓ MinIO backup complete: $MINIO_BACKUP ($SIZE, $FILECOUNT files)${NC}"
    else
        echo -e "${RED}✗ MinIO backup failed${NC}"
        exit 1
    fi
else
    exit 1
fi

echo ""

# === Cleanup Old Backups ===
echo -e "${YELLOW}[3/3] Cleaning up old backups (older than $RETENTION_DAYS days)...${NC}"

# Remove old PostgreSQL backups
DELETED_PG=0
for file in "$BACKUP_DIR"/postgres_*.sql.gz; do
    if [ -f "$file" ]; then
        if [ $(find "$file" -mtime +$RETENTION_DAYS 2>/dev/null | wc -l) -gt 0 ]; then
            rm "$file"
            DELETED_PG=$((DELETED_PG + 1))
        fi
    fi
done

# Remove old MinIO backups
DELETED_MINIO=0
for dir in "$BACKUP_DIR"/minio_*; do
    if [ -d "$dir" ]; then
        if [ $(find "$dir" -maxdepth 0 -mtime +$RETENTION_DAYS 2>/dev/null | wc -l) -gt 0 ]; then
            rm -rf "$dir"
            DELETED_MINIO=$((DELETED_MINIO + 1))
        fi
    fi
done

echo -e "${GREEN}✓ Cleanup complete: Removed $DELETED_PG PostgreSQL and $DELETED_MINIO MinIO backups${NC}"

echo ""

# === Summary ===
echo -e "${GREEN}=== Backup Summary ===${NC}"
echo "Backup timestamp: $TIMESTAMP"
echo "PostgreSQL backup: $POSTGRES_BACKUP"
echo "MinIO backup: $MINIO_BACKUP"
echo ""

# List all current backups
echo "Current backups:"
echo "PostgreSQL backups:"
ls -lh "$BACKUP_DIR"/postgres_*.sql.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "MinIO backups:"
du -sh "$BACKUP_DIR"/minio_* 2>/dev/null | awk '{print "  " $2 " (" $1 ")"}'
echo ""

echo -e "${GREEN}Backup completed successfully at $(date)${NC}"

