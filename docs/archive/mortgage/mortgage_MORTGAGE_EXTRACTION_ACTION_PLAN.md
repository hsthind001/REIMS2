# MORTGAGE EXTRACTION - 100% DATA QUALITY ACTION PLAN

## 📊 CURRENT STATUS (2025-12-25)

### ✅ Completed Steps:
1. ✅ Analyzed Claude solution patterns (35+ fields with comprehensive regex)
2. ✅ Compared with REIMS2 solution (26 default patterns + structured parsing)
3. ✅ Identified gaps: **Only 15.4% completeness** (6/39 fields extracted)
4. ✅ Created comprehensive field patterns combining both solutions (27 fields)
5. ✅ Updated ExtractionTemplate with 17 core field patterns
6. ✅ Created Wells Fargo lender record in database
7. ✅ Identified root cause: Template patterns incomplete + structured parsing not fully utilized

### ⚠️ Current Issues:
- ❌ All 11 mortgage statements were deleted during re-extraction attempt
- ❌ Template update only kept 17/27 patterns (database limitation or JSONB issue)
- ⚠️ Need to re-extract all documents from MinIO PDFs
- ⚠️ Structured table parsing needs verification

---

## 🎯 ACTION PLAN TO ACHIEVE 100% DATA QUALITY

### **STEP 1: Verify Template Patterns (✅ DONE)**

**Current Template Fields (17 patterns):**
```
✓ loan_number (5 patterns)
✓ statement_date (5 patterns)
✓ payment_due_date (2 patterns)
✓ maturity_date (3 patterns)
✓ principal_balance (5 patterns)
✓ tax_escrow_balance (3 patterns)
✓ insurance_escrow_balance (3 patterns)
✓ reserve_balance (3 patterns)
✓ interest_rate (3 patterns)
✓ principal_due (4 patterns)
✓ interest_due (4 patterns)
✓ tax_escrow_due (3 patterns)
✓ insurance_escrow_due (3 patterns)
✓ reserve_due (3 patterns)
✓ total_payment_due (3 patterns)
✓ ytd_principal_paid (3 patterns)
✓ ytd_interest_paid (3 patterns)
```

**Missing Critical Fields (22+ fields):**
```
✗ borrower_name
✗ property_address
✗ other_escrow_balance
✗ suspense_balance
✗ late_fees
✗ other_fees
✗ ytd_taxes_disbursed
✗ ytd_insurance_disbursed
✗ ytd_reserve_disbursed
✗ original_loan_amount
✗ loan_term_months
✗ payment_frequency
✗ amortization_type
... and all calculated fields
```

---

### **STEP 2: Re-Upload Mortgage Statements via REIMS2 UI** ⭐ **NEXT ACTION**

Since all mortgage data was deleted, you need to trigger extraction again through the REIMS2 UI.

**Option A: Re-Upload Documents (Recommended)**

1. **Navigate to REIMS2 UI:** http://localhost:5173
2. **Go to Property:** ESP001-Eastern-Shore-Plaza
3. **Go to Documents Section**
4. **Delete existing uploads** (if they still exist but have no data)
5. **Re-upload all 11 mortgage PDFs** from MinIO:
   ```
   reims/ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_01_Mortgage_Statement.pdf
   reims/ESP001-Eastern-Shore-Plaza/2023/mortgage-statement/ESP_2023_02_Mortgage_Statement.pdf
   ... (all 11 PDFs)
   ```
6. **Select Document Type:** "Mortgage Statement"
7. **Assign to correct period:** January 2023, February 2023, etc.
8. **Click Upload** - Extraction will trigger automatically

**Option B: Trigger Re-Extraction via API**

If uploads still exist, you can trigger re-extraction via API:

```bash
# For each upload, call the re-extraction endpoint
for upload_id in {1..11}; do
  curl -X POST "http://localhost:8000/api/v1/uploads/$upload_id/reextract" \
    -H "Content-Type: application/json"
done
```

---

### **STEP 3: Verify Extraction uses Structured Parsing**

The REIMS2 `MortgageExtractionService` has a method called `_apply_structured_table_parsing()` (lines 247-366) that parses Wells Fargo table layouts.

**Verify it's being called:**

```python
# Check extraction service code
# Should have this flow:
1. extract_mortgage_data() called
2. Regex patterns applied first (from template)
3. _apply_structured_table_parsing() fills gaps
4. _calculate_derived_fields() adds calculated fields
```

**This is CRITICAL because:**
- Wells Fargo uses wide-spacing table layouts
- Example: `"Principal Balance                    $   22,416,794.27"`
- Regex patterns often fail on wide spacing
- Structured parsing extracts by position instead

---

### **STEP 4: Monitor Extraction Quality**

After re-uploading, check extraction quality:

```sql
-- Query to check completeness
SELECT
    statement_date,
    loan_number,
    principal_balance,
    total_payment_due,
    tax_escrow_balance,
    insurance_escrow_balance,
    reserve_balance,
    principal_due,
    interest_due,
    ytd_principal_paid,
    ytd_interest_paid,
    extraction_confidence
FROM mortgage_statement_data
WHERE property_id = 1
ORDER BY statement_date;
```

