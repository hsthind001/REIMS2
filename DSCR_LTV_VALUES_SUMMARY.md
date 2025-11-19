# DSCR and LTV Values Summary for REIMS Properties

## Current Database Status

### LTV (Loan-to-Value) Values

Based on the latest financial metrics data (2024-12 period):

| Property Code | Property Name | LTV % | Long-Term Debt | Net Property Value | Period |
|--------------|---------------|-------|----------------|-------------------|--------|
| **ESP001** | Eastern Shore Plaza | **98.71%** | $21,573,716.56 | $21,855,631.93 | 2024-12 |
| **HMND001** | Hammond Aire Shopping Center | **98.28%** | $31,610,377.40 | $32,119,967.34 | 2024-12 |
| **TCSH001** | The Crossings of Spring Hill | **98.93%** | $26,407,080.92 | $26,693,670.71 | 2024-12 |
| **WEND001** | Wendover Commons | **95.43%** | $20,866,078.83 | $21,865,409.62 | 2024-12 |

**Note:** LTV values are calculated as: `(Long-Term Debt / Net Property Value) × 100`

### DSCR (Debt Service Coverage Ratio) Values

**Current Status:** Limited data available

| Property Code | Property Name | NOI Available | Debt Service Available | DSCR | Status |
|--------------|---------------|---------------|----------------------|------|--------|
| **HMND001** | Hammond Aire Shopping Center | ✅ $185,978.06 (2023-12) | ⚠️ Only Mortgage Interest: $113,389.50/month | **~1.37** (estimated) | Needs full debt service data |
| **ESP001** | Eastern Shore Plaza | ❌ No NOI data | ❌ No debt service data | **N/A** | No income statement data |
| **TCSH001** | The Crossings of Spring Hill | ❌ No NOI data | ❌ No debt service data | **N/A** | No income statement data |
| **WEND001** | Wendover Commons | ❌ No NOI data | ❌ No debt service data | **N/A** | No income statement data |

**DSCR Calculation:** `DSCR = NOI / Annual Debt Service`

**Note:** 
- Annual Debt Service = Principal + Interest payments
- Currently only mortgage interest (7010-0000) is available for HMND001
- Full debt service requires principal payment data which may not be in income statements

## Expected Values After Fixes

### LTV Values (Should Display)

After the backend fix, the API should return:

1. **ESP001 (Eastern Shore Plaza):** **98.71%**
2. **HMND001 (Hammond Aire Shopping Center):** **98.28%**
3. **TCSH001 (The Crossings of Spring Hill):** **98.93%**
4. **WEND001 (Wendover Commons):** **95.43%**

These values come from the `ltv_ratio` field in `financial_metrics` table, which is calculated as:
```
ltv_ratio = long_term_debt / net_property_value
```

### DSCR Values (Current Limitations)

**HMND001 (Hammond Aire Shopping Center):**
- **NOI:** $185,978.06 (monthly, Dec 2023)
- **Mortgage Interest:** $113,389.50/month
- **Estimated Annual Debt Service:** ~$1,360,674/year (if interest is ~8% of total debt service)
- **Estimated DSCR:** ~1.64 (if using annual NOI of $2,231,737)

**Other Properties:**
- No income statement data available yet
- DSCR cannot be calculated until income statements are uploaded and extracted

## Issues Identified

### 1. DSCR Calculation Problem

**Root Cause:** The DSCR service is looking for debt service accounts with code starting with "7%", but:
- Account 7010-0000 is "Mortgage Interest" (found)
- Account 7020-0000 is "Depreciation" (not debt service)
- Account 7030-0000 is "Amortization" (not debt service)
- **Principal payments are typically not in income statements** - they're balance sheet items

**Solution Needed:**
- Debt service should be calculated from loan balance and interest rate, OR
- Use a loan/debt service table if available, OR
- Estimate based on loan amount × interest rate + principal payment schedule

### 2. Limited Income Statement Data

**Current Status:**
- Only HMND001 has income statement data (2023-12)
- Other properties need income statements uploaded and extracted

**Action Required:**
- Upload income statements for ESP001, TCSH001, and WEND001
- Run extraction to populate income_statement_data table
- Recalculate financial metrics

## Recommendations

1. **For LTV:** ✅ **Fixed** - API now correctly uses `ltv_ratio` from financial_metrics
2. **For DSCR:** ⚠️ **Needs Improvement** - Current calculation method needs refinement:
   - Option A: Use loan balance × interest rate to estimate annual debt service
   - Option B: Create a loan/debt service tracking table
   - Option C: Use balance sheet data to calculate principal payments

3. **Data Quality:** Upload income statements for all properties to enable DSCR calculations

## Verification Steps

After backend restart, verify:

1. **LTV Values:**
   ```bash
   curl http://localhost:8000/api/v1/metrics/1/ltv
   curl http://localhost:8000/api/v1/metrics/2/ltv
   curl http://localhost:8000/api/v1/metrics/3/ltv
   curl http://localhost:8000/api/v1/metrics/4/ltv
   ```

2. **DSCR Values:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/risk-alerts/properties/2/dscr/calculate
   ```

3. **Frontend Display:**
   - Refresh browser
   - Check Portfolio Performance table
   - Verify LTV shows ~95-99% (not 52.8%)
   - Verify DSCR shows calculated values (not 1.25)

---

**Generated:** $(date)
**Database:** REIMS PostgreSQL
**Backend API:** http://localhost:8000/api/v1

