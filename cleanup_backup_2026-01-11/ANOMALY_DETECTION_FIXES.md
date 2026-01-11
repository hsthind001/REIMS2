# Anomaly Detection Bulk Re-Run Fixes

## Problem Summary

During the bulk re-run of anomaly detection, 98 documents failed. Investigation revealed several critical issues:

1. **Missing Document Type Support**: `rent_roll` and `mortgage_statement` document types were not handled in `_detect_anomalies_for_document()`, even though detection methods exist for them.

2. **Silent Failures**: Multiple failure scenarios resulted in silent returns without logging:
   - Missing `period_id`
   - Missing period in database
   - No extracted data found
   - Insufficient historical data
   - Unsupported document types

3. **Poor Error Logging**: Used `print()` instead of proper logging, and caught exceptions without re-raising them, causing batch tasks to think documents succeeded when they actually failed.

4. **No Pre-Validation**: Batch task didn't validate documents before processing, leading to wasted processing time on invalid documents.

## Fixes Implemented

### 1. Enhanced `_detect_anomalies_for_document()` Method

**Location**: `backend/app/services/extraction_orchestrator.py`

**Changes**:
- ✅ Added support for `rent_roll` and `mortgage_statement` document types
- ✅ Replaced `print()` with proper `logger` calls
- ✅ Added comprehensive validation before processing:
  - Checks for `period_id` existence
  - Validates period exists in database
  - Validates extraction status is 'completed'
- ✅ Changed silent returns to raise `ValueError` with descriptive messages
- ✅ Improved exception handling: re-raises exceptions so batch task can track failures
- ✅ Added success logging when detection completes

**Before**:
```python
def _detect_anomalies_for_document(self, upload: DocumentUpload):
    try:
        period = self.db.query(FinancialPeriod).filter(...).first()
        if not period:
            return  # Silent failure
        
        if upload.document_type == 'income_statement':
            self._detect_income_statement_anomalies(...)
        elif upload.document_type == 'balance_sheet':
            self._detect_balance_sheet_anomalies(...)
        elif upload.document_type == 'cash_flow':
            self._detect_cash_flow_anomalies(...)
        # Missing rent_roll and mortgage_statement!
    except Exception as e:
        print(f"⚠️  Anomaly detection error: {str(e)}")  # Poor logging
```

**After**:
```python
def _detect_anomalies_for_document(self, upload: DocumentUpload):
    # Validate period_id exists
    if not upload.period_id:
        error_msg = f"Document {upload.id}: Missing period_id"
        logger.warning(error_msg)
        raise ValueError(error_msg)
    
    # Validate period exists
    period = self.db.query(FinancialPeriod).filter(...).first()
    if not period:
        error_msg = f"Document {upload.id}: Period {upload.period_id} not found"
        logger.warning(error_msg)
        raise ValueError(error_msg)
    
    # Validate extraction status
    if upload.extraction_status != 'completed':
        error_msg = f"Document {upload.id}: Extraction status is '{upload.extraction_status}'"
        logger.info(error_msg)
        raise ValueError(error_msg)
    
    # Detect anomalies - now includes all document types
    if upload.document_type == 'income_statement':
        self._detect_income_statement_anomalies(...)
    elif upload.document_type == 'balance_sheet':
        self._detect_balance_sheet_anomalies(...)
    elif upload.document_type == 'cash_flow':
        self._detect_cash_flow_anomalies(...)
    elif upload.document_type == 'rent_roll':  # ✅ Added
        self._detect_rent_roll_anomalies(...)
    elif upload.document_type == 'mortgage_statement':  # ✅ Added
        self._detect_mortgage_statement_anomalies(...)
    else:
        raise ValueError(f"Unsupported document type '{upload.document_type}'")
    
    logger.info(f"Document {upload.id}: Anomaly detection completed successfully")
```

### 2. Enhanced Individual Detection Methods

**Location**: `backend/app/services/extraction_orchestrator.py`

**Methods Updated**:
- `_detect_income_statement_anomalies()`
- `_detect_balance_sheet_anomalies()`
- `_detect_cash_flow_anomalies()`
- `_detect_rent_roll_anomalies()`
- `_detect_mortgage_statement_anomalies()`

**Changes**:
- ✅ Replaced silent returns with `ValueError` exceptions
- ✅ Added descriptive logging for each failure scenario:
  - No extracted data found
  - Insufficient historical data

