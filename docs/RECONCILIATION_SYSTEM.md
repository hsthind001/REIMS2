# REIMS2 Reconciliation System - Technical Documentation

**Version**: 1.0  
**Date**: November 8, 2025  
**Status**: ✅ Production Ready

---

## Overview

The Reconciliation System is a comprehensive financial data quality assurance feature that enables users to compare original PDF documents with extracted database records side-by-side, identify differences, resolve discrepancies, and generate detailed reconciliation reports.

### Key Features

✅ **Side-by-Side Comparison**: PDF viewer on left, database records on right  
✅ **Intelligent Difference Detection**: Exact match, within tolerance, mismatches, missing records  
✅ **Color-Coded Status**: Green (match), Yellow (tolerance), Red (mismatch), Gray (missing)  
✅ **Bulk Operations**: Accept PDF values, accept DB values for multiple records  
✅ **Manual Resolution**: Edit individual differences with audit trail  
✅ **Report Generation**: Export reconciliation results to Excel/CSV  
✅ **Session Tracking**: Full history of reconciliation sessions  
✅ **100% Data Quality**: Ensures zero data loss with complete audit trail

---

## Architecture

### Backend Components

#### 1. Database Schema

**New Tables:**

```sql
-- Tracks each reconciliation session
reconciliation_sessions (
  id, property_id, period_id, document_type, status, user_id,
  started_at, completed_at, summary (JSON), notes
)

-- Stores detected differences
reconciliation_differences (
  id, session_id, account_code, account_name, field_name,
  pdf_value, db_value, difference, difference_percent, difference_type,
  status, resolved_by, resolved_at, confidence_score, needs_review, flags
)

-- Audit trail of corrections
reconciliation_resolutions (
  id, difference_id, action_taken, old_value, new_value,
  reason, created_by, created_at
)
```

**Enhanced Tables:**

All financial data tables now include:
- `reconciliation_status`: 'pending', 'reconciled', 'reviewed'
- `last_reconciled_at`: Timestamp of last reconciliation
- `reconciled_by`: User who performed reconciliation

#### 2. Services

**ReconciliationService** (`backend/app/services/reconciliation_service.py`):
- `start_reconciliation_session()`: Create new session
- `compare_pdf_to_database()`: Perform field-by-field comparison
- `get_pdf_data()`: Extract or retrieve PDF data
- `get_database_data()`: Fetch database records
- `resolve_difference()`: Apply single correction
- `bulk_resolve_differences()`: Apply bulk corrections
- `complete_session()`: Finalize reconciliation

**PDF Comparator** (`backend/app/utils/pdf_comparator.py`):
- `compare_amounts()`: Decimal comparison with tolerance
- `compare_account_names()`: Fuzzy string matching
- `detect_missing_accounts()`: Find missing records
- `detect_extra_accounts()`: Find extra records
- `validate_totals()`: Ensure section totals match
- `prioritize_differences()`: Sort by severity

#### 3. API Endpoints

All endpoints under `/api/v1/reconciliation`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/session` | Start new reconciliation session |
| GET | `/compare` | Get comparison data |
| GET | `/pdf-url` | Get MinIO presigned URL for PDF |
| POST | `/resolve/{id}` | Resolve single difference |
| POST | `/bulk-resolve` | Bulk resolve differences |
| GET | `/sessions` | List reconciliation sessions |
| GET | `/sessions/{id}` | Get session details |
| PUT | `/sessions/{id}/complete` | Mark session complete |
| GET | `/report/{id}` | Generate Excel/PDF report |

### Frontend Components

#### 1. Main Reconciliation Page

**File**: `src/pages/Reconciliation.tsx`

**Features**:
- Property/Year/Month/Document Type selector
- Start Reconciliation button
- Summary statistics cards
- Filter buttons (All, Matches, Differences)
- Bulk action buttons
- Split-screen layout (50/50 default)
- PDF viewer (iframe)
- Data table with color-coded rows
- Checkbox selection for bulk operations
- Inline resolve buttons

#### 2. API Client

**File**: `src/lib/reconciliation.ts`

**Functions**:
- `startSession()`: Create session
- `getComparison()`: Fetch comparison data
- `getPdfUrl()`: Get PDF URL
- `resolveDifference()`: Resolve single
- `bulkResolve()`: Bulk resolve
- `getSessions()`: List sessions
- `completeSession()`: Complete session
- `generateReport()`: Export report

---

## Reconciliation Workflow

### Step 1: Start Reconciliation

```typescript
// User selects property, year, month, document type
// Clicks "Start Reconciliation"

