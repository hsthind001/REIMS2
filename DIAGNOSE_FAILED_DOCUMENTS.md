# Diagnostic Report: 98 Failed Documents in Bulk Re-Run Anomalies

## Analysis of Failure Points

Based on the code review of `_detect_anomalies_for_document` in `extraction_orchestrator.py`, here are the most likely reasons for document failures:

### 1. **Missing Period (period_id is None or Invalid)**
**Location:** Line 1804-1809
```python
period = self.db.query(FinancialPeriod).filter(
    FinancialPeriod.id == upload.period_id
).first()

if not period:
    return  # Silent failure - no error logged
```

**Impact:** If a document's `period_id` is NULL or points to a non-existent period, the method silently returns without processing. This is a **silent failure** that won't be logged.

**Solution:** Check documents with NULL or invalid period_id values.

---

### 2. **Insufficient Historical Data**
**Location:** Line 1855-1856 (for income statements)
```python
if len(historical_periods) < 1:  # Need at least 1 historical period
    return  # Silent failure
```

**Impact:** Documents for properties with no historical periods (new properties or first-time uploads) will fail silently.

**Solution:** These documents should be skipped or handled differently for new properties.

---

### 3. **Missing Extracted Data**
**Location:** Line 1843-1844 (for income statements)
```python
current_data = self.db.query(IncomeStatementData).filter(
    IncomeStatementData.property_id == upload.property_id,
    IncomeStatementData.period_id == upload.period_id
).all()

if not current_data:
    return  # Silent failure
```

**Impact:** If extraction didn't create any data records, anomaly detection has nothing to analyze.

**Solution:** Check documents where extraction_status is "completed" but no data records exist.

---

### 4. **Exception Handling (Generic Catch-All)**
**Location:** Line 1822-1824
```python
except Exception as e:
    # Log error but don't fail extraction
    print(f"⚠️  Anomaly detection error: {str(e)}")
```

**Impact:** Any unexpected error (database connection issues, data type errors, missing dependencies) will be caught but only printed to stdout, not logged properly. The batch job will count this as a failure.

**Common exceptions:**
- Database connection timeouts
- Missing required fields in data
- Type conversion errors (Decimal, float, date parsing)
- Missing dependencies (Prophet, statsmodels)
- Memory errors for large datasets

---

### 5. **Document Type Not Supported**
**Location:** Line 1815-1821
```python
if upload.document_type == 'income_statement':
    self._detect_income_statement_anomalies(...)
elif upload.document_type == 'balance_sheet':
    self._detect_balance_sheet_anomalies(...)
elif upload.document_type == 'cash_flow':
    self._detect_cash_flow_anomalies(...)
# No else clause - rent_roll and mortgage_statement are not handled here!
```

**Impact:** Documents of type `rent_roll` or `mortgage_statement` will not trigger any anomaly detection, but the method returns successfully (no error). However, if called from batch processing, it might still count as processed but with 0 anomalies.

**Note:** The batch task calls `orchestrator._detect_anomalies_for_document(doc)` which doesn't handle rent_roll or mortgage_statement.

---

## Recommended Diagnostic Queries

Run these SQL queries to identify the root cause:

### Query 1: Check for documents with missing periods
```sql
SELECT 
    du.id,
    du.document_type,
    du.property_id,
    du.period_id,
    du.extraction_status,
    CASE WHEN fp.id IS NULL THEN 'MISSING PERIOD' ELSE 'OK' END as period_status
FROM document_uploads du
LEFT JOIN financial_periods fp ON du.period_id = fp.id
WHERE du.extraction_status = 'completed'
  AND (du.period_id IS NULL OR fp.id IS NULL)
ORDER BY du.id DESC
LIMIT 100;
```

### Query 2: Check for documents with no extracted data
```sql
-- Income Statements
SELECT 
    du.id,
    du.document_type,
    du.property_id,
    du.period_id,
    COUNT(isd.id) as data_records
FROM document_uploads du
LEFT JOIN income_statement_data isd ON (
    isd.property_id = du.property_id 
    AND isd.period_id = du.period_id
)
WHERE du.document_type = 'income_statement'
  AND du.extraction_status = 'completed'
GROUP BY du.id, du.document_type, du.property_id, du.period_id
HAVING COUNT(isd.id) = 0
LIMIT 50;

-- Balance Sheets
SELECT 
    du.id,
    du.document_type,
    du.property_id,
    du.period_id,
    COUNT(bsd.id) as data_records
FROM document_uploads du
LEFT JOIN balance_sheet_data bsd ON (
    bsd.property_id = du.property_id 
    AND bsd.period_id = du.period_id
)
WHERE du.document_type = 'balance_sheet'
  AND du.extraction_status = 'completed'
GROUP BY du.id, du.document_type, du.property_id, du.period_id
HAVING COUNT(bsd.id) = 0
LIMIT 50;

-- Cash Flow
SELECT 
    du.id,
    du.document_type,
    du.property_id,
    du.period_id,
    COUNT(cfd.id) as data_records
FROM document_uploads du
LEFT JOIN cash_flow_data cfd ON (
    cfd.property_id = du.property_id 
    AND cfd.period_id = du.period_id
)
WHERE du.document_type = 'cash_flow'
  AND du.extraction_status = 'completed'
GROUP BY du.id, du.document_type, du.property_id, du.period_id
HAVING COUNT(cfd.id) = 0
LIMIT 50;
```

