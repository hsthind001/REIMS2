#!/bin/bash
# REIMS2 Restore Script
# Restores PostgreSQL database and MinIO storage from backups

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BACKUP_DIR="/home/singh/REIMS2/backups"

echo -e "${GREEN}=== REIMS2 Restore Script ===${NC}"
echo ""

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}Error: Backup directory not found: $BACKUP_DIR${NC}"
    exit 1
fi

# List available backups
echo "Available PostgreSQL backups:"
ls -lh "$BACKUP_DIR"/postgres_*.sql.gz 2>/dev/null | nl -w2 -s'. ' | awk '{print $1 " " $11 " (" $7 ")"}'
echo ""

echo "Available MinIO backups:"
du -sh "$BACKUP_DIR"/minio_* 2>/dev/null | nl -w2 -s'. ' | awk '{print $1 " " $3 " (" $2 ")"}'
echo ""

# Function to restore PostgreSQL
restore_postgres() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Error: Backup file not found: $backup_file${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Restoring PostgreSQL database...${NC}"
    echo -e "${RED}WARNING: This will REPLACE the current database!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled"
        return 1
    fi
    
    # Drop and recreate database
    echo "Dropping existing database..."
    docker exec reims-postgres psql -U reims -d postgres -c "DROP DATABASE IF EXISTS reims;"
    docker exec reims-postgres psql -U reims -d postgres -c "CREATE DATABASE reims OWNER reims;"
    
    # Restore from backup
    echo "Restoring from backup..."
    gunzip < "$backup_file" | docker exec -i reims-postgres psql -U reims -d reims > /dev/null
    
    echo -e "${GREEN}✓ PostgreSQL restore complete${NC}"
}

# Function to restore MinIO
restore_minio() {
    local backup_dir="$1"
    
    if [ ! -d "$backup_dir" ]; then
        echo -e "${RED}Error: Backup directory not found: $backup_dir${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Restoring MinIO storage...${NC}"
    echo -e "${RED}WARNING: This will REPLACE the current MinIO data!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled"
        return 1
    fi
    
    # Clear existing bucket
    echo "Clearing existing bucket..."
    docker run --rm \
        --network reims2_reims-network \
        --entrypoint sh \
        minio/mc:latest \
        -c "mc alias set myminio http://minio:9000 minioadmin minioadmin && mc rm --recursive --force myminio/reims" > /dev/null 2>&1
    
    # Restore from backup
    echo "Restoring from backup..."
    docker run --rm \
        --network reims2_reims-network \
        -v "$backup_dir:/backup" \
        --entrypoint sh \
        minio/mc:latest \
        -c "mc alias set myminio http://minio:9000 minioadmin minioadmin && mc mirror /backup/reims myminio/reims" > /dev/null 2>&1
    
    echo -e "${GREEN}✓ MinIO restore complete${NC}"
}

# Interactive restore menu
echo "Select restore option:"
echo "1) Restore PostgreSQL only"
echo "2) Restore MinIO only"
echo "3) Restore both"
echo "4) Exit"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        read -p "Enter PostgreSQL backup filename (or full path): " pg_file
        if [[ "$pg_file" != /* ]]; then
            pg_file="$BACKUP_DIR/$pg_file"
        fi
        restore_postgres "$pg_file"
        ;;
    2)
        read -p "Enter MinIO backup directory name (or full path): " minio_dir
        if [[ "$minio_dir" != /* ]]; then
            minio_dir="$BACKUP_DIR/$minio_dir"
        fi
        restore_minio "$minio_dir"
        ;;
    3)
        read -p "Enter PostgreSQL backup filename (or full path): " pg_file
        if [[ "$pg_file" != /* ]]; then
            pg_file="$BACKUP_DIR/$pg_file"
        fi
        read -p "Enter MinIO backup directory name (or full path): " minio_dir
        if [[ "$minio_dir" != /* ]]; then
            minio_dir="$BACKUP_DIR/$minio_dir"
        fi
        restore_postgres "$pg_file"
        restore_minio "$minio_dir"
        ;;
    4)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Restore completed at $(date)${NC}"

