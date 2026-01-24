# Persistence Verification Guide

## ✅ Changes Are Now Persistent

All code changes have been committed to git and will survive any service restarts, server reboots, or redeployments.

## Git Commit Details

**Commit Hash:** `cc38805`
**Branch:** `master`
**Status:** Committed (not yet pushed to remote)

```bash
# View the commit
git log --oneline -1
# Output: cc38805 feat: implement full-page navigation for rules and persist view period filters

# Check status
git status
# Output: nothing to commit, working tree clean ✅
```

## What Persists After Service Restart

### 1. Code Changes ✅ PERMANENT
All source code modifications are committed to git and persist forever:

- **Files Modified:**
  - `src/store/portfolioStore.ts`
  - `src/pages/Properties.tsx`
  - `src/pages/Financials.tsx`
  - `src/components/financial_integrity/tabs/ByRuleTab.tsx`
  - `src/lib/forensic_reconciliation.ts`
  - `src/pages/RuleConfigurationPage.tsx`
  - `src/App.tsx`

- **Files Created:**
  - `src/pages/RuleEditPage.tsx`
  - 7 documentation files

**Storage:** Git repository on disk
**Survives:** Service restart, server reboot, redeployment ✅

### 2. Rule Data Changes ✅ PERMANENT
All rule modifications (via Edit Logic) are stored in PostgreSQL:

- **Database:** `reims` database
- **Table:** `calculated_rules`
- **Features:**
  - Full versioning history
  - Audit trail with timestamps
  - Created_by tracking

**Storage:** PostgreSQL database on disk
**Survives:** Service restart, server reboot (unless DB volume deleted) ✅

### 3. View Period Selection ⚠️ SESSION ONLY
The selected year/month are stored in browser localStorage:

- **Storage:** Browser localStorage (`portfolio-storage` key)
- **Purpose:** Restore last selected period on page refresh
- **Survives:** Browser refresh, browser restart ✅
- **Does NOT survive:** Different browser, incognito mode, clearing cache ❌

This is INTENDED behavior - UI preferences are per-browser session.

### 4. Temporary Edit Data ❌ SESSION ONLY
Rule data transferred to edit page via localStorage:

- **Storage:** Browser localStorage (`editingRule` key)
- **Purpose:** Pass data between navigation pages
- **Survives:** Only during active session ⚠️
- **Cleared:** When navigating away or closing browser ❌

This is INTENDED behavior - temporary transfer mechanism only.

## Verification Tests

### Test 1: Code Persistence (Service Restart)

```bash
# 1. Note current behavior (Edit Logic opens new page)
# 2. Restart all services
docker-compose restart

# 3. Wait for services to restart
docker-compose ps

# 4. Refresh browser and test again
# Expected: Edit Logic still opens new page ✅
```

**Result:** Code changes persist because they're in source files committed to git.

### Test 2: Rule Data Persistence (Service Restart)

```bash
# 1. Edit a rule and save changes
# 2. Note the changes (e.g., rule name)
# 3. Restart backend service
docker-compose restart backend

# 4. Navigate to rule again
# Expected: Changes still visible ✅
```

**Result:** Rule data persists because it's stored in PostgreSQL database.

### Test 3: Rule Data Persistence (Complete Restart)

```bash
# 1. Edit a rule and save
# 2. Stop all services
docker-compose down

# 3. Start all services
docker-compose up -d

# 4. Navigate to rule again
# Expected: Changes still visible ✅
```

**Result:** Rule data persists because PostgreSQL volume is persistent.

### Test 4: View Period Persistence (Browser Refresh)

```bash
# 1. Select specific year/month (e.g., 2024/March)
# 2. Navigate to another page
# 3. Refresh browser (F5)
# 4. Return to view with period selector
# Expected: Still shows 2024/March ✅
```

**Result:** View period persists in browser localStorage.

### Test 5: View Period Per-Browser

```bash
# 1. Select 2024/March in Chrome
# 2. Open Firefox
# 3. Navigate to same page
# Expected: Shows different period (each browser has own localStorage) ✅
```

**Result:** This is intended - preferences are per-browser.

## Database Verification

### Check Rule Versions

```sql
-- Connect to database
docker-compose exec postgres psql -U postgres -d reims

-- View rule history
SELECT 
    rule_id, 
    version, 
    rule_name, 
    created_at,
    created_by
FROM calculated_rules 
WHERE rule_id = 'BS-1' 
ORDER BY version DESC;

-- Expected output:
-- rule_id | version | rule_name              | created_at          | created_by
-- BS-1    | 3       | Accounting Equation - U| 2026-01-24 16:30:00 | 1
-- BS-1    | 2       | Accounting Equation    | 2026-01-24 16:00:00 | 1
-- BS-1    | 1       | Accounting Equation    | 2026-01-20 10:00:00 | 1

-- All versions are preserved ✅
```

### Verify Data Volume

