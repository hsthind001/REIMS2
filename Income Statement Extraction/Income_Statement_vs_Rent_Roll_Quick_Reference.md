# Income Statement vs Rent Roll Extraction: Quick Reference Guide

## Document Comparison

| Aspect | Rent Roll | Income Statement |
|--------|-----------|------------------|
| **Document Type** | Tenant listing with lease details | Financial performance summary |
| **Update Frequency** | Monthly snapshot | Monthly or Annual |
| **Primary Focus** | Unit-by-unit rental details | Property-level financial performance |
| **Row Type** | One row per unit/tenant | One row per account/line item |
| **Key Metrics** | Occupancy, Rent per SF, Lease terms | NOI, Net Income, Operating ratios |

## Key Data Structures

### Rent Roll
- **Granularity:** Unit level (micro)
- **Main entities:** Property → Unit → Tenant → Lease
- **Key fields:** Unit #, Tenant name, Lease dates, Rent amounts, Square footage
- **Calculations:** Monthly rent × 12 = Annual rent, Rent/SF

### Income Statement
- **Granularity:** Account level (macro)
- **Main entities:** Property → Period → Account Categories → Line Items
- **Key fields:** Account codes, Descriptions, Amounts, Percentages
- **Calculations:** Income - Expenses = NOI; NOI - Below-line items = Net Income

## Critical Validation Rules

### Rent Roll Validations
1. Monthly Rent × 12 = Annual Rent (±5%)
2. Lease end date > Lease start date
3. Monthly Rent / Area = Rent per SF
4. Security deposit typically 1-3 months rent
5. No duplicate unit numbers per property

### Income Statement Validations
1. Sum of income items = Total Income (±$0.05)
2. Sum of all expenses = Total Expenses (±$0.10)
3. Total Income - Total Expenses = NOI (±$0.10)
4. NOI - Other expenses = Net Income (±$0.10)
5. All percentage columns sum to 100% (±0.5%)
6. Period amounts ≤ YTD amounts (for monthly statements)
7. Subtotals match sum of their components

## Common Account Codes (Income Statement)

### Income (4000 series)
- **4010-0000:** Base Rentals (Primary)
- **4020-0000:** Tax reimbursements
- **4030-0000:** Insurance reimbursements
- **4040-0000:** CAM charges
- **4060-0000:** Annual CAM reconciliation
- **4990-0000:** TOTAL INCOME

### Operating Expenses (5000 series)
- **5010-0000:** Property Tax
- **5012-0000:** Property Insurance
- **5100-5199:** Utilities (Electricity, Water, Trash)
- **5200-5299:** Contracted Services (Landscaping, Security, etc.)
- **5300-5399:** Repair & Maintenance
- **5400-5499:** Administration
- **5990-0000:** Total Operating Expenses

### Additional Expenses (6000 series)
- **6010-0000:** Off-Site Management
- **6014-0000:** Leasing Commissions
- **6020-0000:** Professional Fees
- **6040-6069:** Landlord-paid expenses
- **6190-0000:** Total Additional Operating Expenses
- **6199-0000:** TOTAL EXPENSES

### Summary Accounts
- **6299-0000:** NET OPERATING INCOME (NOI)
- **7010-0000:** Mortgage Interest
- **7020-0000:** Depreciation
- **7030-0000:** Amortization
- **9090-0000:** NET INCOME

## Edge Cases

### Rent Roll
- **Vacant units:** Tenant = "VACANT", Rent = $0
- **Month-to-month leases:** End date may be NULL or "MTM"
- **Multiple tenants per unit:** Store as single string or separate records

### Income Statement
- **Negative values:** Common in adjustments (Free Rent, Annual CAM credits)
- **Zero values:** Legitimate for many accounts (e.g., Percentage Rent)
- **Missing accounts:** Different properties have different expense accounts
- **Page breaks:** Sections may span multiple pages

## Quality Thresholds

| Metric | Rent Roll | Income Statement |
|--------|-----------|------------------|
| **Minimum Accuracy** | 95% of fields correct | 95% of fields correct |
| **Auto-Approve** | 99% confidence | 99% confidence |
| **Required Fields Completeness** | 90% of units | All critical accounts present |
| **Manual Review Trigger** | <95% confidence | <95% confidence OR validation failure |

## Output Formats

### Rent Roll CSV Columns (Typical)
```
property_name, unit_number, tenant_name, lease_type, 
lease_start_date, lease_end_date, area_sqft, 
monthly_rent, annual_rent, monthly_rent_per_sf, 
security_deposit
```

### Income Statement CSV Columns (Typical)
```
property_code, property_name, period_start_date, period_end_date,
account_code, account_description, line_category,
period_to_date_amount, period_to_date_percentage,
year_to_date_amount, year_to_date_percentage
```

## Database Schema Differences

