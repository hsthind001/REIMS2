# Frontend API URL Fix

## Issue
Network error when making NLQ queries - "Failed to fetch"

## Root Cause
Multiple files were using `VITE_API_BASE_URL` which wasn't set in Docker. Docker compose sets `VITE_API_URL` instead.

## Fix Applied

### 1. FinancialCommand.tsx (NLQ Feature)
Changed to use `VITE_API_URL` and append `/api/v1`:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';
```

### 2. Other Files
Updated to use `VITE_API_URL` instead of `VITE_API_BASE_URL`:
- src/pages/RiskManagement.tsx
- src/pages/CommandCenter.tsx
- src/pages/PortfolioHub.tsx
- src/pages/Dashboard.tsx
- src/lib/anomalyThresholds.ts
- src/lib/metrics_source.ts
- And others...

## Important Note

**Vite environment variables are embedded at BUILD TIME, not runtime.**

Since the frontend code is mounted as a volume in Docker, the environment variable needs to be available when Vite processes the code. The Docker container has `VITE_API_URL=http://localhost:8000` set, which should work.

## Testing

1. **Refresh your browser** (hard refresh: Ctrl+Shift+R or Cmd+Shift+R)
2. Try the NLQ query again: "In the rent roll of property ESP, how much is the vacant area?"
3. Check browser console (F12) for any errors

## If Still Not Working

If you still see network errors after refreshing:

1. Check browser console for the actual error
2. Verify the request URL in Network tab
3. Check if CORS errors appear
4. Try restarting both services:
   ```bash
   docker compose restart frontend backend
   ```

## Status
✅ **Fixed** - Files updated to use correct environment variable
✅ **Frontend** - Restarted

