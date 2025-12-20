# DSCR Alerts Filter Fix - Properties Without Data

**Date**: 2025-01-XX  
**Issue**: Frontend showing 3 "Unknown - DSCR" alerts when only 1 property has uploaded data

## Problem

The system was creating and displaying DSCR alerts for all properties, even those without uploaded financial documents. This caused:
- Alerts showing "Unknown" property names
- Alerts for properties that haven't uploaded any financial data yet
- Confusion about which properties actually have DSCR issues

## Root Cause

1. **Alert Creation**: The `DSCRMonitoringService.monitor_all_properties()` function was calculating DSCR for all active properties and creating alerts regardless of whether financial data existed.

2. **Alert Display**: The API endpoint was returning all alerts without filtering out alerts for properties without data.

3. **Data Validation**: No check was performed to verify if a property had actual uploaded financial documents before creating alerts.

## Solution

### 1. Prevent Alert Creation for Properties Without Data

**File**: `backend/app/services/dscr_monitoring_service.py`

**Changes**:
- Added `_has_financial_data()` method to check if a property has:
  - Income statement data, OR
  - Mortgage statement data, OR
  - Completed document uploads
- Modified `calculate_dscr()` to skip alert creation if property has no financial data
- Added logging to track when alerts are skipped

**Code**:
```python
def _has_financial_data(self, property_id: int, period_id: int) -> bool:
    """Check if property has actual uploaded financial documents"""
    # Check income statement, mortgage statement, or completed uploads
    ...
    
# In calculate_dscr():
if dscr < self.WARNING_THRESHOLD:
    has_financial_data = self._has_financial_data(property_id, period.id)
    if not has_financial_data:
        logger.info(f"Skipping alert creation: No financial data uploaded")
        result["alert_skipped"] = True
        result["skip_reason"] = "No financial data uploaded"
    else:
        # Create alert only if data exists
        alert = self._create_dscr_alert(...)
```

### 2. Filter Alerts in API Response

**File**: `backend/app/api/v1/risk_alerts.py`

**Changes**:
- Added `_has_financial_data_for_period()` helper function
- Modified both `get_risk_alerts()` and `get_all_alerts()` endpoints
- Filter out DSCR alerts for properties without financial data before returning response

**Code**:
```python
def _has_financial_data_for_period(db: Session, property_id: int, period_id: int) -> bool:
    """Check if property has uploaded financial documents"""
    # Check income statement, mortgage statement, or completed uploads
    ...

# In alert enhancement loop:
if alert.alert_type == AlertType.DSCR_BREACH and alert.financial_period_id:
    has_data = _has_financial_data_for_period(db, alert.property_id, alert.financial_period_id)
    if not has_data:
        logger.debug(f"Skipping DSCR alert {alert.id}: No financial data uploaded")
        continue  # Skip this alert
```

## Impact

### Before Fix
- ❌ Alerts created for all properties (even without data)
- ❌ Frontend shows "Unknown" property names
- ❌ 3 alerts displayed when only 1 property has data

### After Fix
- ✅ Alerts only created for properties with uploaded financial data
- ✅ Frontend shows correct property names
- ✅ Only alerts for properties with actual data are displayed
- ✅ Existing alerts for properties without data are filtered out

## Testing

1. **Verify Alert Creation**:
   - Upload financial documents for Property A
   - Don't upload documents for Property B
   - Run `monitor_all_properties`
   - ✅ Only Property A should have alerts

2. **Verify Alert Display**:
   - Check `/risk-alerts?priority=critical` endpoint
   - ✅ Only alerts for properties with data should be returned
   - ✅ Property names should be correct (not "Unknown")

3. **Verify Frontend**:
   - Load Command Center page
   - ✅ Only alerts for properties with uploaded data should be visible
   - ✅ Property names should display correctly

## Files Modified

1. `backend/app/services/dscr_monitoring_service.py`
   - Added `_has_financial_data()` method
   - Modified `calculate_dscr()` to check for data before creating alerts

2. `backend/app/api/v1/risk_alerts.py`
   - Added `_has_financial_data_for_period()` helper
   - Added imports for `IncomeStatementData`, `MortgageStatementData`, `DocumentUpload`
   - Modified both alert endpoints to filter alerts

## Notes

- Existing alerts in the database for properties without data will be filtered out automatically
- No database cleanup needed - filtering happens at API level
- New alerts will only be created for properties with actual financial data
- The check verifies:
  - Income statement data exists, OR
  - Mortgage statement data exists, OR
  - Document upload with `extraction_status='completed'` exists

---

**Status**: ✅ Fixed - Alerts now only show for properties with uploaded financial data

