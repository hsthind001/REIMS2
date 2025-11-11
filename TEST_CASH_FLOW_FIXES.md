# Cash Flow Gap Fix - Testing Guide

**Deployment Status:** ✅ Fresh deployment complete  
**All Services:** Running  
**Ready for:** Testing

---

## ✅ Pre-Testing Verification

### Step 1: Verify All Services are Running

```bash
docker ps --filter "name=reims" --format "table {{.Names}}\t{{.Status}}"
```

**Expected:** 8 containers running (frontend, backend, celery-worker, flower, postgres, redis, minio, pgadmin)

### Step 2: Check Database Migrations

```bash
docker exec reims-backend alembic current
```

**Expected:** Shows latest revision IDs including our new migrations:
- `cf001aadd001` (Cash Flow constraint fix)
- `cf002std0002` (Standardized fields)

### Step 3: Verify Cash Flow Accounts Loaded

```bash
docker exec -it reims-postgres psql -U reims -d reims -c \
  "SELECT COUNT(*) as total_cf_accounts FROM chart_of_accounts WHERE 'cash_flow' = ANY(document_types);"
```

**Expected:** ~154 accounts (was 29)

### Step 4: Check New Constraint

```bash
docker exec -it reims-postgres psql -U reims -d reims -c \
  "\d cash_flow_data" | grep -A 10 "Indexes:"
```

**Expected:** Should show `uq_cf_property_period_account_name_line` constraint

### Step 5: Check New Columns

```bash
docker exec -it reims-postgres psql -U reims -d reims -c \
  "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'cash_flow_data' AND column_name IN ('account_level', 'extraction_method');"
```

**Expected:** 2 rows showing the new columns

---

## 🧪 Main Testing: Re-Extract Cash Flow Documents

### Test 1: Upload Cash Flow Documents via Swagger UI

1. **Open Swagger UI:**
   ```
   http://localhost:8000/docs
   ```

2. **Navigate to:** `POST /api/v1/documents/upload`

3. **Upload Cash Flow PDFs:**
   - Select 8 cash flow PDF files from MinIO or local storage
   - For each file:
     - Choose property (ESP001, HMND001, TCSH001, WEND001)
     - Choose period (2023 or 2024)
     - Choose document_type: "cash_flow"
     - Upload

4. **Monitor Upload:**
   ```bash
   # Watch extraction logs
   docker logs reims-celery-worker -f
   ```

5. **Expected Logs:**
   - "🔍 Matching X Cash Flow accounts to chart_of_accounts..."
   - "⚠️ Deduplication: X → Y items (Z duplicates removed)" (if any duplicates)
   - "✅ Cash Flow Account Matching: X/Y (Z%)"
   - **Match rate should be 90-95%+** (was 53.64%)

### Test 2: Check Extraction Results

```bash
docker exec -it reims-postgres psql -U reims -d reims
```

```sql
-- Check extraction status
SELECT 
    property_code,
    document_type,
    extraction_status,
    COUNT(*) as doc_count
FROM document_uploads du
JOIN properties p ON du.property_id = p.id
WHERE document_type = 'cash_flow'
GROUP BY property_code, document_type, extraction_status;

-- Expected: Most should show 'completed' status
```

### Test 3: Verify Match Rate Improvement

```sql
-- Overall Cash Flow match rate
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN account_id IS NOT NULL THEN 1 END) as matched_records,
    ROUND(COUNT(CASE WHEN account_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as match_rate_percent
FROM cash_flow_data;

-- Expected: 90-95%+ match rate (was 53.64%)
```

### Test 4: Verify Hierarchical Accounts Work

```sql
-- Check for accounts with same code but different names
SELECT 
    account_code,
    account_name,
    COUNT(*) as record_count,
    SUM(period_amount) as total_amount
FROM cash_flow_data
WHERE account_code != ''
GROUP BY account_code, account_name
HAVING COUNT(DISTINCT account_name) OVER (PARTITION BY account_code) > 1
ORDER BY account_code, account_name
LIMIT 20;

-- Expected: Shows hierarchical accounts like:
-- "Base Rentals", "Base Rentals - Retail", "Base Rentals - Office"
```

### Test 5: Verify Zero Data Loss (No Duplicates Rejected)

```sql
-- Check that no duplicates exist (constraint working)
SELECT 
    property_id,
    period_id,
    account_code,
    account_name,
    line_number,
    COUNT(*)
FROM cash_flow_data
GROUP BY property_id, period_id, account_code, account_name, line_number
HAVING COUNT(*) > 1;

-- Expected: 0 rows (no duplicates)
```

