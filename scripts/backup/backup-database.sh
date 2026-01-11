#!/bin/bash

##############################################################################
# PostgreSQL Database Backup Script
# Automatically backs up the REIMS database with compression
##############################################################################

set -e

# Configuration
BACKUP_DIR="$HOME/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_ONLY=$(date +%Y%m%d)
CONTAINER="reims-postgres"
DB_NAME="reims"
DB_USER="reims"
KEEP_DAYS=7

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "PostgreSQL Database Backup"
echo "=========================================="
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if container is running
if ! docker ps | grep -q "$CONTAINER"; then
    echo -e "${RED}❌ Error: PostgreSQL container '$CONTAINER' is not running${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Container:${NC} $CONTAINER"
echo -e "${BLUE}🗄️  Database:${NC} $DB_NAME"
echo -e "${BLUE}📁 Backup Dir:${NC} $BACKUP_DIR"
echo ""

# Backup database (SQL format - compressed)
echo -e "${BLUE}🔄 Creating backup...${NC}"
BACKUP_FILE="$BACKUP_DIR/reims-db-$TIMESTAMP.sql.gz"

docker exec $CONTAINER pg_dump -U $DB_USER -d $DB_NAME \
  | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backup complete!${NC}"
    echo ""
    echo -e "${GREEN}📄 File:${NC} reims-db-$TIMESTAMP.sql.gz"
    echo -e "${GREEN}📁 Location:${NC} $BACKUP_DIR"
    echo -e "${GREEN}📊 Size:${NC} $(du -h $BACKUP_FILE | cut -f1)"
else
    echo -e "${RED}❌ Backup failed!${NC}"
    exit 1
fi

# Get database statistics
echo ""
echo -e "${BLUE}📊 Database Statistics:${NC}"
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT 
    COUNT(*) || ' tables' as tables
FROM information_schema.tables 
WHERE table_schema = 'public';
" | xargs echo "   Tables:"

docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT pg_size_pretty(pg_database_size('$DB_NAME'));
" | xargs echo "   Database size:"

docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM chart_of_accounts;
" | xargs echo "   Chart of accounts:"

docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM lenders;
" | xargs echo "   Lenders:"

# Clean old backups
echo ""
echo -e "${BLUE}🧹 Cleaning old backups (keeping last $KEEP_DAYS days)...${NC}"
DELETED=$(find "$BACKUP_DIR" -name "reims-db-*.sql.gz" -mtime +$KEEP_DAYS -type f)
if [ -n "$DELETED" ]; then
    echo "$DELETED" | while read file; do
        echo "   Deleting: $(basename $file)"
        rm "$file"
    done
    echo -e "${GREEN}✅ Old backups cleaned${NC}"
else
    echo "   No old backups to clean"
fi

# List recent backups
echo ""
echo -e "${BLUE}📚 Recent backups:${NC}"
ls -lh "$BACKUP_DIR"/reims-db-*.sql.gz 2>/dev/null | tail -5 | awk '{print "   " $9 " (" $5 ")"}'

echo ""
echo "=========================================="
echo -e "${GREEN}✅ BACKUP COMPLETE!${NC}"
echo "=========================================="
echo ""
echo "To restore this backup:"
echo "  1. Stop services: docker compose stop backend celery-worker"
echo "  2. Drop database: docker exec reims-postgres psql -U reims -c 'DROP DATABASE IF EXISTS reims;'"
echo "  3. Create database: docker exec reims-postgres psql -U reims -c 'CREATE DATABASE reims;'"
echo "  4. Restore: gunzip < $BACKUP_FILE | docker exec -i reims-postgres psql -U reims -d reims"
echo "  5. Restart: docker compose up -d"
echo ""
echo "For more information, see: DATABASE_PERSISTENCE.md"

