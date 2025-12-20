# Dependency and Health Check Fixes

**Date:** December 20, 2024  
**Issue:** Missing dependencies and health check failures  
**Solution:** Automatic dependency detection and health check tool installation

---

## 🎯 Problems Identified

### Issue 1: Frontend Dependency Missing
- **Symptom:** `chart.js` dependency was missing from `node_modules` even though it was in `package.json`
- **Root Cause:** 
  - `package.json` is mounted as a volume in `docker-compose.yml`
  - When new dependencies are added to `package.json`, the container doesn't automatically rebuild
  - The anonymous volume `/app/node_modules` preserves old dependencies
  - Manual `npm install` was required inside the container

### Issue 2: Backend Health Check Failure
- **Symptom:** Backend shows as "unhealthy" in Docker health checks
- **Root Cause:**
  - Health check in `docker-compose.yml` uses `curl` command
  - `curl` was not installed in the backend container
  - Health check fails even though the API is working correctly

---

## ✅ Solutions Implemented

### Solution 1: Automatic Frontend Dependency Management

**File:** `frontend-entrypoint.sh`

**Enhancements:**
1. **Dependency Detection:**
   - Checks if `node_modules` exists and has content
   - Compares modification times of `package.json`/`package-lock.json` vs `node_modules`
   - Verifies critical packages (chart.js, react) exist
   - Automatically installs missing dependencies on startup

2. **Smart Installation:**
   - Only installs if dependencies are actually missing
   - Uses `npm install --prefer-offline --no-audit` for faster installs
   - Preserves existing dependencies when not needed

**Implementation:**
```bash
# Check for missing dependencies and install them
if [ ! -d "/app/node_modules" ] || [ ! "$(ls -A /app/node_modules 2>/dev/null)" ]; then
  npm install --prefer-offline --no-audit
elif [ package.json is newer than node_modules ]; then
  npm install --prefer-offline --no-audit
elif [ critical packages missing ]; then
  npm install --prefer-offline --no-audit
fi
```

**File:** `Dockerfile.frontend`

**Changes:**
- Added entrypoint script copy and execution
- Entrypoint runs before CMD, ensuring dependencies are checked on every startup

```dockerfile
COPY frontend-entrypoint.sh /frontend-entrypoint.sh
RUN chmod +x /frontend-entrypoint.sh
ENTRYPOINT ["/frontend-entrypoint.sh"]
```

### Solution 2: Backend Health Check Fix

**File:** `backend/Dockerfile`

**Changes:**
- Added `curl` to the list of installed packages
- Health check in `docker-compose.yml` now works correctly

```dockerfile
RUN apt-get update && apt-get install -y postgresql-client redis-tools curl && rm -rf /var/lib/apt/lists/*
```

**Result:**
- Health check command `curl -f http://localhost:8000/api/v1/health` now works
- Backend shows as "healthy" in Docker status

---

## 📊 Benefits

### Before Fixes
- ❌ Manual intervention required for new dependencies
- ❌ Health checks showing false negatives
- ❌ Developer confusion about service status
- ❌ Time wasted debugging dependency issues

### After Fixes
- ✅ Automatic dependency installation on startup
- ✅ Accurate health check status
- ✅ No manual intervention needed
- ✅ Better developer experience
- ✅ Prevents future dependency issues

---

## 🔄 How It Works

### Frontend Startup Flow
```
Container Starts
    ↓
Entrypoint Script Runs
    ↓
Check node_modules exists?
    ↓
Check package.json modified?
    ↓
Check critical packages exist?
    ↓
Install missing dependencies (if needed)
    ↓
Clear Vite cache
    ↓
Wait for backend
    ↓
Start Vite dev server
```

### Backend Health Check Flow
```
Docker Health Check
    ↓
Runs: curl -f http://localhost:8000/api/v1/health
    ↓
curl is available (installed in Dockerfile)
    ↓
Health check succeeds
    ↓
Container shows as "healthy"
```

---

## 🚀 Usage

### Adding New Dependencies

**Before (Manual Steps):**
1. Add dependency to `package.json`
2. Rebuild container: `docker compose build frontend`
3. Or manually install: `docker exec reims-frontend npm install`

**After (Automatic):**
1. Add dependency to `package.json`
2. Restart container: `docker compose restart frontend`
3. Entrypoint automatically detects and installs

### Verifying Fixes

**Check Frontend Dependencies:**
```bash
docker logs reims-frontend 2>&1 | grep -E "(dependencies|Dependencies)"
```

**Expected output:**
```
🔍 Checking for missing dependencies...
✅ All dependencies are installed
```

**Check Backend Health:**
```bash
docker ps --filter "name=reims-backend" --format "{{.Status}}"
```

**Expected output:**
```
Up X minutes (healthy)
```

---

## 📁 Files Modified

### Created/Modified (3 files)
1. ✅ `frontend-entrypoint.sh` - Enhanced with dependency detection
2. ✅ `Dockerfile.frontend` - Added entrypoint script
3. ✅ `backend/Dockerfile` - Added curl installation

---

## 🧪 Testing

### Test 1: Add New Dependency
```bash
# Add a new dependency to package.json
echo '"new-package": "^1.0.0"' >> package.json

# Restart frontend
docker compose restart frontend

# Check logs
docker logs reims-frontend | grep -E "(dependencies|new-package)"
```

### Test 2: Backend Health Check
```bash
# Check backend health status
docker ps --filter "name=reims-backend"

# Should show: Up X minutes (healthy)
```

### Test 3: Verify curl in Backend
```bash
# Check if curl is available
docker exec reims-backend curl --version

# Should show curl version
```

---

## 🎯 Prevention Strategy

### Future-Proofing
1. **Dependency Management:**
   - Entrypoint automatically handles new dependencies
   - No manual steps required
   - Works with volume mounts

2. **Health Checks:**
   - All required tools installed in Dockerfiles
   - Health checks use available tools
   - Consistent across all services

3. **Documentation:**
   - This file documents the fixes
   - Future developers understand the approach
   - Prevents regression

---

## 📝 Notes

### Why This Approach?
- **Automatic:** No manual intervention needed
- **Efficient:** Only installs when necessary
- **Reliable:** Multiple checks ensure dependencies are present
- **Maintainable:** Clear logic in entrypoint script

### Trade-offs
- **Startup Time:** Slight increase if dependencies need installation (only on first run or when changed)
- **Disk Space:** Minimal impact (dependencies are in anonymous volume)

### Best Practices Applied
- ✅ Dependency checking before startup
- ✅ Health check tools installed in images
- ✅ Clear logging for debugging
- ✅ Idempotent operations (safe to run multiple times)

---

## 🔗 Related Files

- `docker-compose.yml` - Health check configuration
- `package.json` - Frontend dependencies
- `backend/Dockerfile` - Backend image definition
- `Dockerfile.frontend` - Frontend image definition
- `frontend-entrypoint.sh` - Frontend startup script

---

**Status:** ✅ Implemented and tested  
**Impact:** Prevents future dependency and health check issues  
**Maintenance:** Automatic, no ongoing maintenance required

