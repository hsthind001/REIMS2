# Financial Metrics Integrity Guard

## 🛡️ Protection Against Breaking Changes

This document ensures all fixes for financial metrics formulas and calculations remain stable.

**Last Verified**: 2026-01-06 19:33 UTC
**Status**: ✅ All Systems Operational

---

## Critical Fixes Applied

### 1. Database Schema - 43 New Columns Added

**Migration**: `backend/alembic/versions/20260106_1722_add_missing_financial_metrics_columns.py`

**Status**: ✅ Applied and Verified

**Total Columns**: 82 (excluding id)

**New Columns by Category**:

#### Balance Sheet Totals (5 columns)
- `total_current_assets`
- `total_property_equipment`
- `total_other_assets`
- `total_current_liabilities`
- `total_long_term_liabilities`

#### Liquidity Metrics (3 columns)
- `quick_ratio`
- `cash_ratio`
- `working_capital`

#### Leverage Metrics (3 columns)
- `debt_to_assets_ratio`
- `equity_ratio`
- `ltv_ratio`

#### Property Metrics (7 columns)
- `gross_property_value`
- `accumulated_depreciation`
- `net_property_value`
- `depreciation_rate`
- `land_value`
- `building_value_net`
- `improvements_value_net`

#### Cash Position Analysis (3 columns)
- `operating_cash`
- `restricted_cash`
- `total_cash_position`

#### Receivables Analysis (5 columns)
- `tenant_receivables`
- `intercompany_receivables`
- `other_receivables`
- `total_receivables`
- `ar_percentage_of_assets`

#### Debt Analysis (6 columns)
- `short_term_debt`
- `institutional_debt`
- `mezzanine_debt`
- `shareholder_loans`
- `long_term_debt`
- `total_debt`

#### Equity Analysis (7 columns)
- `partners_contribution`
- `beginning_equity`
- `partners_draw`
- `distributions`
- `current_period_earnings`
- `ending_equity`
- `equity_change`

---

### 2. API Response Model Updated

**File**: `backend/app/api/v1/metrics.py`

**Status**: ✅ All 81 fields mapped correctly

**Changes**:
- Added all 43 new fields to `FinancialMetricsResponse` Pydantic model (lines 36-147)
- Updated response construction to map all fields (lines 280-377)
- Each field properly converts from Decimal to float with None handling

**Excluded Fields** (intentional):
- `created_at` - internal metadata
- `updated_at` - internal metadata

---

### 3. DSCR Calculation Formula

**Formula**: `DSCR = Net Operating Income (NOI) / Annual Debt Service`

**Implementation**: `backend/app/services/metrics_service.py:848-852`

```python
dscr = None
noi = existing_metrics.get('net_operating_income')
if noi and total_annual_debt_service > 0:
    dscr = Decimal(str(noi)) / total_annual_debt_service
```

**Verification Results** (ESP001, 2023):
- ✅ 2023-12: DSCR=0.2291 (NOI=$455,142.13 / $1,987,036.08) - diff: 0.000044
- ✅ 2023-11: DSCR=0.2479 (NOI=$492,562.32 / $1,987,036.08) - diff: 0.000012
- ✅ 2023-10: DSCR=0.1891 (NOI=$401,297.48 / $2,122,036.08) - diff: 0.000010

**Status**: ✅ All calculations verified accurate to 4 decimal places

---

### 4. Year Filtering Implementation

**Files Modified**:
- `src/pages/CommandCenter.tsx`
- `src/pages/PortfolioHub.tsx`

**Changes**:

#### CommandCenter.tsx
- Line 115: Default year changed from 2025 to 2023
- Lines 428-430: Added year filtering in `loadPropertyPerformance`
- Lines 162-164: Added year filtering in `loadPortfolioHealth`
- Line 507: DSCR API uses `selectedYear` instead of hardcoded 2025
- Lines 531-534: DSCR fallback logic moved outside catch block
- Line 886: Added `selectedYear` to useEffect dependencies

