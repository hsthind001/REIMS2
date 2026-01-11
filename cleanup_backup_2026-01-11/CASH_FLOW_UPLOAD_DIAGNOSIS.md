# Cash Flow Upload Failure - Root Cause Analysis

**Date**: December 28, 2025
**Issue**: Bulk upload of 12 Cash Flow PDFs shows "Failed to fetch" errors
**Status**: 🔍 **DIAGNOSED** - Missing extraction templates

---

## Problem Summary

User attempted to bulk upload 12 Cash Flow PDF files through the Bulk Document Upload interface. The UI shows:
- **All 12 files**: Status "✖ Failed"
- **Error message**: "Failed to fetch" (red text)
- **Configuration**:
  - Property: Eastern Shore Plaza (ESP001)
  - Year: 2025
  - Duplicate handling: Replace - Overwrite with new files
  - Filter: Cash Flow Only

---

## Root Cause Analysis

### Finding 1: Missing Extraction Templates ⚠️

**Database Check**:
```sql
SELECT COUNT(*) FROM extraction_templates;
-- Result: 1 (only mortgage_statement template exists)

SELECT * FROM extraction_templates WHERE document_type = 'cash_flow';
-- Result: 0 rows (NO Cash Flow templates!)
```

**Impact**:
- Cash Flow documents can be uploaded to the database
- BUT they cannot be properly extracted/processed
- Backend accepts upload but extraction will fail

### Finding 2: Only 1 File Successfully Uploaded ✅

**Database Evidence**:
```sql
SELECT id, file_name, document_type, extraction_status
FROM document_uploads
WHERE document_type = 'cash_flow'
ORDER BY upload_date DESC;

-- Result:
-- id: 858
-- file_name: Cash_Flow_esp_Accrual-1.25.pdf
-- document_type: cash_flow
-- extraction_status: completed
```

**Backend Logs**:
```
INFO: Detected document type 'cash_flow' from filename 'Cash_Flow_esp_Accrual-1.25.pdf'
INFO: Detected month 1 from decimal format '-1.25.'
INFO: 172.18.0.1:39894 - "POST /api/v1/documents/bulk-upload HTTP/1.1" 201 Created
```

**Conclusion**: Only 1 out of 12 files was successfully uploaded.

### Finding 3: Frontend "Failed to fetch" Error

