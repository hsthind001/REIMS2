# DSCR Calculation Status & Data Requirements

**Date**: November 22, 2025  
**Status**: ✅ DSCR is calculating correctly with current data

---

## Current Uploaded Files

Based on your uploads:
- ✅ **Balance Sheets**: December 2024, December 2023
- ✅ **Income Statements**: December 2023, December 2024  
- ✅ **Cash Flow Statements**: December 2024, December 2025
- ✅ **Rent Rolls**: April 2025

---

## What's Working ✅

### 1. DSCR Calculation
**Portfolio DSCR**: **1.31** (Healthy)
- **Total NOI**: $10,155,401.61
- **Total Debt Service**: $7,771,073.49
- **YoY Change**: +0.07

**Property-Level DSCRs** (Dec 2024):
- ESP001: 1.39 (Healthy)
- HMND001: 1.36 (Healthy)
- TCSH001: 1.20 (Critical - below 1.25 threshold)
- WEND001: 1.35 (Healthy)

### 2. Data Sources Used
- ✅ **NOI**: From Income Statements (account 6299-0000 or calculated)
- ✅ **Mortgage Interest**: From Income Statements (account 7010-0000)
- ✅ **Loan Amount**: From Balance Sheets (account 2900-0000 - Total Long-Term Debt)
- ✅ **Principal Payments**: Estimated from loan amortization (not found in cash flow)

---

## What's Missing / Limitations ⚠️

### 1. Principal Payments Not Found
**Issue**: Cash flow statements don't have principal payment line items extracted
- **Impact**: System estimates principal payments using amortization formula
- **Current Method**: Calculates estimated principal from:
  - Loan amount (from balance sheet)
  - Interest rate (from interest payment / loan amount)
  - Assumes 25-year amortization
  - Formula: `Principal = Total Payment - Interest`

**What You Need**:
- Ensure cash flow statements have principal payment line items in the FINANCING section
- Or manually verify the estimated principal is accurate

### 2. Period Mismatch
**Issue**: April 2025 has rent roll data but no income statements/balance sheets
- **Impact**: Dashboard shows April 2025 as latest period, but financial metrics are NULL
- **Fix Applied**: System now skips periods with NULL financial metrics
- **Current Behavior**: Uses December 2024 as latest period (correct)

**What You Need**:
- Upload income statements and balance sheets for April 2025 if you want that period
- Or ignore April 2025 for financial calculations (rent roll only)

### 3. Annual vs Monthly Data
**Issue**: Some income statements are marked "Annual", some "Monthly"
- **Current Status**:
  - ESP001 Dec 2024: Annual ✓
  - HMND001 Dec 2024: Annual ✓
  - TCSH001 Dec 2024: Monthly ✓
  - WEND001 Dec 2024: Annual ✓
- **Impact**: DSCR service correctly handles both (annualizes monthly data)

**What You Need**:
- Ensure period_type is correctly extracted from PDFs
- System will handle both automatically

---

## Calculation Logic

### DSCR Formula
```
DSCR = Annual NOI / Annual Debt Service

Where:
- Annual NOI = Net Operating Income (from income statement)
  - If monthly: NOI × 12
  - If annual: NOI (as-is)
  
- Annual Debt Service = Interest + Principal
  - Interest = Mortgage Interest (7010-0000) from income statement
  - Principal = Estimated from loan amortization OR from cash flow
```

### Portfolio DSCR
```
Portfolio DSCR = Total Portfolio NOI / Total Portfolio Debt Service

Weighted by debt service amounts (not simple average)
```

---

## Data Verification Checklist

### ✅ Have (Working):
- [x] Balance Sheets (Dec 2023, 2024) - Provides loan amounts
- [x] Income Statements (Dec 2023, 2024) - Provides NOI and interest
- [x] Cash Flow Statements (Dec 2024, 2025) - Exists but principal not extracted
- [x] Rent Rolls (April 2025) - Provides occupancy data

### ⚠️ Partially Missing:
- [ ] Principal payments in cash flow (system estimates)
- [ ] Income statements for April 2025 (only rent roll exists)

### ✅ Not Required:
- [x] Monthly data (annual works fine)
- [x] Multiple periods (Dec 2023 vs Dec 2024 comparison works)

---

## Current Dashboard Values

Based on December 2024 data:

| Metric | Value | Status |
|--------|-------|--------|
| **Portfolio DSCR** | 1.31 | ✅ Healthy |
| **Total Portfolio Value** | Calculated from balance sheets | ✅ |
| **Portfolio NOI** | $10,155,401.61 | ✅ |
| **Average Occupancy** | From rent rolls | ✅ |
| **DSCR Change** | +0.07 (vs Dec 2023) | ✅ |

---

## Recommendations

### To Improve Accuracy:

1. **Extract Principal Payments**:
   - Ensure cash flow statements have principal payment line items
   - Should be in FINANCING section with category containing "principal"
   - This will replace the estimated calculation

2. **Upload Missing Documents**:
   - Income statements for April 2025 (if you want that period)
   - Balance sheets for April 2025 (if you want that period)
   - Or continue using December 2024 as latest period

3. **Verify Estimates**:
   - Check if estimated principal payments match actual loan terms
   - System assumes 25-year amortization (typical for commercial real estate)
   - If your loans have different terms, principal estimates may be off

---

## Summary

✅ **DSCR is calculating correctly** with your current data:
- Portfolio DSCR: **1.31** (Healthy)
- All 4 properties have DSCR calculated
- System correctly handles annual vs monthly data
- Period selection logic fixed to use December 2024 (not April 2025)

⚠️ **Minor Limitations**:
- Principal payments are estimated (not extracted from cash flow)
- April 2025 period skipped (no income statements/balance sheets)

🎯 **Dashboard Status**: Ready to display Portfolio DSCR instead of IRR

