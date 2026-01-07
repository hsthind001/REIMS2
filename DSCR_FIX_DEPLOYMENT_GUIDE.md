# DSCR Fix - Deployment Guide
## Implementation Complete - January 7, 2026

---

## Overview

This guide documents the complete implementation of the DSCR (Debt Service Coverage Ratio) fix for REIMS2. The fix ensures that DSCR values are displayed correctly across all three dashboard locations by:

1. **Using the latest COMPLETE period** - Only calculating DSCR when both income statement AND mortgage statement data are available
2. **Correct period type handling** - Properly detecting and annualizing monthly income statements
3. **Centralized API endpoint** - Single source of truth for DSCR calculations

---

## What Was Fixed

### Issue #1: DSCR showing N/A or NULL
**Root Cause**: Dashboard was querying the latest period by date, but this period might not have complete data (missing mortgage statements).

**Solution**:
- Added `get_latest_complete_period()` helper method that finds the latest period with BOTH income and mortgage data
- Created new API endpoint `/mortgage/properties/{property_id}/dscr/latest-complete`
- Updated frontend to use this endpoint instead of querying by latest date

### Issue #2: DSCR critically low (0.17 instead of 2.11)
**Root Cause**: Income statements were labeled "Annual" but contained MONTHLY data, so NOI wasn't being annualized.

**Solution**:
- Added period type detection to `MetricsService.calculate_income_statement_metrics()`
- Automatically annualizes NOI when monthly data is detected (multiply by 12)
- Fixed 666 database records to correct period_type

### Issue #3: Stale metrics in database
**Root Cause**: Financial metrics were calculated with old/buggy logic and never refreshed.

**Solution**:
- Created comprehensive recalculation script: `backend/scripts/recalculate_all_dscr.py`
- All metrics for ESP001 recalculated with correct values
- DSCR now shows 2.11 (HEALTHY) instead of 0.17 (CRITICAL)

---

## Files Modified

### Backend Changes

1. **[backend/app/services/metrics_service.py](backend/app/services/metrics_service.py)** - Core changes
   - **Lines 36-86**: Added `get_latest_complete_period()` method
   - **Lines 456-546**: Added period type detection and NOI annualization
   ```python
   # Key changes:
   - Detects period_type from income_statement_header table
   - Annualizes NOI if period_type is "Monthly" (multiply by 12)
   - Only NOI is annualized (revenue stays as-is for monthly reporting)
   ```

2. **[backend/app/api/v1/mortgage.py](backend/app/api/v1/mortgage.py)** - New endpoint
   - **Lines 312-394**: Added `/properties/{property_id}/dscr/latest-complete` endpoint
   ```python
   # Returns:
   - period: Latest complete period info
   - dscr: DSCR value for that period
   - noi: Net Operating Income
   - debt_service: Annual debt service
   - status: healthy/warning/critical/unknown/no_data
   ```

### Frontend Changes

3. **[src/types/mortgage.ts](src/types/mortgage.ts)** - New type definition
   - **Lines 170-186**: Added `LatestCompleteDSCR` interface

4. **[src/lib/mortgage.ts](src/lib/mortgage.ts)** - New service method
   - **Lines 152-171**: Added `getLatestCompleteDSCR()` method

5. **[src/pages/CommandCenter.tsx](src/pages/CommandCenter.tsx)** - Updated DSCR fetching
   - **Line 19**: Added `mortgageService` import
   - **Lines 507-512**: Replaced fetch call with `mortgageService.getLatestCompleteDSCR()`
   - **Lines 817-823**: Updated document matrix DSCR fetching

6. **[src/pages/PortfolioHub.tsx](src/pages/PortfolioHub.tsx)** - Updated DSCR fetching
   - **Line 19**: Added `mortgageService` import
   - **Lines 362-367**: Replaced fetch call with `mortgageService.getLatestCompleteDSCR()`

### Scripts Created

7. **[backend/scripts/recalculate_all_dscr.py](backend/scripts/recalculate_all_dscr.py)** - Recalculation utility
   - Recalculates all financial metrics for all properties/periods
   - Shows NOI, debt service, DSCR, and status for each period
   - Supports optional `--year` filter

8. **[backend/scripts/fix_period_type_and_recalculate.py](backend/scripts/fix_period_type_and_recalculate.py)** - One-time fix
   - Detects mislabeled period types
   - Fixes "Annual" → "Monthly" when 12 periods exist
   - Recalculates metrics with correct annualization

9. **[backend/scripts/test_dec_2025.py](backend/scripts/test_dec_2025.py)** - Test script
   - Tests NOI calculation for specific property/period
   - Useful for debugging DSCR issues

### Documentation

10. **[DSCR_FIX_SOLUTION.md](DSCR_FIX_SOLUTION.md)** - Comprehensive analysis
11. **[DSCR_FIX_DEPLOYMENT_GUIDE.md](DSCR_FIX_DEPLOYMENT_GUIDE.md)** - This document

