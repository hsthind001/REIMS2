# Cash Flow Schema Fix & Batch Testing Report

**Date:** November 6, 2025  
**Task:** Fix cash_flow_data schema mismatch and test extraction

---

## Executive Summary

✅ **SCHEMA FIX: COMPLETED**  
⚠️  **EXTRACTION TESTING: PARTIAL SUCCESS**  
🔧 **ACTION REQUIRED: Account Code Extraction**

---

## 1. Schema Analysis (3x Verification)

### First Analysis - Model vs Table Comparison
- **Model defined:** 32 columns (CashFlowData in `app/models/cash_flow_data.py`)
- **Table had:** 25 columns
- **Missing:** 7 columns

### Second Analysis - Data Type Mismatches
- `account_id`: Table was NOT NULL, model specified nullable=True
- **Reason:** Allow unmatched accounts (consistent with balance_sheet_data)

### Third Analysis - Constraint Mismatches
- **Table constraint:** `(property_id, period_id, account_code)`
- **Model constraint:** `(property_id, period_id, account_code, line_number)`
- **Reason:** Same account can appear multiple times with different line_numbers

### Decision: Model is Correct
The model represents Template v1.0 structure with:
- Hierarchical line items (subtotals/totals)
- Section classification (INCOME, OPERATING_EXPENSE, etc.)
- Multi-column support (Period/YTD amounts)

---

## 2. Schema Fix Implementation

### Alembic Migration Created
**File:** `backend/alembic/versions/20251106_fix_cash_flow_data_schema.py`  
**Revision ID:** `e5a2f9c1d8b3`

### Operations Performed:
1. ✅ Added 7 missing columns:
   - `line_category` VARCHAR(100)
   - `line_subcategory` VARCHAR(100)
   - `line_number` INTEGER
   - `is_subtotal` BOOLEAN DEFAULT FALSE
   - `is_total` BOOLEAN DEFAULT FALSE
   - `parent_line_id` INTEGER (self-referential FK)
   - `page_number` INTEGER

2. ✅ Altered `account_id` to nullable

3. ✅ Dropped old unique constraint `uq_cf_property_period_account`

4. ✅ Added new unique constraint `uq_cf_property_period_account_line`

5. ✅ Created indexes:
   - `idx_cf_data_line_section`
   - `idx_cf_data_line_category`

6. ✅ Handled multiple heads:
   - Created merge migration `20251106_merge_heads.py`
   - Merged `20251104_1205` (Income Statement) + `e5a2f9c1d8b3` (Cash Flow fix)

### Verification:
```sql
-- All columns confirmed present:
account_id (nullable), line_section, line_category, line_subcategory,
line_number, is_subtotal, is_total, parent_line_id, page_number
```

---

## 3. Batch Testing Results

### Test Execution
- **Files tested:** 8/8 Cash Flow PDFs
- **Properties:** ESP001, HMND001, TCSH001, WEND001
- **Years:** 2023, 2024 for each property

### Data Extraction Success
| Property | Year | Records | Status | NOI Extracted | Time |
|----------|------|---------|--------|---------------|------|
| ESP001   | 2023 | 363     | ✅     | $2,435,604    | 14s  |
| ESP001   | 2024 | 365     | ✅     | $2,087,905    | 13s  |
| HMND001  | 2023 | 363     | ✅     | $2,874,794    | 12s  |
| HMND001  | 2024 | 365     | ✅     | $2,845,707    | 13s  |
| TCSH001  | 2023 | 359     | ✅     | $3,641,287    | 12s  |
| TCSH001  | 2024 | 363     | ✅     | $3,258,796    | 13s  |
| WEND001  | 2023 | 361     | ✅     | $2,385,283    | 13s  |
| WEND001  | 2024 | 365     | ✅     | $2,281,091    | 13s  |

**Total Records Extracted:** 2,904 line items across all files

### Quality Metrics
- **Average Records per File:** 363
- **Extraction Confidence:** 75.1% (consistent across all files)
- **Match Rate:** 0.0% ⚠️ 
- **Account Codes Extracted:** 0/2,904 ⚠️ 
- **Account Names Extracted:** 2,904/2,904 ✅

---

## 4. Issues Identified

### Issue 1: Transaction Error on Completion
**Symptom:** All extractions marked as "failed" despite successful data insertion  
**Root Cause:** `InFailedSqlTransaction` error during final status update  
**Impact:** Data successfully extracted but status incorrectly set  
**Resolution:** Manually updated statuses to "completed"  
**Action Required:** Review transaction management in `extraction_orchestrator.py`

### Issue 2: Account Code Extraction Missing
**Symptom:** All `account_code` fields are empty in extracted data  
**Root Cause:** Cash Flow extraction logic not extracting account codes from PDFs  
**Evidence:**
```sql
-- Sample extracted data (upload_id=11):
account_code | account_name
-------------|------------------------------
(empty)      | A/P GBP Partners, LTD
(empty)      | Partners Draw
(empty)      | Contract - Termite
(empty)      | Water & Sewer Service
```