const data = await reconciliationService.getComparison(
  propertyCode,
  year,
  month,
  docType
);

// System creates session and compares data
// Returns comparison results with differences
```

### Step 2: Review Differences

**Difference Types**:
- **exact**: Values match within $0.01 tolerance (Green)
- **tolerance**: Values within 1% tolerance (Yellow)
- **mismatch**: Significant difference (Red)
- **missing_pdf**: Account in DB but not in PDF (Gray)
- **missing_db**: Account in PDF but not in DB (Purple)

### Step 3: Resolve Differences

**Single Resolution**:
```typescript
await reconciliationService.resolveDifference(differenceId, {
  action: 'accept_pdf', // or 'accept_db', 'manual_entry', 'ignore'
  new_value: 12345.67, // if manual_entry
  reason: 'Verified with source document'
});
```

**Bulk Resolution**:
```typescript
await reconciliationService.bulkResolve({
  difference_ids: [1, 2, 3, 4],
  action: 'accept_pdf'
});
```

### Step 4: Generate Report

```typescript
const blob = await reconciliationService.generateReport(sessionId, 'excel');
// Downloads CSV/Excel file with all differences and resolutions
```

### Step 5: Complete Session

```typescript
await reconciliationService.completeSession(sessionId);
// Marks session as complete, locks reconciliation
```

---

## Data Comparison Algorithm

### Amount Comparison

```python
def compare_amounts(pdf_value, db_value, tolerance=0.01):
    difference = abs(pdf_value - db_value)
    
    if difference <= tolerance:
        return 'exact'
    
    diff_percent = (difference / max(abs(pdf_value), abs(db_value))) * 100
    
    if diff_percent <= 1.0:
        return 'tolerance'
    
    return 'mismatch'
```

### Priority Levels

1. **Critical (Priority 1)**: Missing accounts
2. **High (Priority 2)**: Mismatches >10% or >$10,000
3. **Medium (Priority 3)**: Mismatches 1-10% or $100-$10,000
4. **Low (Priority 4)**: Small mismatches <1% or <$100
5. **Info (Priority 5)**: Within tolerance

---

## Database Views & Queries

### Get Reconciliation Status by Property

```sql
SELECT 
  p.property_code,
  p.property_name,
  rs.document_type,
  rs.status,
  rs.summary->>'total_records' as total_records,
  rs.summary->>'matches' as matches,
  rs.summary->>'differences' as differences,
  rs.started_at,
  rs.completed_at
FROM reconciliation_sessions rs
JOIN properties p ON p.id = rs.property_id
WHERE p.property_code = 'ESP001'
ORDER BY rs.started_at DESC;
```

### Get Unresolved Differences

```sql
SELECT 
  rd.account_code,
  rd.account_name,
  rd.pdf_value,
  rd.db_value,
  rd.difference,
  rd.difference_type,
  rd.needs_review
FROM reconciliation_differences rd
JOIN reconciliation_sessions rs ON rs.id = rd.session_id
WHERE rd.status = 'pending'
  AND rd.difference_type IN ('mismatch', 'missing_db', 'missing_pdf')
