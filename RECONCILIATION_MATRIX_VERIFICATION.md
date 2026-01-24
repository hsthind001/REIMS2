# Reconciliation Matrix Verification Guide

## What the Matrix Shows

The Reconciliation Matrix displays **cross-document validation status** between different financial document types. Each cell shows how many matches exist between document pairs and their status.

## Understanding the Display

### Matrix Structure

```
                BS    IS    CF    RR    MS
Balance Sheet   ●     1     -     -     1
                    VAR               VAR
Income Statement 1    ●     -     -     -
                VAR
Cash Flow       -     -     ●     -     -

Rent Roll       -     -     -     ●     -

Mortgage Stmt   1     -     -     -     ●
                VAR
```

### What Each Cell Means

**Number (e.g., "1")**
- Total count of cross-document matches found
- Example: "1" means 1 line item matched between these documents

**Status Labels**
- **MATCH** (Green) - Perfect matches, no discrepancies
- **VARIANCE** (Amber) - Matches found but with discrepancies
- **"-"** (Gray) - No rules or matches between these documents
- **"●"** (Gray dot) - Same document (diagonal, self-reference)

### What "VARIANCE" Means

A variance indicates:
1. ✅ A match WAS found between documents
2. ⚠️ BUT the values don't perfectly align
3. 📊 Reasons could be:
   - Amount differences
   - Low confidence score (<100%)
   - Pending review status
   - Rejected or modified status

**Important:** VARIANCE is not an error - it means "needs review"

## Your Current Matrix Analysis

Based on your screenshot:

### Cross-Document Matches Found

