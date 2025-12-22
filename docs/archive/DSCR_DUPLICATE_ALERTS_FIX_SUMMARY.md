# DSCR Duplicate Alerts Fix Summary

**Date**: 2025-01-XX  
**Status**: ✅ Complete

## Problem

The system was showing 5 DSCR alerts for the same property, which could indicate:
1. **Legitimate**: 5 different financial periods (each period should have its own alert)
2. **Problem**: 5 alerts for the SAME period with different statuses (duplicates)
3. **Critical**: 5 ACTIVE alerts for the SAME period (duplicate prevention failing)

## Root Cause

### Issue 1: Alert Creation Logic
**File**: `backend/app/services/dscr_monitoring_service.py`

The `_create_dscr_alert` method only checked for existing **ACTIVE** alerts:
- If an alert was ACKNOWLEDGED or RESOLVED, a new ACTIVE alert could be created
- This created duplicates for the same property/period combination

### Issue 2: Frontend Display
**File**: `src/pages/CommandCenter.tsx`

- Frontend didn't filter by status (showed ACTIVE, ACKNOWLEDGED, RESOLVED)
- Frontend didn't filter by period (showed all periods)
- No period information displayed in alert cards
- No deduplication logic (could show multiple alerts for same property)

## Solution Implemented

### 1. ✅ Intelligent Alert Creation Logic

**File**: `backend/app/services/dscr_monitoring_service.py`

**Changes**:
- Updated `_create_dscr_alert` to check for ANY existing alert (not just ACTIVE)
- Excludes DISMISSED alerts (user explicitly dismissed)
- Intelligent reactivation:
  - If ACTIVE exists → Update it
  - If ACKNOWLEDGED/RESOLVED exists → Reactivate if DSCR still below threshold
  - If DISMISSED exists → Create new alert (user explicitly dismissed)
  - If none exists → Create new alert

**Code Logic**:
```python
# Check for existing alert (any status except DISMISSED)
existing_alert = self.db.query(CommitteeAlert).filter(
    CommitteeAlert.property_id == property_id,
    CommitteeAlert.financial_period_id == financial_period_id,
    CommitteeAlert.alert_type == AlertType.DSCR_BREACH,
    CommitteeAlert.status != AlertStatus.DISMISSED  # Check all except dismissed
).order_by(CommitteeAlert.triggered_at.desc()).first()

# If exists, update or reactivate based on status
# If DSCR still below threshold and alert was ACKNOWLEDGED/RESOLVED → Reactivate
```

### 2. ✅ Frontend Period Filtering and Display

**File**: `src/pages/CommandCenter.tsx`