### Rent Roll
- **Main table:** rent_roll_entries
- **One row per:** Unit/Tenant combination
- **Foreign keys:** property_id
- **Typical row count:** 10-100 per property (# of units)

### Income Statement
- **Main tables:** 
  - income_statement_header (1 per statement)
  - income_statement_line_items (40-120 per statement)
  - income_statement_summary (1 per statement)
- **One row per:** Account line item
- **Foreign keys:** statement_id → header
- **Typical row count:** 40-120 line items per statement

## Integration Points

### Rent Roll → Income Statement Validation
The sum of all tenant rents from the Rent Roll should approximately equal the "Base Rentals" line item in the Income Statement (within 5% tolerance due to timing differences, vacancies, and rent adjustments).

**Formula:**
```
Sum(Rent Roll Monthly Rents) × 12 ≈ Income Statement Base Rentals (Annual)
```

### Key Reconciliation Checks
1. **Base Rental Reconciliation:** Rent Roll total ≈ Income Statement 4010-0000
2. **Occupancy Impact:** If Rent Roll shows high vacancy, expect lower Base Rentals
3. **New Leases:** Rent Roll changes should appear in subsequent Income Statements
4. **Lease Expirations:** Should impact future Income Statement projections

## Processing Recommendations

### Rent Roll Processing
1. Extract property and date first
2. Process unit by unit (row by row)
3. Validate each unit independently
4. Roll up to property totals
5. Compare totals to Income Statement

### Income Statement Processing
1. Extract header (property, period) first
2. Extract income section with all accounts
3. Extract expense sections (Operating, Additional)
4. Extract below-the-line items
5. Validate all calculations
6. Generate summary metrics
7. Cross-validate with Rent Roll if available

## Common Pitfalls

### Rent Roll
- ❌ Missing vacant units
- ❌ Incorrect date formats
- ❌ Mixing up lease start/end dates
- ❌ Wrong rent per SF calculation
- ❌ Not handling month-to-month leases

### Income Statement
- ❌ Missing page 2 or 3 data
- ❌ Confusing PTD and YTD columns
- ❌ Not extracting negative values correctly
- ❌ Missing subtotals
- ❌ Not handling (parentheses) format for negatives
- ❌ Account code format errors

## Best Practices

### For Both Documents
✅ Always validate mathematical calculations
✅ Check for required fields before proceeding
✅ Compare to previous periods for anomalies
✅ Flag low-confidence extractions for review
✅ Maintain audit trail of all extractions
✅ Store original source document reference

### Rent Roll Specific
✅ Create records for vacant units with $0 rent
✅ Standardize date formats before storage
✅ Calculate missing fields when possible
✅ Flag unusual lease terms (very short or very long)
✅ Check for duplicate unit numbers

### Income Statement Specific
✅ Preserve account code hierarchy
✅ Flag unexpected negative values
✅ Verify all subtotals match their components
✅ Compare YTD to PTD for consistency
✅ Calculate and validate NOI margin
✅ Check operating expense ratio

## Error Code Summary

### Rent Roll Errors
- **R-E001:** Duplicate unit number
- **R-E002:** Monthly rent × 12 ≠ Annual rent
- **R-E003:** Lease end date ≤ Lease start date
- **R-E004:** Missing required field
- **R-W001:** Unusual rent per SF value
- **R-W002:** Security deposit outside typical range

### Income Statement Errors
- **I-E001:** Total Income calculation mismatch
- **I-E002:** Total Expenses calculation mismatch
- **I-E003:** NOI calculation mismatch
- **I-E004:** Net Income calculation mismatch
- **I-E005:** Missing required account
- **I-W001:** Unexpected negative value
- **I-W002:** Percentage sum ≠ 100%
- **I-W003:** Large period-over-period variance

## Template Files

### Project: REIMS2

**Templates Created:**
1. ✅ **Rent_Roll_Extraction_Requirements_v1.0.md**
   - Location: Project documentation
   - Use: Extracting tenant and lease data from rent rolls

2. ✅ **Income_Statement_Extraction_Template_v1.0.md**
   - Location: /mnt/user-data/outputs/
   - Use: Extracting financial data from income statements

**Sample Data Files:**
- Rent Roll: [Previously created examples]
- Income Statements: 
  - ESP_2023_Income_Statement.pdf
  - ESP_2024_Income_Statement.pdf
  - Hammond_Aire_2023_Income_Statement.pdf
  - Hammond_Aire_2024_Income_Statement.pdf
  - TCSH_2023_Income_Statement.pdf
  - TCSH_2024_Income_Statement.pdf
  - Wendover_Commons_2023_Income_Statement.pdf
  - Wendover_Commons_2024_Income_Statement.pdf

---

## Quick Start Checklist

### For Rent Roll Extraction:
- [ ] Read Rent Roll template document
- [ ] Identify property and date
- [ ] Extract all units (including vacant)
- [ ] Validate date ranges
- [ ] Calculate and verify rent per SF
- [ ] Check for duplicate units
- [ ] Generate output CSV
- [ ] Run quality checks

### For Income Statement Extraction:
- [ ] Read Income Statement template document
- [ ] Extract header information
- [ ] Extract all income accounts (4000 series)
- [ ] Extract all expense accounts (5000-6000 series)
- [ ] Extract below-the-line items (7000 series)
- [ ] Validate all calculations
- [ ] Verify account code formats
- [ ] Check percentage columns
- [ ] Generate summary metrics
- [ ] Run quality checks

---

*Last Updated: February 2025*
*Document Version: 1.0*
*Project: REIMS2 - Real Estate Income and Management System*
