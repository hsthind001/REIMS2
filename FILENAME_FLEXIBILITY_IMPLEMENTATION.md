# Filename Flexibility Implementation

**Date**: December 28, 2025
**Issue**: System requires specific filename patterns to detect document type
**Requirement**: Accept ANY filename, allow user to specify document type manually
**Status**: 📋 **IMPLEMENTATION PLAN**

---

## Current Problem

### Issue 1: Filename Pattern Dependency ❌

**Current Behavior**:
```python
# backend/app/services/document_service.py:718-725
type_detection = detector.detect_from_filename(file.filename or "")
detected_type = type_detection.get("document_type", "unknown")

if detected_type == "unknown":
    result["error"] = "Could not detect document type from filename"
    results.append(result)
    failed_count += 1
    continue  # ❌ REJECTS FILE
```

**Impact**:
- Files with non-standard names are REJECTED
- Examples that would fail:
  - `statement_01.pdf` (no document type keyword)
  - `ESP_financial_data.pdf` (ambiguous)
  - `monthly_report.pdf` (generic name)
  - `2025-01-document.pdf` (no type indicator)

### Issue 2: No Manual Override

**Current Limitation**:
- Frontend has fileTypeFilter dropdown (Balance Sheet, Income Statement, etc.)
- BUT this is only for FILTERING files to display
- It doesn't SEND the selected type to backend
- Backend relies 100% on filename auto-detection

**Frontend Code** (BulkImport.tsx):
```typescript
// Lines 204-211: FormData only includes property, year, duplicate strategy
formData.append('property_code', propertyCode)
formData.append('year', selectedYear.toString())
formData.append('duplicate_strategy', duplicateStrategy)
files.forEach(fileWithMeta => {
  formData.append('files', fileWithMeta.file, fileWithMeta.file.name)
  // ❌ NO document_type sent per file!
})
```

---

## Solution Design

### Approach 1: Per-File Document Type Override (RECOMMENDED) ✅

**User Experience**:
1. User uploads files with ANY filename
2. Frontend shows each file with detected type (if possible)
3. User can **manually select/override** document type for each file
4. Frontend sends document type along with each file
5. Backend uses manual type OR falls back to detection

**Benefits**:
- ✅ Supports any filename
- ✅ User has full control
- ✅ Still benefits from auto-detection when it works
- ✅ No breaking changes (backward compatible)

### Approach 2: Single Document Type for All Files (SIMPLER)

**User Experience**:
1. User selects document type dropdown (e.g., "Cash Flow")
2. User uploads multiple files
3. All files are treated as that document type
4. No per-file override needed

**Benefits**:
- ✅ Simpler UI (fewer dropdowns)
- ✅ Faster for bulk uploads of same type
- ✅ Less cognitive load

**Limitations**:
- ❌ Cannot upload mixed document types in one batch
- ❌ User must upload Cash Flow, then Income Statement separately

---

## Recommended Solution: Hybrid Approach ✅

Combine both approaches for maximum flexibility:

### 1. Backend Changes

**Modify Bulk Upload API** to accept optional document type metadata:

**Option A: File Metadata in JSON** (Clean, structured)
```python
# backend/app/api/v1/documents.py

@router.post("/documents/bulk-upload", status_code=status.HTTP_201_CREATED)
async def bulk_upload_documents(
    property_code: str = Form(...),
    year: int = Form(...),
    files: List[UploadFile] = File(...),
    file_metadata: Optional[str] = Form(None, description="JSON array of file metadata"),
    duplicate_strategy: str = Form("skip"),
    uploaded_by: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    file_metadata format:
    [
        {"filename": "statement1.pdf", "document_type": "cash_flow", "month": 1},
        {"filename": "report.pdf", "document_type": "income_statement", "month": 2}
    ]
    """
    # Parse file_metadata if provided
    metadata_dict = {}
    if file_metadata:
        import json
        metadata_list = json.loads(file_metadata)
        metadata_dict = {item['filename']: item for item in metadata_list}

    # Pass to service
    result = await doc_service.bulk_upload_documents(
        property_code=property_code,
        year=year,
        files=files,
        file_metadata=metadata_dict,  # NEW PARAMETER
        uploaded_by=uploaded_by,
        duplicate_strategy=duplicate_strategy
    )
```

**Option B: Individual Form Fields** (Simpler for small batches)
```python
# For each file, send: files[0], document_types[0], months[0]
document_types: Optional[List[str]] = Form(None)
months: Optional[List[int]] = Form(None)
```