**Before**:
```python
if not current_data:
    return  # Silent failure

if len(historical_periods) < 1:
    return  # Silent failure
```

**After**:
```python
if not current_data:
    logger.warning(f"Income statement {upload.id}: No extracted data found")
    raise ValueError(f"No extracted income statement data found for document {upload.id}")

if len(historical_periods) < 1:
    logger.info(f"Income statement {upload.id}: Insufficient historical data")
    raise ValueError(f"Insufficient historical data for document {upload.id}")
```

### 3. Enhanced Batch Reprocessing Task

**Location**: `backend/app/tasks/batch_reprocessing_tasks.py`

**Changes**:
- ✅ Added pre-validation before processing each document:
  - Checks extraction status
  - Validates `period_id` exists
  - Validates period exists in database
- ✅ Separated `skipped` count from `failed` count
- ✅ Improved error tracking with detailed error information
- ✅ Better exception handling: distinguishes between validation errors (skipped) and processing errors (failed)
- ✅ Added rollback on errors to prevent partial commits
- ✅ Enhanced results summary with error details

**Before**:
```python
for doc in chunk:
    try:
        orchestrator._detect_anomalies_for_document(doc)
        successful += 1
    except Exception as e:
        logger.error(f"Error processing document {doc.id}: {str(e)}")
        failed += 1  # All errors counted as failures
```

**After**:
```python
for doc in chunk:
    try:
        # Pre-validate document
        if doc.extraction_status != 'completed':
            validation_error = f"Extraction status is '{doc.extraction_status}'"
        elif not doc.period_id:
            validation_error = "Missing period_id"
        elif not db.query(FinancialPeriod).filter(...).first():
            validation_error = f"Period {doc.period_id} not found"
        
        if validation_error:
            logger.warning(f"Document {doc.id}: Skipping - {validation_error}")
            skipped += 1  # ✅ Separate tracking
            error_details.append({...})  # ✅ Track reason
            continue
        
        # Process document
        orchestrator._detect_anomalies_for_document(doc)
        db.commit()  # ✅ Commit after success
        successful += 1
        
    except ValueError as e:
        # Validation errors - skip
        logger.warning(f"Document {doc.id}: Validation error - {str(e)}")
        skipped += 1
        db.rollback()  # ✅ Rollback on error
        continue
        
    except Exception as e:
        # Processing errors - fail
        logger.error(f"Document {doc.id}: Processing error - {str(e)}", exc_info=True)
        failed += 1
        db.rollback()  # ✅ Rollback on error
        continue
```

## Benefits

1. **Complete Document Type Coverage**: All document types (income_statement, balance_sheet, cash_flow, rent_roll, mortgage_statement) are now supported.

2. **Better Error Tracking**: 
   - Validation errors are tracked separately as "skipped"
   - Processing errors are tracked as "failed"
   - Detailed error information stored in results summary

3. **Improved Logging**: 
   - All failures are properly logged with context
   - Success cases are logged for audit trail
   - Error details include document ID, file name, and specific reason

4. **Data Integrity**: 
   - Rollback on errors prevents partial commits
   - Explicit commits after successful processing

5. **Better Diagnostics**: 
   - Error details in batch job results_summary
   - Clear distinction between validation and processing errors
   - Logs provide actionable information for troubleshooting

## Testing Recommendations

1. **Run Bulk Re-Run Again**: Execute the bulk anomaly re-run and verify:
   - All document types are processed
   - Skipped documents are properly categorized
   - Failed documents have detailed error messages
   - Results summary contains error details

2. **Check Logs**: Review application logs for:
   - Warning messages for skipped documents
   - Error messages for failed documents
   - Success messages for completed documents

3. **Verify Database**: Check that:
   - No partial anomaly detections are created
   - Batch job results_summary contains error_details
   - Skipped and failed counts match expectations

## Migration Notes

- **No Database Changes Required**: All fixes are code-level improvements
- **Backward Compatible**: Existing anomaly detection continues to work
- **No Breaking Changes**: API endpoints remain unchanged

## Next Steps

1. Deploy the fixes to the environment
2. Run a test bulk re-run on a small subset of documents
3. Verify error tracking and logging work correctly
4. Run full bulk re-run and monitor results
5. Review error_details in results_summary to identify any remaining issues