### Test 6: Check New Fields Are Populated

```sql
-- Check account_level and extraction_method
SELECT 
    account_level,
    extraction_method,
    COUNT(*) as count
FROM cash_flow_data
GROUP BY account_level, extraction_method;

-- Note: May be NULL initially (populated in future extractions)
```

---

## 📊 Expected Results Summary

| Test | Before Fix | After Fix | Status |
|------|-----------|-----------|---------|
| Chart of Accounts | 29 CF accounts | ~154 CF accounts | ⏳ Test |
| Match Rate | 53.64% | 90-95%+ | ⏳ Test |
| Hierarchical Support | ❌ Not working | ✅ Working | ⏳ Test |
| Deduplication | ❌ Not implemented | ✅ Implemented | ⏳ Test |
| Unique Constraint | Missing account_name | Includes account_name | ⏳ Test |
| Standardized Fields | Missing | Added | ⏳ Test |

---

## 🔍 Detailed Match Rate Analysis

### By Property and Year

```sql
SELECT 
    p.property_code,
    fp.period_year,
    COUNT(*) as total_records,
    COUNT(CASE WHEN account_id IS NOT NULL THEN 1 END) as matched,
    ROUND(COUNT(CASE WHEN account_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as match_rate
FROM cash_flow_data cfd
JOIN properties p ON cfd.property_id = p.id
JOIN financial_periods fp ON cfd.period_id = fp.id
GROUP BY p.property_code, fp.period_year
ORDER BY p.property_code, fp.period_year;
```

### Top Unmatched Accounts (If Any)

```sql
SELECT 
    account_code,
    account_name,
    COUNT(*) as occurrences,
    AVG(extraction_confidence) as avg_confidence
FROM cash_flow_data
WHERE account_id IS NULL
GROUP BY account_code, account_name
ORDER BY COUNT(*) DESC
LIMIT 20;
```

---

## 🎯 Success Criteria Checklist

- [ ] All 8 containers running
- [ ] Migrations applied successfully
- [ ] ~154 Cash Flow accounts in database
- [ ] New constraint includes account_name
- [ ] New columns (account_level, extraction_method) exist
- [ ] 8 Cash Flow documents uploaded successfully
- [ ] Extraction status: "completed" for all
- [ ] Match rate improved to 90-95%+
- [ ] Hierarchical accounts (same code, different names) working
- [ ] No duplicate key violations
- [ ] Zero data loss verified
- [ ] Deduplication working (check logs)

---

## 🐛 Troubleshooting

### Issue: Match Rate Still Low

**Check:**
```sql
-- See which accounts are still unmatched
SELECT account_name, COUNT(*) 
FROM cash_flow_data 
WHERE account_id IS NULL 
GROUP BY account_name 
ORDER BY COUNT(*) DESC 
LIMIT 10;
```

**Solution:** May need to add more property-specific accounts

### Issue: Duplicate Key Violations

**Check:**
```bash
docker logs reims-celery-worker | grep "duplicate key"
```

**Solution:** Should not happen with new constraint; if it does, check the constraint was applied:
```sql
\d cash_flow_data
```

### Issue: Extraction Stuck in "processing"

**Check:**
```bash
docker logs reims-celery-worker -f
```

**Solution:** Restart celery worker:
```bash
docker compose restart celery-worker
```

---

## 📈 Performance Comparison

### Before Fix (Nov 6, 2025)
```
Match Rate: 53.64%
Unmatched: 46.36% of records
Chart Accounts: 29
Hierarchical: Not working
Duplicates: Potential issues
```

### After Fix (Nov 7, 2025 - Expected)
```
Match Rate: 90-95%+
Unmatched: 5-10% of records
Chart Accounts: 154
Hierarchical: Working ✅
Duplicates: Prevented ✅
```

---

## 🚀 Next Steps After Testing

1. **If match rate is 90%+:** Success! Document results
2. **If match rate is 70-89%:** Good progress, identify remaining unmatched accounts
3. **If match rate is <70%:** Investigate logs and unmatched accounts

### Document Results

Create a test results file:
```bash
# Export match rate stats
docker exec -it reims-postgres psql -U reims -d reims -c \
  "COPY (SELECT * FROM cash_flow_data WHERE account_id IS NULL) TO STDOUT CSV HEADER" \
  > remaining_unmatched_accounts.csv
```

---

**Ready to Test!** Follow the steps above to verify all fixes are working. 🎉

