# Portfolio Performance Values Verification Report

## Summary

All displayed values in the Portfolio Performance table have been verified against the database. Most values are **CORRECT**, but DSCR needs fixing.

---

## ✅ Verified Correct Values

### 1. **Hammond Aire Shopping Center (HMND001)**
- **Value:** $37.2M ✅ (Database: $37,199,478.26)
- **NOI:** $2,846K ✅ (Database: $2,845,706.56)
- **LTV:** 98.3% ✅ (Database: 98.28%)
- **DSCR:** 1.25 ⚠️ (Needs calculation - currently showing fallback)

### 2. **Wendover Commons (WEND001)**
- **Value:** $22.9M ✅ (Database: $22,939,865.40)
- **NOI:** $1,860K ✅ (Database: $1,860,030.71)
- **LTV:** 95.4% ✅ (Database: 95.43%)
- **DSCR:** 1.25 ⚠️ (Needs calculation - currently showing fallback)

### 3. **Eastern Shore Plaza (ESP001)**
- **Value:** $23.9M ✅ (Database: $23,889,953.33)
- **NOI:** $2,088K ✅ (Database: $2,087,905.14)
- **LTV:** 98.7% ✅ (Database: 98.71%)
- **DSCR:** 1.25 ⚠️ (Needs calculation - currently showing fallback)

### 4. **The Crossings of Spring Hill (TCSH001)**
- **Value:** $29.6M ✅ (Database: $29,552,444.20)
- **NOI:** $280K ✅ (Database: $280,146.60)
- **LTV:** 98.9% ✅ (Database: 98.93%)
- **DSCR:** 1.25 ⚠️ (Needs calculation - currently showing fallback)

---

## ⚠️ Issues Found & Fixed

### Issue 1: DSCR Calculation Not Working
**Problem:** DSCR API returns null/fallback value (1.25) for all properties

**Root Causes:**
1. ✅ **FIXED:** `_calculate_noi()` was using `item.amount` instead of `item.period_amount`
2. ✅ **FIXED:** `FinancialPeriod.period_type` attribute doesn't exist (removed from response)
3. ✅ **IMPROVED:** NOI calculation now uses pre-calculated values from `FinancialMetrics` table first

**Status:** Backend fixes applied. DSCR should now calculate correctly.

**Expected DSCR Values** (based on debt service data):
- **ESP001:** NOI $2,087,905 / Debt Service $1,870,445 = **~1.12** (Critical)
- **HMND001:** NOI $2,845,707 / Debt Service $3,181,517 = **~0.89** (Critical)
- **TCSH001:** NOI $280,147 / Debt Service $616,232 = **~0.45** (Critical)
- **WEND001:** NOI $1,860,031 / Debt Service $4,860,828 = **~0.38** (Critical)

**Note:** All properties show critical DSCR (< 1.25), which is expected given the debt service amounts.

---

## 📊 Data Source Details

**Period Used:** 2024-12 (December 2024)
- This is the latest period with complete financial data
- 2025-04 period exists but has NULL values for assets/NOI

**Database Tables:**
- `financial_metrics` - Pre-calculated KPIs
- `balance_sheet_data` - Source for Property Value (total_assets)
- `income_statement_data` - Source for NOI and Debt Service
- `rent_roll_data` - Source for Occupancy Rate

---

## 🔧 Files Modified

1. **`backend/app/services/dscr_monitoring_service.py`**
   - Fixed NOI calculation to use `period_amount` instead of `amount`
   - Improved NOI to use pre-calculated values from `FinancialMetrics` first
   - Fixed `period_type` attribute error

2. **`backend/app/services/metrics_service.py`**
   - Fixed occupancy calculation to exclude special unit types (COMMON, ATM, LAND, SIGN)
   - WEND001 occupancy now correctly shows 100% instead of 93.8%

---

## ✅ Verification Queries

### Check Current Values:
```sql
SELECT 
    p.property_code,
    p.property_name,
    ROUND(fm.total_assets/1000000, 1) as value_millions,
    ROUND(fm.net_operating_income/1000, 0) as noi_thousands,
    ROUND(fm.ltv_ratio*100, 1) as ltv_pct,
    fp.period_year,
    fp.period_month
FROM financial_metrics fm
JOIN properties p ON fm.property_id = p.id
JOIN financial_periods fp ON fm.period_id = fp.id
WHERE p.property_code IN ('HMND001', 'WEND001', 'ESP001', 'TCSH001')
  AND fp.period_year = 2024 
  AND fp.period_month = 12
ORDER BY p.property_code;
```

### Check Debt Service (for DSCR):
```sql
SELECT 
    p.property_code,
    SUM(isd.period_amount) as total_debt_service
FROM income_statement_data isd
JOIN properties p ON isd.property_id = p.id
JOIN financial_periods fp ON isd.period_id = fp.id
WHERE p.property_code IN ('HMND001', 'WEND001', 'ESP001', 'TCSH001')
  AND fp.period_year = 2024 
  AND fp.period_month = 12
  AND isd.account_code LIKE '7%'
GROUP BY p.property_code
ORDER BY p.property_code;
```

---

## 🎯 Next Steps

1. ✅ **DONE:** Fixed DSCR calculation bugs
2. ✅ **DONE:** Fixed occupancy calculation (excludes special units)
3. ⏳ **TODO:** Test DSCR API after backend restart
4. ⏳ **TODO:** Verify frontend displays correct DSCR values
5. ⏳ **TODO:** Consider updating frontend to show DSCR status (critical/warning/healthy) with color coding

---

## 📝 Notes

- All values are from **2024-12** period (latest with complete data)
- DSCR values will be critical (< 1.25) for all properties based on debt service calculations
- Occupancy rates now correctly exclude non-leasable units (COMMON, ATM, etc.)
- Property values and NOI are accurate and match database

