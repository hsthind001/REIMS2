# Auto-Replace Duplicates Feature

## 🎯 **What Changed**

The REIMS system now **automatically replaces duplicate files** instead of rejecting them.

### **Previous Behavior:**
- Upload duplicate file → System rejects it
- Old failed upload blocks new attempts
- User sees "Duplicate file already exists" error

### **New Behavior:**
- Upload duplicate file → System **auto-deletes old upload**
- Old file removed from MinIO
- All related financial data deleted (cascade)
- New file uploaded and extraction triggered
- ✅ **No more failed uploads blocking new attempts!**

---

## 🔍 **How It Works**

### **Duplicate Detection:**
1. System calculates MD5 hash of uploaded file content
2. Checks database for existing upload with:
   - Same property
   - Same period
   - Same document type
   - Same file hash

### **Auto-Replace Process:**
If duplicate found:
1. 🗑️ **Delete old file from MinIO**
2. 🗑️ **Delete old database record** (cascades to all related data):
   - balance_sheet_data
   - income_statement_data  
   - cash_flow_data
   - cash_flow_headers
   - cash_flow_adjustments
   - extraction_logs
   - validation_results
3. ✅ **Upload new file to MinIO**
4. ✅ **Create new database record**
5. ⚙️ **Trigger extraction task**

---

## 📊 **Testing the Feature**

### **Current Failed Uploads (Hammond Aire):**
```
ID 11: Hammond Aire 2023 Balance Sheet      - FAILED
ID 12: Hammond Aire 2024 Balance Sheet      - FAILED  
ID 13: Hammond Aire 2023 Income Statement   - FAILED
ID 14: Hammond Aire 2024 Income Statement   - FAILED
```

### **To Test Auto-Replace:**

1. **Go to frontend** (http://localhost:5173)
2. **Upload one of these files again:**
   - Hammond Aire 2023 Balance Sheet.pdf
   - Hammond Aire 2023 Income Statement.pdf
3. **Watch the behavior:**
   - Old failed upload (ID 11 or 13) will be deleted
   - New upload will be created with fresh ID
   - Extraction will run automatically
   - Should show as COMPLETED (with fixed schema)

---

## 🔧 **Code Changes**

### **Modified Files:**

1. **`backend/app/services/document_service.py`** (Lines 89-112)
   - Changed duplicate detection to auto-delete and replace
   - Deletes old file from MinIO
   - Deletes old database record (cascade delete)

2. **`backend/app/api/v1/documents.py`** (Lines 55-79)
   - Updated API documentation
   - Explains new auto-replace behavior

### **Database Schema Fixed:**
Added missing columns to `cash_flow_data` table:
- `parent_line_id` - References parent line item
- `parent_account_code` - Parent account code
- `is_calculated` - Whether value is calculated
- `cash_flow_category` - Legacy category field
- `is_inflow` - Whether transaction is inflow

---

## ✅ **Benefits**

1. ✅ **No more blocked uploads** - Failed uploads don't prevent retries
2. ✅ **Clean database** - Old failed data automatically removed
3. ✅ **Clean storage** - Old files automatically deleted from MinIO
4. ✅ **Better UX** - Users can simply re-upload without manual cleanup
5. ✅ **Data integrity** - Cascade delete ensures no orphaned records

---

## 📝 **Logs to Watch**

When uploading a duplicate, you'll see in backend logs:
```
🔄 Duplicate detected (ID 11). Auto-replacing with new upload...
🗑️  Deleted old file from MinIO: HMND001-Hammond-Aire/2023/balance-sheet/...
✅ Old upload deleted. Proceeding with new upload...
```

---

## 🚀 **Ready to Test!**

The system is now configured for auto-replace. Simply upload your files through the frontend and duplicates will be automatically replaced!

