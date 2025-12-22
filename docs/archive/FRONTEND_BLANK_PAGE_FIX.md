# 🔧 Frontend Blank Page - Troubleshooting Guide

**Issue:** Frontend shows blank white page at http://localhost:5173  
**Status:** Container running, but page not rendering

---

## 🔍 Immediate Diagnosis Steps

### Step 1: Check Browser Console for Errors

**In Firefox:**
1. Press `F12` to open Developer Tools
2. Click **"Console"** tab
3. Look for **RED error messages**

**Common errors to look for:**
- `Uncaught SyntaxError`
- `Failed to fetch module`
- `Cannot read property of undefined`
- `Network error`

📸 **Please check and report what error you see!**

---

### Step 2: Hard Refresh the Page

The issue might be cached JavaScript. Try:

**Method 1: Hard Refresh**
```
Ctrl + Shift + R  (Linux/Windows)
Cmd + Shift + R   (Mac)
```

**Method 2: Clear Cache**
1. Press `Ctrl + Shift + Delete`
2. Select "Cached Web Content"
3. Click "Clear Now"
4. Refresh page with `Ctrl + R`

---

### Step 3: Check Network Tab

1. Open Developer Tools (`F12`)
2. Click **"Network"** tab
3. Refresh page (`Ctrl + R`)
4. Look for:
   - **Failed requests (red)** - API connection issues
   - **404 errors** - Missing files
   - **CORS errors** - Cross-origin issues

---

## 🔧 Quick Fixes

### Fix 1: Restart Frontend Container (Already Done ✅)

```bash
cd /home/gurpyar/Documents/R/REIMS2
docker compose restart frontend
```

**Then refresh browser:**
```
Ctrl + Shift + R
```

---

### Fix 2: Check Backend API Connection

The frontend might be failing because it can't reach the backend:

```bash
# Test backend health
curl http://localhost:8000/api/v1/health
```

**Expected:** `{"status":"healthy","api":"ok","database":"connected","redis":"connected"}`

**If backend is down:**
```bash
docker compose restart backend
```

---

### Fix 3: Rebuild Frontend Container

If the above doesn't work, rebuild:

```bash
cd /home/gurpyar/Documents/R/REIMS2
docker compose down frontend
docker compose build frontend
docker compose up -d frontend
```

**Wait 30 seconds, then refresh browser with `Ctrl + Shift + R`**

---

### Fix 4: Check Frontend Logs

```bash
docker logs reims-frontend -f
```

**Look for:**
- ✅ `ready in XXX ms` - Good, server started
- ❌ `Error:` lines - JavaScript errors
- ❌ `ECONNREFUSED` - Can't connect to backend

---

## 🐛 Common Issues & Solutions

### Issue 1: "CORS Error" in Console

**Solution:** Backend CORS configuration issue

```bash
# Check backend is allowing localhost:5173
docker logs reims-backend | grep CORS
```

**Fix:** Backend should already allow `http://localhost:5173`

---

### Issue 2: "Failed to load module" Error

**Cause:** Build issue or missing dependencies

**Solution:**
```bash
cd /home/gurpyar/Documents/R/REIMS2
docker compose exec frontend npm install
docker compose restart frontend
```

---

### Issue 3: "Cannot read property 'render' of null"

**Cause:** React can't find the root element

**Solution:** Check index.html has `<div id="root"></div>`

```bash
curl http://localhost:5173 | grep root
```

Should show: `<div id="root"></div>`

---

### Issue 4: Backend Not Responding

**Check:**
```bash
curl http://localhost:8000/api/v1/health
```

**If no response:**
```bash
docker logs reims-backend --tail 50
docker compose restart backend
```

---

## 🔍 Advanced Diagnostics

### Check All Services Status

```bash
docker compose ps
```

**All should be "Up":**
- reims-frontend
- reims-backend
- reims-postgres
- reims-redis
- reims-minio
- reims-celery-worker
- reims-flower
- reims-pgadmin

---

### Test Frontend Container Directly

```bash
# Enter frontend container
docker exec -it reims-frontend /bin/sh

# Check if node_modules exist
ls -la /app/node_modules | head -20

# Check if source files exist
ls -la /app/src/

# Exit
exit
```

---

### View Full Frontend Logs

```bash
docker logs reims-frontend --tail 100
```

**Look for:**
- Vite server started
- Port 5173 listening
- Any error messages

---

## 📋 Information to Collect

Please provide the following to help diagnose:

1. **Browser Console Errors** (F12 → Console tab)
   - Any red error messages?
   
2. **Network Tab Status** (F12 → Network tab → Refresh)
   - Any failed requests?
   - What's the status of `main.tsx`?

3. **Backend Health Check**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
   Output?

4. **Frontend Logs**
   ```bash
   docker logs reims-frontend --tail 30
   ```
   Any errors?

---

## 🚀 Nuclear Option: Full Restart

If nothing works, do a complete restart:

```bash
cd /home/gurpyar/Documents/R/REIMS2

# Stop everything
docker compose down

# Rebuild frontend
docker compose build frontend

# Start everything
docker compose up -d

# Wait 60 seconds for all services
sleep 60

# Check status
docker compose ps

# Open browser and hard refresh
# http://localhost:5173 (Ctrl + Shift + R)
```

---

## ✅ What Should Work

After fixes, you should see:

1. **Browser:** Login/Register form (not blank page)
2. **Console:** No red errors (warnings are OK)
3. **Network:** All requests successful (green/200 status)
4. **Backend:** Health check returns healthy

---

## 📞 Next Steps

**Right now, please do:**

1. ✅ Frontend container restarted (already done)
2. **Hard refresh your browser:** `Ctrl + Shift + R`
3. **Check console:** Press `F12` → Console tab
4. **Report:** What errors do you see?

---

**The frontend container is running correctly. The blank page is likely a browser-side JavaScript error that will be visible in the developer console (F12).**

Let me know what you find in the console! 🔍



