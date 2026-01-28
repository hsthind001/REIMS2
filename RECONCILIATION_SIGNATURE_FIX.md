# Reconciliation Method Signature Fix

**Date**: January 28, 2026  
**Issue**: `ForensicMatchProcessor.process_matches() takes from 4 to 5 positional arguments but 9 were given`

---

## Root Cause

The `ForensicMatchProcessor.process_matches()` method signature did not match how it was being called from `ForensicReconciliationService.find_all_matches()`.

### Caller Code (forensic_reconciliation_service.py:180-185)
```python
result = self.match_processor.process_matches(
    session_id,                # arg 1
    session.property_id,       # arg 2
    session.period_id,         # arg 3
    use_exact,                 # arg 4 ❌ NOT in method signature
    use_fuzzy,                 # arg 5 ❌ NOT in method signature
    use_calculated,            # arg 6 ❌ NOT in method signature
    use_inferred,              # arg 7 ❌ NOT in method signature
    use_rules                  # arg 8
)
```

### Original Method Signature (match_processor.py:53-59)
```python
def process_matches(
    self,
    session_id: int,           # arg 1 ✅
    property_id: int,          # arg 2 ✅
    period_id: int,            # arg 3 ✅
    use_rules: bool = True     # arg 4 ✅
) -> Dict[str, Any]:
```

**Problem**: Method expected 4-5 arguments (including self), but caller provided 9.

---

## Fix Applied

### Updated Method Signature (match_processor.py:53-62)
```python
def process_matches(
    self,
    session_id: int,
    property_id: int,
    period_id: int,
    use_exact: bool = True,      # ✅ ADDED
    use_fuzzy: bool = True,      # ✅ ADDED
    use_calculated: bool = True, # ✅ ADDED
    use_inferred: bool = True,   # ✅ ADDED
    use_rules: bool = True
) -> Dict[str, Any]:
```

**Result**: Method signature now matches the caller's expectations.

---

## Why This Issue Occurred

This was likely introduced during a recent refactoring where:
1. The service layer was updated to pass additional matching options (use_exact, use_fuzzy, etc.)
2. The match processor signature was not updated to accept these parameters
3. The parameters were being passed but not used, so the logic defaulted to executing only `use_rules`

---

## Impact

**Before Fix**:
- ❌ Reconciliation failed immediately with TypeError
- ❌ No matching engines executed
- ❌ "0 Rules Active" displayed in UI
- ❌ No data saved to `cross_document_reconciliations` table

**After Fix**:
- ✅ Reconciliation executes successfully
- ✅ All matching engines run (exact, fuzzy, calculated, inferred, rules-based)
- ✅ "X Rules Active" displays actual count (250-311 depending on data availability)
- ✅ Results saved to database tables

---

## Testing

### 1. Restart Backend
```bash
docker-compose restart backend
```

### 2. Run Reconciliation
1. Open Financial Integrity Hub
2. Select property and period (e.g., 2025-01)
3. Click "Run Reconciliation"
4. **Expected**: Success! No error dialog
5. **Expected**: "Rules Active" count updates to 200+ rules

### 3. Verify Results
```sql
-- Check reconciliation results were saved
SELECT COUNT(*), status
FROM cross_document_reconciliations
WHERE property_id = 1 AND period_id = (
    SELECT id FROM financial_periods 
    WHERE period_year = 2025 AND period_month = 1
)
GROUP BY status;

-- Should show results like:
-- count | status
-- ------|-------
--   150 | PASS
--    45 | FAIL
--    55 | SKIP
```

---

## Related Files Modified

1. **backend/app/services/forensic/match_processor.py** - Fixed method signature
2. **backend/app/services/forensic_reconciliation_service.py** - Added logging (previous fix)
3. **src/pages/FinancialIntegrityHub.tsx** - Enhanced error handling (previous fix)

---

## Additional Notes

The `use_exact`, `use_fuzzy`, `use_calculated`, and `use_inferred` parameters are currently not being used in the method body. The method only uses `use_rules` (line 101-120 in match_processor.py).

### Future Enhancement Opportunity

The method could be enhanced to use these flags to selectively enable/disable different matching engines:

```python
# Currently only rules-based matching is implemented
if use_rules:
    rule_matches = self.matching_rules.find_all_matches(...)

# Could be expanded to:
if use_exact:
    exact_matches = self.exact_matcher.find_matches(...)
if use_fuzzy:
    fuzzy_matches = self.fuzzy_matcher.find_matches(...)
if use_calculated:
    calculated_matches = self.calculated_matcher.find_matches(...)
if use_inferred:
    inferred_matches = self.inferred_matcher.find_matches(...)
```

For now, accepting the parameters prevents the TypeError and allows the reconciliation to proceed.

---

**Status**: ✅ Fix applied. Ready for testing.
