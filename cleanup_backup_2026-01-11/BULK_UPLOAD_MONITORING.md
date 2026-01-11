# Bulk Document Upload Monitoring Guide

Comprehensive guide for monitoring bulk document uploads, detecting issues, and recovery procedures.

## Quick Start

### Real-Time Monitoring
```bash
# Start continuous monitoring (updates every 10 seconds)
./scripts/monitor_bulk_upload.sh

# Custom interval (5 seconds)
./scripts/monitor_bulk_upload.sh --interval 5

# Run once and exit
./scripts/monitor_bulk_upload.sh --once
```

### Quick Status Checks
```bash
# Full summary
./scripts/quick_status.sh

# Individual checks
./scripts/quick_status.sh queue    # Queue depth and workers
./scripts/quick_status.sh recent    # Recent uploads count
./scripts/quick_status.sh failed    # Failed uploads count
./scripts/quick_status.sh stuck     # Stuck uploads count
```

## Monitoring Components

### 1. Backend API Monitoring

**Endpoint**: `POST /api/v1/documents/bulk-upload`

**What to Monitor**:
- HTTP response codes (400, 500 errors)
- File validation failures
- Property not found errors
- Document type detection failures
- Month detection issues
- MinIO upload failures
- Database transaction errors

**Commands**:
```bash
# Real-time backend logs
docker compose logs -f backend | grep -E "(bulk|upload|error|failed|exception)"

# Filter for specific errors
docker compose logs backend | grep -i "property.*not found"
docker compose logs backend | grep -i "document type"
docker compose logs backend | grep -i "minio"
docker compose logs backend | grep -i "failed to upload"
```

**Key Log Patterns**:
- `✅ File uploaded to MinIO successfully` - Success
- `⚠️  Warning:` - Warning (non-critical)
- `❌ Error:` or `Failed` - Error requiring attention
- `Exception` - Exception that needs investigation

### 2. Database Status Monitoring

**Table**: `document_uploads`

**Key Fields to Monitor**:
- `id` - Upload ID
- `file_name` - Original filename
- `document_type` - Detected document type
- `extraction_status` - Current status (pending, processing, completed, failed)
- `upload_date` - When file was uploaded
- `extraction_task_id` - Celery task ID
- `notes` - Error messages or warnings

**SQL Queries**:

```sql
-- Recent uploads (last 30 minutes)
SELECT id, file_name, document_type, extraction_status, 
       upload_date, extraction_task_id
FROM document_uploads 
WHERE upload_date > NOW() - INTERVAL '30 minutes'
ORDER BY upload_date DESC;

-- Failed extractions
SELECT id, file_name, extraction_status, notes, upload_date
FROM document_uploads 
WHERE extraction_status = 'failed'
ORDER BY upload_date DESC
LIMIT 20;

-- Stuck uploads (pending > 10 minutes)
SELECT id, file_name, extraction_status, upload_date,
       EXTRACT(EPOCH FROM (NOW() - upload_date))/60 as minutes_pending
FROM document_uploads 
WHERE extraction_status = 'pending' 
  AND upload_date < NOW() - INTERVAL '10 minutes'
ORDER BY upload_date ASC;

-- Upload summary by status
SELECT extraction_status, COUNT(*) as count
FROM document_uploads
WHERE upload_date > NOW() - INTERVAL '1 hour'
GROUP BY extraction_status;

-- Recent uploads with details
SELECT 
    id,
    file_name,
    document_type,
    extraction_status,
    EXTRACT(EPOCH FROM (NOW() - upload_date))/60 as minutes_ago,
    extraction_task_id
FROM document_uploads 
WHERE upload_date > NOW() - INTERVAL '5 minutes'
ORDER BY upload_date DESC;
```

