# Docker Files Updated for Cash Flow Gap Fix

**Date:** November 7, 2025  
**Purpose:** Ensure all Docker initialization paths include the new comprehensive cash flow seed file

---

## Files Updated

### 1. ✅ docker-compose.yml
**Location:** `/home/gurpyar/Documents/R/REIMS2/docker-compose.yml`

**Changes:**
- Added comprehensive cash flow seed file to db-init container initialization

**Lines Modified:** 70-72
```yaml
echo 'Seeding comprehensive cash flow accounts (125+ accounts)...';
PGPASSWORD=$$POSTGRES_PASSWORD psql -h $$POSTGRES_SERVER -U $$POSTGRES_USER -d $$POSTGRES_DB -f scripts/seed_cash_flow_accounts_comprehensive.sql;
```

**Impact:** db-init container now seeds 154 cash flow accounts on fresh deployment

---

### 2. ✅ backend/entrypoint.sh
**Location:** `/home/gurpyar/Documents/R/REIMS2/backend/entrypoint.sh`

**Changes:**
- Added comprehensive cash flow seed file to backend entrypoint initialization

**Lines Modified:** 62-63
```bash
echo "🌱 Seeding comprehensive cash flow accounts (125+ accounts)..."
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_cash_flow_accounts_comprehensive.sql
```

**Impact:** Backend container initialization now seeds 154 cash flow accounts if RUN_MIGRATIONS=true and SEED_DATABASE=true

---

## Initialization Flow

### Path 1: db-init Container (Fresh Deployment)
```
docker-compose up -d
  ↓
db-init container starts
  ↓
Runs migrations (alembic upgrade head)
  ↓
Seeds database:
  1. Balance sheet accounts
  2. Income statement accounts
  3. Validation rules
  4. Extraction templates
  5. Lenders
  6. Cash flow specific accounts (23)
  7. ✨ NEW: Comprehensive cash flow accounts (125+)
  ↓
Exits successfully
  ↓
Backend and other services start
```

### Path 2: Backend Entrypoint (If RUN_MIGRATIONS=true)
```
backend container starts
  ↓
entrypoint.sh runs
  ↓
Waits for PostgreSQL
  ↓
If RUN_MIGRATIONS=true:
  - Runs alembic upgrade head
  - If SEED_DATABASE=true:
    - Seeds all accounts including comprehensive cash flow
  ↓
Starts uvicorn
```

---

## Verification

### Check Seed File Exists
```bash
docker exec reims-backend ls -la /app/scripts/seed_cash_flow_accounts_comprehensive.sql

# Should show the file (~18KB)
```

### Check Seed File Loads
```bash
# Fresh deployment
docker-compose down -v
docker-compose build
docker-compose up -d

# Wait 60 seconds, then check
docker exec -it reims-postgres psql -U reims -d reims -c \
  "SELECT COUNT(*) as total FROM chart_of_accounts WHERE 'cash_flow' = ANY(document_types);"

# Should return ~154 accounts (was 29)
```

### Check Logs
```bash
# db-init logs
docker logs reims-db-init 2>&1 | grep "comprehensive"

# Should show:
# 🌱 Seeding comprehensive cash flow accounts (125+ accounts)...

# backend logs
docker logs reims-backend 2>&1 | grep "comprehensive"

# If RUN_MIGRATIONS=true, should show same message
```

---

## Files That Don't Need Updates

### ✅ backend/Dockerfile
- Uses `COPY . .` which automatically includes new seed file
- No changes needed

### ✅ backend/celery-entrypoint.sh
- Celery worker doesn't handle database initialization
- No changes needed

### ✅ backend/flower-entrypoint.sh
- Flower monitoring doesn't handle database initialization
- No changes needed

### ✅ Dockerfile.frontend
- Frontend has no database access
- No changes needed

---

## Summary

**Docker Files Updated:** 2 files
1. `docker-compose.yml` - db-init container
2. `backend/entrypoint.sh` - backend container

**Purpose:** Both initialization paths now seed 154 cash flow accounts

**Result:** Consistent database state regardless of initialization method

**Testing:** Ready to deploy with `docker-compose down -v && docker-compose build && docker-compose up -d`

---

## Next Steps

1. Rebuild containers: `docker-compose build`
2. Fresh start: `docker-compose down -v && docker-compose up -d`
3. Verify account count: Should be ~154 cash flow accounts
4. Re-extract cash flow documents
5. Verify match rate: Should be 95%+

---

**Status:** ✅ ALL DOCKER FILES UPDATED AND READY

