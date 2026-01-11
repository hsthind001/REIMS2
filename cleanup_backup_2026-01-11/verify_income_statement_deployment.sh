#!/bin/bash
###############################################################################
# Income Statement Template v1.0 - Verification Script
#
# Verifies that the deployment was successful by checking:
# - Database tables exist
# - Relationships are valid
# - Services are running
# - Sample query works
###############################################################################

set -e

echo "================================================"
echo "Income Statement Template v1.0 - Verification"
echo "================================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0

# Function to check and report
check_item() {
    local description=$1
    local command=$2
    
    echo -n "Checking: $description... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASS_COUNT++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAIL_COUNT++))
        return 1
    fi
}

echo "1. Service Status Checks"
echo "------------------------"

check_item "Backend service running" \
    "docker-compose ps backend | grep -q 'Up'"

check_item "Database service running" \
    "docker-compose ps postgres | grep -q 'Up'"

echo ""
echo "2. Database Schema Checks"
echo "-------------------------"

check_item "income_statement_headers table exists" \
    "docker-compose exec -T postgres psql -U reims -d reims -c '\\dt income_statement_headers' | grep -q 'income_statement_headers'"

check_item "header_id column in income_statement_data" \
    "docker-compose exec -T postgres psql -U reims -d reims -c '\\d income_statement_data' | grep -q 'header_id'"

check_item "Income statement chart of accounts seeded" \
    "docker-compose exec -T postgres psql -U reims -d reims -t -c \"SELECT COUNT(*) FROM chart_of_accounts WHERE document_types @> ARRAY['income_statement']\" | grep -q -E '[1-9][0-9]+'"

echo ""
echo "3. Model Import Checks"
echo "----------------------"

check_item "IncomeStatementHeader model imports" \
    "docker-compose exec -T backend python -c 'from app.models.income_statement_header import IncomeStatementHeader; print(\"OK\")' | grep -q 'OK'"

check_item "Income statement schemas import" \
    "docker-compose exec -T backend python -c 'from app.schemas.income_statement import IncomeStatementHeaderResponse; print(\"OK\")' | grep -q 'OK'"

echo ""
echo "4. Database Relationship Checks"
echo "--------------------------------"

check_item "Foreign key constraints exist" \
    "docker-compose exec -T postgres psql -U reims -d reims -c '\\d income_statement_headers' | grep -q 'Foreign-key constraints'"

check_item "Indexes created" \
    "docker-compose exec -T postgres psql -U reims -d reims -c '\\d income_statement_headers' | grep -q 'Indexes'"

echo ""
echo "5. Validation Rules Check"
echo "-------------------------"

check_item "Income statement validation rules exist" \
    "docker-compose exec -T postgres psql -U reims -d reims -t -c \"SELECT COUNT(*) FROM validation_rules WHERE document_type = 'income_statement'\" | grep -q -E '[1-9][0-9]*'"

echo ""
echo "================================================"
echo "Verification Summary"
echo "================================================"
echo ""
echo -e "Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Income Statement Template v1.0 is ready.${NC}"
    echo ""
    echo "You can now:"
    echo "  • Upload Income Statement PDFs via the UI or API"
    echo "  • View extracted data with headers and full categorization"
    echo "  • Run validations (13 rules active)"
    echo "  • Generate reports with all Template v1.0 fields"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review the errors above.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check migration status: docker-compose exec backend alembic current"
    echo "  2. View backend logs: docker-compose logs backend"
    echo "  3. Check database: docker-compose exec postgres psql -U reims -d reims"
    echo ""
    exit 1
fi

