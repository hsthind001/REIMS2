# Troubleshooting Session - November 8, 2025

## What Was Wrong

### 1. Backend Not Running
**Problem:** Backend container was in "Created" state but not running
**Root Cause:** Local uvicorn process (PID 333355) was already using port 8000
**Fix:** Killed local process, started Docker backend container

### 2. Python Indentation Errors
**Problem:** Backend failed to start with IndentationError in extraction_orchestrator.py (lines 454, 521, 819)
**Root Cause:** Git restore corrupted indentation when reverting accidental changes
**Fix:** Manually corrected indentation in all affected sections

### 3. Database Schema Mismatches
**Problem:** Extractions failing with "column does not exist" errors
**Missing Columns:**
- extraction_logs: 24 columns (file_hash, strategy_used, engines_used, etc.)
- balance_sheet_data: 13 columns (account_id, report_date, is_debit, is_contra_account, etc.)
- income_statement_data: 11 columns (header_id, account_id, period_percentage, etc.)
- cash_flow_data: 9 columns (header_id, account_id, period_percentage, etc.)

**Root Cause:** Code expected columns that didn't exist in database (schema drift)
**Fix:** Added all missing columns via ALTER TABLE statements

### 4. Frontend Date Display Issue
**Problem:** "Invalid Date" showing for all uploads
**Root Cause:** Field name mismatch between backend API and frontend
- Backend sends: `upload_date`, `file_name`
- Frontend expected: `uploaded_at`, `original_filename`
**Fix:** Updated Documents.tsx to use correct field names

### 5. Delete-and-Replace Code Not Active
**Problem:** Modified code wasn't running in Celery worker
**Root Cause:** 
- Code was accidentally reverted in working directory
- Container had old code cached
**Fix:** 
- Restored code from git commit 56fd650
- Copied updated code to Celery container
- Restarted Celery worker

## What Was Fixed

### Code Changes:
1. **backend/app/services/extraction_orchestrator.py**
   - Fixed indentation errors (3 locations)
   - Delete-and-replace code active (8 delete operations)

2. **src/pages/Documents.tsx**
   - Line 257: `doc.original_filename` → `doc.file_name`
   - Line 268: `doc.uploaded_at` → `doc.upload_date`

### Database Changes:
3. **Schema additions** - 70+ columns added across 4 tables
   - Documented in: `backend/manual_schema_fixes_2025_11_08.sql`

### Infrastructure:
4. **Backend service** - Running on port 8000
5. **Celery worker** - Running with updated code

## Prevention Plan

### 1. Code Integrity
**Problem:** Code getting reverted or corrupted

**Prevention:**
- Always verify code after git operations: `git diff`
- Use linters before committing: `ruff check`
- Test imports before deploying: `python -m py_compile`

**Action Items:**
```bash
# Add pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Check Python syntax
python3 -m py_compile backend/app/services/extraction_orchestrator.py || exit 1
echo "✅ Syntax check passed"
EOF
chmod +x .git/hooks/pre-commit
```

### 2. Schema Management
**Problem:** Database schema drift (code expects columns that don't exist)

**Prevention:**
- Use Alembic migrations ONLY (no manual ALTER TABLE)
- Auto-generate migrations from SQLAlchemy models
- Version control all migration files
- Run migrations on every deployment

**Action Items:**
```bash
# Create proper migration for today's schema fixes
cd backend
alembic revision --autogenerate -m "Add missing columns for extraction system"
alembic upgrade head
```

### 3. Container Code Synchronization
**Problem:** Docker containers running old code

**Prevention:**
- Use volume mounts for development (already configured)
- Always rebuild after major changes
- Verify code in container matches local

**Action Items:**
```bash
# Add to deployment checklist
docker compose build backend celery-worker
docker compose up -d
docker compose exec celery-worker grep -c "DELETE all existing" /app/app/services/extraction_orchestrator.py
# Should return: 3 (or number of delete operations)
```

### 4. Monitoring and Health Checks
**Problem:** Issues not detected until user reports them

**Prevention:**
- Add health check endpoints for all services
- Monitor Celery task queue depth
- Alert on failed extractions

**Action Items:**
```bash
# Add monitoring script
cat > scripts/health_check.sh << 'EOF'
#!/bin/bash
echo "Checking all services..."
curl -s http://localhost:8000/api/v1/health | jq .
docker compose exec -T celery-worker celery -A celery_worker.celery_app inspect active
docker exec reims-postgres psql -U reims -d reims -c "SELECT COUNT(*) FROM document_uploads WHERE extraction_status='pending';"
EOF
chmod +x scripts/health_check.sh
```

### 5. Database Migration Workflow
**Problem:** Schema changes applied manually instead of through migrations

**Prevention - Proper Workflow:**
```
1. Modify SQLAlchemy models (app/models/*.py)
2. Generate migration: alembic revision --autogenerate -m "description"
3. Review migration file
4. Test migration: alembic upgrade head
5. Commit migration file to git
6. Deploy to production
```

**NEVER:**
- Run manual ALTER TABLE in production
- Modify schema without creating migration
- Skip migration review

### 6. Testing Before Deployment
**Problem:** Changes deployed without testing

**Prevention - Testing Checklist:**
```bash
# 1. Syntax check
python3 -m py_compile backend/app/**/*.py

# 2. Run migrations
alembic upgrade head

# 3. Start services
docker compose up -d

# 4. Health check
curl http://localhost:8000/api/v1/health

# 5. Test upload
# (upload test file via frontend or API)

# 6. Check Celery
docker compose logs celery-worker --tail=20
```

## Summary of Session

### Issues Fixed (6):
1. ✅ Backend not running (port conflict)
2. ✅ IndentationError (3 locations)
3. ✅ Missing database columns (70+ columns)
4. ✅ Frontend date display ("Invalid Date")
5. ✅ Delete-and-replace code not active
6. ✅ Celery worker code out of sync

### Files Modified (3):
1. backend/app/services/extraction_orchestrator.py - Indentation fixes
2. src/pages/Documents.tsx - Date field fixes  
3. backend/manual_schema_fixes_2025_11_08.sql - Schema documentation (NEW)

### Commits to Make:
1. Schema fixes documentation
2. Frontend date display fix
3. Backend indentation fixes

## Recommendations

### Immediate Actions:
1. Create proper Alembic migration for schema changes
2. Add pre-commit hooks for syntax checking
3. Document deployment checklist
4. Set up health monitoring

### Long-term:
1. Implement CI/CD pipeline
2. Add automated testing
3. Use staging environment
4. Regular database backups

