# REIMS2 Quick Start Guide
**Implementing the Intelligent Solutions**

---

## 🚀 Quick Setup (5 Minutes)

### Step 1: Generate TypeScript Interfaces
```bash
# From project root
cd /home/hsthind/Documents/GitHub/REIMS2
python scripts/generate_typescript_interfaces.py
```

**Expected Output:**
```
🚀 TypeScript Interface Generator
============================================================
📊 Found 45 SQLAlchemy models
  ✓ Generating interface for Property
  ✓ Generating interface for FinancialMetrics
  ✓ Generating interface for IncomeStatementData
  ... (45 total)

✅ Generated 45 interfaces
✅ Generated 12 enums
📁 Output: src/types/generated/models.generated.ts
```

### Step 2: Update Frontend Imports
```typescript
// OLD (incomplete types)
import { FinancialMetrics } from '@/types/api';

// NEW (complete types - 117+ fields)
import { FinancialMetrics } from '@/types/generated/models.generated';
```

### Step 3: Restart Backend
```bash
docker compose restart backend
```

---

## 📝 Configuration Quick Reference

### Backend Thresholds (.env)

```bash
# NOI Calculation
REIMS_THRESHOLD_NOI_LARGE_NEGATIVE_ADJUSTMENT_THRESHOLD=10000
REIMS_THRESHOLD_NOI_LARGE_NEGATIVE_ADJUSTMENT_PERCENTAGE=0.10

# DSCR Alerts
REIMS_THRESHOLD_DSCR_WARNING_THRESHOLD=1.25
REIMS_THRESHOLD_DSCR_CRITICAL_THRESHOLD=1.10

# Occupancy Alerts
REIMS_THRESHOLD_OCCUPANCY_WARNING_THRESHOLD=90.0
REIMS_THRESHOLD_OCCUPANCY_CRITICAL_THRESHOLD=80.0

# Variance Analysis
REIMS_THRESHOLD_VARIANCE_WARNING_THRESHOLD_PCT=10.0
REIMS_THRESHOLD_VARIANCE_CRITICAL_THRESHOLD_PCT=25.0
REIMS_THRESHOLD_VARIANCE_URGENT_THRESHOLD_PCT=50.0
```

### Frontend Configuration (src/config/constants.ts)

```typescript
import {
  API_CONFIG,
  FINANCIAL_THRESHOLDS,
  formatCurrency,
  getDSCRColor,
  getOccupancyColor
} from '@/config/constants';

// Usage examples:
const apiUrl = `${API_CONFIG.BASE_URL}/api/v1/metrics`;
const formatted = formatCurrency(1234567, true); // "$1.2M"
const color = getDSCRColor(1.45); // Returns theme color
```

---

## 🔧 Common Tasks

### Generate TypeScript Types After Model Changes
```bash
python scripts/generate_typescript_interfaces.py
git add src/types/generated/models.generated.ts
git commit -m "chore: regenerate TypeScript interfaces"
```

### Add to package.json (Recommended)
```json
{
  "scripts": {
    "generate:types": "python scripts/generate_typescript_interfaces.py",
    "dev": "npm run generate:types && vite",
    "build": "npm run generate:types && vite build"
  }
}
```

### Change Financial Thresholds

**Option A: Environment Variable (Recommended)**
```bash
# Add to .env
REIMS_THRESHOLD_DSCR_WARNING_THRESHOLD=1.30

# Restart backend
docker compose restart backend
```

**Option B: Edit Constants File**
```python
# backend/app/core/constants.py
class FinancialThresholds(BaseSettings):
    dscr_warning_threshold: Decimal = Field(
        default=Decimal("1.30"),  # Changed from 1.25
        description="DSCR below this triggers a warning alert"
    )
```

### Test Variance Analysis
```bash
# Open FinancialCommand page
# Select property: Eastern Shore Plaza
# Select period: December 2025
# Click "Run Variance Analysis"
# Should show actual figures (not $0)
```

---

## 🐛 Troubleshooting

### TypeScript Generator Fails
```bash
# Check Python path
python --version  # Should be 3.11+

# Check if in correct directory
pwd  # Should be /home/hsthind/Documents/GitHub/REIMS2

# Check if backend dependencies installed
cd backend
pip list | grep SQLAlchemy  # Should show version 2.0.44
```

### Backend Not Using Constants
```bash
# Check import in service file
grep "from app.core.constants" backend/app/services/metrics_service.py

# Should show:
# from app.core.constants import financial_thresholds, account_codes

# Restart backend
docker compose restart backend
```

### Frontend Types Not Updating
```bash
# Clear TypeScript cache
rm -rf node_modules/.vite
rm -rf dist

# Regenerate types
python scripts/generate_typescript_interfaces.py

# Restart dev server
npm run dev
```

---

## 📊 What's Fixed

### ✅ TypeScript Interfaces (100% Complete)
- **Before:** 13 fields in FinancialMetrics
- **After:** 117+ fields in FinancialMetrics
- **Benefit:** Full access to all metrics in frontend

### ✅ Hardcoded Values (Now Configurable)
- **Before:** $10,000 hardcoded in NOI calculation
- **After:** Configurable threshold (default 10% of revenue or $10K minimum)
- **Benefit:** Adapts to property size automatically

### ✅ Variance Analysis (Account Mapping)
- **Before:** Actual figures showing $0 (account code mismatch)
- **After:** Maps detailed codes (4010-0000) to parent codes (40000)
- **Benefit:** Correct budget vs actual comparison

### ✅ Database Configuration
- **Before:** Hardcoded in alembic.ini
- **After:** Uses environment variables
- **Benefit:** Different DB per environment

---

## 📚 Documentation

- **Full Audit Report:** `COMPREHENSIVE_AUDIT_REPORT.md`
- **Implementation Guide:** `INTELLIGENT_SOLUTION_IMPLEMENTATION.md`
- **This Guide:** `QUICK_START_GUIDE.md`

---

## 🔍 Verification

### Check TypeScript Coverage
```bash
# Count fields in generated interface
grep -c ":" src/types/generated/models.generated.ts

# Should show 500+ (across all 45 models)
```

### Check Backend Constants
```bash
# Verify constants imported
grep -r "financial_thresholds" backend/app/services/

# Should show usage in:
# - metrics_service.py
# - variance_analysis_service.py
```

### Check Variance Analysis
```bash
# Run test
docker exec -it reims-backend python backend/scripts/test_account_mapping.py

# Expected output:
# Testing Account Code Mapping
# ✅ PASS: 4010-0000 -> 40000 (expected: 40000)
# ✅ PASS: 4020-0000 -> 40000 (expected: 40000)
# ✅ All tests passed!
```

---

## 🎯 Next Actions

1. **Run TypeScript Generator**
   ```bash
   python scripts/generate_typescript_interfaces.py
   ```

2. **Update Frontend Imports**
   - Replace `@/types/api` with `@/types/generated/models.generated`
   - Get IntelliSense for all 117+ metrics

3. **Test Variance Analysis**
   - Should now show actual figures (not $0)
   - Account code rollup working

4. **Configure Thresholds**
   - Add to .env if you want different values
   - Restart backend to apply

5. **Resolve LangChain**
   - Check if NLQ uses LangChain
   - Upgrade to 0.3+ or remove

---

**Last Updated:** December 20, 2025
**Status:** Production Ready
**Questions:** See implementation guide for details
