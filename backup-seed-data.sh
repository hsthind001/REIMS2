#!/bin/bash

##############################################################################
# Seed Data Backup Script
# Exports extraction templates, validation rules, chart of accounts, and lenders
##############################################################################

set -e

# Configuration
BACKUP_DIR="$HOME/backups/seed-data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_ONLY=$(date +%Y%m%d)
CONTAINER="reims-postgres"
DB_NAME="reims"
DB_USER="reims"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Seed Data Backup"
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

# Count records before backup
echo -e "${BLUE}📊 Counting seed data...${NC}"
TEMPLATES=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM extraction_templates;" | xargs)
RULES=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM validation_rules;" | xargs)
ACCOUNTS=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM chart_of_accounts;" | xargs)
LENDERS=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM lenders;" | xargs)

echo "  Extraction Templates: $TEMPLATES"
echo "  Validation Rules: $RULES"
echo "  Chart of Accounts: $ACCOUNTS"
echo "  Lenders: $LENDERS"
echo ""

# Backup extraction templates
echo -e "${BLUE}🔄 Backing up extraction templates...${NC}"
docker exec $CONTAINER pg_dump -U $DB_USER -d $DB_NAME \
  --table=extraction_templates \
  --data-only --inserts \
  > "$BACKUP_DIR/extraction_templates_$TIMESTAMP.sql"
echo -e "${GREEN}✅ Extraction templates backed up${NC}"

# Backup validation rules
echo -e "${BLUE}🔄 Backing up validation rules...${NC}"
docker exec $CONTAINER pg_dump -U $DB_USER -d $DB_NAME \
  --table=validation_rules \
  --data-only --inserts \
  > "$BACKUP_DIR/validation_rules_$TIMESTAMP.sql"
echo -e "${GREEN}✅ Validation rules backed up${NC}"

# Backup chart of accounts
echo -e "${BLUE}🔄 Backing up chart of accounts...${NC}"
docker exec $CONTAINER pg_dump -U $DB_USER -d $DB_NAME \
  --table=chart_of_accounts \
  --data-only --inserts \
  > "$BACKUP_DIR/chart_of_accounts_$TIMESTAMP.sql"
echo -e "${GREEN}✅ Chart of accounts backed up${NC}"

# Backup lenders
echo -e "${BLUE}🔄 Backing up lenders...${NC}"
docker exec $CONTAINER pg_dump -U $DB_USER -d $DB_NAME \
  --table=lenders \
  --data-only --inserts \
  > "$BACKUP_DIR/lenders_$TIMESTAMP.sql"
echo -e "${GREEN}✅ Lenders backed up${NC}"

# Create combined backup
echo ""
echo -e "${BLUE}🔄 Creating combined backup...${NC}"
COMBINED_FILE="$BACKUP_DIR/all_seed_data_$TIMESTAMP.sql"
cat > "$COMBINED_FILE" << EOF
-- REIMS Seed Data Backup
-- Date: $(date)
-- Extraction Templates: $TEMPLATES
-- Validation Rules: $RULES
-- Chart of Accounts: $ACCOUNTS
-- Lenders: $LENDERS

-- ========================================
-- Extraction Templates
-- ========================================

EOF

cat "$BACKUP_DIR/extraction_templates_$TIMESTAMP.sql" >> "$COMBINED_FILE"

cat >> "$COMBINED_FILE" << EOF

-- ========================================
-- Validation Rules
-- ========================================

EOF

cat "$BACKUP_DIR/validation_rules_$TIMESTAMP.sql" >> "$COMBINED_FILE"

cat >> "$COMBINED_FILE" << EOF

-- ========================================
-- Chart of Accounts
-- ========================================

EOF

cat "$BACKUP_DIR/chart_of_accounts_$TIMESTAMP.sql" >> "$COMBINED_FILE"

cat >> "$COMBINED_FILE" << EOF

-- ========================================
-- Lenders
-- ========================================

EOF

cat "$BACKUP_DIR/lenders_$TIMESTAMP.sql" >> "$COMBINED_FILE"

# Compress combined backup
gzip "$COMBINED_FILE"
echo -e "${GREEN}✅ Combined backup created and compressed${NC}"
echo ""

# Show file sizes
echo -e "${BLUE}📊 Backup file sizes:${NC}"
ls -lh "$BACKUP_DIR"/extraction_templates_$TIMESTAMP.sql | awk '{print "  Extraction Templates: " $5}'
ls -lh "$BACKUP_DIR"/validation_rules_$TIMESTAMP.sql | awk '{print "  Validation Rules:     " $5}'
ls -lh "$BACKUP_DIR"/chart_of_accounts_$TIMESTAMP.sql | awk '{print "  Chart of Accounts:    " $5}'
ls -lh "$BACKUP_DIR"/lenders_$TIMESTAMP.sql | awk '{print "  Lenders:              " $5}'
ls -lh "$BACKUP_DIR"/all_seed_data_$TIMESTAMP.sql.gz | awk '{print "  Combined (compressed):" $5}'
echo ""

# List recent backups
echo -e "${BLUE}📚 Recent backups:${NC}"
ls -lt "$BACKUP_DIR"/all_seed_data_*.sql.gz 2>/dev/null | head -5 | \
  awk '{print "  " $9 " (" $5 ")"}'
echo ""

echo "=========================================="
echo -e "${GREEN}✅ SEED DATA BACKUP COMPLETE!${NC}"
echo "=========================================="
echo ""
echo "Files created:"
echo "  📄 extraction_templates_$TIMESTAMP.sql"
echo "  📄 validation_rules_$TIMESTAMP.sql"
echo "  📄 chart_of_accounts_$TIMESTAMP.sql"
echo "  📄 lenders_$TIMESTAMP.sql"
echo "  📦 all_seed_data_$TIMESTAMP.sql.gz (combined, compressed)"
echo ""
echo "📁 Location: $BACKUP_DIR"
echo ""
echo "To restore this backup:"
echo "  1. Extract combined backup:"
echo "     gunzip $BACKUP_DIR/all_seed_data_$TIMESTAMP.sql.gz"
echo ""
echo "  2. Restore to database:"
echo "     docker exec -i reims-postgres psql -U reims -d reims \\"
echo "       < $BACKUP_DIR/all_seed_data_$TIMESTAMP.sql"
echo ""
echo "Or restore individual tables:"
echo "  docker exec -i reims-postgres psql -U reims -d reims \\"
echo "    < $BACKUP_DIR/extraction_templates_$TIMESTAMP.sql"
echo ""
echo "For more information, see: SEED_DATA_PERSISTENCE.md"