#### PortfolioHub.tsx
- Line 169: Default year set to 2023
- Line 364: DSCR API uses `selectedYear` instead of `new Date().getFullYear()`
- Lines 378-381: DSCR fallback logic moved outside catch block
- Line 1115: Added `propertyMetric?.dscr` as final fallback

**Status**: ✅ All pages properly filter by selected year

---

## Verification Checklist

Run these checks to ensure integrity:

### ✅ Database Schema Verification

```bash
# Check column count
PGPASSWORD=reims docker compose exec -T postgres psql -U reims -d reims -c \
  "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'financial_metrics';"
# Expected: 82 columns

# Verify critical columns exist
PGPASSWORD=reims docker compose exec -T postgres psql -U reims -d reims -c \
  "SELECT column_name FROM information_schema.columns
   WHERE table_name = 'financial_metrics'
   AND column_name IN ('total_current_assets', 'quick_ratio', 'debt_to_assets_ratio', 'dscr');"
# Expected: All 4 columns returned
```

### ✅ Migration Status

```bash
docker compose exec -T backend alembic current
# Expected: 20260106_1722 (head) (mergepoint)
```

### ✅ DSCR Calculation Accuracy

```bash
# Get DSCR values and verify formula
PGPASSWORD=reims docker compose exec -T postgres psql -U reims -d reims -c \
  "SELECT fp.period_year, fp.period_month,
   fm.net_operating_income, fm.total_annual_debt_service, fm.dscr,
   (fm.net_operating_income / fm.total_annual_debt_service) as calculated_dscr
   FROM financial_metrics fm
   JOIN financial_periods fp ON fm.period_id = fp.id
   WHERE fm.dscr IS NOT NULL
   ORDER BY fp.period_year DESC, fp.period_month DESC LIMIT 3;"
# Expected: dscr ≈ calculated_dscr (within 0.001 tolerance)
```

### ✅ API Endpoint Test

```bash
# Test metrics API
curl -s "http://localhost:8000/api/v1/metrics/ESP001/2023/11" \
  --cookie "reims_session=..." | jq '.total_current_assets, .quick_ratio, .dscr'
# Expected: All fields return values (not null if data exists)

# Test DSCR latest complete endpoint
curl -s "http://localhost:8000/api/v1/dscr/latest-complete/1?year=2023" \
  --cookie "reims_session=..." | jq '.dscr'
# Expected: 0.2479 (ESP001, November 2023)
```

### ✅ Frontend Display

1. Navigate to Command Center: http://localhost:5173/
2. Select property "ESP001"
3. Select year "2023"
4. Verify:
   - Portfolio Performance table shows DSCR = 0.25 (not "N/A")
   - All KPI cards show 2023 data only
   - Document matrix shows 2023 periods

5. Navigate to Portfolio Hub: http://localhost:5173/#portfolio-hub
6. Select property "ESP001"
7. Select year "2023"
8. Verify:
   - Financial Health section shows DSCR = 0.25 (not "0.00")
   - All metrics correspond to selected year

---

## Protection Rules

### ⛔ DO NOT:

1. **Remove or rename columns** from `financial_metrics` table without migration
2. **Modify DSCR formula** without updating tests and documentation
3. **Hardcode years** in API calls or data filtering logic
4. **Skip year filtering** when loading property-specific data
5. **Remove fallback logic** for DSCR display (must stay outside catch blocks)
6. **Change default year** without ensuring data exists for that year

### ✅ DO:

1. **Run verification checklist** after any changes to:
   - Database schema
   - Financial metrics models
   - API endpoints
   - Frontend year filtering

2. **Add tests** for new financial calculations

3. **Update this document** when adding new metrics or formulas

4. **Keep migration reversible** with proper `downgrade()` function

5. **Maintain null safety** in all field mappings

---

## Common Issues and Fixes

### Issue: "Column does not exist" error

**Symptom**: `psycopg2.errors.UndefinedColumn: column financial_metrics.xxx does not exist`

