# Cash Flow Template v1.0 - Docker Deployment Guide

**Quick Start:** Run `./deploy_cash_flow_template.sh` and follow the prompts.

---

## Overview

The Cash Flow Template v1.0 implementation is **fully compatible** with the existing Docker setup. No Docker file modifications are needed.

### What's Already Configured:
- ✅ `entrypoint.sh` runs migrations automatically
- ✅ `Dockerfile` copies all application code
- ✅ `requirements.txt` has all needed packages
- ✅ `docker-compose.yml` has correct configuration

**Result:** Simply rebuild and restart containers to deploy.

---

## Deployment Options

### Option 1: Automated Deployment Script (Recommended)

**Quick & Safe - Use the automated script:**

```bash
cd /home/gurpyar/Documents/R/REIMS2
./deploy_cash_flow_template.sh
```

**Features:**
- Interactive prompts (choose deployment type)
- Automatic backup (for safe deployment)
- Health checks and verification
- Color-coded output
- Optional test execution
- Comprehensive summary

**Deployment Types:**
1. **Quick Restart** - Fastest (10 seconds) - For development
2. **Full Rebuild** - Recommended (2-3 minutes) - For production
3. **Backup + Rebuild** - Safest (3-4 minutes) - Includes database backup

---

### Option 2: Manual Deployment

#### Quick Restart (Development):
```bash
cd /home/gurpyar/Documents/R/REIMS2
docker-compose restart backend celery-worker flower
```

#### Full Rebuild (Production):
```bash
cd /home/gurpyar/Documents/R/REIMS2

# Stop services
docker-compose down

# Rebuild images
docker-compose build backend celery-worker flower

# Start services
docker-compose up -d

# Watch logs
docker-compose logs -f backend
```

#### With Backup (Safest):
```bash
cd /home/gurpyar/Documents/R/REIMS2

# 1. Backup database
docker exec reims-postgres pg_dump -U reims reims > backend/backups/backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Stop services
docker-compose down

# 3. Rebuild
docker-compose build backend celery-worker flower

# 4. Start
docker-compose up -d

# 5. Watch logs
docker-compose logs -f backend
```

---

## What Happens During Deployment

### 1. Container Start
- `entrypoint.sh` executes
- Waits for PostgreSQL to be ready

### 2. Automatic Migration
```bash
alembic upgrade heads
```
- Applies migration: `939c6b495488`
- Creates 3 new tables:
  - `cash_flow_headers`
  - `cash_flow_adjustments`
  - `cash_account_reconciliations`
- Modifies `cash_flow_data` table:
  - Adds `header_id` column
  - Adds `line_section`, `line_category`, `line_subcategory` columns
  - Adds `line_number`, `is_subtotal`, `is_total`, `parent_line_id` columns
  - Adds `ytd_amount`, `period_percentage`, `ytd_percentage` columns
  - Adds `page_number` column
  - Updates unique constraint

### 3. Database Seeding (If Needed)
- Seeds chart of accounts (if not already seeded)
- Seeds lenders data

### 4. Application Start
- FastAPI server starts on port 8000
- Celery worker starts processing tasks
- All new models loaded
- All new endpoints available

**Total Time:** 30-90 seconds

---

## Verification

### Automated Verification Script:

```bash
cd /home/gurpyar/Documents/R/REIMS2
./verify_cash_flow_deployment.sh
```

**Checks:**
- ✅ Docker containers running
- ✅ Migration applied correctly
- ✅ New tables created
- ✅ New columns added
- ✅ API health endpoint
- ✅ Swagger UI accessible
- ✅ Models loaded
- ✅ Validation rules available
- ✅ Parser functionality

**Output:** Pass/Fail for each check with summary

---

### Manual Verification:

#### Check Migration:
```bash
docker exec reims-backend alembic current
```
Expected: `939c6b495488 (head)`

#### Check Tables:
```bash
docker exec reims-postgres psql -U reims -d reims -c "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'cash_flow%' ORDER BY table_name;"
```
Expected:
```
 table_name
---------------------------------
 cash_account_reconciliations
 cash_flow_adjustments
 cash_flow_data
 cash_flow_headers
(4 rows)
```

#### Check Columns in cash_flow_data:
```bash
docker exec reims-postgres psql -U reims -d reims -c "\d cash_flow_data"
```
Look for new columns:
- `header_id`
- `line_section`
- `line_category`
- `line_subcategory`
- `line_number`
- `is_subtotal`
- `is_total`
- `parent_line_id`
- `ytd_amount`
- `period_percentage`
- `ytd_percentage`
- `page_number`

#### Check API:
```bash
curl http://localhost:8000/api/v1/health
```
Expected: `{"status":"healthy"}`

#### Check Swagger:
Open browser: http://localhost:8000/docs

Look for updated schemas with new Cash Flow fields.

---

## Rollback (If Needed)

### Automated Rollback Script:

```bash
cd /home/gurpyar/Documents/R/REIMS2
./rollback_cash_flow_template.sh
```

**Features:**
- Creates safety backup before rollback
- Downgrades migration by 1 step
- Restarts services
- Verifies rollback success
- Provides restore instructions

### Manual Rollback:

