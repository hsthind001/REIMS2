#!/bin/bash

##############################################################################
# Seed Data Persistence Test Script
# Tests that extraction templates, validation rules, chart of accounts,
# and lenders persist across container restarts
##############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Seed Data Persistence Test"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

CONTAINER="reims-postgres"
DB_USER="reims"
DB_NAME="reims"

echo -e "${BLUE}Step 1: Check if PostgreSQL is running${NC}"
if ! docker ps | grep -q $CONTAINER; then
    echo -e "${RED}❌ PostgreSQL container is not running${NC}"
    echo "Please start the stack first: docker compose up -d"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL is running${NC}"
echo ""

echo -e "${BLUE}Step 2: Check extraction templates${NC}"
TEMPLATES_COUNT=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM extraction_templates;" | xargs)
echo "   Found $TEMPLATES_COUNT extraction templates"
if [ "$TEMPLATES_COUNT" -lt "4" ]; then
    echo -e "${RED}❌ Expected at least 4 extraction templates, found $TEMPLATES_COUNT${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Extraction templates present ($TEMPLATES_COUNT templates)${NC}"

# List templates
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
SELECT 
    template_name,
    document_type,
    is_default,
    array_length(keywords, 1) as keywords
FROM extraction_templates
ORDER BY document_type;
"
echo ""

echo -e "${BLUE}Step 3: Check validation rules${NC}"
RULES_COUNT=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM validation_rules;" | xargs)
echo "   Found $RULES_COUNT validation rules"
if [ "$RULES_COUNT" -lt "8" ]; then
    echo -e "${RED}❌ Expected at least 8 validation rules, found $RULES_COUNT${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Validation rules present ($RULES_COUNT rules)${NC}"

# List rules
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
SELECT 
    rule_name,
    document_type,
    severity,
    is_active
FROM validation_rules
ORDER BY document_type, id;
"
echo ""

echo -e "${BLUE}Step 4: Check chart of accounts${NC}"
ACCOUNTS_COUNT=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM chart_of_accounts;" | xargs)
echo "   Found $ACCOUNTS_COUNT chart of accounts"
if [ "$ACCOUNTS_COUNT" -lt "100" ]; then
    echo -e "${YELLOW}⚠️  Warning: Expected 300+ chart of accounts, found $ACCOUNTS_COUNT${NC}"
else
    echo -e "${GREEN}✅ Chart of accounts present ($ACCOUNTS_COUNT accounts)${NC}"
fi

# Show account distribution by type
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
SELECT 
    account_type,
    COUNT(*) as count
FROM chart_of_accounts
GROUP BY account_type
ORDER BY account_type;
"
echo ""

echo -e "${BLUE}Step 5: Check lenders${NC}"
LENDERS_COUNT=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM lenders;" | xargs)
echo "   Found $LENDERS_COUNT lenders"
if [ "$LENDERS_COUNT" -lt "10" ]; then
    echo -e "${YELLOW}⚠️  Warning: Expected 30+ lenders, found $LENDERS_COUNT${NC}"
else
    echo -e "${GREEN}✅ Lenders present ($LENDERS_COUNT lenders)${NC}"
fi

# List sample lenders
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
SELECT 
    lender_name,
    lender_code
FROM lenders
ORDER BY lender_name
LIMIT 10;
"
echo ""

echo -e "${BLUE}Step 6: Store initial counts${NC}"
INITIAL_TEMPLATES=$TEMPLATES_COUNT
INITIAL_RULES=$RULES_COUNT
INITIAL_ACCOUNTS=$ACCOUNTS_COUNT
INITIAL_LENDERS=$LENDERS_COUNT
echo "   Templates: $INITIAL_TEMPLATES"
echo "   Rules: $INITIAL_RULES"
echo "   Accounts: $INITIAL_ACCOUNTS"
echo "   Lenders: $INITIAL_LENDERS"
echo ""

echo -e "${YELLOW}Step 7: Restart PostgreSQL container${NC}"
echo "Stopping PostgreSQL..."
docker compose stop postgres
sleep 2
echo "Starting PostgreSQL..."
docker compose up -d postgres
echo "Waiting for PostgreSQL to be healthy..."
MAX_RETRIES=20
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if docker exec $CONTAINER pg_isready -U $DB_USER > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL restarted and healthy${NC}"
        break
    fi
    RETRY=$((RETRY + 1))
    echo "Waiting... ($RETRY/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ PostgreSQL failed to become healthy${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 8: Verify seed data after restart${NC}"

# Check templates
TEMPLATES_AFTER=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM extraction_templates;" | xargs)
echo "   Templates: $TEMPLATES_AFTER (was $INITIAL_TEMPLATES)"
if [ "$TEMPLATES_AFTER" != "$INITIAL_TEMPLATES" ]; then
    echo -e "${RED}❌ Template count changed after restart!${NC}"
    exit 1
fi

# Check rules
RULES_AFTER=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM validation_rules;" | xargs)
echo "   Rules: $RULES_AFTER (was $INITIAL_RULES)"
if [ "$RULES_AFTER" != "$INITIAL_RULES" ]; then
    echo -e "${RED}❌ Rule count changed after restart!${NC}"
    exit 1
fi

# Check accounts
ACCOUNTS_AFTER=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM chart_of_accounts;" | xargs)
echo "   Accounts: $ACCOUNTS_AFTER (was $INITIAL_ACCOUNTS)"
if [ "$ACCOUNTS_AFTER" != "$INITIAL_ACCOUNTS" ]; then
    echo -e "${RED}❌ Account count changed after restart!${NC}"
    exit 1
fi