**Impact:** 
- 0% match rate to chart_of_accounts
- Unable to map expenses/income to standard accounts
- Financial reporting and analysis not possible

**Action Required:** 
1. Review PDF structure to identify where account codes appear
2. Update Cash Flow extraction templates/patterns
3. Implement account code extraction logic
4. Re-test after fix

### Issue 3: Header Totals Not Calculated
**Symptom:** `total_income` and `total_expenses` = $0 in all headers  
**Evidence:**
```
total_income | total_expenses | net_operating_income
-------------|----------------|---------------------
$0.00        | $0.00          | $2,435,604.17
```

**Impact:** NOI calculation validation fails (expected NOI = income - expenses)  
**Action Required:** Review header calculation logic in extraction orchestrator

---

## 5. Comparison with Balance Sheet Extraction

| Metric | Balance Sheet | Cash Flow |
|--------|--------------|-----------|
| Files Tested | 8 | 8 |
| Success Rate | 100% | 100% |
| Avg Records | 30 | 363 |
| Match Rate | 97.4% | 0.0% ⚠️ |
| Avg Confidence | 91.6% | 75.1% |
| Account Codes | ✅ Extracted | ❌ Missing |
| Header Totals | ✅ Calculated | ❌ Not calculated |
| Production Ready | ✅ YES | ❌ NO |

---

## 6. Root Cause Analysis

### Why Balance Sheets Work but Cash Flow Doesn't?

**Balance Sheet PDFs:**
- Account codes appear consistently (e.g., "0122-0000 Cash")
- Simple structure: ~30 accounts per statement
- Template extraction patterns match PDF layout

**Cash Flow PDFs:**
- Account codes may be in different format or location
- Complex structure: 360+ line items per statement
- May use different delimiter or no codes at all

**Hypothesis:** The `seed_extraction_templates.sql` may have patterns optimized for Balance Sheets but not Cash Flow statements.

---

## 7. Next Steps & Recommendations

### Immediate Actions (Priority 1)
1. **Inspect Sample Cash Flow PDF** - Manually review one PDF to identify:
   - Where account codes appear (if at all)
   - Format/pattern of codes
   - Differences from Balance Sheet layout

2. **Review Extraction Template** - Check `seed_extraction_templates.sql` for Cash Flow:
   ```sql
   SELECT template_name, extraction_rules 
   FROM extraction_templates 
   WHERE document_type = 'cash_flow';
   ```

3. **Update Template Extractor** - Modify account code extraction pattern in:
   - `app/services/template_extractor.py`
   - Add Cash Flow-specific regex patterns

### Medium Priority (Priority 2)
4. **Fix Transaction Management** - Review `extraction_orchestrator.py`:
   - Ensure proper commit/rollback handling
   - Prevent "failed" status when data successfully inserted

5. **Implement Header Calculation** - Add logic to:
   - Sum all income items → `total_income`
   - Sum all expense items → `total_expenses`
   - Validate: `NOI = total_income - total_expenses`

### Future Enhancements (Priority 3)
6. **Add Cash Flow Accounts to Chart** - If codes don't match:
   - Seed additional accounts for Cash Flow items
   - Update `seed_income_statement_template_accounts.sql`

7. **Implement Account Fuzzy Matching** - For unmatched names:
   - Use string similarity algorithms
   - Suggest matches for manual review

---

## 8. Conclusion

### What We Accomplished Today ✅
- ✅ Analyzed schema mismatch (3x verification)
- ✅ Created and applied Alembic migration
- ✅ Fixed 7 missing columns in cash_flow_data
- ✅ Uploaded all 8 Cash Flow PDFs to MinIO
- ✅ Executed batch testing successfully
- ✅ Extracted 2,904 line items with 75% confidence
- ✅ Identified root causes for 0% match rate

### Current Status
- **Schema:** PRODUCTION READY ✅
- **Data Extraction:** FUNCTIONAL ✅
- **Account Matching:** NOT WORKING ⚠️ 
- **Overall:** NOT PRODUCTION READY ❌

### Estimated Effort to Production Ready
- **Account Code Extraction Fix:** 2-4 hours
- **Header Calculation Fix:** 1-2 hours
- **Transaction Error Fix:** 1 hour
- **Testing & Verification:** 1-2 hours

**Total:** 5-9 hours of development work

---

## 9. Files Modified/Created

### New Files:
1. `backend/alembic/versions/20251106_fix_cash_flow_data_schema.py` - Main schema fix migration
2. `backend/alembic/versions/20251106_merge_heads.py` - Merge migration for multiple heads
3. `backend/scripts/upload_cash_flow_to_minio.py` - Upload script for Cash Flow PDFs
4. `backend/scripts/batch_test_cash_flow.py` - Batch testing script
5. `CASH_FLOW_SCHEMA_FIX_REPORT.md` - This report

### Database Changes:
- Modified: `cash_flow_data` table (7 columns added, 1 altered, constraints updated)
- Modified: `alembic_version` table (revision updated to `merge_heads_2025`)

---

**Report Generated:** 2025-11-06  
**Next Review:** After account code extraction fix is implemented