**Modify DocumentService.bulk_upload_documents**:
```python
# backend/app/services/document_service.py

async def bulk_upload_documents(
    self,
    property_code: str,
    year: int,
    files: List[UploadFile],
    file_metadata: Optional[Dict[str, Dict]] = None,  # NEW
    uploaded_by: Optional[int] = None,
    duplicate_strategy: str = "skip"
) -> Dict:
    """
    file_metadata: {
        "filename.pdf": {"document_type": "cash_flow", "month": 1},
        ...
    }
    """
    detector = DocumentTypeDetector()

    for file in files:
        filename = file.filename or "unknown"

        # NEW: Check if user provided manual document type
        manual_metadata = file_metadata.get(filename, {}) if file_metadata else {}
        manual_doc_type = manual_metadata.get("document_type")
        manual_month = manual_metadata.get("month")

        # Step 2: Determine document type
        if manual_doc_type:
            # USER OVERRIDE: Use manually selected type
            detected_type = manual_doc_type
            result["document_type"] = detected_type
            result["detection_method"] = "manual"
        else:
            # AUTO-DETECT: Fallback to filename detection
            type_detection = detector.detect_from_filename(filename)
            detected_type = type_detection.get("document_type", "unknown")

            if detected_type == "unknown":
                # NEW: Instead of rejecting, mark as needing manual input
                result["error"] = "Could not detect document type - please specify manually"
                result["needs_manual_input"] = True
                results.append(result)
                failed_count += 1
                continue

            result["document_type"] = detected_type
            result["detection_method"] = "filename"

        # Step 3: Determine month
        if manual_month:
            month = manual_month
        else:
            month = detector.detect_month_from_filename(filename, year) or 1

        result["month"] = month

        # Continue with upload...
```

### 2. Frontend Changes

**Modify BulkImport.tsx** to allow per-file document type selection:

**UI Enhancement 1: Per-File Dropdown**
```typescript
// Add document type selection to FileWithMetadata
interface FileWithMetadata {
  file: File
  detectedType: string
  manualType?: string  // NEW: User-selected type
  status: 'pending' | 'uploading' | 'success' | 'skipped' | 'replaced' | 'error'
  // ... existing fields
}

// UI Component: File list with type dropdown
{files.map((fileWithMeta, index) => (
  <div key={index} className="file-row">
    <span>{fileWithMeta.file.name}</span>

    {/* Document Type Dropdown */}
    <select
      value={fileWithMeta.manualType || fileWithMeta.detectedType}
      onChange={(e) => updateFileType(index, e.target.value)}
    >
      <option value="balance_sheet">Balance Sheet</option>
      <option value="income_statement">Income Statement</option>
      <option value="cash_flow">Cash Flow</option>
      <option value="rent_roll">Rent Roll</option>
      <option value="mortgage_statement">Mortgage Statement</option>
    </select>

    {/* Month Dropdown (optional) */}
    <select
      value={fileWithMeta.month || 1}
      onChange={(e) => updateFileMonth(index, parseInt(e.target.value))}
    >
      {[1,2,3,4,5,6,7,8,9,10,11,12].map(m => (
        <option key={m} value={m}>{monthNames[m-1]}</option>
      ))}
    </select>

    {/* Status indicator */}
    <StatusBadge status={fileWithMeta.status} />
  </div>
))}
```

**Upload Logic Update**:
```typescript
const handleBulkUpload = async () => {
  const formData = new FormData()
  formData.append('property_code', propertyCode)
  formData.append('year', selectedYear.toString())
  formData.append('duplicate_strategy', duplicateStrategy)

  // NEW: Create file metadata
  const fileMetadata = files.map(f => ({
    filename: f.file.name,
    document_type: f.manualType || f.detectedType,
    month: f.month || 1
  }))

  // Append metadata as JSON
  formData.append('file_metadata', JSON.stringify(fileMetadata))

  // Append files
  files.forEach(fileWithMeta => {
    formData.append('files', fileWithMeta.file, fileWithMeta.file.name)
  })

  // Send request...
}
```

