#!/bin/bash

# Cash Flow Template v1.0 Rollback Script
# Safely rolls back the Cash Flow Template v1.0 migration if needed
# Date: November 4, 2025

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  Cash Flow Template v1.0 - ROLLBACK${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC}  $1"
}

echo -e "${RED}⚠️  WARNING: This will rollback the Cash Flow Template v1.0 migration${NC}"
echo -e "${RED}⚠️  The following will be removed:${NC}"
echo "  • cash_flow_headers table"
echo "  • cash_flow_adjustments table"
echo "  • cash_account_reconciliations table"
echo "  • New columns in cash_flow_data table"
echo ""

read -p "Are you sure you want to rollback? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    print_info "Rollback cancelled"
    exit 0
fi

echo ""

# Step 1: Backup current database
print_info "Step 1/4: Creating safety backup..."
BACKUP_FILE="backup_before_rollback_$(date +%Y%m%d_%H%M%S).sql"

if docker exec reims-postgres pg_dump -U reims reims > "backend/backups/$BACKUP_FILE"; then
    gzip "backend/backups/$BACKUP_FILE"
    print_status "Backup created: backend/backups/${BACKUP_FILE}.gz"
else
    print_error "Backup failed. Aborting rollback for safety."
    exit 1
fi

echo ""

# Step 2: Get current migration
print_info "Step 2/4: Checking current migration..."
CURRENT_MIGRATION=$(docker exec reims-backend alembic current 2>&1 || echo "unknown")

if echo "$CURRENT_MIGRATION" | grep -q "939c6b495488"; then
    print_info "Current migration: 939c6b495488 (Cash Flow Template v1.0)"
else
    print_warning "Current migration not as expected: $CURRENT_MIGRATION"
fi

echo ""

# Step 3: Rollback migration
print_info "Step 3/4: Rolling back migration..."

if docker exec reims-backend alembic downgrade -1; then
    print_status "Migration rolled back successfully"
else
    print_error "Migration rollback failed"
    print_error "You may need to restore from backup: backend/backups/${BACKUP_FILE}.gz"
    exit 1
fi

echo ""

# Step 4: Restart services
print_info "Step 4/4: Restarting services..."

docker-compose restart backend celery-worker

print_status "Services restarted"

echo ""

# Verification
print_info "Verifying rollback..."

# Check migration
NEW_MIGRATION=$(docker exec reims-backend alembic current 2>&1 || echo "unknown")
print_info "Current migration: $NEW_MIGRATION"

# Check tables
TABLE_COUNT=$(docker exec reims-postgres psql -U reims -d reims -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name IN ('cash_flow_headers', 'cash_flow_adjustments', 'cash_account_reconciliations');" 2>&1 | tr -d '[:space:]' || echo "0")

if [ "$TABLE_COUNT" = "0" ]; then
    print_status "New tables removed successfully"
else
    print_warning "Some tables may still exist (count: $TABLE_COUNT)"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Rollback Complete${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

print_status "System rolled back to previous state"
print_info "Backup available at: backend/backups/${BACKUP_FILE}.gz"
echo ""

echo "To restore from backup if needed:"
echo "  gunzip backend/backups/${BACKUP_FILE}.gz"
echo "  cat backend/backups/${BACKUP_FILE} | docker exec -i reims-postgres psql -U reims -d reims"
echo ""

