#!/bin/bash
#
# Database Restore Script
# 
# Restores a REIMS PostgreSQL database from a backup file
#
# Usage:
#   ./scripts/restore_database.sh <backup_file>
#   ./scripts/restore_database.sh backups/reims_backup_20251104_120000.sql.gz
#

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backup file provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: No backup file specified${NC}"
    echo ""
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh backups/reims_backup_*.sql.gz 2>/dev/null | awk '{print "  "$9" ("$5")"}' || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Check if file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}WARNING: This will overwrite the current database!${NC}"
echo "Backup file: $BACKUP_FILE"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo "Restore cancelled"
    exit 0
fi

echo "Starting database restore..."

# Drop existing connections
echo "Closing active connections..."
docker exec reims-postgres psql -U reims -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'reims' AND pid <> pg_backend_pid();" \
    > /dev/null 2>&1 || true

# Restore database
echo "Restoring from backup..."
gunzip -c "$BACKUP_FILE" | docker exec -i reims-postgres psql -U reims reims

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database restored successfully${NC}"
    echo ""
    echo "Verifying restoration..."
    
    # Quick verification
    TABLE_COUNT=$(docker exec reims-postgres psql -U reims -d reims -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
    PROPERTY_COUNT=$(docker exec reims-postgres psql -U reims -d reims -t -c "SELECT COUNT(*) FROM properties;" | tr -d ' ')
    
    echo "  Tables found: $TABLE_COUNT"
    echo "  Properties: $PROPERTY_COUNT"
    echo ""
    echo -e "${GREEN}Restore complete!${NC}"
else
    echo -e "${RED}✗ Restore failed${NC}"
    exit 1
fi

