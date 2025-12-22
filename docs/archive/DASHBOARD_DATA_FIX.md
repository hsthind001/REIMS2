# Dashboard Data Loading Fix

## Issue
After refreshing the page, dashboard shows all zeros ($0, 0.0%) even though backend has data.

## Root Cause
Multiple frontend files were using incorrect API URL pattern:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
```

**Problem**: When `VITE_API_URL` is set to `http://localhost:8000` (without `/api/v1`), this code would use `http://localhost:8000` directly, which is missing the `/api/v1` prefix.

## Fix Applied

Changed all files to properly append `/api/v1`:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';
```

## Files Fixed

1. ✅ `src/pages/CommandCenter.tsx` - Main dashboard
2. ✅ `src/pages/Dashboard.tsx`
3. ✅ `src/pages/PortfolioHub.tsx`
4. ✅ `src/pages/FinancialCommand.tsx` - NLQ feature
5. ✅ `src/lib/metrics_source.ts`
6. ✅ `src/lib/anomalyThresholds.ts`
7. ✅ `src/pages/RiskManagement.tsx`
8. ✅ `src/pages/DataControlCenter.tsx`

## Verification

Backend API is returning data correctly:
- `/api/v1/metrics/summary` - Returns property metrics
- `/api/v1/metrics/portfolio-changes` - Returns portfolio changes
- `/api/v1/exit-strategy/portfolio-dscr` - Returns DSCR data

## Next Steps

1. **Hard refresh browser** (Ctrl+Shift+R or Cmd+Shift+R)
2. Dashboard should now show:
   - Total Portfolio Value (sum of total_assets)
   - Portfolio NOI (sum of net_operating_income)
   - Average Occupancy (average of occupancy_rate)
   - Portfolio DSCR (from API)
   - Property performance table with actual values

## Status
✅ **Fixed** - All API URLs corrected
✅ **Frontend** - Restarted
✅ **Backend** - Healthy and returning data

