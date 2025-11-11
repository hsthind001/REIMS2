# 🎨 REIMS2 Frontend Testing Guide - Cash Flow Fixes

**Date:** November 7, 2025  
**Purpose:** Test Cash Flow improvements via frontend UI  
**Expected:** 95%+ match rate (from 53.64%)

---

## 🚀 Quick Start

### Step 1: Access Frontend
```
http://localhost:5173
```

**You should see:** REIMS2 login/register page

---

## 👤 Authentication

### Option A: Register New Account
1. Click **"Register"** button
2. Fill in:
   - Email: `test@reims.com`
   - Username: `testuser`
   - Password: `Test1234!` (or stronger)
3. Click **"Register"**
4. You'll be auto-logged in

### Option B: Login (if account exists)
1. Enter username and password
2. Click **"Login"**

**Success:** You should see the Dashboard

---

## 📊 Dashboard Overview

After login, you should see:

### Summary Cards
- Total Properties: 5
- Documents Uploaded: X
- Completed Extractions: Y
- Pending Reviews: Z

### Property Cards
- Eastern Shore Plaza (ESP001)
- Hammond Aire (HMND001)
- The Crossing Shopping Center (TCSH001)
- Wendover Commons (WEND001)
- Test Property (TEST001)

### Recent Uploads Table
Shows recently uploaded documents with status

---

## 📄 Test 1: Upload Cash Flow Documents

### Navigate to Documents Page
1. Click **"Documents"** in navigation menu
2. You should see:
   - Upload section at top
   - Document list below

### Upload Your First Cash Flow Document

#### A. Prepare Upload
1. **Select Property** from dropdown
   - Choose: ESP001 or HMND001 or TCSH001 or WEND001
   
2. **Select Period**
   - Year: 2024 or 2023
   - Month: December (or any month)
   
3. **Select Document Type**
   - Choose: **"Cash Flow"**

#### B. Upload File
1. **Drag & Drop** PDF file into upload zone
   - OR click **"Browse"** to select file
   
2. **File Validation**
   - Must be PDF format
   - Max size: 50MB
   - Shows file name after selection

3. Click **"Upload"**

#### C. Monitor Upload
- Progress indicator appears
- Success message: "Document uploaded successfully"
- Document appears in list below with status: **"pending"**

---

## ⏳ Test 2: Monitor Extraction Progress

### Watch Status Changes

Documents go through these statuses:
1. **pending** → Document uploaded, waiting for processing
2. **processing** → Extraction in progress (Celery worker active)
3. **completed** → ✅ Extraction successful
4. **failed** → ❌ Extraction error

### Check Status
- Refresh the Documents page
- Look at **"Extraction Status"** column
- **Color codes:**
  - 🔵 Blue = pending
  - 🟡 Yellow = processing
  - 🟢 Green = completed
  - 🔴 Red = failed

### Expected Timeline
- Upload: Instant
- Processing: 30-60 seconds
- Total: 1-2 minutes per document

---

## 📊 Test 3: View Extraction Results

### Once Status = "completed"

1. **In Documents Page:**
   - Find your uploaded document
   - Status should show: ✅ **"completed"**
   - Note the **Match Rate** (if shown)

2. **Check Quality Metrics:**
   - Look for quality badge/indicator
   - **Expected:** High confidence (90%+)

---

## 🔍 Test 4: Review Queue (Optional)

### Navigate to Reports Page
1. Click **"Reports"** in navigation
2. You should see **"Review Queue"** section

### Check Items Needing Review
- Shows records with:
  - Low confidence (<85%)
  - Unmatched accounts
  - Validation failures

### Expected for Cash Flow
- **Before fix:** 46% unmatched (many items in queue)
- **After fix:** 5-10% unmatched (few items in queue)

---

## 🎯 Test 5: Verify Match Rate Improvement

### Backend Verification (Best Method)

Open a new terminal and run:

```bash
docker exec -it reims-postgres psql -U reims -d reims
```

Then run this query:

```sql
-- Overall Cash Flow match rate
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN account_id IS NOT NULL THEN 1 END) as matched_records,
    ROUND(COUNT(CASE WHEN account_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as match_rate_percent,
    COUNT(CASE WHEN needs_review = TRUE THEN 1 END) as needs_review_count
FROM cash_flow_data;
```

**Expected Results:**
- Total records: 300-500+ (depending on documents uploaded)
- Match rate: **90-95%+** (was 53.64%)
- Needs review: **5-10%** (was 46%)

### By Property and Year

```sql
SELECT 
    p.property_code,
    fp.period_year,
    COUNT(*) as total,
    COUNT(CASE WHEN account_id IS NOT NULL THEN 1 END) as matched,
    ROUND(COUNT(CASE WHEN account_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as match_rate
FROM cash_flow_data cfd
JOIN properties p ON cfd.property_id = p.id
JOIN financial_periods fp ON cfd.period_id = fp.id
GROUP BY p.property_code, fp.period_year
ORDER BY p.property_code, fp.period_year;
```

---

## 📸 What Success Looks Like

### ✅ Upload Screen
- Clean interface
- Property, period, and type selectors work
- Drag-drop functional
- Upload progress visible

### ✅ Documents List
- Shows all uploaded documents
- Status updates automatically
- Can filter by property, type, status
- Download button works

### ✅ Extraction Results
- Status changes to "completed" within 2 minutes
- High match rate (90%+)
- Low items in review queue
- Quality indicators green/high

