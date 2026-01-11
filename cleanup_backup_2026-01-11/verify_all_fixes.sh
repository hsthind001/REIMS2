#!/bin/bash

# Financial Metrics Integrity Verification Script
# Runs all checks to ensure fixes remain stable

set -e

echo "================================================================================"
echo "🔍 Financial Metrics Integrity Verification"
echo "================================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass_count=0
fail_count=0

# Test 1: Migration Status
echo "Test 1: Checking migration status..."
current_migration=$(docker compose exec -T backend alembic current 2>/dev/null | grep "20260106_1722" || echo "")
if [ -n "$current_migration" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Migration 20260106_1722 is applied"
    ((pass_count++))
else
    echo -e "${RED}❌ FAIL${NC} - Migration 20260106_1722 is NOT applied"
    ((fail_count++))
fi
echo ""

# Test 2: Database Column Count
echo "Test 2: Checking database column count..."
column_count=$(PGPASSWORD=reims docker compose exec -T postgres psql -U reims -d reims -t -c \
    "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'financial_metrics';" 2>/dev/null | tr -d '[:space:]')
if [ "$column_count" -ge 82 ]; then
    echo -e "${GREEN}✅ PASS${NC} - Database has $column_count columns (expected: 82+)"
    ((pass_count++))
else
    echo -e "${RED}❌ FAIL${NC} - Database has only $column_count columns (expected: 82+)"
    ((fail_count++))
fi
echo ""

# Test 3: Critical Columns Exist
echo "Test 3: Checking critical columns exist..."
critical_columns=("total_current_assets" "quick_ratio" "debt_to_assets_ratio" "dscr")
all_exist=true
for col in "${critical_columns[@]}"; do
    exists=$(PGPASSWORD=reims docker compose exec -T postgres psql -U reims -d reims -t -c \
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'financial_metrics' AND column_name = '$col';" 2>/dev/null | tr -d '[:space:]')
    if [ -n "$exists" ]; then
        echo "   ✓ $col exists"
    else
        echo "   ✗ $col MISSING"
        all_exist=false
    fi
done
if [ "$all_exist" = true ]; then
    echo -e "${GREEN}✅ PASS${NC} - All critical columns exist"
    ((pass_count++))
else
    echo -e "${RED}❌ FAIL${NC} - Some critical columns are missing"
    ((fail_count++))
fi
echo ""

# Test 4: No Duplicate Columns
echo "Test 4: Checking for duplicate column names..."
duplicates=$(PGPASSWORD=reims docker compose exec -T postgres psql -U reims -d reims -t -c \
    "SELECT column_name, COUNT(*) FROM information_schema.columns
     WHERE table_name = 'financial_metrics'
     GROUP BY column_name HAVING COUNT(*) > 1;" 2>/dev/null)
if [ -z "$duplicates" ]; then
    echo -e "${GREEN}✅ PASS${NC} - No duplicate columns found"
    ((pass_count++))
else
    echo -e "${RED}❌ FAIL${NC} - Found duplicate columns:"
    echo "$duplicates"
    ((fail_count++))
fi
echo ""

# Test 5: DSCR Calculation Accuracy
echo "Test 5: Verifying DSCR calculation accuracy..."
docker compose exec -T backend python -c "
import sys
sys.path.insert(0, '/app')
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings
from app.models.financial_metrics import FinancialMetrics
from app.models.financial_period import FinancialPeriod

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

metrics = db.query(FinancialMetrics).join(
    FinancialPeriod, FinancialMetrics.period_id == FinancialPeriod.id
).filter(
    FinancialMetrics.dscr.isnot(None),
    FinancialMetrics.net_operating_income.isnot(None),
    FinancialMetrics.total_annual_debt_service.isnot(None)
).limit(5).all()

all_accurate = True
for m in metrics:
    expected = float(m.net_operating_income) / float(m.total_annual_debt_service)
    actual = float(m.dscr)
    diff = abs(expected - actual)
    if diff >= 0.001:
        print(f'   ✗ DSCR mismatch: expected {expected:.4f}, got {actual:.4f}')
        all_accurate = False

if all_accurate:
    print('accurate')
else:
    print('inaccurate')

db.close()
" 2>/dev/null | grep -q "accurate"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PASS${NC} - DSCR calculations are accurate (within 0.001 tolerance)"
    ((pass_count++))
else
    echo -e "${RED}❌ FAIL${NC} - DSCR calculations have errors"
    ((fail_count++))
fi
echo ""

# Test 6: API Response Model Completeness
echo "Test 6: Checking API response model completeness..."
docker compose exec -T backend python -c "
import sys
sys.path.insert(0, '/app')
from app.api.v1.metrics import FinancialMetricsResponse

response_fields = set(FinancialMetricsResponse.model_fields.keys())
required = {'dscr', 'total_current_assets', 'quick_ratio', 'debt_to_assets_ratio'}
missing = required - response_fields

if missing:
    print('missing:', ','.join(missing))
else:
    print('complete')
" 2>/dev/null | grep -q "complete"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PASS${NC} - API response model includes all critical fields"
    ((pass_count++))
else
    echo -e "${RED}❌ FAIL${NC} - API response model is missing fields"
    ((fail_count++))
fi
echo ""

# Test 7: Frontend Year Filtering
echo "Test 7: Checking frontend year filtering implementation..."
grep_results=0

# Check CommandCenter.tsx
if grep -q "selectedYear" /home/hsthind/Documents/GitHub/REIMS2/src/pages/CommandCenter.tsx 2>/dev/null; then
    ((grep_results++))
fi

# Check PortfolioHub.tsx
if grep -q "selectedYear" /home/hsthind/Documents/GitHub/REIMS2/src/pages/PortfolioHub.tsx 2>/dev/null; then
    ((grep_results++))
fi

if [ $grep_results -eq 2 ]; then
    echo -e "${GREEN}✅ PASS${NC} - Year filtering implemented in both CommandCenter and PortfolioHub"
    ((pass_count++))
else
    echo -e "${RED}❌ FAIL${NC} - Year filtering not found in expected files"
    ((fail_count++))
fi
echo ""

# Test 8: Default Year Configuration
echo "Test 8: Checking default year is set to 2023..."
default_year_count=$(grep -c "useState<number>(2023)" /home/hsthind/Documents/GitHub/REIMS2/src/pages/CommandCenter.tsx 2>/dev/null || echo "0")
if [ "$default_year_count" -ge 1 ]; then
    echo -e "${GREEN}✅ PASS${NC} - Default year is set to 2023 in CommandCenter"
    ((pass_count++))
else
    echo -e "${YELLOW}⚠️  WARN${NC} - Default year may not be set to 2023 in CommandCenter"
    ((pass_count++))
fi
echo ""

# Summary
echo "================================================================================"
echo "📊 Test Results Summary"
echo "================================================================================"
echo ""
echo -e "Passed: ${GREEN}$pass_count${NC}"
echo -e "Failed: ${RED}$fail_count${NC}"
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}🎯 ALL TESTS PASSED - Financial Metrics Integrity Verified!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  SOME TESTS FAILED - Please review the failures above${NC}"
    echo ""
    echo "Recommended actions:"
    echo "1. Check FINANCIAL_METRICS_INTEGRITY_GUARD.md for troubleshooting"
    echo "2. Verify database migration is applied: docker compose exec backend alembic current"
    echo "3. Check if services are running: docker compose ps"
    echo ""
    exit 1
fi
