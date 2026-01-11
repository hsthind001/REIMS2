#!/bin/bash

##############################################################################
# PostgreSQL Database Persistence Test Script
# Tests that database schema and data persist across container restarts
##############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "PostgreSQL Database Persistence Test"
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
TEST_EMAIL="persistence-test-$(date +%s)@example.com"

echo -e "${BLUE}Step 1: Check if PostgreSQL is running${NC}"
if ! docker ps | grep -q $CONTAINER; then
    echo -e "${RED}❌ PostgreSQL container is not running${NC}"
    echo "Please start the stack first: docker compose up -d"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL is running${NC}"
echo ""

echo -e "${BLUE}Step 2: Check database exists${NC}"
DB_EXISTS=$(docker exec $CONTAINER psql -U $DB_USER -lqt | cut -d \| -f 1 | grep -w $DB_NAME | wc -l)
if [ "$DB_EXISTS" -eq "0" ]; then
    echo -e "${RED}❌ Database '$DB_NAME' does not exist${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Database '$DB_NAME' exists${NC}"
echo ""

echo -e "${BLUE}Step 3: Check tables exist${NC}"
TABLE_COUNT=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
")
echo "   Found $TABLE_COUNT tables"
if [ "$TABLE_COUNT" -lt "10" ]; then
    echo -e "${RED}❌ Expected at least 10 tables, found $TABLE_COUNT${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Schema has $TABLE_COUNT tables${NC}"
echo ""

echo -e "${BLUE}Step 4: Check seeded data (Chart of Accounts)${NC}"
COA_COUNT=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM chart_of_accounts;
" | xargs)
echo "   Chart of Accounts: $COA_COUNT entries"
if [ "$COA_COUNT" -lt "100" ]; then
    echo -e "${YELLOW}⚠️  Warning: Expected 300+ chart of accounts, found $COA_COUNT${NC}"
else
    echo -e "${GREEN}✅ Chart of accounts seeded ($COA_COUNT entries)${NC}"
fi
echo ""

echo -e "${BLUE}Step 5: Check seeded data (Lenders)${NC}"
LENDER_COUNT=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM lenders;
" | xargs)
echo "   Lenders: $LENDER_COUNT entries"
if [ "$LENDER_COUNT" -lt "10" ]; then
    echo -e "${YELLOW}⚠️  Warning: Expected 30+ lenders, found $LENDER_COUNT${NC}"
else
    echo -e "${GREEN}✅ Lenders seeded ($LENDER_COUNT entries)${NC}"
fi
echo ""

echo -e "${BLUE}Step 6: Check migration history${NC}"
MIGRATION_VERSION=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT version_num FROM alembic_version LIMIT 1;
" | xargs)
if [ -z "$MIGRATION_VERSION" ]; then
    echo -e "${RED}❌ No migration version found${NC}"
    exit 1
fi
echo "   Current migration: $MIGRATION_VERSION"
echo -e "${GREEN}✅ Migrations tracked${NC}"
echo ""

