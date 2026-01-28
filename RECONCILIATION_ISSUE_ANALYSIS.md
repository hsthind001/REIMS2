# Reconciliation Issue Analysis & Fix

**Date**: January 28, 2026  
**Issue**: Reconciliation failing for periods 2025-01 through 2025-11 despite all documents being uploaded

---

## Problem Summary

User reports:
- Year 2025: All documents uploaded for Jan-Nov (Balance Sheet, Income Statement, Cash Flow, Rent Roll, Mortgage Statement)
- December 2025: Missing Mortgage Statement only
- **Issue**: When running reconciliation for periods 2025-01 through 2025-11, getting error: "Failed to run reconciliation: [object Object]"
- **Symptom**: UI shows "0 Rules Active" for these periods

---

## Root Cause Analysis

### 1. Frontend Error Handling Issue (FIXED)

**Problem**: Error object being converted to string as "[object Object]" instead of extracting the actual error message.

**Location**: `src/pages/FinancialIntegrityHub.tsx:214-217`

**Original Code**:
```typescript
} catch (error) {
    console.error("Reconciliation failed", error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    alert(`Failed to run reconciliation: ${errorMessage}...`);
}
```

**Issue**: `String(error)` on an object produces "[object Object]", hiding the real error message.

**Fix Applied**: Enhanced error extraction to handle various error formats:
```typescript
} catch (error) {
    console.error("Reconciliation failed", error);
    // Extract error message from various error formats
    let errorMessage = 'Unknown error';
    if (error instanceof Error) {
        errorMessage = error.message;
    } else if (typeof error === 'object' && error !== null) {
        // Handle response error objects from API
        if ('response' in error && typeof error.response === 'object' && error.response !== null) {
            const response = error.response as any;
            errorMessage = response.data?.detail || response.data?.message || response.statusText || 'API request failed';
        } else if ('message' in error) {
            errorMessage = String((error as any).message);
        } else if ('detail' in error) {
            errorMessage = String((error as any).detail);
        } else {
            errorMessage = JSON.stringify(error);
        }
    } else if (typeof error === 'string') {
        errorMessage = error;
    }
    
    alert(`Failed to run reconciliation: ${errorMessage}...`);
}
```

**Result**: Now the actual error message will be displayed to users.

---

### 2. "0 Rules Active" Display

**Problem**: UI shows "0 Rules Active" because `cross_document_reconciliations` table has no records for these periods.

**Location**: 
- Frontend: `src/pages/FinancialIntegrityHub.tsx:403`
- Backend API: `backend/app/api/v1/forensic_reconciliation.py:1356-1435`

**How it works**:
1. Frontend calls: `GET /forensic-reconciliation/calculated-rules/evaluate/{property_id}/{period_id}`
2. Backend queries: `SELECT ... FROM cross_document_reconciliations WHERE property_id = :p_id AND period_id = :period_id`
3. Returns count of results
4. UI displays: `{calculatedRulesData?.rules?.length || 0} Rules Active`

**Why "0"**: The `ReconciliationRuleEngine` hasn't been executed yet for these periods, so no records exist in `cross_document_reconciliations` table.

---

### 3. Possible Root Cause of Reconciliation Failure

Several potential issues:

#### A. Document Validation (Most Likely)
**Hypothesis**: System may be checking for ALL 5 document types (BS, IS, CF, RR, MS) and failing if any are missing.

**Where to check**:
- `backend/app/services/forensic_reconciliation_service.py:153-204`
- `backend/app/services/forensic/match_processor.py:53-124`
- `backend/app/services/reconciliation_diagnostics_service.py:44-163`

**Problem**: Mortgage Statement is OPTIONAL for most properties, but validation may be treating it as REQUIRED.

#### B. Cross-Document Matching Failure
**Hypothesis**: Matching rules expect certain document combinations and fail silently.

**Location**: `backend/app/services/forensic/match_processor.py:101-120`

#### C. Rule Engine Execution Failure
**Hypothesis**: `ReconciliationRuleEngine.execute_all_rules()` may be throwing an exception that's being caught and swallowed.

**Location**: `backend/app/services/reconciliation_rule_engine.py:92-202`

---

## Testing Steps to Identify Real Issue

### Step 1: Check Backend Logs
```bash
# View backend container logs
docker logs reims2-backend-1 --tail 200 --follow

# Look for errors during reconciliation
grep -i "error\|exception\|failed" backend_logs.txt
```

### Step 2: Test API Endpoint Directly
```bash
# Test creating session
curl -X POST http://localhost:8000/api/v1/forensic-reconciliation/sessions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"property_id": 1, "period_id": 1, "session_type": "full_reconciliation"}'

# Test running reconciliation
curl -X POST http://localhost:8000/api/v1/forensic-reconciliation/sessions/{session_id}/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"use_exact": true, "use_fuzzy": true, "use_calculated": true, "use_inferred": true, "use_rules": true}'
```