### ✅ Database Verification
- 90-95%+ match rate
- 5-10% needs review
- Hierarchical accounts working (same code, different names)
- Zero duplicate key errors

---

## 🐛 Troubleshooting

### Issue: Upload Button Disabled
**Cause:** Missing required fields  
**Fix:** Ensure property, year, month, and file are selected

### Issue: Upload Fails
**Check:**
1. File is PDF format
2. File size < 50MB
3. Backend is running: `curl http://localhost:8000/api/v1/health`

### Issue: Stuck in "pending"
**Check Celery Worker:**
```bash
docker logs reims-celery-worker -f
```

**If not processing:**
```bash
docker compose restart celery-worker
```

### Issue: Status shows "failed"
**Check Backend Logs:**
```bash
docker logs reims-backend -f
```

**Common causes:**
- Invalid PDF format
- Corrupted file
- Missing property/period in database

### Issue: Low Match Rate (<90%)
**Check:**
1. Accounts were loaded:
   ```bash
   docker exec -it reims-postgres psql -U reims -d reims -c \
     "SELECT COUNT(*) FROM chart_of_accounts WHERE 'cash_flow' = ANY(document_types);"
   ```
   Should show: ~142 accounts

2. Check which accounts are unmatched:
   ```sql
   SELECT account_name, COUNT(*) 
   FROM cash_flow_data 
   WHERE account_id IS NULL 
   GROUP BY account_name 
   ORDER BY COUNT(*) DESC 
   LIMIT 10;
   ```

---

## 📋 Testing Checklist

### Pre-Testing
- [ ] All services running (8 containers)
- [ ] Frontend accessible at http://localhost:5173
- [ ] Backend healthy: http://localhost:8000/api/v1/health
- [ ] 142 Cash Flow accounts in database

### Authentication
- [ ] Can register new account
- [ ] Can login successfully
- [ ] Dashboard loads after login
- [ ] Shows 5 properties

### Upload Functionality
- [ ] Can select property from dropdown
- [ ] Can select year and month
- [ ] Can select "Cash Flow" document type
- [ ] Can drag-drop or browse for PDF
- [ ] Upload button works
- [ ] Success message appears

### Extraction Process
- [ ] Document appears in list with "pending" status
- [ ] Status changes to "processing" (within 30 seconds)
- [ ] Status changes to "completed" (within 2 minutes)
- [ ] No "failed" status

### Results Verification
- [ ] Match rate 90-95%+ (database check)
- [ ] Few items in review queue (5-10%)
- [ ] Hierarchical accounts working
- [ ] No duplicate key errors in logs

### Overall Quality
- [ ] Multiple documents upload successfully
- [ ] Consistent high match rates
- [ ] UI responsive and user-friendly
- [ ] No crashes or errors

---

## 🎯 Success Criteria

### Must Have ✅
1. Upload works smoothly
2. Extraction completes without errors
3. Match rate ≥ 90%
4. Review queue ≤ 10% of records
5. No duplicate key violations

### Nice to Have 🌟
1. Match rate ≥ 95%
2. Review queue ≤ 5% of records
3. Fast extraction (< 60 seconds)
4. Beautiful UI feedback

---

## 📊 Expected Results Summary

| Metric | Before Fix | After Fix | Target |
|--------|-----------|-----------|---------|
| Match Rate | 53.64% | 90-95%+ | ≥90% ✅ |
| Needs Review | 46% | 5-10% | ≤10% ✅ |
| Chart Accounts | 29 | 142 | 150 ✅ |
| Hierarchical | ❌ | ✅ | Working ✅ |
| Duplicates | Issues | ✅ | Prevented ✅ |

---

## 🚀 Batch Testing (Upload Multiple Documents)

### Test All 8 Cash Flow Documents

For comprehensive testing, upload all cash flow PDFs:

1. **ESP (Eastern Shore Plaza)**
   - 2023-12 Cash Flow
   - 2024-12 Cash Flow

2. **HMND (Hammond Aire)**
   - 2023-12 Cash Flow
   - 2024-12 Cash Flow

3. **TCSH (The Crossing)**
   - 2023-12 Cash Flow
   - 2024-12 Cash Flow

4. **WEND (Wendover Commons)**
   - 2023-12 Cash Flow
   - 2024-12 Cash Flow

### Monitor Batch Processing
```bash
# Watch all extractions
docker logs reims-celery-worker -f

# Look for:
# "✅ Cash Flow Account Matching: X/Y (Z%)"
# Z should be 90-95%+ for each document
```

---

## 📸 Screenshots to Capture (Optional)

1. Dashboard with properties
2. Upload interface
3. Document list with "completed" status
4. High match rate results
5. Review queue (showing few items)

---

## 🎉 When Testing is Complete

### Document Your Results

Create a simple report:

```markdown
# Cash Flow Testing Results

**Date:** [Date]
**Documents Tested:** 8 cash flow PDFs

## Results:
- Upload Success Rate: X/8 (100%?)
- Average Match Rate: XX%
- Items Needing Review: X%
- Errors: None / [List if any]

## Conclusion:
✅ Cash Flow fixes working as expected
✅ Match rate improved from 53.64% to XX%
✅ Ready for production use
```

---

**Ready to Start Testing!** 🚀

Open http://localhost:5173 and follow the steps above!



