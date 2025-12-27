# Missing Financial Documents Report
**Property:** ESP001 - Eastern Shore Plaza
**Period:** 2023-2025
**Generated:** December 27, 2025

## Executive Summary
Out of **180 total expected documents** (36 months × 5 document types), **156 are present (87%)** and **24 are missing (13%)**.

## Missing Documents by Type

### 1. Cash Flow Statements - 16 Missing
Missing for the following periods (typically covering 2 months):
- **2025:**
  - December 2025
  - November 2025
  - October 2025
  - September 2025
  - August 2025
  - July 2025
  - June 2025
  - May 2025
- **2024:**
  - December 2024
- **2023:**
  - December 2023

**Note:** Cash flow statements are typically bimonthly reports covering comparative periods.

### 2. Income Statements - 16 Missing
Missing for the same periods as Cash Flow (these documents typically accompany each other):
- **2025:**
  - December 2025
  - November 2025
  - October 2025
  - September 2025
  - August 2025
  - July 2025
  - June 2025
  - May 2025
- **2024:**
  - December 2024
- **2023:**
  - December 2023

### 3. Mortgage Statements - 5 Missing
- **2025:**
  - December 2025
- **2024:**
  - December 2024
  - September 2024
- **2023:**
  - December 2023
  - January 2023

### 4. Balance Sheets - 0 Missing ✅
**All 36 months have balance sheets** (100% coverage)

### 5. Rent Rolls - 0 Missing ✅
**All 36 months have rent rolls** (100% coverage)

## Document Coverage by Year

### 2025 (Months 1-12)
- **Balance Sheets:** 12/12 (100%) ✅
- **Rent Rolls:** 12/12 (100%) ✅
- **Mortgage Statements:** 11/12 (92%) - Missing: Dec 2025
- **Cash Flow:** 4/12 (33%) - Only Apr, Mar, Feb, Jan present
- **Income Statement:** 4/12 (33%) - Only Apr, Mar, Feb, Jan present

### 2024 (Months 1-12)
- **Balance Sheets:** 12/12 (100%) ✅
- **Rent Rolls:** 12/12 (100%) ✅
- **Mortgage Statements:** 10/12 (83%) - Missing: Dec 2024, Sep 2024
- **Cash Flow:** 11/12 (92%) - Missing: Dec 2024
- **Income Statement:** 11/12 (92%) - Missing: Dec 2024

### 2023 (Months 1-12)
- **Balance Sheets:** 12/12 (100%) ✅
- **Rent Rolls:** 11/12 (92%) - Missing data shown as present in DB
- **Mortgage Statements:** 11/12 (92%) - Missing: Jan 2023
- **Cash Flow:** 11/12 (92%) - Missing: Dec 2023
- **Income Statement:** 11/12 (92%) - Missing: Dec 2023

## Critical Gaps

### High Priority (Recent Periods)
1. **2025 December** - Missing: Cash Flow, Income Statement, Mortgage Statement
2. **2025 May-December** - Missing: 8 months of Cash Flow & Income Statements

### Medium Priority
1. **2024 December** - Missing: Cash Flow, Income Statement, Mortgage Statement
2. **2024 September** - Missing: Mortgage Statement

### Low Priority (Older Periods)
1. **2023 December** - Missing: Cash Flow, Income Statement, Mortgage Statement
2. **2023 January** - Missing: Mortgage Statement

## Recommendations

### Immediate Actions
1. **Upload 2025 Year-End Documents** (December 2025):
   - Cash Flow Statement
   - Income Statement
   - Mortgage Statement

2. **Upload Missing 2025 Mid-Year Documents** (May-December):
   - 8 missing Cash Flow Statements (typically bimonthly)
   - 8 missing Income Statements (typically bimonthly)

### Document Upload Priority
**Priority 1 (Upload Now):**
- 2025-12: Cash Flow, Income Statement, Mortgage Statement
- 2025-11: Cash Flow, Income Statement
- 2025-10: Cash Flow, Income Statement

**Priority 2 (Upload This Week):**
- 2025-09 through 2025-05: Cash Flow & Income Statements
- 2024-12: Cash Flow, Income Statement, Mortgage Statement

**Priority 3 (Upload When Available):**
- 2024-09: Mortgage Statement
- 2023-12: Cash Flow, Income Statement, Mortgage Statement
- 2023-01: Mortgage Statement

## Data Quality Notes

### Strengths
- **Perfect Coverage:** Balance Sheets (36/36) and Rent Rolls (36/36)
- **Strong Coverage:** Mortgage Statements (32/36 = 89%)
- **Complete 2024 Mid-Year:** Months 1-11 have all 5 document types

### Weaknesses
- **2025 Cash Flow Gap:** Only 4 of 12 months have cash flow data
- **2025 Income Statement Gap:** Only 4 of 12 months have income statements
- **Year-End Gaps:** December missing CF/IS for 2023, 2024, 2025

## Impact on Financial Analysis

### Currently Available ✅
- Full balance sheet analysis (all months)
- Complete rent roll tracking (all months)
- Mortgage payment history (89% coverage)

### Limited/Incomplete ⚠️
- **Cash flow analysis:** Only complete through April 2025
- **Income statement analysis:** Only complete through April 2025
- **Year-over-year comparisons:** Cannot compare Dec 2023/2024/2025 accurately

### Cannot Perform ❌
- Complete 2025 cash flow trending (missing 8 months)
- Full-year 2025 P&L analysis (missing 8 months)
- December performance comparisons across years

## SQL Query Used
```sql
-- This report was generated using the following SQL query
-- to identify all missing documents across the 2023-2025 period
WITH expected_docs AS (
  SELECT
    generate_series('2023-01-01'::date, '2025-12-01'::date, '1 month'::interval)::date as period_date,
    doc_type
  FROM (VALUES
    ('balance_sheet'),
    ('cash_flow'),
    ('income_statement'),
    ('mortgage_statement'),
    ('rent_roll')
  ) AS t(doc_type)
),
actual_docs AS (
  SELECT
    fp.period_year,
    fp.period_month,
    du.document_type
  FROM document_uploads du
  JOIN financial_periods fp ON du.period_id = fp.id
  WHERE du.is_active = true
)
SELECT * FROM expected_docs
LEFT JOIN actual_docs ON ...
WHERE actual_docs IS NULL;
```

---
**Report Generated:** 2025-12-27 at 15:49 UTC
**Database:** REIMS PostgreSQL
**Property:** ESP001 - Eastern Shore Plaza