**UI Enhancement 2: Bulk Type Selection**
```typescript
// Add "Apply Type to All" button
<div className="bulk-actions">
  <label>Apply to all files:</label>
  <select onChange={(e) => applyTypeToAll(e.target.value)}>
    <option value="">-- Select Type --</option>
    <option value="balance_sheet">Balance Sheet</option>
    <option value="income_statement">Income Statement</option>
    <option value="cash_flow">Cash Flow</option>
    <option value="rent_roll">Rent Roll</option>
    <option value="mortgage_statement">Mortgage Statement</option>
  </select>
</div>

// Handler
const applyTypeToAll = (docType: string) => {
  setFiles(prev => prev.map(f => ({ ...f, manualType: docType })))
}
```

---

## Implementation Steps

### Phase 1: Backend (Priority 1)

**Step 1.1**: Update bulk upload API endpoint
- File: `backend/app/api/v1/documents.py`
- Add `file_metadata` Form parameter
- Pass to DocumentService

**Step 1.2**: Update DocumentService.bulk_upload_documents
- File: `backend/app/services/document_service.py`
- Add `file_metadata` parameter
- Check for manual document type first
- Fall back to auto-detection if not provided
- Don't reject files with unknown type - mark for manual input

**Step 1.3**: Add validation
- Validate document_type values (balance_sheet, income_statement, etc.)
- Validate month values (1-12)

### Phase 2: Frontend (Priority 2)

**Step 2.1**: Update FileWithMetadata interface
- Add `manualType` field
- Add `manualMonth` field

**Step 2.2**: Add per-file UI controls
- Document type dropdown per file
- Month dropdown per file
- Show detected type as hint/placeholder

**Step 2.3**: Add bulk actions
- "Apply Type to All" dropdown
- "Apply Month to All" option

**Step 2.4**: Update upload logic
- Build file_metadata JSON
- Send with FormData

### Phase 3: Testing

**Test Case 1**: Generic filenames
- Upload `file1.pdf`, `file2.pdf`, `file3.pdf`
- Manually select: Cash Flow, Income Statement, Balance Sheet
- Verify all upload successfully

**Test Case 2**: Auto-detection works
- Upload `Cash_Flow_Jan_2025.pdf`
- System detects: cash_flow, month 1
- User doesn't need to change anything
- Verify uploads successfully

**Test Case 3**: Override auto-detection
- Upload `Balance_Sheet_Dec_2024.pdf`
- System detects: balance_sheet
- User manually changes to: income_statement
- Verify uses manual selection

**Test Case 4**: Bulk type assignment
- Upload 12 files with generic names
- Select "Apply to All: Cash Flow"
- All files set to cash_flow type
- Verify uploads successfully

---

## Alternative: Simpler Quick Fix

If the full solution above is too complex, here's a **quick fix** to unblock users:

### Quick Fix: Don't Reject Unknown Files

**Change 1 line in backend**:
```python
# backend/app/services/document_service.py:721-725

# BEFORE (rejects file):
if detected_type == "unknown":
    result["error"] = "Could not detect document type from filename"
    results.append(result)
    failed_count += 1
    continue  # ❌ REJECTS

# AFTER (uses default type):
if detected_type == "unknown":
    # Default to cash_flow or let user set via fileTypeFilter
    detected_type = "cash_flow"  # Or use a "default_document_type" parameter
    result["warning"] = "Could not detect type from filename, using default"
```

**Limitations**:
- All unknown files default to same type
- User cannot override per file
- Not ideal but UNBLOCKS uploads

---

## Recommended Path Forward

### Option A: Full Implementation (Best UX) ✅
- Implement Phases 1-3 above
- Estimated time: 2-3 hours
- Benefits: Complete flexibility, best user experience

### Option B: Quick Fix + Phase 1 (Balanced)
- Implement quick fix now (5 minutes)
- Implement backend Phase 1 (1 hour)
- Defer frontend Phase 2 to later
- Benefits: Unblocks users immediately, adds proper API later

### Option C: Quick Fix Only (Fastest)
- Implement quick fix (5 minutes)
- Add configuration for default document type
- Benefits: Immediate unblock, minimal code change

---

## Decision Needed

**Question for User**:

Which approach do you prefer?

1. **Full Implementation** - Per-file document type selection with UI controls
2. **Backend Only** - API supports manual type, frontend uses fileTypeFilter as default
3. **Quick Fix** - Don't reject unknown files, default to cash_flow (or configurable type)

---

## Status

**Current Limitation**: ❌ Filenames must match specific patterns
**User Impact**: ❌ Generic filenames are rejected
**Solution Ready**: ✅ Implementation plan complete
**Awaiting Decision**: User preference on approach

---

**Next Step**: User selects preferred approach, then I implement immediately.