**Success Criteria:**
- ✅ All 11 statements extracted
- ✅ `extraction_confidence` >= 90%
- ✅ `total_payment_due` is NOT NULL
- ✅ All escrow balances extracted
- ✅ All YTD fields extracted
- ✅ Borrower name and property address extracted

---

### **STEP 5: If Completeness Still < 90%, Apply Enhanced Patterns**

If extraction is still incomplete after re-upload, we need to add the missing fields to the template manually.

**Create SQL script to update template:**

```sql
-- Update extraction template with all 27 comprehensive patterns
UPDATE extraction_templates
SET template_structure = jsonb_set(
  template_structure,
  '{field_patterns}',
  '{
    "loan_number": {...},
    "borrower_name": {...},
    "property_address": {...},
    ...all 27 fields...
  }'::jsonb
)
WHERE document_type = 'mortgage_statement'
AND is_default = true;
```

---

### **STEP 6: Enable Self-Learning (Future Enhancement)**

Once extraction works at 90%+, enable self-learning:

1. **Verify MortgageLearningService is active**
   - Check `app/services/mortgage_learning_service.py`
   - Should auto-learn patterns from successful extractions

2. **Monitor learned patterns:**
   ```sql
   SELECT * FROM extraction_patterns
   WHERE lender_name = 'Wells Fargo'
   ORDER BY success_count DESC;
   ```

3. **Review and approve learned patterns periodically**

---

## 📈 EXPECTED RESULTS AFTER FIX

### Before Fix:
```
Completeness: 15.4% (6/39 fields)
Confidence: 75%
Missing Fields: 33
Status: ❌ CRITICAL
```

### After Fix:
```
Completeness: 90%+ (35+/39 fields)
Confidence: 90%+
Missing Fields: <5 (optional fields only)
Status: ✅ SUCCESS
```

---

## 🔧 TROUBLESHOOTING

### Issue: Extraction confidence < 90%

**Solution:**
1. Check PDF text extraction quality
2. Verify patterns match Wells Fargo format
3. Enable debug logging in `mortgage_extraction_service.py`
4. Review `validation_errors` table

### Issue: Fields still missing after re-extraction

**Solution:**
1. Check if `_apply_structured_table_parsing()` is being called
2. Manually test extraction on one PDF:
   ```python
   from app.services.mortgage_extraction_service import MortgageExtractionService
   service = MortgageExtractionService(db)
   result = service.extract_mortgage_data(pdf_text)
   print(result['mortgage_data'])
   ```
3. Add debug prints to see which patterns are matching

### Issue: Template patterns not saving

**Solution:**
- JSONB field might have size limit
- Split patterns into multiple templates
- Store patterns in separate `extraction_patterns` table

---

## 📝 NEXT IMMEDIATE STEPS

1. ⭐ **Re-upload all 11 mortgage PDFs** via REIMS2 UI
2. ⭐ **Verify extraction completeness** after upload
3. ⭐ **Check if total_payment_due is now populated**
4. If completeness < 90%, manually add missing patterns to template
5. Generate quality report and verify 100% success

---

## 📊 QUALITY METRICS TO TRACK

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Field Completeness | 90%+ | 0% (data deleted) | ❌ |
| Extraction Confidence | 90%+ | N/A | ❌ |
| Statements Extracted | 11/11 | 0/11 | ❌ |
| YTD Fields Extracted | 5/5 | 0/5 | ❌ |
| Payment Fields Extracted | 8/8 | 0/8 | ❌ |
| Balance Fields Extracted | 7/7 | 0/7 | ❌ |

---

## 🎯 SUCCESS DEFINITION

**100% Data Quality Achieved When:**
1. ✅ All 11 mortgage statements extracted successfully
2. ✅ Average field completeness >= 90%
3. ✅ Average extraction confidence >= 90%
4. ✅ Zero critical validation errors
5. ✅ All required fields populated (loan_number, dates, principal, payment due)
6. ✅ All escrow balances captured
7. ✅ All YTD payment fields captured
8. ✅ Borrower and property information captured

---

## 📞 SUPPORT

If you encounter issues during re-extraction:

1. Check backend logs: `docker compose logs backend`
2. Check celery worker logs: `docker compose logs celery-worker`
3. Review extraction_log table for errors
4. Check validation_errors table for specific field failures

---

## 🔗 REFERENCE FILES

- **Comprehensive Patterns:** `/home/hsthind/Documents/GitHub/REIMS2/backend/comprehensive_mortgage_fix.py`
- **REIMS2 Service:** `/home/hsthind/Documents/GitHub/REIMS2/backend/app/services/mortgage_extraction_service.py`
- **Claude Patterns:** `/home/hsthind/Downloads/files/mortgage_extractor.py`
- **Template Update Script:** `/home/hsthind/Documents/GitHub/REIMS2/backend/simple_reextract.py`

---

**Last Updated:** 2025-12-25 07:54 UTC
**Status:** Ready for re-upload and extraction
