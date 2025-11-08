# Granular Status Tracking Feature

## 🎯 **Feature Overview**

The REIMS system now shows **detailed status updates** during document upload and extraction, allowing you to see exactly what stage each document is in and where failures occur.

---

## 📊 **Status Flow**

### **Success Path:**
```
1. 📤 "Uploaded to MinIO"   → File successfully stored in MinIO bucket
2. 🔍 "Extracting"          → Reading PDF and extracting text  
3. ✓  "Validating"          → Parsing and validating financial data
4. ✅ "Completed"           → Data successfully loaded in database
```

### **Failure States (shows exactly where it failed):**
```
❌ "Failed: Download"       → Could not download file from MinIO
❌ "Failed: Extraction"     → PDF reading/text extraction failed
❌ "Failed: Validation"     → Data parsing or validation failed
```

---

## 🎨 **Visual Indicators**

Each status has a distinct color-coded badge:

| Status | Color | Description |
|--------|-------|-------------|
| Uploaded to MinIO | 🟣 Purple | File in storage, waiting for extraction |
| Extracting | 🔵 Blue | Reading PDF content |
| Validating | 🟡 Yellow | Parsing and validating data |
| Completed | 🟢 Green | Successfully extracted |
| Failed: Download | 🔴 Red | Storage access failed |
| Failed: Extraction | 🔴 Red | PDF reading failed |
| Failed: Validation | 🟠 Orange | Data validation failed |

---

## 🔧 **Implementation Details**

### **Backend Changes:**

**1. document_service.py**
- Sets initial status to `uploaded_to_minio` when file is stored
- Logs: "📤 Uploading to MinIO: {file_path}"

**2. extraction_orchestrator.py**
- Updates status to `extracting` when starting PDF processing
- Updates status to `validating` when inserting/validating data
- Sets specific failure states:
  - `failed_download` - MinIO download failed
  - `failed_extraction` - PDF extraction failed
  - `failed_validation` - Data parsing/validation failed

### **Frontend Changes:**

**1. Documents.tsx**
- Added `formatExtractionStatus()` helper function
- Maps internal status codes to user-friendly labels
- Displays formatted status in Recent Uploads table

**2. App.css**
- Added CSS classes for all new status values
- Color-coded badges for visual differentiation

---

## 🧪 **Testing the Feature**

### **How to See It In Action:**

1. **Refresh your browser**: http://localhost:5173
2. **Upload a file** through the Documents page
3. **Watch the status change** in real-time:
   - Starts as "Uploaded to MinIO" (purple)
   - Changes to "Extracting" (blue)
   - Changes to "Validating" (yellow)
   - Ends as "Completed" (green)

### **Monitoring During Upload:**

```bash
# Watch database status change in real-time
watch -n 1 'docker compose exec -T postgres psql -U reims -d reims -c "SELECT id, file_name, extraction_status FROM document_uploads ORDER BY upload_date DESC LIMIT 5;"'
```

### **Example Status Progression:**

```
Time    | ID | File Name                    | Status
--------|----|------------------------------|-------------------
15:00:01| 25 | Example.pdf                  | uploaded_to_minio
15:00:03| 25 | Example.pdf                  | extracting
15:00:06| 25 | Example.pdf                  | validating
15:00:10| 25 | Example.pdf                  | completed
```

---

## 💡 **Benefits**

### **Before:**
- ❌ Status showed only "pending" or "completed"
- ❌ No visibility into progress
- ❌ Failed uploads didn't show where they failed
- ❌ Users didn't know if system was working

### **After:**
- ✅ See exactly what stage each upload is in
- ✅ Monitor progress in real-time
- ✅ Specific failure messages show where it broke
- ✅ Better troubleshooting and user experience

---

## 📋 **Status Reference Guide**

### **Normal Flow (Everything Works):**

1. **File uploaded to frontend** → API receives file
2. **"Uploaded to MinIO"** → File stored in object storage (reims bucket)
3. **"Extracting"** → Celery worker downloads PDF and extracts text
4. **"Validating"** → System parses financial data and validates structure
5. **"Completed"** → Data inserted into database tables

### **Failure Scenarios:**

**If stuck at "Uploaded to MinIO":**
- Celery worker may not be running
- Check: `docker compose ps celery-worker`
- Check: `docker compose logs celery-worker`

**If shows "Failed: Download":**
- MinIO connection issue
- File may have been deleted
- Check: MinIO console at http://localhost:9001

**If shows "Failed: Extraction":**
- PDF is corrupted or unreadable
- Check extraction logs for details
- May need different PDF engine

**If shows "Failed: Validation":**
- Financial data doesn't match expected template
- Missing required columns in database
- Check celery worker logs for specific error

---

## 🔍 **Troubleshooting**

### **Check Current Status:**
```bash
# See all uploads with their statuses
curl -s http://localhost:8000/api/v1/documents/uploads?limit=10 | python3 -m json.tool
```

### **Monitor Specific Upload:**
```bash
# Replace 25 with your upload ID
docker compose exec -T postgres psql -U reims -d reims -c "SELECT id, file_name, extraction_status, upload_date FROM document_uploads WHERE id = 25;"
```

### **Watch Status Changes:**
```bash
# Monitor status changes in real-time
docker compose logs -f celery-worker | grep "extraction_status"
```

---

## 📝 **Developer Notes**

### **Adding New Status States:**

1. **Backend** (`extraction_orchestrator.py`):
   ```python
   upload.extraction_status = "your_new_status"
   self.db.commit()
   ```

2. **Frontend** (`Documents.tsx`):
   ```typescript
   const statusMap: Record<string, string> = {
     'your_new_status': 'Display Text',
     ...
   }
   ```

3. **CSS** (`App.css`):
   ```css
   .status-badge.your_new_status {
     background: #color;
     color: #text-color;
   }
   ```

---

## ✅ **Summary**

**The REIMS system now provides full transparency into the upload/extraction pipeline!**

Users can see:
- ✅ When files are uploaded to storage
- ✅ When extraction is in progress
- ✅ When data is being validated
- ✅ When everything is complete
- ✅ Exactly where failures occur

This dramatically improves the user experience and makes troubleshooting much easier!

---

**Date Implemented:** November 8, 2025  
**Status:** ✅ Complete and ready for testing

