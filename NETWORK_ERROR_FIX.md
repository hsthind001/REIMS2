# Network Error Fix for NLQ

## Issue
Frontend showing "Network Error: Failed to fetch" when making NLQ queries.

## Root Cause
The `FinancialCommand.tsx` component was using `VITE_API_BASE_URL` environment variable which wasn't set in Docker. The Docker compose file sets `VITE_API_URL` instead.

## Fix Applied

**File**: `src/pages/FinancialCommand.tsx` (line 27)

Changed from:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
```

To:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';
```

## How It Works

1. Uses `VITE_API_URL` from Docker environment (set to `http://localhost:8000`)
2. Appends `/api/v1` to create the full API base URL
3. Falls back to `http://localhost:8000/api/v1` if env var not set

## Status
✅ **Fixed** - Frontend restarted with corrected API URL
✅ **Backend** - Healthy and responding

## Testing
Try asking: "In the rent roll of property ESP, how much is the vacant area?"

The network error should be resolved and the query should go through.