```bash
# 1. Backup current state
docker exec reims-postgres pg_dump -U reims reims > backup_current.sql

# 2. Downgrade migration
docker exec reims-backend alembic downgrade -1

# 3. Restart
docker-compose restart backend celery-worker

# 4. Verify
docker exec reims-backend alembic current
```

---

## Testing After Deployment

### Run Automated Tests:
```bash
docker exec reims-backend pytest tests/test_cash_flow_extraction.py tests/test_cash_flow_validation.py -v
```

Expected: 50+ tests passing

### Upload Test PDF:
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "property_code=ESP" \
  -F "period_year=2024" \
  -F "period_month=12" \
  -F "document_type=cash_flow" \
  -F "file=@test_cash_flow.pdf"
```

Expected response:
```json
{
  "upload_id": 123,
  "task_id": "abc-123-def-456",
  "message": "Document uploaded successfully",
  "file_path": "ESP/2024/12/cash_flow_20241104_123456.pdf",
  "extraction_status": "pending"
}
```

### Check Extraction Results:
```bash
# Wait a few seconds for processing, then:
curl "http://localhost:8000/api/v1/documents/uploads/123/data"
```

Should return:
- Complete header with all metrics
- All line items with classifications
- All adjustments
- All cash account reconciliations
- Validation results

---

## Monitoring

### View Logs:
```bash
# Backend logs
docker-compose logs -f backend

# Celery worker logs
docker-compose logs -f celery-worker

# All services
docker-compose logs -f
```

### Monitor Celery Tasks:
Open Flower: http://localhost:5555

### Monitor Database:
Open pgAdmin: http://localhost:5050
- Email: admin@pgadmin.com
- Password: admin

### Monitor Redis:
Open RedisInsight: http://localhost:8001

---

## Troubleshooting

### Issue: Migration Doesn't Run

**Symptom:** New tables not created

**Solution:**
```bash
# Run migration manually
docker exec -it reims-backend alembic upgrade head

# Check migration history
docker exec -it reims-backend alembic history

# Check current version
docker exec -it reims-backend alembic current
```

### Issue: Services Won't Start

**Symptom:** Container exits immediately

**Solution:**
```bash
# Check logs
docker-compose logs backend

# Check container status
docker ps -a | grep reims

# Restart specific service
docker-compose restart backend
```

### Issue: Import Errors

**Symptom:** "ModuleNotFoundError" or "ImportError"

**Solution:**
```bash
# Rebuild with no cache
docker-compose build --no-cache backend celery-worker

# Restart
docker-compose up -d
```

### Issue: Database Connection Fails

**Symptom:** "could not connect to server"

**Solution:**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Wait for health check
docker-compose ps postgres
```

---

## Production Deployment Checklist

- [ ] **Backup database:** `pg_dump` before deployment
- [ ] **Review changes:** Check migration SQL
- [ ] **Test in staging:** Deploy to staging environment first
- [ ] **Rebuild images:** `docker-compose build --no-cache`
- [ ] **Tag images:** `docker tag reims-backend:latest reims-backend:cf-v1.0`
- [ ] **Deploy:** `docker-compose up -d`
- [ ] **Verify migration:** Check `alembic current`
- [ ] **Verify tables:** Check tables exist
- [ ] **Test API:** Upload test PDF
- [ ] **Monitor logs:** Watch for errors
- [ ] **Run tests:** `pytest tests/test_cash_flow*.py`
- [ ] **Check validation:** Review validation results
- [ ] **Monitor performance:** Check extraction times
- [ ] **User acceptance:** Get user sign-off

---

## Service URLs After Deployment

| Service | URL | Description |
|---------|-----|-------------|
| API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Flower | http://localhost:5555 | Celery monitoring |
| pgAdmin | http://localhost:5050 | Database GUI |
| RedisInsight | http://localhost:8001 | Redis monitoring |
| MinIO Console | http://localhost:9001 | Object storage |
| Frontend | http://localhost:5173 | React app |

---

## Environment Variables

All environment variables are already configured in `docker-compose.yml`. No changes needed.

**Key Variables:**
- `RUN_MIGRATIONS: "true"` - Enables automatic migrations
- `SEED_DATABASE: "true"` - Enables automatic seeding
- Database, Redis, MinIO credentials - All configured

---

## Files Created

### Deployment Scripts (3):
1. **`deploy_cash_flow_template.sh`** - Main deployment script
   - Interactive deployment options
   - Automated verification
   - Optional testing
   - Comprehensive output

2. **`rollback_cash_flow_template.sh`** - Rollback script
   - Safety backup before rollback
   - Automated rollback process
   - Verification
   - Restore instructions

3. **`verify_cash_flow_deployment.sh`** - Verification script
   - 15+ comprehensive checks
   - Pass/Fail reporting
   - Troubleshooting guidance

All scripts are executable and ready to use.

---

## Quick Start

### One-Command Deployment:
```bash
cd /home/gurpyar/Documents/R/REIMS2
./deploy_cash_flow_template.sh
```

Follow the prompts and you're done!

---

## Conclusion

**The Docker deployment is straightforward:**
1. No Docker file changes needed
2. Migration runs automatically
3. All code is already included
4. Just rebuild and restart

**Use the automated script for the easiest deployment experience.**

---

**Status:** ✅ Ready to Deploy  
**Risk Level:** Low (additive migration, no breaking changes)  
**Downtime:** ~30-60 seconds  
**Rollback:** Available via script

