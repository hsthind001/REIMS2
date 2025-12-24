# Mortgage Statement Re-Extraction Guide

## Do You Need to Re-Upload? **NO!** ✅

**You do NOT need to re-upload your 2023 mortgage statements.** The self-learning solution works automatically for:

1. **New uploads** - Will use improved patterns immediately
2. **Re-extraction** - Can fix existing problematic extractions without re-uploading

## Current Status

### Your 2023 Mortgage Statements
- ✅ **11 statements already uploaded and extracted**
- ✅ **10 statements extracted correctly** (with valid loan numbers)
- ⚠️ **1 statement needs fixing** (Upload ID 353 has "Total" as loan_number)

### What Works Automatically

**For NEW uploads going forward:**
- ✅ Improved period detection (uses "LOAN INFORMATION As of Date")
- ✅ Better loan number extraction (section-specific patterns)
- ✅ Self-healing validation (filters invalid values)
- ✅ Automatic learning from successful extractions

**For EXISTING uploads:**
- ✅ Data is already stored in database
- ✅ Can be re-extracted using API endpoint (no re-upload needed)
- ✅ Self-healing will fix issues on re-extraction

## Option 1: Fix Only Problematic Uploads (Recommended)

If you want to fix the one problematic upload (ID 353 with "Total" as loan_number), use the re-extract endpoint:

### Via API:
```bash
POST /api/v1/documents/uploads/353/re-extract
```

### Via Frontend:
The frontend should have a "Re-extract" button for each upload, or you can use the bulk re-extract endpoint:

```bash
POST /api/v1/documents/re-extract-failed?document_type=mortgage_statement
```

This will:
- Re-run extraction with improved patterns
- Apply self-healing validation
- Learn from successful extraction
- Update the database record

## Option 2: Leave As-Is (Also Fine)

If the 10 correctly extracted statements are sufficient for your needs:
- ✅ **No action needed**
- ✅ New uploads will automatically use improved system
- ✅ Learning will happen on future extractions

## What Happens on Re-Extraction

When you re-extract an existing upload:

1. **Uses Updated Template**: Applies new patterns from `standard_mortgage_statement` template
2. **Enhanced Period Detection**: Uses "LOAN INFORMATION As of Date" pattern
3. **Self-Healing**: Filters invalid values (like "Total" as loan number)
4. **Learning**: Captures successful patterns for future use
5. **Database Update**: Updates `mortgage_statement_data` table with corrected values

## Recommendation

**For Upload ID 353 specifically:**
- Use re-extract endpoint to fix the "Total" loan_number issue
- No need to re-upload the file
- The PDF is already stored in MinIO

**For all other uploads:**
- They're already correctly extracted
- No action needed
- System will learn from future uploads automatically

## Testing the Fix

After re-extracting upload 353, verify the fix:

```sql
SELECT 
    upload_id, 
    loan_number, 
    statement_date, 
    principal_balance 
FROM mortgage_statement_data 
WHERE upload_id = 353;
```

**Expected Result:**
- `loan_number` should be a valid number (not "Total")
- All other fields should remain correct

## Summary

✅ **No re-upload needed** - Files are already in the system  
✅ **Re-extraction available** - Can fix problematic uploads via API  
✅ **Automatic for new uploads** - All improvements apply automatically  
✅ **Learning active** - System improves with each extraction  

The self-learning solution is **already active and working** for all new uploads. You only need to re-extract if you want to fix the one problematic upload (ID 353).

