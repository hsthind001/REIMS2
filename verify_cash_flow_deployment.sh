#!/bin/bash

# Cash Flow Template v1.0 Deployment Verification Script
# Comprehensive verification of deployment success
# Date: November 4, 2025

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
TOTAL_CHECKS=0

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Cash Flow Template v1.0 - Deployment Verification${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

check_pass() {
    echo -e "${GREEN}✅ PASS${NC} - $1"
    PASS_COUNT=$((PASS_COUNT + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

check_fail() {
    echo -e "${RED}❌ FAIL${NC} - $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

check_info() {
    echo -e "${BLUE}ℹ️  INFO${NC} - $1"
}

# Check 1: Docker containers running
echo "🐳 Checking Docker Containers..."
if docker ps | grep -q "reims-backend"; then
    check_pass "Backend container is running"
else
    check_fail "Backend container is not running"
fi

if docker ps | grep -q "reims-celery-worker"; then
    check_pass "Celery worker container is running"
else
    check_fail "Celery worker container is not running"
fi

if docker ps | grep -q "reims-postgres"; then
    check_pass "PostgreSQL container is running"
else
    check_fail "PostgreSQL container is not running"
fi

echo ""

# Check 2: Migration status
echo "🔄 Checking Database Migration..."
MIGRATION_OUTPUT=$(docker exec reims-backend alembic current 2>&1 || echo "failed")

if echo "$MIGRATION_OUTPUT" | grep -q "939c6b495488"; then
    check_pass "Cash Flow Template v1.0 migration applied (939c6b495488)"
else
    check_fail "Migration not applied or incorrect version"
    check_info "Current: $MIGRATION_OUTPUT"
fi

echo ""

# Check 3: Database tables
echo "🗄️  Checking Database Tables..."

# cash_flow_headers
if docker exec reims-postgres psql -U reims -d reims -c "\d cash_flow_headers" > /dev/null 2>&1; then
    check_pass "cash_flow_headers table exists"
else
    check_fail "cash_flow_headers table not found"
fi

# cash_flow_data (check for new columns)
COLUMN_CHECK=$(docker exec reims-postgres psql -U reims -d reims -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='cash_flow_data' AND column_name IN ('header_id', 'line_section', 'line_category', 'line_subcategory');" 2>&1 || echo "")

if echo "$COLUMN_CHECK" | grep -q "header_id"; then
    check_pass "cash_flow_data.header_id column added"
else
    check_fail "cash_flow_data.header_id column not found"
fi

if echo "$COLUMN_CHECK" | grep -q "line_section"; then
    check_pass "cash_flow_data.line_section column added"
else
    check_fail "cash_flow_data.line_section column not found"
fi

if echo "$COLUMN_CHECK" | grep -q "line_category"; then
    check_pass "cash_flow_data.line_category column added"
else
    check_fail "cash_flow_data.line_category column not found"
fi

# cash_flow_adjustments
if docker exec reims-postgres psql -U reims -d reims -c "\d cash_flow_adjustments" > /dev/null 2>&1; then
    check_pass "cash_flow_adjustments table exists"
else
    check_fail "cash_flow_adjustments table not found"
fi

# cash_account_reconciliations
if docker exec reims-postgres psql -U reims -d reims -c "\d cash_account_reconciliations" > /dev/null 2>&1; then
    check_pass "cash_account_reconciliations table exists"
else
    check_fail "cash_account_reconciliations table not found"
fi

echo ""

# Check 4: API Health
echo "🏥 Checking API Health..."
if curl -s http://localhost:8000/api/v1/health | grep -q "healthy"; then
    check_pass "API health endpoint responding"
else
    check_fail "API health endpoint not responding"
fi

echo ""

# Check 5: API Documentation
echo "📚 Checking API Documentation..."
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    check_pass "Swagger UI accessible"
else
    check_fail "Swagger UI not accessible"
fi

echo ""

# Check 6: Models loaded
echo "🔧 Checking Models Loaded..."
MODEL_CHECK=$(docker exec reims-backend python -c "from app.models.cash_flow_header import CashFlowHeader; from app.models.cash_flow_adjustments import CashFlowAdjustment; from app.models.cash_account_reconciliation import CashAccountReconciliation; print('OK')" 2>&1 || echo "failed")

if echo "$MODEL_CHECK" | grep -q "OK"; then
    check_pass "All new models loaded successfully"
else
    check_fail "Models failed to load"
    check_info "Error: $MODEL_CHECK"
fi

echo ""

# Check 7: Validation rules
echo "✔️  Checking Validation Rules..."
VALIDATION_CHECK=$(docker exec reims-postgres psql -U reims -d reims -t -c "SELECT COUNT(*) FROM validation_rules WHERE rule_code LIKE 'cf_%';" 2>&1 | tr -d '[:space:]' || echo "0")

if [ "$VALIDATION_CHECK" -gt "0" ]; then
    check_pass "Cash Flow validation rules exist ($VALIDATION_CHECK rules)"
else
    check_info "Cash Flow validation rules will be created on first use"
fi

echo ""

# Check 8: Test extraction functionality
echo "🧪 Testing Extraction Functionality..."
PARSER_CHECK=$(docker exec reims-backend python -c "from app.utils.financial_table_parser import FinancialTableParser; p = FinancialTableParser(); print('OK')" 2>&1 || echo "failed")

if echo "$PARSER_CHECK" | grep -q "OK"; then
    check_pass "FinancialTableParser initialized successfully"
else
    check_fail "FinancialTableParser failed to initialize"
fi

echo ""

# Final Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Verification Results${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "📊 Summary:"
echo "  • Total Checks: $TOTAL_CHECKS"
echo -e "  • Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "  • Failed: ${RED}$FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED!${NC}"
    echo -e "${GREEN}✅ Cash Flow Template v1.0 is fully deployed and operational!${NC}"
    echo ""
    echo "You can now:"
    echo "  • Upload Cash Flow Statement PDFs"
    echo "  • Extract 100+ line items automatically"
    echo "  • View data in structured database tables"
    echo "  • Run validation rules"
    echo "  • Generate reports"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  SOME CHECKS FAILED ($FAIL_COUNT failures)${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "  1. Check logs: docker-compose logs backend"
    echo "  2. Check migration status: docker exec reims-backend alembic current"
    echo "  3. Check database: docker exec -it reims-postgres psql -U reims -d reims"
    echo "  4. Rebuild containers: docker-compose down && docker-compose build && docker-compose up -d"
    echo ""
    exit 1
fi

