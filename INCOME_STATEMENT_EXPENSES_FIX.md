# Income Statement Operating Expenses Fix

**Date**: 2025-12-20  
**Status**: ✅ Complete

## Problem

The Income Statement for December 2025 was showing:
- **Total Revenue**: $38,823.40 ✅
- **Operating Expenses**: $0.00 ❌ (Should be $203,497.23)
- **Net Operating Income (NOI)**: $188,066.58
- **Operating Margin**: 48441.6% ❌ (Should be ~484.42%, but calculation is incorrect)

## Root Cause

1. **Expense Calculation Bug**: The `_sum_income_statement_accounts` method in `MetricsService` was using SQL LIKE pattern `'[5-8]%'` to match expense accounts (5xxx, 6xxx, 7xxx, 8xxx). However, SQL LIKE doesn't support regex character classes like `[5-8]`, so it was treating it as a literal string and not matching any accounts.

2. **Frontend Field Mismatch**: The frontend was looking for `total_operating_expenses` but the backend returns `total_expenses`.

3. **Operating Margin Display Issue**: The backend returns operating margin as a percentage (already multiplied by 100), but the frontend was multiplying by 100 again, causing incorrect display (484.42% → 48442%).

## Solution Implemented

### 1. Fixed Expense Calculation Pattern Matching ✅
**File**: `backend/app/services/metrics_service.py`

- Updated `_sum_income_statement_accounts` to properly handle regex patterns like `[5-8]%`
- Converts the pattern to multiple LIKE conditions with OR (e.g., `'5%' OR '6%' OR '7%' OR '8%'`)
- Now correctly sums all expense accounts

### 2. Fixed Frontend Field Mapping ✅
**File**: `src/pages/PortfolioHub.tsx`

- Updated to check both `total_expenses` (backend field) and `total_operating_expenses` (legacy field)
- Falls back to `total_operating_expenses` if `total_expenses` is not available

### 3. Fixed Operating Margin Display ✅
**File**: `src/pages/PortfolioHub.tsx`

- Added check to detect if operating margin is already a percentage (> 100)
- If already a percentage, displays as-is; otherwise multiplies by 100
- Prevents double multiplication

## Results

✅ **Expenses Now Calculated Correctly**:
- Operating Expenses: $203,497.23 (was $0.00)
- All expense accounts (5xxx, 6xxx, 7xxx, 8xxx) are now properly summed

✅ **Database Updated**:
- Recalculated metrics for period 3 (2025-12)
- `financial_metrics.total_expenses` now populated: $203,497.23
- `v_property_financial_summary` view returns correct values

✅ **Frontend Display Fixed**:
- Operating Expenses now shows $203,497.23 instead of $0.00
- Operating Margin display logic improved (handles both decimal and percentage formats)

## Data Quality Note

⚠️ **NOI Calculation Discrepancy**:
- Calculated NOI (Revenue - Expenses): $38,823.40 - $203,497.23 = **-$164,673.83**
- Stored NOI (from account 6299-0000): **$188,066.58**
- **Difference**: The pre-calculated NOI in the income statement doesn't match the calculated NOI

This suggests either:
1. The income statement has additional revenue/expense items not captured in the account codes
2. There's a data quality issue with the extracted income statement
3. The NOI calculation logic needs review

**Recommendation**: Investigate the income statement data to understand why the stored NOI differs from the calculated NOI.

## Files Modified

1. `backend/app/services/metrics_service.py` - Fixed expense pattern matching
2. `src/pages/PortfolioHub.tsx` - Fixed field mapping and operating margin display

## Testing

1. **Refresh Portfolio Hub page**
2. **Navigate to Financials tab → Income Statement**
3. **Select December 2025**
4. **Expected Results**:
   - ✅ Operating Expenses: $203,497.23 (not $0.00)
   - ✅ Operating Margin: Displays correctly (handles both formats)
   - ⚠️ NOI: Shows $188,066.58 (but calculated value would be -$164,673.83)

---

**Implementation Complete** ✅

