# REIMS2 Data Management Guide

Complete guide for managing sample data, backups, and data quality verification.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Loading Sample Data](#loading-sample-data)
3. [Monthly File Upload](#monthly-file-upload)
4. [Data Quality Verification](#data-quality-verification)
5. [Backup and Restore](#backup-and-restore)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Load All Sample Data (28 Files)

```bash
cd backend
./scripts/quick_upload_samples.sh
```

This uploads all 28 annual PDF files from `/home/gurpyar/REIMS_Uploaded/uploads/Sampledata/`.

### Verify Data Quality

```bash
cd backend
python3 scripts/verify_data_quality.py --all
python3 scripts/verify_data_quality.py --all --html
```

### Create Backup

```bash
cd backend
./scripts/backup_database.sh
```

---

## Loading Sample Data

### Properties

Four properties are automatically created:
- **ESP001** - Esplanade Shopping Center (Phoenix, AZ)
- **HMND001** - Hammond Aire Shopping Center (Hammond, IN)
- **TCSH001** - Town Center Shopping (Town Center, FL)
- **WEND001** - Wendover Commons (Greensboro, NC)

Properties are created via Alembic migration and are idempotent.

### Sample PDFs

28 annual financial documents (2023-2024):
- 6-7 files per property
- Document types: Balance Sheet, Income Statement, Cash Flow, Rent Roll
- Located at: `/home/gurpyar/REIMS_Uploaded/uploads/Sampledata/`

### Upload Methods

**Method 1: Quick Upload Script (Recommended)**

```bash
./scripts/quick_upload_samples.sh
```

- Uploads all 28 files
- Fast (doesn't wait for extraction)
- Extraction happens asynchronously via Celery

**Method 2: Python Seed Script**

```bash
python3 scripts/seed_sample_data.py --all
python3 scripts/seed_sample_data.py --property ESP001
python3 scripts/seed_sample_data.py --year 2024
python3 scripts/seed_sample_data.py --dry-run  # Test without uploading
```

- More control and filtering
- Monitors extraction progress
- Waits for completion (slower)

**Method 3: Manual Upload**

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "property_code=ESP001" \
  -F "period_year=2024" \
  -F "period_month=12" \
  -F "document_type=balance_sheet" \
  -F "file=@/path/to/file.pdf"
```

---

## Monthly File Upload

### File Naming Convention

Monthly files must follow this format:

```
{PropertyCode}_{Year}_{Month:02d}_{DocumentType}.pdf
```

**Examples:**
```
ESP001_2024_01_balance_sheet.pdf
ESP001_2024_01_income_statement.pdf
ESP001_2024_01_cash_flow.pdf
ESP001_2024_02_balance_sheet.pdf
...
```

### Required Files

For complete monthly data, each property needs 3 files per month:
- Balance Sheet (`balance_sheet`)
- Income Statement (`income_statement`)
- Cash Flow Statement (`cash_flow`)

**Annual requirement:** 36 files per property (12 months × 3 documents)

### Bulk Upload Tool

```bash
python3 scripts/bulk_upload_monthly.py --directory /path/to/monthly/files
python3 scripts/bulk_upload_monthly.py --directory /path --property ESP001
python3 scripts/bulk_upload_monthly.py --directory /path --year 2024
python3 scripts/bulk_upload_monthly.py --directory /path --dry-run  # Analyze only
```

**Features:**
- Auto-detects property/period from filenames
- Creates missing financial periods
- Reports missing months/documents
- Parallel uploads with progress tracking

**Example directory structure:**
```
monthly_files/
├── ESP001_2024_01_balance_sheet.pdf
├── ESP001_2024_01_income_statement.pdf
├── ESP001_2024_01_cash_flow.pdf
├── ESP001_2024_02_balance_sheet.pdf
├── ESP001_2024_02_income_statement.pdf
├── ESP001_2024_02_cash_flow.pdf
└── ...
```

See [MONTHLY_FILES_SPECIFICATION.md](MONTHLY_FILES_SPECIFICATION.md) for complete details.

---

## Data Quality Verification

### Verify All Uploads

```bash
python3 scripts/verify_data_quality.py --all
```

Shows:
- Extraction status (completed/pending/failed)
- Quality scores
- Line item counts
- Issues found

### Verify Specific Property

```bash
python3 scripts/verify_data_quality.py --property ESP001
```

### Generate HTML Report

```bash
python3 scripts/verify_data_quality.py --all --html
python3 scripts/verify_data_quality.py --all --html --output custom_report.html
```

Opens a detailed HTML report with:
- Summary statistics
- Property-by-property breakdown
- Quality scores
- Issue details

### Generate JSON Report

```bash
python3 scripts/verify_data_quality.py --all --json --output report.json
```

Machine-readable format for automated processing.

### Quality Metrics

- **Quality Score**: 0-100 based on extraction confidence
  - 85-100: Excellent
  - 70-84: Good
  - Below 70: Needs review
  
- **Extraction Status**:
  - `pending`: Waiting for Celery to process
  - `processing`: Currently extracting
  - `completed`: Extraction finished
  - `failed`: Error occurred

- **Issues Flagged**:
  - Low confidence items (< 85%)
  - Missing line items
  - Needs manual review
  - Validation failures

---

## Backup and Restore

### Create Backup

```bash
./scripts/backup_database.sh
```

**What it does:**
- Creates compressed SQL dump
- Saves to `backups/` directory
- Auto-rotates (keeps last 7 backups)
- Shows backup size

**Output:**
```
backups/reims_backup_20251104_120000.sql.gz
```

### Restore from Backup

```bash
./scripts/restore_database.sh backups/reims_backup_20251104_120000.sql.gz
```

**Warning:** This overwrites the current database!

**Safety features:**
- Requires confirmation (`yes/no`)
- Closes active connections
- Verifies restoration
- Shows table/record counts

### List Available Backups

```bash
ls -lh backups/reims_backup_*.sql.gz
```

### Manual Backup (Alternative)

```bash
docker exec reims-postgres pg_dump -U reims reims | gzip > my_backup.sql.gz
```

### Manual Restore (Alternative)

```bash
gunzip -c my_backup.sql.gz | docker exec -i reims-postgres psql -U reims reims
```

---

## Troubleshooting

### Issue: "Property not found"

**Solution:**
```sql
-- Check if properties exist
docker exec reims-postgres psql -U reims -d reims -c "SELECT property_code, property_name FROM properties;"

-- If missing, run seed script
python3 scripts/seed_properties.py
```

### Issue: "Extraction stuck in pending"

**Check Celery worker:**
```bash
docker logs reims-celery-worker --tail 50
```

**Restart Celery worker:**
```bash
docker restart reims-celery-worker
```

**Check Redis:**
```bash
docker exec reims-redis redis-cli ping
```

### Issue: "Upload failed with HTTP 400/500"

**Check backend logs:**
```bash
docker logs reims-backend --tail 50
```

**Check if MinIO is running:**
```bash
docker ps | grep minio
curl http://localhost:9001
```

**Check if property/period exists:**
```bash
curl http://localhost:8000/api/v1/properties/ESP001
```

### Issue: "No data extracted"

**Verify file is a valid PDF:**
```bash
file /path/to/file.pdf
```

**Test extraction directly:**
```bash
curl -X POST http://localhost:8000/api/v1/extraction/analyze \
  -F "file=@/path/to/file.pdf" \
  -F "strategy=auto"
```

### Issue: "Duplicate upload error"

Files are deduplicated by MD5 hash. If you want to re-upload:

1. Delete old upload via API
2. Or modify the PDF slightly (add a page)
3. Or use version numbers

### Database Connection Issues

**Check if PostgreSQL is running:**
```bash
docker ps | grep postgres
docker logs reims-postgres --tail 20
```

**Test connection:**
```bash
docker exec reims-postgres psql -U reims -d reims -c "SELECT 1;"
```

### Reset Everything (Nuclear Option)

```bash
# Stop all containers
docker compose down

# Remove volumes (THIS DELETES ALL DATA!)
docker volume rm reims2_postgres-data reims2_minio-data reims2_redis-data

# Start fresh
docker compose up -d

# Wait for services to be ready
sleep 10

# Re-seed data
./scripts/quick_upload_samples.sh
```

---

## API Endpoints

### Documents

- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents/uploads` - List uploads
- `GET /api/v1/documents/uploads/{id}` - Get upload details
- `GET /api/v1/documents/uploads/{id}/data` - Get extracted data
- `DELETE /api/v1/documents/uploads/{id}` - Delete upload

### Properties

- `POST /api/v1/properties/` - Create property
- `GET /api/v1/properties/` - List properties
- `GET /api/v1/properties/{code}` - Get property by code

### Extraction

- `POST /api/v1/extraction/analyze` - Analyze PDF
- `GET /api/v1/tasks/{task_id}` - Check Celery task status

### Full API Documentation

```
http://localhost:8000/docs
```

---

## File Locations

### Scripts
- `/home/gurpyar/Documents/R/REIMS2/backend/scripts/`

### Backups
- `/home/gurpyar/Documents/R/REIMS2/backend/backups/`

### Sample Data
- `/home/gurpyar/REIMS_Uploaded/uploads/Sampledata/`

### Docker Volumes
- `reims2_postgres-data` - Database
- `reims2_minio-data` - File storage
- `reims2_redis-data` - Cache/queues

---

## Support

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker logs reims-backend -f
docker logs reims-celery-worker -f
docker logs reims-postgres -f
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health | jq .
```

### Service Status

```bash
docker compose ps
```

---

## Best Practices

1. **Always backup before major operations**
   ```bash
   ./scripts/backup_database.sh
   ```

2. **Test with dry-run first**
   ```bash
   python3 scripts/seed_sample_data.py --dry-run
   ```

3. **Monitor extraction progress**
   ```bash
   docker logs reims-celery-worker -f
   ```

4. **Verify data quality after uploads**
   ```bash
   python3 scripts/verify_data_quality.py --all --html
   ```

5. **Keep backups for at least 7 days**
   (Automatic with backup script)

---

## Next Steps

1. Load sample data
2. Verify extraction quality
3. Review HTML quality report
4. Prepare monthly files (see MONTHLY_FILES_SPECIFICATION.md)
5. Set up automated backups (cron job)

For monthly file requirements, see: [MONTHLY_FILES_SPECIFICATION.md](MONTHLY_FILES_SPECIFICATION.md)