**Quick Database Checks**:
```bash
# Count recent uploads
docker compose exec postgres psql -U reims -d reims -c \
  "SELECT COUNT(*) FROM document_uploads WHERE upload_date > NOW() - INTERVAL '10 minutes';"

# Check failed extractions
docker compose exec postgres psql -U reims -d reims -c \
  "SELECT COUNT(*) FROM document_uploads WHERE extraction_status = 'failed' AND upload_date > NOW() - INTERVAL '1 hour';"

# Check stuck uploads
docker compose exec postgres psql -U reims -d reims -c \
  "SELECT COUNT(*) FROM document_uploads WHERE extraction_status = 'pending' AND upload_date < NOW() - INTERVAL '10 minutes';"
```

### 3. Celery Worker & Queue Monitoring

**What to Monitor**:
- Worker availability
- Queue depth (pending tasks)
- Active extraction tasks
- Task failures
- Worker crashes

**Commands**:
```bash
# Check Celery worker status
docker compose ps celery-worker

# Check queue status via API
curl http://localhost:8000/api/v1/documents/queue-status

# Monitor Celery logs
docker compose logs -f celery-worker | grep -E "(extract|error|failed|task)"

# Check Flower dashboard (if available)
# http://localhost:5555
```

**API Endpoint**: `GET /api/v1/documents/queue-status`

**Response**:
```json
{
  "queue_depth": 5,
  "workers_available": 1,
  "pending_uploads": 3,
  "workers": ["celery@worker1"]
}
```

**Health Indicators**:
- ✅ `workers_available > 0` - Workers are running
- ✅ `queue_depth < 50` - Queue is manageable
- ⚠️ `queue_depth > 50` - Queue is backing up
- ❌ `workers_available = 0` - No workers available (critical)

### 4. MinIO Storage Monitoring

**What to Monitor**:
- File upload success/failure
- Storage space
- Bucket access issues
- File corruption

**Commands**:
```bash
# Check MinIO container status
docker compose ps minio

# Monitor MinIO logs
docker compose logs -f minio | grep -E "(error|failed|upload)"

# Check MinIO health
curl http://localhost:9000/minio/health/live

# Access MinIO Console
# http://localhost:9001 (minioadmin / minioadmin)
```

**MinIO Console**:
- URL: http://localhost:9001
- Username: `minioadmin`
- Password: `minioadmin`
- Check: Bucket `reims` for uploaded files

### 5. Extraction Task Monitoring

**Location**: `backend/app/tasks/extraction_tasks.py`

**What to Monitor**:
- Task execution time
- Task timeouts (10 minute limit)
- Extraction errors
- Task retries

**Key Statuses**:
- `pending` - Waiting to be processed
- `processing` - Currently extracting
- `completed` - Successfully extracted
- `failed` - Extraction failed

**Check Task Status**:
```bash
# Get task ID from database
docker compose exec postgres psql -U reims -d reims -c \
  "SELECT id, extraction_task_id FROM document_uploads WHERE id = <upload_id>;"

# Check task in Flower (if available)
# Navigate to http://localhost:5555 and search for task_id
```

### 6. Frontend Error Monitoring

**Location**: Browser Developer Tools

**What to Monitor**:
- Network errors (failed API calls)
- JavaScript errors
- File validation errors
- Upload progress

**How to Check**:
1. Open Browser Developer Tools (F12)
2. Go to "Console" tab for JavaScript errors
3. Go to "Network" tab for API call status
4. Filter by "bulk-upload" or "documents" to see relevant requests

## Error Detection Patterns

### Common Issues and Solutions

#### 1. Property Not Found
**Pattern**: `Property 'XXX' not found`
**Location**: Backend logs
**Action**:
```bash
# Verify property exists
docker compose exec postgres psql -U reims -d reims -c \
  "SELECT id, property_code, property_name FROM properties WHERE property_code = 'XXX';"
```
**Solution**: Ensure property code matches exactly (case-sensitive)

#### 2. Document Type Detection Failure
**Pattern**: `Could not detect document type from filename`
**Location**: Backend logs, upload results
**Action**: Check filename patterns
**Solution**: Ensure filename contains keywords like:
- `balance*sheet*` or `balance_sheet`
- `income*statement*` or `income_statement`
- `cash*flow*` or `cash_flow`
- `rent*roll*` or `rent_roll`