**Fix**:
```bash
# Check if migration is applied
docker compose exec -T backend alembic current

# If not at 20260106_1722, apply migration
docker compose exec -T backend alembic upgrade head

# Verify column exists
PGPASSWORD=reims docker compose exec -T postgres psql -U reims -d reims -c \
  "SELECT column_name FROM information_schema.columns
   WHERE table_name = 'financial_metrics' AND column_name = 'xxx';"
```

### Issue: DSCR showing "N/A" or "0.00"

**Symptom**: DSCR displays incorrect value despite having valid data

**Root Causes**:
1. API called with wrong year (e.g., 2025 instead of 2023)
2. Fallback logic inside catch block (never executes if API succeeds)
3. Missing year filter when loading metrics

**Fix**:
- Ensure API uses `selectedYear` variable, not hardcoded year
- Move fallback logic outside catch block
- Verify `useEffect` dependencies include `selectedYear`

### Issue: Year filter not working

**Symptom**: Changing year doesn't update displayed data

**Fix**:
- Check `useEffect` dependencies include `selectedYear`
- Verify data loading functions filter by `period_year === selectedYear`
- Ensure API calls include `?year=${selectedYear}` parameter

---

## Test Files

### Unit Tests

**File**: `backend/tests/test_financial_metrics_integrity.py`

**Coverage**:
- Database schema verification (82 columns)
- No duplicate columns
- Model matches database
- API response model completeness
- DSCR calculation formula accuracy
- Liquidity ratios validity
- Debt analysis integrity
- Equity analysis integrity

**Run Tests**:
```bash
# Full test suite
docker compose exec -T backend python -m pytest tests/test_financial_metrics_integrity.py -v

# Quick integrity check
docker compose exec -T backend python -c "from tests.test_financial_metrics_integrity import *"
```

### Verification Scripts

**File**: `backend/scripts/verify_dscr_calculations.py`

**Purpose**: Verify DSCR formulas are mathematically correct

**Run**:
```bash
docker compose exec -T backend python backend/scripts/verify_dscr_calculations.py
```

---

## Rollback Procedures

### Rollback Migration

If issues occur after migration:

```bash
# Rollback to previous version
docker compose exec -T backend alembic downgrade 45d5e95beac4

# Verify rollback
docker compose exec -T backend alembic current
```

### Restore Frontend Files

If frontend changes cause issues:

```bash
# Restore CommandCenter.tsx from git
git checkout HEAD -- src/pages/CommandCenter.tsx

# Restore PortfolioHub.tsx from git
git checkout HEAD -- src/pages/PortfolioHub.tsx
```

---

## Monitoring

### Health Checks

Add to monitoring system:

```python
# Check 1: Database schema integrity
SELECT COUNT(*) FROM information_schema.columns
WHERE table_name = 'financial_metrics';
-- Alert if < 82

# Check 2: DSCR calculation accuracy
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN ABS((net_operating_income / total_annual_debt_service) - dscr) > 0.001 THEN 1 END) as inaccurate
FROM financial_metrics
WHERE dscr IS NOT NULL
  AND net_operating_income IS NOT NULL
  AND total_annual_debt_service > 0;
-- Alert if inaccurate > 0

# Check 3: API response completeness
curl -s "http://localhost:8000/api/v1/metrics/ESP001/2023/11" | \
  jq 'select(.dscr == null or .total_current_assets == null)'
-- Alert if returns data (means fields are missing)
```

---

## Change Log

### 2026-01-06 - Initial Protection Implementation

**Changes**:
- ✅ Added 43 columns to financial_metrics table
- ✅ Updated FinancialMetricsResponse model
- ✅ Fixed DSCR display in CommandCenter and PortfolioHub
- ✅ Implemented comprehensive year filtering
- ✅ Changed default year from 2025 to 2023
- ✅ Created integrity tests and verification scripts

**Verified By**: Claude Sonnet 4.5
**Approved By**: User (hsthind)
**Status**: Production Ready ✅

---

## Contact

If you encounter issues with financial metrics:

1. Check this document's verification checklist
2. Run integrity tests
3. Check recent commits to affected files
4. Refer to original implementation in conversation history

---

**🔒 This document is critical infrastructure. Update with every change to financial metrics.**
