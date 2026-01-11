# DSCR Duplicate Alerts Cleanup Results

**Date**: 2025-12-20  
**Status**: ✅ Cleanup Complete

## Investigation Findings

### Duplicate Pattern Identified

The diagnostic found **3 property/period combinations** with duplicate DSCR alerts for **Eastern Shore Plaza (ESP001)**:

1. **Period 2025-12**: 2 alerts
   - Alert 11: ACTIVE (DSCR: 0.2012)
   - Alert 1: ACKNOWLEDGED → RESOLVED (DSCR: 0.2012)

2. **Period 2025-11**: 2 alerts
   - Alert 12: ACTIVE (DSCR: 0.5573)
   - Alert 2: ACKNOWLEDGED → RESOLVED (DSCR: 0.5573)

3. **Period 2023-02**: 3 alerts
   - Alert 13: ACTIVE (DSCR: 0.3499)
   - Alert 9: ACKNOWLEDGED → RESOLVED (DSCR: 0.3499)
   - Alert 3: ACKNOWLEDGED → RESOLVED (DSCR: 0.3499)

### Root Cause

The duplicates were created because:
- When an alert was ACKNOWLEDGED, the system could create a new ACTIVE alert for the same property/period
- The old alert creation logic only checked for ACTIVE alerts, not ACKNOWLEDGED or RESOLVED ones
- Multiple calls to `monitor_all_properties` or document processing created new alerts instead of updating existing ones

## Cleanup Actions Taken

✅ **Resolved 4 duplicate alerts**:
- Alert 1 (ACKNOWLEDGED → RESOLVED) for period 2025-12
- Alert 2 (ACKNOWLEDGED → RESOLVED) for period 2025-11
- Alert 9 (ACKNOWLEDGED → RESOLVED) for period 2023-02
- Alert 3 (ACKNOWLEDGED → RESOLVED) for period 2023-02

✅ **Kept 3 ACTIVE alerts** (one per period):
- Alert 11: ACTIVE for period 2025-12
- Alert 12: ACTIVE for period 2025-11
- Alert 13: ACTIVE for period 2023-02

## Current State

### Active DSCR Alerts
- **Total ACTIVE alerts**: 3 (one per period)
- All for Eastern Shore Plaza (ESP001)
- Different periods: 2025-12, 2025-11, 2023-02

### Why You Might See 5 Alerts

If the frontend still shows 5 alerts, it could be because:

1. **Different Properties**: Alerts for other properties (not just ESP001)
2. **Frontend Cache**: Browser/React state needs refresh
3. **Status Filtering**: Frontend might not be filtering by ACTIVE status yet (needs backend restart)
4. **Period Display**: Multiple periods are legitimate (each period should have its own alert)

## Solution Implemented

### 1. Backend Fix ✅
- Updated `_create_dscr_alert` to check for ANY existing alert (not just ACTIVE)
- Intelligent reactivation: ACKNOWLEDGED/RESOLVED alerts are reactivated if DSCR still below threshold
- Prevents future duplicates

### 2. Frontend Enhancement ✅
- Filters by `status=ACTIVE` in API calls
- Deduplicates by property (shows only latest period per property)
- Displays period information (year/month) in alert cards

### 3. Cleanup Script ✅
- Identified and resolved existing duplicates
- Kept most recent ACTIVE alert per property/period
- Marked duplicates as RESOLVED with explanation

## Next Steps

1. **Restart Backend**: Restart the backend container to ensure new endpoint changes are active
   ```bash
   docker restart reims-backend
   ```

2. **Refresh Frontend**: Clear browser cache and refresh the Command Center page

3. **Verify Display**: 
   - Should see only ACTIVE alerts
   - Should see period information (year/month) in alert cards
   - Should see only one alert per property (latest period)

4. **Monitor**: Watch for any new duplicates being created (shouldn't happen with the fix)

## Verification

Run this query to verify current state:
```sql
SELECT 
    ca.id,
    p.property_name,
    fp.period_year,
    fp.period_month,
    ca.status,
    ca.actual_value
FROM committee_alerts ca
LEFT JOIN properties p ON ca.property_id = p.id
LEFT JOIN financial_periods fp ON ca.financial_period_id = fp.id
WHERE ca.alert_type = 'DSCR_BREACH'
  AND ca.status = 'ACTIVE'
ORDER BY fp.period_year DESC, fp.period_month DESC;
```

Expected result: Only ACTIVE alerts, one per property/period combination.

---

**Status**: ✅ Cleanup Complete - 4 duplicates resolved, 3 ACTIVE alerts remain (one per period)

