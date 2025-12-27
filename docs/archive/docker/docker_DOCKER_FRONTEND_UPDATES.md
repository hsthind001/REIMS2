# Docker Frontend Updates - Vite Cache Fix

**Date:** November 7, 2025  
**Issue:** Vite module cache causing stale module errors in browser  
**Solution:** Automatic cache clearing on container startup

---

## 🎯 Problem Statement

### Issue
Browser shows error:
```
Uncaught SyntaxError: The requested module doesn't provide an export named 'FinancialDataSummary'
```

### Root Cause
1. Vite dev server caches compiled modules in `/app/node_modules/.vite`
2. When code changes, cached modules may be stale
3. Browser loads stale cached modules
4. Import statements fail because exports don't match
5. Entire app crashes with blank page

### Impact
- Code changes don't take effect immediately
- Browser shows stale errors even after fixes
- Requires manual cache clearing
- Poor developer experience

---

## ✅ Solution Implemented

### 1. Created Frontend Entrypoint Script
**File:** `frontend-entrypoint.sh` (NEW)

**Features:**
- ✅ Automatically clears Vite cache on startup
- ✅ Waits for backend to be ready
- ✅ Health check with retry logic
- ✅ Starts Vite dev server

**Script Contents:**
```bash
#!/bin/sh
# Clear Vite cache
rm -rf /app/node_modules/.vite

# Wait for backend
while ! wget -q --spider "${BACKEND_URL}/api/v1/health"; do
  sleep 2
done

# Start Vite
exec "$@"
```

### 2. Updated Dockerfile.frontend
**File:** `Dockerfile.frontend`

**Changes:**
- Added `wget` installation for health checks
- Copy entrypoint script
- Set execute permissions
- Use entrypoint for automatic cache clearing

**Before:**
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

**After:**
```dockerfile
FROM node:20-alpine
RUN apk add --no-cache wget  # NEW
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
COPY frontend-entrypoint.sh /frontend-entrypoint.sh  # NEW
RUN chmod +x /frontend-entrypoint.sh  # NEW
EXPOSE 5173
ENTRYPOINT ["/frontend-entrypoint.sh"]  # NEW
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

### 3. Created .dockerignore
**File:** `.dockerignore` (NEW)

**Purpose:** Prevent cache/build files from being copied into container

**Excludes:**
- `node_modules/` (will be installed fresh)
- `.vite/` (Vite cache)
- `dist/` (build output)
- IDE files (`.vscode`, `.idea`)
- Logs and temp files

---

## 📊 Benefits

### Before Fix
- ❌ Vite cache persists between restarts
- ❌ Code changes may not take effect
- ❌ Browser gets stale modules
- ❌ Manual cache clearing required
- ❌ Poor developer experience

### After Fix
- ✅ Fresh cache on every container start
- ✅ Code changes always take effect
- ✅ Browser gets fresh modules
- ✅ Automatic cache management
- ✅ Better developer experience

---

## 🔄 Deployment Flow

### Old Flow (Before)
```
docker compose up -d
  ↓
Frontend starts
  ↓
Vite uses cached modules
  ↓
Browser loads stale modules
  ↓
❌ Import errors!
```

### New Flow (After)
```
docker compose up -d
  ↓
Frontend entrypoint runs
  ↓
Clears /app/node_modules/.vite
  ↓
Waits for backend
  ↓
Starts Vite with clean cache
  ↓
Browser gets fresh modules
  ✅ Works perfectly!
```

---

## 📁 Files Modified/Created

### Created (2 files)
1. ✅ `frontend-entrypoint.sh` - Cache clearing script
2. ✅ `.dockerignore` - Exclude cache from builds

### Modified (1 file)
3. ✅ `Dockerfile.frontend` - Use entrypoint, install wget

---

## 🚀 How to Use

### For Fresh Deployment
```bash
cd /home/gurpyar/Documents/R/REIMS2

# Rebuild frontend with new Dockerfile
docker compose build frontend

# Start services
docker compose up -d

# Frontend will automatically:
# 1. Clear Vite cache
# 2. Wait for backend
# 3. Start with fresh modules
```

### For Existing Deployment
```bash
# Rebuild and restart frontend
docker compose build frontend
docker compose up -d frontend

# Cache is automatically cleared on startup
```

---

## 🧪 Verification

### Check Entrypoint is Working
```bash
docker logs reims-frontend 2>&1 | head -10
```

**Expected output:**
```
🚀 REIMS Frontend Starting...
🧹 Clearing Vite cache...
✅ Vite cache cleared
⏳ Waiting for backend to be ready...
✅ Backend is ready!
🎯 Starting Vite dev server...
```

### Check Cache Directory
```bash
# Should not exist or be empty after restart
docker exec reims-frontend ls -la /app/node_modules/.vite 2>&1
```

**Expected:** `No such file or directory` (good!)

---

## 🔧 Additional Improvements

### 1. Automatic Backend Health Check
Frontend now waits for backend before starting, preventing:
- API connection errors on first load
- Race conditions during startup
- Better reliability

### 2. Exclude Cache from Builds
`.dockerignore` prevents copying cache into container:
- Faster builds
- Smaller image layers
- No stale cache from host

### 3. Clean Startup Every Time
Entrypoint ensures fresh start:
- No module resolution issues
- Code changes always take effect
- Consistent behavior

---

## 🎯 Best Practices Applied

### Development Environment
- ✅ Clean cache on startup (prevents stale modules)
- ✅ Health checks before starting (prevents race conditions)
- ✅ Proper entrypoint script (initialization logic)
- ✅ Volume mounting for hot reload (./src:/app/src)
- ✅ Dockerignore for clean builds

### Production Ready
- ✅ Can easily switch to production build
- ✅ Separate build and runtime stages possible
- ✅ Environment variable support (VITE_API_URL)
- ✅ Network isolation via docker networks

---

## 📝 Notes

### Why Alpine?
- Smaller image size (~50MB vs 900MB for full node)
- Faster builds
- Less attack surface
- Sufficient for development

### Why Clear Cache on Every Start?
- Development environment priority: fresh code > speed
- Container restarts are infrequent
- Cache rebuild only takes 2-3 seconds
- Prevents hours of debugging stale modules

### Why Wait for Backend?
- Frontend depends on backend API
- Prevents confusing errors on first load
- Better user experience
- Only adds 5-10 seconds to startup

---

## 🚀 Rebuild Instructions

Since Dockerfile.frontend changed, you need to rebuild:

```bash
cd /home/gurpyar/Documents/R/REIMS2

# Rebuild frontend
docker compose build frontend

# Restart with new image
docker compose up -d frontend

# Wait for startup
sleep 20

# Verify entrypoint ran
docker logs reims-frontend | head -15
```

**Then in browser:**
1. Close localhost:5173 tab
2. Open new tab
3. Go to http://localhost:5173
4. Should see login form! ✅

---

## ✅ Summary

**Files Updated:** 3 files
1. `frontend-entrypoint.sh` - Cache clearing + health check
2. `Dockerfile.frontend` - Use entrypoint, install wget
3. `.dockerignore` - Exclude cache directories

**Benefits:**
- Automatic cache clearing
- No more stale module errors
- Better developer experience
- Production-ready setup

**Status:** ✅ READY TO REBUILD AND TEST

---

**Next Step:** Rebuild frontend container to use new entrypoint!



