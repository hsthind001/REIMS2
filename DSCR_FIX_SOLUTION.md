# DSCR Fix - Comprehensive Solution

## Date: January 7, 2026
## Issue: DSCR showing N/A or 0.0 in Command Center, Portfolio Performance, and Financial Health

---

## Root Cause Analysis

### Issue #1: Dashboard Uses Incomplete Period
**Problem**: The dashboard queries for the "latest period" by date, but this period may not have complete data (missing mortgage statements).

**Evidence**:
- Period 2025-12 (latest): Has income statement but NO mortgage data → DSCR = N/A
- Period 2025-11 (complete): Has BOTH income and mortgage data → DSCR = 0.1761

**Impact**: Command Center and Portfolio Hub show N/A for DSCR even though data exists for an earlier complete period.

### Issue #2: Stale Metrics Not Recalculated
**Problem**: Financial metrics were calculated at some point with old/incomplete data and were never refreshed.

**Evidence**:
- Period 2025-11 showed NOI = $0.00 in database
- Manual recalculation produced NOI = $436,808.05 (correct!)
- DSCR = 0.1761 (correct!)

**Impact**: Even when showing the right period, metrics may be stale and incorrect.

### Issue #3: Missing Data for Other Properties
**Problem**: Only ESP001 has 2025 data. Other properties (HMND001, TCSH001, WEND001) have no uploaded documents for 2025.

**Evidence**: Diagnostic script found no income or mortgage data for 2025 for these properties.

**Impact**: These properties will always show N/A until data is uploaded.

---

## Solution Components

### 1. Latest Complete Period Detection

Add a helper method to find the latest period with COMPLETE data (both income and mortgage):

```python
def get_latest_complete_period(self, property_id: int, year: Optional[int] = None) -> Optional[FinancialPeriod]:
    """
    Get the latest period that has COMPLETE financial data
    (both income statement AND mortgage statement)

    This ensures DSCR can be calculated accurately.
    """
    from app.models.document_upload import DocumentUpload
    from sqlalchemy import and_, func

    query = self.db.query(FinancialPeriod).filter(
        FinancialPeriod.property_id == property_id
    )

    if year:
        query = query.filter(FinancialPeriod.period_year == year)

    # Get periods that have both income and mortgage data
    query = query.join(
        IncomeStatementData,
        and_(
            IncomeStatementData.property_id == FinancialPeriod.property_id,
            IncomeStatementData.period_id == FinancialPeriod.id
        )
    ).join(
        MortgageStatementData,
        and_(
            MortgageStatementData.property_id == FinancialPeriod.property_id,
            MortgageStatementData.period_id == FinancialPeriod.id
        )
    ).group_by(FinancialPeriod.id).order_by(
        FinancialPeriod.period_year.desc(),
        FinancialPeriod.period_month.desc()
    ).first()

    return query
```

### 2. Update API Endpoints to Use Latest Complete Period

**File**: `backend/app/api/v1/mortgage.py`

Update all DSCR-related endpoints to use `get_latest_complete_period()` instead of just getting the latest period by date.

Example:
```python
@router.get("/properties/{property_id}/dscr")
def get_property_dscr(property_id: int, db: Session = Depends(get_db)):
    """Get DSCR for property using latest COMPLETE period"""
    service = DSCRMonitoringService(db)

    # Get latest complete period (has both income and mortgage data)
    period = get_latest_complete_period(db, property_id)

    if not period:
        return {"dscr": None, "error": "No complete financial data available"}

    return service.calculate_dscr(property_id, period.id)
```

### 3. Recalculation Script

**File**: `backend/scripts/recalculate_all_dscr.py`

```python
"""
Recalculate all financial metrics for all properties

This script:
1. Finds all properties
2. For each property, finds all periods with data
3. Recalculates financial metrics using MetricsService
4. Updates DSCR calculations
"""

from app.db.database import SessionLocal
from app.services.metrics_service import MetricsService
from app.services.dscr_monitoring_service import DSCRMonitoringService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from sqlalchemy import func

def recalculate_all():
    db = SessionLocal()

    try:
        metrics_service = MetricsService(db)
        dscr_service = DSCRMonitoringService(db)

        # Get all properties
        properties = db.query(Property).all()

        print(f"Found {len(properties)} properties")

        for prop in properties:
            print(f"\n{'='*80}")
            print(f"Property: {prop.property_code} - {prop.property_name}")
            print(f"{'='*80}")

            # Get all periods for this property
            periods = db.query(FinancialPeriod).filter(
                FinancialPeriod.property_id == prop.id
            ).order_by(
                FinancialPeriod.period_year.desc(),
                FinancialPeriod.period_month.desc()
            ).all()

            print(f"Found {len(periods)} periods")

            for period in periods:
                period_label = f"{period.period_year}-{period.period_month:02d}"
                print(f"\n  Recalculating {period_label}...")

                try:
                    # Recalculate all metrics
                    metrics = metrics_service.calculate_all_metrics(prop.id, period.id)

                    noi = metrics.net_operating_income if metrics.net_operating_income else 0
                    debt_service = metrics.total_annual_debt_service if metrics.total_annual_debt_service else 0
                    dscr = metrics.dscr if metrics.dscr else None

                    print(f"    NOI: ${noi:,.2f}")
                    print(f"    Debt Service: ${debt_service:,.2f}")
                    print(f"    DSCR: {dscr:.4f}" if dscr else "    DSCR: NULL")

                except Exception as e:
                    print(f"    ERROR: {str(e)}")

        print(f"\n{'='*80}")
        print("Recalculation Complete!")
        print(f"{'='*80}")

    finally:
        db.close()

if __name__ == "__main__":
    recalculate_all()
```

### 4. Frontend Update