### Query 3: Check for documents with no historical periods
```sql
SELECT 
    du.id,
    du.document_type,
    du.property_id,
    du.period_id,
    fp.period_end_date,
    COUNT(hp.id) as historical_period_count
FROM document_uploads du
JOIN financial_periods fp ON du.period_id = fp.id
LEFT JOIN financial_periods hp ON (
    hp.property_id = du.property_id
    AND hp.id != du.period_id
    AND hp.period_end_date >= (fp.period_start_date - INTERVAL '365 days')
)
WHERE du.extraction_status = 'completed'
  AND du.document_type IN ('income_statement', 'balance_sheet', 'cash_flow')
GROUP BY du.id, du.document_type, du.property_id, du.period_id, fp.period_end_date
HAVING COUNT(hp.id) < 1
LIMIT 50;
```

### Query 4: Check for unsupported document types
```sql
SELECT 
    du.id,
    du.document_type,
    du.property_id,
    du.period_id,
    du.extraction_status
FROM document_uploads du
WHERE du.extraction_status = 'completed'
  AND du.document_type IN ('rent_roll', 'mortgage_statement')
ORDER BY du.id DESC
LIMIT 50;
```

---

## Recommended Fixes

### Fix 1: Improve Error Logging
Update `_detect_anomalies_for_document` to log specific failure reasons:

```python
def _detect_anomalies_for_document(self, upload: DocumentUpload):
    """Detect anomalies in extracted financial data for a document."""
    try:
        from app.models.financial_period import FinancialPeriod
        import logging
        logger = logging.getLogger(__name__)
        
        # Get the period for this upload
        period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.id == upload.period_id
        ).first()
        
        if not period:
            logger.warning(f"Document {upload.id}: Missing period (period_id={upload.period_id})")
            return
        
        # Initialize anomaly detector
        detector = StatisticalAnomalyDetector(self.db)
        
        # Detect anomalies based on document type
        if upload.document_type == 'income_statement':
            self._detect_income_statement_anomalies(upload, period, detector)
        elif upload.document_type == 'balance_sheet':
            self._detect_balance_sheet_anomalies(upload, period, detector)
        elif upload.document_type == 'cash_flow':
            self._detect_cash_flow_anomalies(upload, period, detector)
        elif upload.document_type in ('rent_roll', 'mortgage_statement'):
            logger.info(f"Document {upload.id}: Anomaly detection not implemented for {upload.document_type}")
        else:
            logger.warning(f"Document {upload.id}: Unknown document type '{upload.document_type}'")
            
    except Exception as e:
        logger.error(f"Document {upload.id}: Anomaly detection error: {str(e)}", exc_info=True)
        raise  # Re-raise to be caught by batch processor
```

### Fix 2: Handle Missing Historical Data Gracefully
For new properties, consider using property-class baselines or industry averages instead of requiring historical data.

### Fix 3: Add Validation Before Processing
In the batch task, validate documents before processing:

```python
# In batch_reprocessing_tasks.py, before calling _detect_anomalies_for_document:
if not doc.period_id:
    logger.warning(f"Document {doc.id}: Skipping - no period_id")
    skipped += 1
    continue

period = db.query(FinancialPeriod).filter(FinancialPeriod.id == doc.period_id).first()
if not period:
    logger.warning(f"Document {doc.id}: Skipping - period {doc.period_id} not found")
    skipped += 1
    continue
```

---

## Next Steps

1. **Run the diagnostic queries** to identify which category of failures is most common
2. **Check application logs** for specific error messages (grep for "Anomaly detection error")
3. **Review the batch job results_summary** JSON for any error details
4. **Implement improved logging** to capture failure reasons
5. **Add validation** in the batch task to skip invalid documents gracefully