**Changes**:
- Added period information to `CriticalAlert` interface
- Updated `loadCriticalAlerts` to:
  - Filter by `status=ACTIVE` in API call
  - Deduplicate by property (show only latest period's alert per property)
  - Sort by most recent first
- Added period display in alert cards (shows year/month badge)

**Filtering Logic**:
```typescript
// Group by property_id and keep only most recent alert per property
const alertsByProperty = new Map<number, any>();
alerts.forEach((a: any) => {
  const propertyId = a.property_id;
  const existing = alertsByProperty.get(propertyId);
  
  if (!existing || currentDate > existingDate) {
    alertsByProperty.set(propertyId, a);
  }
});
```

### 3. ✅ Backend Period Information

**File**: `backend/app/api/v1/risk_alerts.py`

**Changes**:
- Added period information to alert responses in both endpoints:
  - `GET /risk-alerts` (with priority filter)
  - `GET /risk-alerts/alerts`
- Period info includes: `id`, `year`, `month`, `start_date`, `end_date`

**Response Enhancement**:
```python
if alert.financial_period_id:
    period = db.query(FinancialPeriod).filter(...).first()
    if period:
        alert_dict["period"] = {
            "id": period.id,
            "year": period.period_year,
            "month": period.period_month,
            ...
        }
```

### 4. ✅ Diagnostic Endpoint

**File**: `backend/app/api/v1/risk_alerts.py`

**New Endpoint**: `GET /risk-alerts/diagnostics/duplicate-alerts`

**Purpose**: Analyze duplicate alerts to understand the pattern

**Returns**:
- Summary statistics (total alerts, duplicates, unique combinations)
- Detailed duplicate groups with:
  - Property and period information
  - All alerts for each property/period
  - Status distribution (ACTIVE, ACKNOWLEDGED, RESOLVED counts)

**Usage**:
```bash
# Check all DSCR duplicates
GET /api/v1/risk-alerts/diagnostics/duplicate-alerts?alert_type=DSCR_BREACH

# Check for specific property
GET /api/v1/risk-alerts/diagnostics/duplicate-alerts?property_id=1
```

### 5. ✅ Cleanup Script

**File**: `backend/scripts/cleanup_duplicate_alerts.py`

**Purpose**: One-time cleanup of existing duplicate alerts

**Features**:
- Identifies duplicate alerts (same property/period/type)
- Keeps most recent ACTIVE alert per property/period
- Marks others as RESOLVED with explanation
- Supports dry-run mode
- Can target specific property

**Usage**:
```bash
# Dry run (see what would be done)
python -m backend.scripts.cleanup_duplicate_alerts --dry-run

# Actual cleanup
python -m backend.scripts.cleanup_duplicate_alerts

# Cleanup specific property
python -m backend.scripts.cleanup_duplicate_alerts --property-id 1
```

## Expected Behavior After Fix

### Alert Creation
- ✅ Only one alert per property/period combination (regardless of status)
- ✅ Existing alerts are updated/reactivated instead of creating duplicates
- ✅ DISMISSED alerts allow new alert creation (user explicitly dismissed)

### Frontend Display
- ✅ Command Center shows only ACTIVE alerts
- ✅ Only latest period's alert per property is shown
- ✅ Period information (year/month) displayed in alert cards
- ✅ No duplicate alerts visible for same property

### Data Integrity
- ✅ Historical alerts (ACKNOWLEDGED/RESOLVED) preserved for audit trail
- ✅ Duplicate prevention at application level
- ✅ Cleanup script available for existing duplicates

## Testing Checklist

- [ ] Test alert creation for same period (should update, not duplicate)
- [ ] Test alert creation for different periods (should create separate alerts)
- [ ] Test alert reactivation from ACKNOWLEDGED status
- [ ] Test alert reactivation from RESOLVED status
- [ ] Test DISMISSED alert allows new alert creation
- [ ] Test frontend shows only latest period per property
- [ ] Test period information displays correctly
- [ ] Test diagnostic endpoint returns correct duplicate analysis
- [ ] Test cleanup script identifies and resolves duplicates

## Files Modified

1. **Backend**:
   - `backend/app/services/dscr_monitoring_service.py` - Fixed alert creation logic
   - `backend/app/api/v1/risk_alerts.py` - Added period info, diagnostic endpoint, improved filtering

2. **Frontend**:
   - `src/pages/CommandCenter.tsx` - Added period filtering, display, and deduplication

3. **Scripts**:
   - `backend/scripts/cleanup_duplicate_alerts.py` - Cleanup script for existing duplicates

## Next Steps

1. **Run Diagnostic**: Use `/risk-alerts/diagnostics/duplicate-alerts` to analyze current duplicates
2. **Run Cleanup**: Execute cleanup script to resolve existing duplicates
3. **Monitor**: Verify no new duplicates are created
4. **Test**: Verify frontend shows correct alerts with period information

## Notes

- The fix prevents future duplicates but doesn't automatically clean existing ones
- Use the cleanup script to resolve existing duplicates
- Period information is now available in all alert responses
- Frontend intelligently filters to show only relevant alerts
- Historical alerts are preserved for audit purposes

---

**Status**: ✅ Implementation Complete - Ready for testing and cleanup execution