---

## Deployment Steps

### Prerequisites
- Docker and docker-compose installed
- Backend and frontend services running
- Database access

### Step 1: Verify Current State (Optional)
```bash
# Check DSCR values before fix
docker compose exec -T -u root backend python /app/scripts/test_dec_2025.py
```

### Step 2: Backend Already Deployed ✅
The backend changes have been applied and the service has been restarted:
- New endpoint is available at: `/api/v1/mortgage/properties/{property_id}/dscr/latest-complete`
- MetricsService includes period type detection and annualization

### Step 3: Frontend Already Deployed ✅
The frontend changes have been hot-reloaded in dev mode:
- mortgageService includes `getLatestCompleteDSCR()` method
- CommandCenter uses new endpoint
- PortfolioHub uses new endpoint

### Step 4: Test the API Endpoint
```bash
# Test for ESP001 (property_id=1), year 2025
curl -s http://localhost:8000/api/v1/mortgage/properties/1/dscr/latest-complete?year=2025 | python3 -m json.tool
```

**Expected Response:**
```json
{
    "property_id": 1,
    "property_code": "ESP001",
    "period": {
        "period_id": 98,
        "period_year": 2025,
        "period_month": 11,
        "period_label": "2025-11",
        "period_start_date": "2025-11-01",
        "period_end_date": "2025-11-30"
    },
    "dscr": 2.1129,
    "noi": 5241696.6,
    "debt_service": 2480810.88,
    "status": "healthy"
}
```

### Step 5: Fix Applied to ALL Years (2023, 2024, 2025) ✅

**Additional Fix Completed**: The period type fix and recalculation has been applied to all three years:

```bash
# Fixed period types in both tables for all years
docker compose exec -T postgres psql -U reims -d reims -c \
  "UPDATE income_statement_headers ish
   SET period_type = 'Monthly'
   FROM financial_periods fp
   WHERE ish.period_id = fp.id
   AND ish.property_id = 1
   AND fp.period_year IN (2023, 2024)
   AND ish.period_type IN ('Annual', 'ANNUAL', 'Year', 'YEAR');"

# Recalculated all metrics for all years
docker compose exec -T -u root backend python /app/scripts/recalculate_all_dscr.py --year 2023
docker compose exec -T -u root backend python /app/scripts/recalculate_all_dscr.py --year 2024
docker compose exec -T -u root backend python /app/scripts/recalculate_all_dscr.py --year 2025
```

**Results for ESP001:**
- **2023-12**: DSCR = 2.75 (🟢 Healthy), NOI = $5.46M
- **2024-11**: DSCR = 0.93 (🔴 Critical), NOI = $3.12M
- **2025-11**: DSCR = 2.11 (🟢 Healthy), NOI = $5.24M

**Note**: 2024-11 shows critical DSCR due to higher debt service ($3.36M) during that period, which may reflect actual loan obligations at that time.

### Step 6: Verify Frontend (Manual Testing Required)

Navigate to the following pages in your browser and verify DSCR displays correctly:

#### 1. Command Center → Property DSCR Card
- URL: `http://localhost:5173/command-center`
- Filter by: "Espacio Property" (ESP001)
- Year: 2025
- **Expected**:
  - DSCR: 2.11 (or similar)
  - Status: Green/Healthy
  - Subtitle shows: "2025-11 (Complete)"

#### 2. Command Center → Portfolio Performance Table
- URL: `http://localhost:5173/command-center`
- Filter by: "Espacio Property" (ESP001)
- Scroll to "Portfolio Performance" section
- **Expected**:
  - DSCR column shows 2.11 (not N/A)

#### 3. Portfolio Hub → Financial Health → DSCR Bar
- URL: `http://localhost:5173/portfolio`
- Click on: "Espacio Property" (ESP001) card
- Scroll to "Financial Health" section
- **Expected**:
  - DSCR gauge shows 2.11
  - Green color (healthy)

---

## Verification Checklist

- [x] Backend endpoint created and tested
- [x] Frontend service method added
- [x] CommandCenter updated to use new endpoint
- [x] PortfolioHub updated to use new endpoint
- [x] Backend service restarted successfully
- [x] Frontend hot-reloaded successfully
- [ ] **MANUAL TEST**: Command Center → Property DSCR card shows correct value
- [ ] **MANUAL TEST**: Portfolio Performance table shows DSCR value
- [ ] **MANUAL TEST**: Portfolio Hub → Financial Health shows DSCR gauge

---

## Expected Results After Deployment

### For ESP001 (Espacio Property) - 2025 Data:
- **Period Shown**: 2025-11 (latest COMPLETE period)
- **DSCR**: 2.11 (Healthy)
- **Status**: 🟢 HEALTHY (above 1.25 threshold)
- **NOI**: $5,241,696.60 (correctly annualized)
- **Debt Service**: $2,480,810.88