**File**: `src/pages/CommandCenter.tsx` and `src/pages/PortfolioHub.tsx`

Update the API calls to request the latest COMPLETE period, not just the latest period.

Example:
```typescript
// OLD (gets latest by date):
const response = await mortgageService.getDebtSummary(propertyId, latestPeriodId);

// NEW (gets latest complete period):
const response = await mortgageService.getLatestCompleteDSCR(propertyId, year);
```

---

## Implementation Steps

### Step 1: Run Diagnostic (Already Done ✓)
```bash
docker compose exec -T -u root backend python /app/scripts/diagnose_dscr_issues.py
```

**Results**:
- ESP001: Latest complete period is 2025-11, expected DSCR = 0.1761
- Other properties: No 2025 data

### Step 2: Recalculate All Metrics (REQUIRED)
```bash
docker compose exec -T -u root backend python /app/scripts/recalculate_all_dscr.py
```

This will:
- Update NOI from $0.00 to $436,808.05 for period 2025-11
- Calculate DSCR = 0.1761
- Update all other periods

### Step 3: Add Latest Complete Period Logic (Code Changes Needed)

**Backend Changes**:
1. Add `get_latest_complete_period()` method to MetricsService
2. Update mortgage API endpoints to use latest complete period
3. Update DSCR monitoring service to use latest complete period

**Frontend Changes**:
1. Update Command Center to request latest complete period
2. Update Portfolio Hub to request latest complete period
3. Update Financial Health dashboard

### Step 4: Verify Fix

Check these 3 locations:
1. **Command Center** → Property DSCR card
2. **Portfolio Performance** → DSCR column
3. **Portfolio Hub** → Financial Health → DSCR bar

Expected values for ESP001 (2025):
- Period: 2025-11 (not 2025-12!)
- NOI: $436,808.05
- Debt Service: $2,480,810.88
- DSCR: 0.1761 (🔴 CRITICAL - below 1.25 threshold)

---

## Expected Results After Fix

### For ESP001:
- **Period Shown**: 2025-11 (latest COMPLETE period)
- **DSCR**: 0.1761 (Critical - requires attention)
- **Status**: 🔴 CRITICAL (below 1.25 threshold)
- **NOI**: $436,808.05
- **Debt Service**: $2,480,810.88

### For Other Properties (HMND001, TCSH001, WEND001):
- Will continue showing N/A until 2025 data is uploaded
- **Action Required**: Upload income statements and mortgage statements for 2025

---

## Maintenance & Prevention

### 1. Automatic Recalculation
Set up a scheduled task to recalculate metrics when new documents are uploaded:

```python
# In document upload service, after extraction:
def after_extraction_complete(self, upload_id):
    # ... existing code ...

    # Recalculate metrics for this property/period
    metrics_service.calculate_all_metrics(property_id, period_id)

    # Recalculate DSCR
    dscr_service.calculate_dscr(property_id, period_id)
```

### 2. Data Validation
Add validation to warn users when mortgage data is missing:

```python
def validate_period_completeness(property_id, period_id):
    """Check if period has complete data for DSCR calculation"""
    has_income = check_income_statement_exists(property_id, period_id)
    has_mortgage = check_mortgage_statement_exists(property_id, period_id)

    if not has_income:
        raise Warning(f"Missing income statement for period {period_id}")
    if not has_mortgage:
        raise Warning(f"Missing mortgage statement for period {period_id} - DSCR cannot be calculated")
```

### 3. Logging
Add comprehensive logging to track DSCR calculations:

```python
logger.info(f"DSCR calculation: Property {property_id}, Period {period_id}, "
            f"NOI: ${noi:,.2f}, Debt Service: ${debt_service:,.2f}, "
            f"DSCR: {dscr:.4f}, Status: {status}")
```

---

## Files Modified

### Backend:
1. `backend/app/services/metrics_service.py` - Add `get_latest_complete_period()`
2. `backend/app/api/v1/mortgage.py` - Update endpoints
3. `backend/app/services/dscr_monitoring_service.py` - Use latest complete period
4. `backend/scripts/recalculate_all_dscr.py` - NEW recalculation script

### Frontend:
1. `src/pages/CommandCenter.tsx` - Use latest complete period API
2. `src/pages/PortfolioHub.tsx` - Use latest complete period API
3. `src/lib/mortgage.ts` - Add `getLatestCompleteDSCR()` method

### Documentation:
1. `DSCR_FIX_SOLUTION.md` - This document
2. `backend/scripts/diagnose_dscr_issues.py` - Diagnostic script (already created)

---

## Testing Checklist

- [ ] Run diagnostic script - confirms issues
- [ ] Run recalculation script - updates all metrics
- [ ] Check Command Center - DSCR displays correctly
- [ ] Check Portfolio Performance - DSCR column populated
- [ ] Check Portfolio Hub - DSCR gauge shows value
- [ ] Upload new documents - metrics auto-recalculate
- [ ] Check logging - DSCR calculations logged
- [ ] Test with incomplete data - shows appropriate warnings

---

## Summary

**The Fix**:
1. ✅ Diagnostic shows root causes
2. ⏳ Recalculate all metrics (run script)
3. ⏳ Add latest-complete-period detection (code changes)
4. ⏳ Update frontend to use complete periods (code changes)
5. ⏳ Verify all 3 dashboard locations

**The Result**:
- DSCR will display correctly in all 3 locations
- System will automatically use latest COMPLETE period
- Metrics will stay up-to-date with auto-recalculation
- Clear warnings when data is incomplete

**Next Steps for User**:
1. Run recalculation script (immediate fix)
2. Upload 2025 data for other 3 properties
3. Review DSCR = 0.1761 for ESP001 (critical status)