#### 3. MinIO Upload Failure
**Pattern**: `Failed to upload file to storage`
**Location**: Backend logs
**Action**:
```bash
# Check MinIO container
docker compose ps minio
docker compose logs minio --tail 50

# Check storage space
docker system df
```
**Solution**: 
- Restart MinIO: `docker compose restart minio`
- Check disk space
- Verify MinIO credentials

#### 4. Celery Worker Unavailable
**Pattern**: `Failed to queue extraction` or `Celery unavailable`
**Location**: Backend logs, queue status
**Action**:
```bash
# Check worker status
docker compose ps celery-worker
docker compose logs celery-worker --tail 50

# Restart worker
docker compose restart celery-worker
```
**Solution**: Restart Celery worker if it's down

#### 5. Extraction Timeout
**Pattern**: `Extraction task timed out` (after 10 minutes)
**Location**: Celery logs, database notes
**Action**:
```bash
# Check extraction logs
docker compose logs celery-worker | grep -A 20 "timeout"

# Check specific upload
docker compose exec postgres psql -U reims -d reims -c \
  "SELECT id, file_name, notes FROM document_uploads WHERE id = <upload_id>;"
```
**Solution**: 
- Check if PDF is corrupted or too complex
- May need to retry with smaller file
- Check extraction logs for specific errors

#### 6. Database Connection Issues
**Pattern**: `Database connection error` or `could not connect`
**Location**: Backend logs
**Action**:
```bash
# Check PostgreSQL
docker compose ps postgres
docker compose logs postgres --tail 50

# Test connection
docker compose exec postgres psql -U reims -d reims -c "SELECT 1;"
```
**Solution**: Restart PostgreSQL if needed: `docker compose restart postgres`

#### 7. Stuck Uploads (Pending > 10 minutes)
**Pattern**: Uploads with `extraction_status = 'pending'` for > 10 minutes
**Location**: Database query
**Action**:
```bash
# Find stuck uploads
docker compose exec postgres psql -U reims -d reims -c "
  SELECT id, file_name, extraction_status, upload_date,
         EXTRACT(EPOCH FROM (NOW() - upload_date))/60 as minutes_pending
  FROM document_uploads 
  WHERE extraction_status = 'pending' 
    AND upload_date < NOW() - INTERVAL '10 minutes';
"
```
**Solution**:
- Check if Celery worker is running
- Check queue depth
- May need to manually retry: Check extraction task queuing

#### 8. File Size Exceeded
**Pattern**: `File size exceeds 50MB limit`
**Location**: Backend logs, API response
**Solution**: Compress PDF or split into smaller files

#### 9. Invalid File Format
**Pattern**: `File must be a PDF` or format validation errors
**Location**: Backend logs, upload results
**Solution**: Ensure files are valid PDFs, CSVs, or Excel files

## Recovery Procedures

### If Uploads Fail

1. **Check Backend Logs**:
   ```bash
   docker compose logs backend --tail 100 | grep -i error
   ```

2. **Verify Property Exists**:
   ```bash
   docker compose exec postgres psql -U reims -d reims -c \
     "SELECT * FROM properties WHERE property_code = '<CODE>';"
   ```

3. **Check MinIO**:
   ```bash
   docker compose ps minio
   docker compose logs minio --tail 50
   ```

4. **Retry Failed Uploads**:
   - Use the frontend to re-upload specific files
   - Or use the bulk upload again with `replace` strategy

### If Extractions Stuck

1. **Check Celery Worker**:
   ```bash
   docker compose ps celery-worker
   docker compose logs celery-worker --tail 100
   ```

2. **Check Queue Depth**:
   ```bash
   curl http://localhost:8000/api/v1/documents/queue-status
   ```

3. **Restart Worker if Needed**:
   ```bash
   docker compose restart celery-worker
   ```