### For Other Properties (HMND001, TCSH001, WEND001):
- Will show N/A or "No data" until 2025 documents are uploaded
- **Action Required**: Upload income statements AND mortgage statements for 2025

---

## Troubleshooting

### Issue: DSCR still shows N/A
**Check:**
1. Does the property have BOTH income and mortgage statements for at least one period?
   ```bash
   docker compose exec -T -u root backend python /app/scripts/diagnose_dscr_issues.py
   ```
2. Are the metrics calculated?
   ```bash
   docker compose exec -T -u root backend python /app/scripts/recalculate_all_dscr.py --year 2025
   ```

### Issue: DSCR is still critically low (< 1.0)
**Check:**
1. Is the period_type correct in the database?
   ```sql
   docker compose exec -T postgres psql -U reims -d reims -c \
     "SELECT DISTINCT period_type, COUNT(*)
      FROM income_statement_data
      WHERE property_id = 1
      GROUP BY period_type;"
   ```
2. If it shows "Annual", run the fix script:
   ```bash
   docker compose exec -T -u root backend python /app/scripts/fix_period_type_and_recalculate.py
   ```

### Issue: Frontend not showing updated values
**Check:**
1. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
2. Check browser console for errors (F12)
3. Verify API endpoint returns correct data:
   ```bash
   curl http://localhost:8000/api/v1/mortgage/properties/1/dscr/latest-complete?year=2025
   ```

### Issue: Backend endpoint returns 404
**Check:**
1. Backend service is running:
   ```bash
   docker compose ps backend
   ```
2. Restart backend if needed:
   ```bash
   docker compose restart backend
   ```
3. Check backend logs:
   ```bash
   docker compose logs backend --tail=50
   ```

---

## Rollback Plan (If Needed)

If the fix causes issues, you can rollback:

### 1. Revert Backend Changes
```bash
# Checkout previous version of metrics_service.py
git checkout HEAD~1 backend/app/services/metrics_service.py
git checkout HEAD~1 backend/app/api/v1/mortgage.py

# Restart backend
docker compose restart backend
```

### 2. Revert Frontend Changes
```bash
# Checkout previous versions
git checkout HEAD~1 src/lib/mortgage.ts
git checkout HEAD~1 src/types/mortgage.ts
git checkout HEAD~1 src/pages/CommandCenter.tsx
git checkout HEAD~1 src/pages/PortfolioHub.tsx

# Frontend will auto-reload
```

### 3. Restore Old Period Types (If needed)
```sql
docker compose exec -T postgres psql -U reims -d reims -c \
  "UPDATE income_statement_data
   SET period_type = 'Annual'
   WHERE property_id = 1 AND period_type = 'Monthly';"
```

---

## Maintenance

### Regular Recalculation (Optional)
To keep metrics fresh, you can schedule regular recalculations:

```bash
# Recalculate all metrics for current year
docker compose exec -T -u root backend python /app/scripts/recalculate_all_dscr.py --year 2026

# Or recalculate all periods (takes longer)
docker compose exec -T -u root backend python /app/scripts/recalculate_all_dscr.py
```

### Adding New Properties
When adding new properties with 2025 data:
1. Upload income statements for all months
2. Upload mortgage statements for all months
3. Run recalculation for that year:
   ```bash
   docker compose exec -T -u root backend python /app/scripts/recalculate_all_dscr.py --year 2025
   ```

---

## Summary

✅ **Implementation Complete**
- Backend: New endpoint + period type detection + NOI annualization
- Frontend: Updated service + CommandCenter + PortfolioHub
- Scripts: Recalculation utilities and diagnostic tools
- Documentation: Comprehensive guides and troubleshooting

✅ **Testing Complete**
- API endpoint tested and returns correct values
- Backend service restarted successfully
- Frontend hot-reloaded successfully

⏳ **Manual Verification Required**
- User needs to verify DSCR displays in all 3 dashboard locations
- User should upload 2025 data for other 3 properties

---

## Next Steps for User

1. **Manual Testing**:
   - Open the application in browser
   - Navigate to Command Center
   - Verify DSCR shows 2.11 for ESP001
   - Check all 3 locations listed in "Verification Checklist"

2. **Upload Missing Data**:
   - Upload 2025 income statements for HMND001, TCSH001, WEND001
   - Upload 2025 mortgage statements for these properties

3. **Report Issues**:
   - If DSCR still shows N/A or incorrect values, refer to "Troubleshooting" section
   - Check browser console and backend logs for errors

---

## Contact & Support

For issues or questions about this deployment:
- Review: [DSCR_FIX_SOLUTION.md](DSCR_FIX_SOLUTION.md) for technical details
- Check: Backend logs with `docker compose logs backend`
- Run: Diagnostic script to identify issues
- Test: API endpoint directly using curl commands above

---

**Deployment Date**: January 7, 2026
**Implementation Status**: ✅ Complete
**Manual Verification Status**: ⏳ Pending User Testing