### Step 3: Check Data Availability
```sql
-- Check which documents are present for period 2025-01
SELECT 
    'Balance Sheet' as doc_type,
    COUNT(*) as record_count
FROM balance_sheet_data
WHERE period_id = (SELECT id FROM financial_periods WHERE period_year = 2025 AND period_month = 1)
UNION ALL
SELECT 
    'Income Statement',
    COUNT(*)
FROM income_statement_data
WHERE period_id = (SELECT id FROM financial_periods WHERE period_year = 2025 AND period_month = 1)
UNION ALL
SELECT 
    'Cash Flow',
    COUNT(*)
FROM cash_flow_data
WHERE period_id = (SELECT id FROM financial_periods WHERE period_year = 2025 AND period_month = 1)
UNION ALL
SELECT 
    'Rent Roll',
    COUNT(*)
FROM rent_roll_data
WHERE period_id = (SELECT id FROM financial_periods WHERE period_year = 2025 AND period_month = 1)
UNION ALL
SELECT 
    'Mortgage Statement',
    COUNT(*)
FROM mortgage_statement_data
WHERE period_id = (SELECT id FROM financial_periods WHERE period_year = 2025 AND period_month = 1);
```

### Step 4: Check for Existing Sessions
```sql
-- Check if sessions exist for these periods
SELECT 
    s.id,
    s.property_id,
    p.period_year,
    p.period_month,
    s.status,
    s.started_at,
    s.completed_at
FROM forensic_reconciliation_sessions s
JOIN financial_periods p ON s.period_id = p.id
WHERE p.period_year = 2025
ORDER BY p.period_month;
```

---

## Recommended Fixes

### Fix 1: Enhanced Error Logging (IMMEDIATE)

Add detailed logging to identify where the failure occurs:

```python
# In backend/app/services/forensic_reconciliation_service.py:153
def find_all_matches(self, session_id: int, ...) -> Dict[str, Any]:
    logger.info(f"Starting find_all_matches for session {session_id}")
    
    session = self.db.query(ForensicReconciliationSession).filter(
        ForensicReconciliationSession.id == session_id
    ).first()

    if not session:
        logger.error(f"Session {session_id} not found")
        return {'error': 'Session not found'}
    
    logger.info(f"Session found: property={session.property_id}, period={session.period_id}")
    
    try:
        # Delegate to processor
        result = self.match_processor.process_matches(
            session_id,
            session.property_id,
            session.period_id,
            use_exact, use_fuzzy, use_calculated, use_inferred, use_rules
        )
        logger.info(f"Match processing completed: {len(result.get('stored_matches', []))} matches")
    except Exception as e:
        logger.error(f"Match processing failed: {e}", exc_info=True)
        raise
```

### Fix 2: Make Mortgage Statement Optional (CRITICAL)

Ensure rules skip gracefully when mortgage data is unavailable:

```python
# In backend/app/services/rules/mortgage_rules.py
def _execute_mortgage_rules(self):
    """Execute mortgage rules only if mortgage data exists"""
    # Check if mortgage data exists
    ms_count = self.db.query(func.count(MortgageStatementData.id)).filter(
        and_(
            MortgageStatementData.property_id == self.property_id,
            MortgageStatementData.period_id == self.period_id
        )
    ).scalar()
    
    if ms_count == 0:
        logger.info(f"No mortgage data for property {self.property_id}, period {self.period_id}. Skipping mortgage rules.")
        return
    
    # Execute mortgage rules...
```

### Fix 3: Add Data Availability Check Before Reconciliation (PREVENTIVE)

Add validation in frontend to show which documents are missing:

```typescript
// In src/pages/FinancialIntegrityHub.tsx
const handleRunReconciliation = async () => {
    if (!selectedPropertyId || !selectedPeriodId) return;
    
    // Check data availability first
    const availability = await api.get(
        `/forensic-reconciliation/data-availability/${selectedPropertyId}/${selectedPeriodId}`
    );
    
    if (!availability.balance_sheet || !availability.income_statement || !availability.cash_flow) {
        alert('Cannot run reconciliation: Missing required documents (Balance Sheet, Income Statement, or Cash Flow)');
        return;
    }
    
    // Proceed with reconciliation...
};
```

---

## Next Steps

1. **Test the frontend fix** - Run reconciliation again and observe the actual error message
2. **Check backend logs** - Identify the exact failure point
3. **Verify data** - Confirm all required data is in the database for periods 2025-01 through 2025-11
4. **Apply appropriate fix** - Based on the actual error revealed by step 1

---

## Expected Behavior After Fix

- Clear error messages showing actual failure reason
- Mortgage rules skip gracefully when mortgage data unavailable
- Reconciliation succeeds for periods with 4 out of 5 documents
- "Rules Active" count reflects actual executed rules (likely 250-290 instead of 311 due to missing mortgage rules)

---

**Status**: Frontend error handling fixed. Awaiting user testing to identify actual backend error.