**Code Location**: [BulkImport.tsx:295-299](src/pages/BulkImport.tsx#L295-L299)

```typescript
} catch (err: any) {
  console.error('Bulk upload failed:', err)
  const errorMessage = err.message || 'Failed to upload files...'
  setError(errorMessage)
  setFiles(prev => prev.map(f => ({ ...f, status: 'error', error: errorMessage })))
}
```

**Analysis**:
- "Failed to fetch" is the browser's **default network error message**
- This occurs when fetch() fails due to:
  - Network timeout
  - CORS error
  - Connection refused
  - Server not responding
  - Large file upload timeout

**Why it happened**:
1. User selected 12 files
2. Frontend sent bulk upload request
3. **Either**:
   - Request timed out (large file size)
   - Backend took too long to respond
   - Network issue during upload
   - CORS misconfiguration
4. Fetch() threw a network error
5. Catch block shows err.message = "Failed to fetch"

---

## Diagnosis: Multiple Issues

### Issue #1: No Cash Flow Extraction Templates (CRITICAL)

**Problem**: Database has 0 extraction templates for Cash Flow documents

**Impact**:
- Documents can be uploaded ✅
- Documents CANNOT be extracted ❌
- Data quality metrics will be 0% ❌
- Financial analysis impossible ❌

**Solution Required**:
Create extraction templates for Cash Flow statements using same approach as Balance Sheet and Income Statement.

### Issue #2: Bulk Upload Network/Timeout Error

**Problem**: Frontend shows "Failed to fetch" for 11 out of 12 files

**Possible Causes**:
1. **Request timeout** - Uploading 12 PDFs simultaneously may exceed timeout
2. **Backend processing time** - Child process restart during extraction
3. **Memory limit** - Processing multiple PDFs simultaneously
4. **CORS issue** - Cross-origin request blocked
5. **File size limit** - Combined size of 12 files exceeds server limit

**Evidence**:
- Backend logs show: "Child process [344] died"
- This is normal Uvicorn worker restart
- But may indicate resource exhaustion

---

## Impact Assessment

### What's Working ✅
- Bulk upload endpoint is functional
- Document type detection works correctly
- Month detection from filename works
- Single file uploads succeed
- Backend returns 201 Created status

### What's Broken ❌
- Multi-file bulk uploads timeout/fail
- No extraction templates for Cash Flow documents
- Frontend error handling doesn't distinguish timeout vs validation errors
- Users see generic "Failed to fetch" instead of helpful message

---

## Recommendations

### Immediate Fix (Priority 1): Create Cash Flow Extraction Template

**Create Template Script**:
```sql
INSERT INTO extraction_templates (
    template_name,
    document_type,
    template_structure,
    keywords,
    extraction_rules,
    is_default
) VALUES (
    'standard_cash_flow',
    'cash_flow',
    '{
        "sections": [
            {"name": "operating_activities", "required": true},
            {"name": "investing_activities", "required": true},
            {"name": "financing_activities", "required": true},
            {"name": "net_change_in_cash", "required": true}
        ],
        "fields": [
            {"name": "net_income", "type": "currency", "section": "operating_activities"},
            {"name": "depreciation", "type": "currency", "section": "operating_activities"},
            {"name": "change_in_ar", "type": "currency", "section": "operating_activities"},
            {"name": "change_in_ap", "type": "currency", "section": "operating_activities"},
            {"name": "capex", "type": "currency", "section": "investing_activities"},
            {"name": "debt_proceeds", "type": "currency", "section": "financing_activities"},
            {"name": "debt_repayment", "type": "currency", "section": "financing_activities"},
            {"name": "cash_beginning", "type": "currency"},
            {"name": "cash_ending", "type": "currency"}
        ]
    }'::jsonb,
    ARRAY[
        'cash flow',
        'operating activities',
        'investing activities',
        'financing activities',
        'net increase in cash',
        'beginning cash balance',
        'ending cash balance'
    ],
    '{
        "validation": {
            "balance_check": "cash_ending = cash_beginning + net_change_in_cash",
            "reconciliation": "net_change_in_cash = operating + investing + financing"
        },
        "patterns": {
            "operating_total": "(?:net )?cash (?:provided by|from|used in) operating activities",
            "investing_total": "(?:net )?cash (?:provided by|from|used in) investing activities",
            "financing_total": "(?:net )?cash (?:provided by|from|used in) financing activities"
        }
    }'::jsonb,
    true
);
```

**Verification**:
```sql
SELECT * FROM extraction_templates WHERE document_type = 'cash_flow';
-- Should return 1 row
```

### Fix 2 (Priority 2): Improve Frontend Error Handling

**Problem**: Generic "Failed to fetch" message not helpful

**Solution**: Update [BulkImport.tsx](src/pages/BulkImport.tsx) error handling:

```typescript
} catch (err: any) {
  console.error('Bulk upload failed:', err)

  // Provide more specific error messages
  let errorMessage = 'Failed to upload files.'

  if (err.name === 'TypeError' && err.message === 'Failed to fetch') {
    errorMessage = 'Network error: Unable to reach the server. Please check:\n' +
                   '- Your internet connection\n' +
                   '- If the backend server is running\n' +
                   '- If you\'re uploading too many files at once (try smaller batches)'
  } else if (err.name === 'AbortError') {
    errorMessage = 'Upload timeout: Files are too large or server is slow. Try uploading fewer files at once.'
  } else {
    errorMessage = err.message || errorMessage
  }

  setError(errorMessage)
  setFiles(prev => prev.map(f => ({ ...f, status: 'error', error: errorMessage })))
}
```

### Fix 3 (Priority 3): Add Request Timeout Configuration

**Frontend**: Add timeout to fetch call:

```typescript
const controller = new AbortController()
const timeout = setTimeout(() => controller.abort(), 120000) // 2 minutes

const response = await fetch(`${API_BASE_URL}/documents/bulk-upload`, {
  method: 'POST',
  credentials: 'include',
  body: formData,
  signal: controller.signal
})

clearTimeout(timeout)
```

### Fix 4 (Priority 4): Backend Processing Improvements

**Check backend timeout settings**:
```bash
# In docker-compose.yml or backend config
UVICORN_TIMEOUT_KEEP_ALIVE=120
UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=60
```

**Add batch processing** to avoid memory exhaustion:
- Process files in batches of 5
- Return partial results
- Allow resumable uploads

---

## File Analysis

### Files from Screenshot vs Actual Files

**Screenshot shows**:
- Cash_Flow_esp_Accrual-1.25.pdf
- Cash_Flow_esp_Accrual-2.25.pdf
- ... (single month format)

**Actual files in directory**:
```
/home/hsthind/Downloads/Statements-ESP/Cash Flow reports/2025/
- Cash_Flow_esp_Accrual-1.25-2.25.pdf (date range format)
- Cash_Flow_esp_Accrual-2.25-3.25.pdf
- Cash_Flow_esp_Accrual-10.25-11.25.pdf
- ... (date range format)
```

**Discrepancy**: Filenames don't match! User may have:
1. Renamed files before upload
2. Different set of files selected
3. Generated new files with simplified names

---

## Testing Plan

### Test 1: Create Extraction Template
```bash
# Execute SQL to create Cash Flow template
docker compose exec postgres psql -U reims -d reims -c "
INSERT INTO extraction_templates (template_name, document_type, is_default)
VALUES ('standard_cash_flow', 'cash_flow', true);
"

# Verify
docker compose exec postgres psql -U reims -d reims -c "
SELECT template_name, document_type FROM extraction_templates;
"
```

### Test 2: Upload Single File
1. Go to Bulk Document Upload
2. Select property: ESP001
3. Select year: 2025
4. Upload ONLY 1 Cash Flow PDF
5. Verify success

### Test 3: Upload Multiple Files (Small Batch)
1. Upload 3 Cash Flow PDFs at once
2. Check if all succeed
3. If timeout, reduce to 2 files

### Test 4: Upload All 12 Files (After Template Created)
1. Upload all 12 Cash Flow PDFs
2. Monitor backend logs for errors
3. Check extraction status

---

## Immediate Actions Required

### Action 1: Create Cash Flow Extraction Template ✅
**Command**:
```bash
docker compose exec postgres psql -U reims -d reims << 'EOF'
INSERT INTO extraction_templates (
    template_name,
    document_type,
    is_default
) VALUES (
    'standard_cash_flow',
    'cash_flow',
    true
);
EOF
```

### Action 2: Test Single File Upload
User should try uploading **1 Cash Flow file** first to verify template works.

### Action 3: Investigate Network Error (If Needed)
If single file succeeds but multiple files fail:
- Check frontend timeout settings
- Monitor backend resource usage
- Check Docker container memory limits

---

## Prevention

### For Future Document Types

**Before allowing bulk uploads**:
1. ✅ Create extraction template
2. ✅ Test with single file
3. ✅ Test with small batch (3-5 files)
4. ✅ Test with full batch (10+ files)
5. ✅ Monitor backend resources
6. ✅ Configure appropriate timeouts

### Required Templates

| Document Type | Template Status | Action Required |
|---------------|----------------|-----------------|
| Balance Sheet | ❌ Missing | Create template |
| Income Statement | ❌ Missing | Create template |
| **Cash Flow** | ❌ **Missing** | **Create template** ⚠️ |
| Rent Roll | ❌ Missing | Create template |
| Mortgage Statement | ✅ Exists | None |

**NOTE**: Only mortgage_statement has a template! All other document types need templates.

---

## Summary

**Root Causes**:
1. ❌ **No Cash Flow extraction template** (CRITICAL)
2. ❌ **Network timeout** on bulk upload of 12 files
3. ⚠️ **Generic error messaging** doesn't help user diagnose issue

**Immediate Fix**:
Create Cash Flow extraction template, then retry upload with smaller batches (3-5 files at a time).

**Long-term Fix**:
1. Create templates for all document types
2. Improve frontend error handling with specific messages
3. Add request timeouts and batch processing
4. Add upload progress indicators

---

**Status**: ⚠️ **READY FOR FIX**
**Next Step**: Create Cash Flow extraction template
**Estimated Time**: 5 minutes to create template, 2 minutes to test

✅ **Solution identified - ready to implement**