1. **Balance Sheet ↔ Income Statement: 1 VARIANCE**
   - 1 line item matched between these documents
   - Variance detected (values don't perfectly match)
   - **This is CORRECT if you expect relationships between BS and IS**

2. **Balance Sheet ↔ Mortgage Statement: 1 VARIANCE**
   - 1 line item matched
   - Variance detected
   - **This is CORRECT if mortgage data relates to BS accounts**

3. **Income Statement → Balance Sheet: 1 VARIANCE**
   - This might be the SAME match as #1 (bidirectional)
   - OR a different line item
   - **Check if this is a duplicate or legitimate separate match**

4. **Mortgage Statement → Balance Sheet: 1 VARIANCE**
   - This might be the SAME match as #2 (bidirectional)
   - OR a different line item
   - **Check if this is a duplicate or legitimate separate match**

### Empty Cells Analysis

**Cash Flow: All dashes (-)**
- ✅ CORRECT if no Cash Flow document uploaded
- ❌ INCORRECT if Cash Flow document exists but not reconciled

**Rent Roll: All dashes (-)**
- ✅ CORRECT if no Rent Roll document uploaded
- ❌ INCORRECT if Rent Roll document exists but not reconciled

## Verification Steps

### Step 1: Check Browser Console

1. Open browser Developer Tools (F12)
2. Go to "Console" tab
3. Look for logs starting with "ReconciliationMatrix Data Summary:"
4. This will show:
   ```javascript
   {
     totalMatches: 4,  // How many matches exist
     gridData: {...},  // The matrix data structure
     documentTypes: [...] // Document type names found
   }
   ```

### Step 2: Verify Document Types

Check if document type names match:

**Expected Frontend Format:**
- `balance_sheet`
- `income_statement`
- `cash_flow`
- `rent_roll`
- `mortgage_statement`

**Common Backend Variations:**
- `Balance Sheet` or `BalanceSheet` → Auto-normalized to `balance_sheet`
- `Income Statement` or `IncomeStatement` → Auto-normalized to `income_statement`
- `Mortgage Stmt` → Auto-normalized to `mortgage_statement`

If console shows warnings like:
```
Unmatched document types: someType -> otherType
```
This means the backend is using different document type names that need mapping.

### Step 3: Verify Match Data

Open the Network tab and check the API response:

**Endpoint:** `/forensic-reconciliation/sessions/{sessionId}/matches`

**Expected Response:**
```json
{
  "session_id": 123,
  "total": 4,
  "matches": [
    {
      "id": 1,
      "source_document_type": "balance_sheet",
      "target_document_type": "income_statement",
      "source_amount": 1000.00,
      "target_amount": 1050.00,
      "confidence_score": 0.95,
      "status": "pending",
      "amount_difference": 50.00
    },
    ...
  ]
}
```

### Step 4: Check Match Status Logic

**Perfect Match (Green) requires:**
- `status === 'approved'` OR
- `confidence_score >= 1.0` (100%)

**Variance (Amber) includes:**
- `status === 'pending'` AND `confidence_score >= 0.8`
- `status === 'modified'`
- `status === 'rejected'`
- Any match with `confidence_score < 1.0` not approved

**Warning (Low confidence):**
- `status === 'pending'` AND `confidence_score < 0.8`

## Common Issues & Solutions

### Issue 1: Matrix Shows All Dashes

**Symptoms:** Every cell shows "-"

**Causes:**
1. No reconciliation has been run
2. No matches created yet
3. Session ID is null or invalid
4. Document types don't match

**Solutions:**
1. Click "Run Reconciliation" button
2. Wait for reconciliation to complete
3. Click "Validate" button
4. Check browser console for errors

### Issue 2: Wrong Document Type Names

**Symptoms:** Console warnings about unmatched document types

**Causes:**
- Backend returns different format (e.g., "Balance Sheet" vs "balance_sheet")
- Custom document types not in DOCUMENTS array

**Solutions:**
1. Check console log for actual document type names
2. Add mapping in `normalizeDocType` function
3. Update backend to use consistent naming

### Issue 3: Duplicate Matches (Bidirectional)

**Symptoms:** Balance Sheet→Income Statement AND Income Statement→Balance Sheet both show values

**Causes:**
- Backend stores matches bidirectionally
- Frontend shows each direction separately

**This is CORRECT behavior** - shows relationships from both perspectives

**To verify if they're the same match:**
1. Click on Balance Sheet→Income Statement cell
2. Note the match details
3. Click on Income Statement→Balance Sheet cell
4. Compare match details
5. If match IDs are different, they're separate matches
6. If match IDs are the same, it's bidirectional display (expected)

### Issue 4: All Matches Show "VARIANCE"

**Symptoms:** No green "MATCH" cells, only amber "VARIANCE"

**Causes:**
1. All matches have discrepancies (amounts don't match)
2. No matches have been approved yet
3. Confidence scores are all <100%

**This might be CORRECT if:**
- Documents are from different sources with rounding differences
- Manual review is required before approval
- System is correctly detecting discrepancies

**To fix if incorrect:**
1. Review individual matches
2. Approve matches that are acceptable
3. Adjust tolerance thresholds in rule configuration
4. Investigate why confidence scores are low

## Expected vs Actual Behavior

### Expected Behavior

**After Running Reconciliation:**
1. Matrix populates with numbers
2. Green "MATCH" for perfect alignments
3. Amber "VARIANCE" for discrepancies
4. Dashes for no relationships

**When Clicking a Cell:**
1. Document Pair Panel opens
2. Shows list of matches between those documents
3. Can drill down into details

### Your Current Behavior Analysis

Based on screenshot:

✅ **CORRECT:**
- Matrix shows numbers (matches found)
- VARIANCE labels visible
- Appropriate cross-document relationships (BS↔IS, BS↔MS)

⚠️ **VERIFY:**
- Are Cash Flow and Rent Roll documents uploaded?
- Should there be matches between CF/RR and other documents?
- Are the variance amounts acceptable or need investigation?

❓ **CHECK:**
- Click on a variance cell - does detail panel open?
- Are the actual amounts shown in detail panel?
- Do the amounts make sense for those document pairs?

## How to Fix Issues

### If Matches Are Incorrect

1. **Check Source Data:**
   ```sql
   -- Check if documents are uploaded
   SELECT document_type, COUNT(*) 
   FROM extracted_line_items 
   WHERE property_id = X AND period_id = Y 
   GROUP BY document_type;
   ```

2. **Re-run Reconciliation:**
   - Click "Run Reconciliation" again
   - Use different matching options
   - Check "use_exact", "use_fuzzy", "use_calculated"

3. **Review Match Rules:**
   - Go to rule configuration
   - Check matching thresholds
   - Adjust confidence requirements

### If Document Types Don't Match

Update the normalization mapping:

```typescript
const mappings: Record<string, string> = {
  'your_backend_format': 'frontend_format',
  'Balance Sheet': 'balance_sheet',
  'BalanceSheet': 'balance_sheet',
  // Add your specific mappings
};
```

## Testing Matrix Accuracy

### Test 1: Verify Match Count

```sql
-- Get actual match count
SELECT 
  source_document_type,
  target_document_type,
  COUNT(*) as match_count,
  AVG(confidence_score) as avg_confidence,
  COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_count
FROM forensic_matches 
WHERE session_id = X
GROUP BY source_document_type, target_document_type;
```

Compare SQL results with matrix display.

### Test 2: Verify Variance Classification

```sql
-- Check matches that should show as variance
SELECT 
  source_document_type,
  target_document_type,
  status,
  confidence_score,
  amount_difference
FROM forensic_matches 
WHERE session_id = X
  AND (status != 'approved' OR confidence_score < 1.0)
ORDER BY source_document_type, target_document_type;
```

These should match the variance cells in the matrix.

### Test 3: Click-Through Test

1. Click Balance Sheet → Income Statement cell
2. Detail panel should show:
   - The 1 match referenced
   - Source and target amounts
   - Confidence score
   - Variance reason

If panel doesn't match the cell number, there's a data issue.

## Summary: Is Your Matrix Correct?

Based on the screenshot, the matrix appears **FUNCTIONALLY CORRECT** if:

✅ **YES - Matrix is Correct If:**
1. You have Balance Sheet and Income Statement documents uploaded
2. You have Mortgage Statement uploaded
3. You do NOT have Cash Flow or Rent Roll uploaded (or they have no matching rules)
4. There is legitimately 1 cross-document match between:
   - BS and IS (e.g., Net Income appears on both)
   - BS and MS (e.g., Mortgage liability/principal)
5. These matches have discrepancies that need review (hence VARIANCE)

❌ **NO - Matrix is Incorrect If:**
1. Cash Flow or Rent Roll documents ARE uploaded but show dashes
2. There should be more matches between documents
3. The variance matches should actually be perfect matches
4. The numbers don't match the actual document relationships

## Next Steps

1. **Verify Data Source:**
   - Check browser console logs
   - Look at API response in Network tab
   - Confirm document types match

2. **Test Interactivity:**
   - Click on a VARIANCE cell
   - Verify detail panel opens
   - Check match details make sense

3. **Compare with Database:**
   - Run SQL queries above
   - Compare counts with matrix
   - Investigate any mismatches

4. **Review Variances:**
   - Are the discrepancies expected?
   - Do amounts need reconciliation?
   - Should matches be approved?

## Conclusion

The Reconciliation Matrix is displaying data **as designed**. Whether the data is "correct" depends on:

1. **What documents you've uploaded**
2. **What matching rules are configured**
3. **What relationships should exist between documents**
4. **Whether the variances are expected or errors**

Use the verification steps above to confirm the displayed information matches your expectations and the actual data in the system.

---

*Last Updated: January 24, 2026*
*Component: ReconciliationMatrix*
*Status: Enhanced with debugging and normalization*