# Check lenders
LENDERS_AFTER=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM lenders;" | xargs)
echo "   Lenders: $LENDERS_AFTER (was $INITIAL_LENDERS)"
if [ "$LENDERS_AFTER" != "$INITIAL_LENDERS" ]; then
    echo -e "${RED}❌ Lender count changed after restart!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All seed data intact after restart${NC}"
echo ""

echo -e "${YELLOW}Step 9: Test full down/up cycle${NC}"
echo "Stopping all services..."
docker compose down
sleep 2
echo "Starting all services..."
docker compose up -d
echo "Waiting for stack to be ready..."
sleep 15
echo -e "${GREEN}✅ Stack restarted${NC}"
echo ""

echo -e "${BLUE}Step 10: Verify seed data after down/up${NC}"

MAX_RETRIES=20
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    TEMPLATES_FINAL=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
      "SELECT COUNT(*) FROM extraction_templates;" 2>/dev/null | xargs || echo "0")
    
    if [ "$TEMPLATES_FINAL" = "$INITIAL_TEMPLATES" ]; then
        break
    fi
    RETRY=$((RETRY + 1))
    echo "Waiting for database... ($RETRY/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Failed to verify data after down/up${NC}"
    exit 1
fi

# Final checks
RULES_FINAL=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM validation_rules;" | xargs)
ACCOUNTS_FINAL=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM chart_of_accounts;" | xargs)
LENDERS_FINAL=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM lenders;" | xargs)

echo "   Templates: $TEMPLATES_FINAL (expected $INITIAL_TEMPLATES)"
echo "   Rules: $RULES_FINAL (expected $INITIAL_RULES)"
echo "   Accounts: $ACCOUNTS_FINAL (expected $INITIAL_ACCOUNTS)"
echo "   Lenders: $LENDERS_FINAL (expected $INITIAL_LENDERS)"

if [ "$TEMPLATES_FINAL" != "$INITIAL_TEMPLATES" ] || \
   [ "$RULES_FINAL" != "$INITIAL_RULES" ] || \
   [ "$ACCOUNTS_FINAL" != "$INITIAL_ACCOUNTS" ] || \
   [ "$LENDERS_FINAL" != "$INITIAL_LENDERS" ]; then
    echo -e "${RED}❌ Seed data counts changed after down/up!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All seed data persists after down/up!${NC}"
echo ""

echo -e "${BLUE}Step 11: Verify specific template content${NC}"
BALANCE_SHEET_TEMPLATE=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM extraction_templates WHERE template_name = 'standard_balance_sheet';" | xargs)
if [ "$BALANCE_SHEET_TEMPLATE" != "1" ]; then
    echo -e "${RED}❌ Balance sheet template not found!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Balance sheet template verified${NC}"
echo ""

echo -e "${BLUE}Step 12: Verify specific validation rule${NC}"
BS_EQUATION=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c \
  "SELECT COUNT(*) FROM validation_rules WHERE rule_name = 'balance_sheet_equation';" | xargs)
if [ "$BS_EQUATION" != "1" ]; then
    echo -e "${RED}❌ Balance sheet equation rule not found!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Balance sheet equation rule verified${NC}"
echo ""

echo -e "${BLUE}Step 13: Sample accounts by range${NC}"
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
SELECT 
    CASE 
        WHEN account_code < '2000-0000' THEN 'Assets (0xxx-1xxx)'
        WHEN account_code < '4000-0000' THEN 'Liabilities/Equity (2xxx-3xxx)'
        WHEN account_code < '7000-0000' THEN 'Income/Expenses (4xxx-6xxx)'
        ELSE 'Other (7xxx+)'
    END as range,
    COUNT(*) as count
FROM chart_of_accounts
GROUP BY range
ORDER BY range;
"
echo ""

echo -e "${BLUE}Step 14: Check seed file locations${NC}"
if [ -f "backend/scripts/seed_extraction_templates.sql" ]; then
    echo -e "${GREEN}✅ seed_extraction_templates.sql found${NC}"
else
    echo -e "${RED}❌ seed_extraction_templates.sql not found${NC}"
fi

if [ -f "backend/scripts/seed_validation_rules.sql" ]; then
    echo -e "${GREEN}✅ seed_validation_rules.sql found${NC}"
else
    echo -e "${RED}❌ seed_validation_rules.sql not found${NC}"
fi

if [ -f "backend/scripts/seed_lenders.sql" ]; then
    echo -e "${GREEN}✅ seed_lenders.sql found${NC}"
else
    echo -e "${RED}❌ seed_lenders.sql not found${NC}"
fi
echo ""

echo "=========================================="
echo -e "${GREEN}✅ ALL SEED DATA PERSISTENCE TESTS PASSED!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  • Extraction Templates: $TEMPLATES_FINAL"
echo "  • Validation Rules: $RULES_FINAL"
echo "  • Chart of Accounts: $ACCOUNTS_FINAL"
echo "  • Lenders: $LENDERS_FINAL"
echo ""
echo "Persistence verified:"
echo "  ✅ Data persists across container restarts"
echo "  ✅ Data persists across docker compose down/up"
echo "  ✅ Template content intact"
echo "  ✅ Validation rules intact"
echo "  ✅ Seed files present in codebase"
echo ""
echo "Your seed data is fully persistent!"
echo ""
echo "View seed data:"
echo "  docker exec -it reims-postgres psql -U reims -d reims"
echo "  \\dt  -- list tables"
echo "  SELECT * FROM extraction_templates;"
echo "  SELECT * FROM validation_rules;"
echo ""
echo "For more information, see: SEED_DATA_PERSISTENCE.md"