echo -e "${BLUE}Step 7: Insert test data${NC}"
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
INSERT INTO users (email, full_name, is_active, created_at, updated_at)
VALUES ('$TEST_EMAIL', 'Persistence Test User', true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;
" > /dev/null
echo -e "${GREEN}✅ Test user created: $TEST_EMAIL${NC}"
echo ""

echo -e "${BLUE}Step 8: Verify test data exists${NC}"
USER_EXISTS=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM users WHERE email = '$TEST_EMAIL';
" | xargs)
if [ "$USER_EXISTS" -ne "1" ]; then
    echo -e "${RED}❌ Test user not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Test user exists in database${NC}"
echo ""

echo -e "${YELLOW}Step 9: Restart PostgreSQL container${NC}"
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

echo -e "${BLUE}Step 10: Verify data persists after restart${NC}"
USER_EXISTS_AFTER=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM users WHERE email = '$TEST_EMAIL';
" | xargs)
if [ "$USER_EXISTS_AFTER" -ne "1" ]; then
    echo -e "${RED}❌ Test user disappeared after restart!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Test user still exists after restart${NC}"
echo ""

echo -e "${BLUE}Step 11: Verify seeded data still intact${NC}"
COA_COUNT_AFTER=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT COUNT(*) FROM chart_of_accounts;
" | xargs)
if [ "$COA_COUNT_AFTER" != "$COA_COUNT" ]; then
    echo -e "${RED}❌ Chart of accounts count changed! Before: $COA_COUNT, After: $COA_COUNT_AFTER${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Chart of accounts intact ($COA_COUNT_AFTER entries)${NC}"
echo ""

echo -e "${YELLOW}Step 12: Test full down/up cycle${NC}"
echo "Stopping all services..."
docker compose down
sleep 2
echo "Starting all services..."
docker compose up -d
echo "Waiting for stack to be ready..."
sleep 15
echo -e "${GREEN}✅ Stack restarted${NC}"
echo ""

echo -e "${BLUE}Step 13: Verify data persists after down/up${NC}"
MAX_RETRIES=20
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    USER_EXISTS_FINAL=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
    SELECT COUNT(*) FROM users WHERE email = '$TEST_EMAIL';
    " 2>/dev/null | xargs || echo "0")
    
    if [ "$USER_EXISTS_FINAL" = "1" ]; then
        echo -e "${GREEN}✅ Test user still exists after down/up!${NC}"
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
echo ""

echo -e "${BLUE}Step 14: Verify migration version intact${NC}"
MIGRATION_VERSION_FINAL=$(docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
SELECT version_num FROM alembic_version LIMIT 1;
" | xargs)
if [ "$MIGRATION_VERSION_FINAL" != "$MIGRATION_VERSION" ]; then
    echo -e "${RED}❌ Migration version changed!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Migration version intact: $MIGRATION_VERSION_FINAL${NC}"
echo ""

echo -e "${BLUE}Step 15: Database statistics${NC}"
echo "Database statistics:"
docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
SELECT 
    schemaname,
    COUNT(*) as tables,
    SUM(n_live_tup) as total_rows
FROM pg_stat_user_tables
GROUP BY schemaname;
"
echo ""

echo -e "${BLUE}Step 16: Volume information${NC}"
VOLUME_INFO=$(docker volume inspect reims_postgres-data --format '{{.Mountpoint}}' 2>/dev/null || echo "Volume not found")
echo "   Volume location: $VOLUME_INFO"
if [ "$VOLUME_INFO" != "Volume not found" ]; then
    VOLUME_SIZE=$(docker run --rm -v reims_postgres-data:/data ubuntu du -sh /data 2>/dev/null | cut -f1 || echo "Unknown")
    echo "   Volume size: $VOLUME_SIZE"
    echo -e "${GREEN}✅ Volume exists and is accessible${NC}"
else
    echo -e "${RED}❌ Volume not found!${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 17: Cleanup (optional)${NC}"
read -p "Do you want to delete the test user? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "
    DELETE FROM users WHERE email = '$TEST_EMAIL';
    " > /dev/null
    echo -e "${GREEN}✅ Test user deleted${NC}"
else
    echo -e "${YELLOW}ℹ️  Test user kept: $TEST_EMAIL${NC}"
fi
echo ""

echo "=========================================="
echo -e "${GREEN}✅ ALL PERSISTENCE TESTS PASSED!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  • Database: $DB_NAME"
echo "  • Tables: $TABLE_COUNT"
echo "  • Chart of Accounts: $COA_COUNT entries"
echo "  • Lenders: $LENDER_COUNT"
echo "  • Migration: $MIGRATION_VERSION"
echo "  • Volume: reims_postgres-data ($VOLUME_SIZE)"
echo "  • Data persists across container restarts: ✅"
echo "  • Data persists across docker compose down/up: ✅"
echo "  • Schema and migrations intact: ✅"
echo ""
echo "Your PostgreSQL database is fully persistent!"
echo ""
echo "Access database:"
echo "  docker exec -it reims-postgres psql -U reims -d reims"
echo ""
echo "Access pgAdmin:"
echo "  http://localhost:5050"
echo "  Email: admin@pgadmin.com"
echo "  Password: admin"
echo ""
echo "For more information, see: DATABASE_PERSISTENCE.md"