4. **Check for Stuck Tasks in Database**:
   ```bash
   docker compose exec postgres psql -U reims -d reims -c "
     SELECT id, file_name, extraction_task_id, extraction_status
     FROM document_uploads 
     WHERE extraction_status = 'pending' 
       AND upload_date < NOW() - INTERVAL '10 minutes';
   "
   ```

### If MinIO Issues

1. **Check Container**:
   ```bash
   docker compose ps minio
   ```

2. **Check Logs**:
   ```bash
   docker compose logs minio --tail 50
   ```

3. **Restart if Needed**:
   ```bash
   docker compose restart minio
   ```

4. **Verify Bucket Exists**:
   - Access MinIO Console: http://localhost:9001
   - Check if `reims` bucket exists
   - Verify files are being stored

### If Database Issues

1. **Check Container**:
   ```bash
   docker compose ps postgres
   ```

2. **Test Connection**:
   ```bash
   docker compose exec postgres psql -U reims -d reims -c "SELECT 1;"
   ```

3. **Check Logs**:
   ```bash
   docker compose logs postgres --tail 50
   ```

4. **Restart if Needed**:
   ```bash
   docker compose restart postgres
   ```

## Automated Alerts

### Recommended Alert Thresholds

- **Queue Depth > 50 tasks**: Queue is backing up, may need more workers
- **Worker Unavailable**: Critical - no tasks can be processed
- **Failed Uploads > 5 in last 10 minutes**: High failure rate, investigate
- **Stuck Extractions > 10 minutes**: Tasks not being processed
- **MinIO Storage > 80% full**: Need to clean up or expand storage

### Monitoring Checklist

During bulk upload, check:

- [ ] Backend service is running
- [ ] Celery worker is running
- [ ] Queue depth is reasonable (< 50)
- [ ] No recent errors in logs
- [ ] Uploads appearing in database
- [ ] Extraction status progressing (pending → processing → completed)
- [ ] MinIO is accessible
- [ ] No stuck uploads (> 10 minutes pending)

## Success Indicators

✅ **Upload Successful**:
- File appears in `document_uploads` table
- Status is `pending` or `processing`
- `extraction_task_id` is set
- File exists in MinIO

✅ **Extraction Successful**:
- Status changes to `completed`
- Financial data appears in respective tables (balance_sheet_data, income_statement_data, etc.)
- No errors in Celery logs

✅ **Bulk Upload Successful**:
- All files processed (uploaded, skipped, or replaced)
- Summary shows success counts
- No critical errors in logs

## Quick Reference Commands

```bash
# Full monitoring dashboard
./scripts/monitor_bulk_upload.sh

# Quick status check
./scripts/quick_status.sh

# Check queue
curl http://localhost:8000/api/v1/documents/queue-status | jq .

# Recent uploads
docker compose exec postgres psql -U reims -d reims -c \
  "SELECT id, file_name, extraction_status FROM document_uploads WHERE upload_date > NOW() - INTERVAL '10 minutes' ORDER BY upload_date DESC LIMIT 10;"

# Watch backend logs
docker compose logs -f backend | grep -E "(upload|error|failed)"

# Watch Celery logs
docker compose logs -f celery-worker | grep -E "(extract|error|failed)"

# Service status
docker compose ps
```

## Troubleshooting Workflow

1. **Check Quick Status**: `./scripts/quick_status.sh`
2. **If Issues Found**: Start full monitoring `./scripts/monitor_bulk_upload.sh`
3. **Check Specific Component**:
   - Backend: `docker compose logs backend --tail 100`
   - Celery: `docker compose logs celery-worker --tail 100`
   - Database: Query `document_uploads` table
   - MinIO: Check container and console
4. **Apply Recovery Procedure** based on error pattern
5. **Verify Fix**: Re-run quick status check

## Additional Resources

- **Flower Dashboard**: http://localhost:5555 (Celery monitoring)
- **MinIO Console**: http://localhost:9001
- **API Docs**: http://localhost:8000/docs
- **Backend Health**: http://localhost:8000/api/v1/health