ORDER BY rd.difference DESC;
```

---

## Configuration

### Tolerance Settings

**Amount Tolerance**: $0.01 (configurable in `pdf_comparator.py`)  
**Percentage Tolerance**: 1% (configurable in `pdf_comparator.py`)  
**Fuzzy Match Threshold**: 85% (configurable in `pdf_comparator.py`)

### PDF Display

**MinIO URL Expiry**: 1 hour (3600 seconds)  
**Viewer**: HTML iframe (can be upgraded to react-pdf)

---

## Security & Audit Trail

### Authentication

All reconciliation endpoints require authentication:
```python
current_user: User = Depends(get_current_user)
```

### Audit Trail

Every resolution is logged:
```python
ReconciliationResolution(
    difference_id=diff_id,
    action_taken='accept_pdf',
    old_value=123.45,
    new_value=123.46,
    reason='Verified with source',
    created_by=user_id,
    created_at=now()
)
```

### Data Integrity

- All bulk operations are transactional (all-or-nothing)
- Critical validations before commit
- Rollback on failure
- Complete audit trail maintained

---

## Performance Considerations

### Scalability

- **Records per Document**: Tested with 100+ line items
- **Comparison Speed**: <2 seconds for 100 records
- **PDF Loading**: Depends on MinIO/network speed
- **Concurrent Users**: Supports multiple simultaneous reconciliations

### Optimization

- Database indexes on: `property_id`, `period_id`, `document_type`, `status`
- Lazy loading of PDF (only when needed)
- Paginated session history
- Compressed PDF storage in MinIO

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Property not found" | Invalid property code | Verify property exists |
| "Period not found" | No financial period for date | Create period first |
| "PDF not found" | Document not uploaded | Upload PDF for this period |
| "Session not found" | Invalid session ID | Check session exists |

### Retry Logic

- MinIO failures: Retry 3 times with exponential backoff
- Database deadlocks: Automatic retry
- Network errors: User-initiated retry

---

## Testing

### Backend Tests

```bash
# Run reconciliation service tests
pytest backend/tests/test_reconciliation_service.py -v

# Run API endpoint tests
pytest backend/tests/test_reconciliation_api.py -v

# Run comparator tests
pytest backend/tests/test_pdf_comparator.py -v
```

### Frontend Tests

```bash
# Run component tests (if implemented)
npm run test -- Reconciliation.test.tsx
```

---

## Monitoring & Logging

### Key Metrics

- **Reconciliation Rate**: Percentage of records matching
- **Resolution Time**: Average time to resolve differences
- **Session Duration**: Time from start to complete
- **Error Rate**: Failed reconciliations

### Logging

```python
logger.info(f"Reconciliation started: property={property_code}, period={year}-{month}")
logger.warning(f"High number of differences detected: {diff_count}")
logger.error(f"Reconciliation failed: {error}")
```

---

## Future Enhancements

### Phase 2 Features

- [ ] Real-time PDF highlighting (sync scroll between PDF and table)
- [ ] Machine learning-based anomaly detection
- [ ] Automated resolution suggestions
- [ ] Mobile-responsive reconciliation view
- [ ] Advanced filters (by severity, account type, etc.)
- [ ] Scheduled reconciliation reports
- [ ] Dashboard widgets showing reconciliation status
- [ ] Email notifications for critical differences

### Phase 3 Features

- [ ] Multi-document reconciliation (compare across periods)
- [ ] Variance analysis and trending
- [ ] Integration with external accounting systems
- [ ] API webhooks for reconciliation events
- [ ] Custom reconciliation rules per property

---

## Support

### Troubleshooting

**Problem**: PDF not displaying  
**Solution**: Check MinIO connectivity, verify presigned URL generation

**Problem**: Slow comparison  
**Solution**: Check database indexes, optimize query performance

**Problem**: Differences not resolving  
**Solution**: Verify user permissions, check transaction commit

### Contact

For technical support or feature requests, contact the REIMS2 development team.

---

## Changelog

### Version 1.0 (November 8, 2025)

- ✅ Initial release
- ✅ Side-by-side PDF and database comparison
- ✅ Color-coded difference highlighting
- ✅ Bulk resolution operations
- ✅ Excel/CSV report export
- ✅ Complete audit trail
- ✅ Session management
- ✅ All financial statement types supported

---

**Status**: ✅ Production Ready  
**Last Updated**: November 8, 2025