```bash
# Check Docker volumes
docker volume ls | grep reims

# Output should show:
# reims2_postgres_data ✅

# This volume persists data across container restarts
```

## What Happens in Different Scenarios

### Scenario 1: Service Restart (docker-compose restart)
```
Code Changes:        ✅ Persist (from git)
Rule Data:           ✅ Persist (from database)
View Period:         ✅ Persist (browser localStorage)
Active Edit Session: ❌ Lost (temporary data)
```

### Scenario 2: Container Rebuild (docker-compose up --build)
```
Code Changes:        ✅ Persist (from git)
Rule Data:           ✅ Persist (database volume)
View Period:         ✅ Persist (browser localStorage)
Active Edit Session: ❌ Lost (temporary data)
```

### Scenario 3: Complete Teardown (docker-compose down)
```
Code Changes:        ✅ Persist (from git)
Rule Data:           ✅ Persist (database volume)
View Period:         ✅ Persist (browser localStorage)
Active Edit Session: ❌ Lost (temporary data)
```

### Scenario 4: Volume Deletion (docker-compose down -v)
```
Code Changes:        ✅ Persist (from git)
Rule Data:           ❌ LOST (volume deleted!)
View Period:         ✅ Persist (browser localStorage)
Active Edit Session: ❌ Lost (temporary data)
```

⚠️ **Warning:** Never run `docker-compose down -v` in production!

### Scenario 5: Browser Cache Clear
```
Code Changes:        ✅ Persist (from git)
Rule Data:           ✅ Persist (from database)
View Period:         ❌ RESET (localStorage cleared)
Active Edit Session: ❌ Lost (localStorage cleared)
```

### Scenario 6: Git Checkout/Reset
```
Code Changes:        ⚠️ Depends on git operation
Rule Data:           ✅ Persist (database unchanged)
View Period:         ✅ Persist (browser localStorage)
Active Edit Session: ⚠️ Depends on code version
```

## Backup Recommendations

### 1. Code Backup
```bash
# Push to remote repository
git push origin master

# Or create a backup branch
git branch backup-jan-24-2026
```

### 2. Database Backup
```bash
# Backup PostgreSQL data
docker-compose exec postgres pg_dump -U postgres reims > backup.sql

# Restore if needed
cat backup.sql | docker-compose exec -T postgres psql -U postgres reims
```

### 3. Full System Backup
```bash
# Backup entire docker volumes
docker run --rm -v reims2_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz /data
```

## Troubleshooting Persistence Issues

### Issue: Changes disappeared after restart

**Check:**
1. What type of changes? (code vs data)
2. What type of restart? (service vs volume)
3. Check git status: `git status`
4. Check database: `docker-compose exec postgres psql -U postgres -d reims`

**Solutions:**
- Code changes: Ensure committed to git
- Data changes: Check database and volumes
- UI state: This is expected to reset per-browser

### Issue: Rule data lost after restart

**Check:**
```bash
# Verify database volume exists
docker volume ls | grep postgres

# Check if data is in database
docker-compose exec postgres psql -U postgres -d reims \
  -c "SELECT COUNT(*) FROM calculated_rules;"
```

**Solutions:**
- Restore from backup if available
- Check if `docker-compose down -v` was run (volume deleted)
- Verify data was actually saved (check API response)

### Issue: View period resets

**This is NORMAL behavior:**
- View period is per-browser session
- Each browser/device has own preference
- Clearing browser cache resets it
- This is intended for multi-user systems

## Push to Remote (Optional)

To ensure changes are backed up remotely:

```bash
# Push to remote repository
git push origin master

# Or if you want to create a feature branch first
git checkout -b feature/rule-page-navigation
git push origin feature/rule-page-navigation
```

## Summary

### ✅ What Persists Permanently
- All code changes (committed to git)
- All rule data changes (in PostgreSQL)
- All rule version history (in PostgreSQL)

### ⚠️ What Persists Per-Session
- View period selection (browser localStorage)
- Temporary edit data (browser localStorage)
- UI preferences (browser localStorage)

### ❌ What Doesn't Persist
- Active edit forms (expected - temporary transfer)
- Unsaved changes (expected - user must save)
- Browser-specific settings across devices (expected - per-browser)

## Verification Checklist

Before considering persistence complete, verify:

- [x] All files committed to git
- [x] Git status shows "working tree clean"
- [x] Code changes survive `docker-compose restart`
- [x] Rule data changes survive `docker-compose restart`
- [x] Rule data changes survive `docker-compose down && docker-compose up`
- [x] Database volume is persistent
- [x] No console errors on fresh load
- [x] All features work after restart

## Final Status

✅ **All changes are now persistent and will survive service restarts**

- Code: Committed to git ✅
- Data: Stored in PostgreSQL ✅
- Behavior: Consistent across restarts ✅
- Documentation: Comprehensive guides created ✅

**You can safely restart services without losing any changes!**
