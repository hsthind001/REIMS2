# Income Statement Extraction Requirements v1.0

## 1. Document Overview
- **Document Type:** Income Statement (Commercial Real Estate Properties)
- **Source:** Property Management System (Accrual Basis Accounting)
- **Frequency:** Monthly and Annual
- **Format:** PDF (native)
- **Properties Covered:** Eastern Shore Plaza (ESP), Hammond Aire Plaza (HMND), The Crossings of Spring Hill (TCSH), Wendover Commons (WEND)
- **Accounting Method:** Accrual Basis

## 2. Property Header Information

### 2.1 Property Identification
**Column Name:** Property Name
- **Description:** Full legal name of the property
- **Data Type:** Text
- **Required:** Yes
- **Example:** "Eastern Shore Plaza (esp)", "Hammond Aire Plaza (hmnd)"
- **Can be NULL:** No
- **Notes:** Often includes property code in parentheses

**Column Name:** Property Code
- **Description:** Short code identifier for the property
- **Data Type:** Text (2-4 characters)
- **Required:** Yes
- **Example:** "esp", "hmnd", "tcsh", "wend"
- **Can be NULL:** No
- **Validation:** Must be unique within portfolio

### 2.2 Period Information
**Column Name:** Period Type
- **Description:** Type of reporting period
- **Data Type:** Text (enumerated)
- **Required:** Yes
- **Possible Values:** "Monthly", "Annual", "Quarterly"
- **Example:** "Dec 2023" (Monthly), "Jan 2024-Dec 2024" (Annual)
- **Can be NULL:** No

**Column Name:** Period Start Date
- **Description:** Beginning date of the reporting period
- **Data Type:** Date
- **Format:** MM/DD/YYYY or MMM YYYY
- **Required:** Yes
- **Example:** "01/01/2024", "Dec 2023"
- **Can be NULL:** No

**Column Name:** Period End Date
- **Description:** Ending date of the reporting period
- **Data Type:** Date
- **Format:** MM/DD/YYYY or MMM YYYY
- **Required:** Yes
- **Example:** "12/31/2024", "Dec 2023"
- **Can be NULL:** No
- **Validation:** Must be >= Period Start Date

**Column Name:** Accounting Basis
- **Description:** Method of accounting used
- **Data Type:** Text
- **Required:** Yes
- **Example:** "Accrual"
- **Possible Values:** "Accrual", "Cash"
- **Can be NULL:** No

**Column Name:** Report Generation Date
- **Description:** Date when report was generated
- **Data Type:** Date
- **Format:** Day, Month DD, YYYY
- **Required:** No
- **Example:** "Thursday, February 06, 2025"
- **Can be NULL:** Yes

## 3. Income Line Items Structure

### 3.1 Line Item Fields (Repeating for each income item)

**Column Name:** Account Code
- **Description:** Unique identifier for the account/line item
- **Data Type:** Text (format: ####-####)
- **Required:** Yes
- **Example:** "4010-0000", "4020-0000"
- **Can be NULL:** No
- **Pattern:** Four digits, hyphen, four digits

**Column Name:** Account Description
- **Description:** Name/description of the income line item
- **Data Type:** Text
- **Required:** Yes
- **Example:** "Base Rentals", "Tax", "Insurance", "CAM"
- **Can be NULL:** No

**Column Name:** Period to Date Amount
- **Description:** Amount for the current reporting period
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes
- **Example:** 229422.31, -8089.61 (negative for adjustments)
- **Can be NULL:** Only if not applicable
- **Validation:** Can be positive or negative

**Column Name:** Period to Date Percentage
- **Description:** Percentage of total income for period
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes
- **Format:** Percentage value (0-100)
- **Example:** 89.18, -3.14
- **Can be NULL:** Only if amount is 0
- **Validation:** Sum of all percentages should equal 100%

**Column Name:** Year to Date Amount
- **Description:** Cumulative amount from start of year to date
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes
- **Example:** 2768568.46, 150962.44
- **Can be NULL:** Only for monthly statements where YTD not applicable
- **Validation:** For annual statements, YTD = Period Amount

**Column Name:** Year to Date Percentage
- **Description:** Percentage of total income year to date
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes
- **Format:** Percentage value (0-100)
- **Example:** 81.43, 4.44
- **Can be NULL:** Only if YTD Amount is null
- **Validation:** Sum should equal 100%

### 3.2 Standard Income Categories

**Primary Income Categories:**
1. **4010-0000:** Base Rentals - Primary rental income
2. **4013-0000:** Management Fee Income - Fees earned for management services
3. **4018-0000:** Interest Income - Interest earned on accounts
4. **4020-0000:** Tax - Real estate tax reimbursements
5. **4030-0000:** Insurance - Insurance reimbursements
6. **4040-0000:** CAM - Common Area Maintenance charges
7. **4050-0000:** Percentage Rent - Rent based on tenant sales percentage
8. **4055-0000:** Utilities Reimbursement - Utility cost recoveries
9. **4056-0000:** Termination Fee Income - Early lease termination fees
10. **4060-0000:** Annual Cams - Annual CAM reconciliation
11. **4090-0000:** Other Income - Miscellaneous income
12. **4091-0000:** End of Day Investment Sweep Int Income - Investment interest

**Special Income Adjustments:**
- Holdover Rent
- Free Rent (negative value)
- Co-Tenancy Rent Reduction (negative value)
- Bad Debt Expense (negative value)
- Less Bad Debt Write Offs (negative value)

**Column Name:** Total Income
- **Description:** Sum of all income line items
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes
- **Account Code:** 4990-0000
- **Validation:** Must equal sum of all income items
- **Tolerance:** ±0.05 for rounding

## 4. Expense Line Items Structure

### 4.1 Operating Expenses Category

**Account Code Range:** 5000-0000 to 5999-0000

**Major Subcategories:**

**A. Property Costs (5010-5014):**
- **5010-0000:** Property Tax
- **5012-0000:** Property Insurance
- **5014-0000:** Property Tax Savings Consultant

**B. Utility Expenses (5100-5199):**
- **5105-0000:** Electricity Service
- **5110-0000:** Gas Service
- **5115-0000:** Water & Sewer Service
- **5125-0000:** Trash Service
- **5199-0000:** Total Utility Expense (subtotal)

**C. Contracted Expenses (5200-5299):**
- **5210-0000:** Contract - Parking Lot Sweeping
- **5215-0000:** Contract - Building Pressure Washing
- **5220-0000:** Contract - Sidewalk Pressure Washing
- **5225-0000:** Contract - Snow Removal & Ice Melt
- **5230-0000:** Contract - Landscaping
- **5235-0000:** Contract - Janitorial/Portering
- **5240-0000:** Contract - Fire Safety Monitoring
- **5245-0000:** Contract - Pest Control
- **5255-0000:** Contract - Security
- **5270-0000:** Contract - Plumbing
- **5275-0000:** Contract - Elevator
- **5299-0000:** Total Contracted Expenses (subtotal)

**D. Repair & Maintenance Operating Expenses (5300-5399):**
- **5302-0000:** R&M - Elevator Repairs
- **5306-0000:** R&M - Landscape Repairs
- **5308-0000:** R&M - Irrigation Repairs
- **5312-0000:** R&M - Bulk Trash Removal
- **5314-0000:** R&M - Fire Safety Repairs
- **5316-0000:** R&M - Fire Sprinkler Inspection
- **5318-0000:** R&M - Plumbing
- **5322-0000:** R&M - Electrical Inspections & Repairs
- **5326-0000:** R&M - Building Maintenance
- **5332-0000:** R&M - Exterior Painting
- **5334-0000:** R&M - Parking Lot Repairs
- **5336-0000:** R&M - Sidewalk & Concrete Repairs
- **5338-0000:** R&M - Exterior
- **5340-0000:** R&M - Interior
- **5342-0000:** R&M - HVAC
- **5356-0000:** R&M - Lighting
- **5358-0000:** R&M - Misc Maintenance Supplies
- **5360-0000:** R&M - Roofing Repairs - Major
- **5362-0000:** R&M - Roofing Repairs - Minor
- **5364-0000:** R&M - Doors/Locks N Keys
- **5366-0000:** R&M - Seasonal Decoration
- **5370-0000:** R&M - Pylon Signs
- **5376-0000:** R&M - Misc
- **5399-0000:** Total R&M Operating Expenses (subtotal)

**E. Administration Expenses (5400-5499):**
- **5400-0002:** Salaries Expense
- **5400-0003:** Benefits Expense
- **5400-0004:** Computer & Software Expense
- **5400-0006:** Employee HR Related Expense
- **5400-0090:** Office Supplies Expense
- **5435-0000:** Meals & Entertainment
- **5440-0000:** Management Office Expense
- **5445-0000:** Management Office Supplies & Equip
- **5455-0000:** Permits
- **5460-0000:** Postage & Carrier
- **5465-0000:** Telephone
- **5470-0000:** Travel
- **5490-0000:** Lease Abstracting
- **5499-0000:** Total Administration Expense (subtotal)

**F. Total Operating Expenses:**
- **5990-0000:** Total Operating Expenses
- **Validation:** Must equal sum of all operating expense subcategories

### 4.2 Additional Operating Expenses Category

**Account Code Range:** 6000-0000 to 6199-0000

**Major Line Items:**
- **6010-0000:** Off Site Management
- **6010-5000:** On-Site Management Fee
- **6012-0000:** Franchise Tax
- **6012-5000:** Pass Thru Entity Tax
- **6014-0000:** Leasing Commissions
- **6016-0000:** Tenant Improvements
- **6020-0000:** Professional Fees
- **6020-5000:** Accounting Fee
- **6020-6000:** Asset Management Fee
- **6020-7000:** CMF-Construction Management Fee
- **6022-0000:** Legal Fees / SOS Fee
- **6024-0000:** Bank Charges
- **6025-0000:** Bank Control A/c Fee

**G. Landlord Expenses (6040-6069):**
- **6050-0000:** LL Repairs & Maintenance
- **6051-0000:** LL - Plumbing
- **6052-0000:** LL - Electrical Repairs
- **6054-0000:** LL - HVAC Repairs
- **6058-0000:** LL - Vacant Space Expenses
- **6059-0000:** LL - General Repairs
- **6061-0000:** LL - Electricity
- **6064-0000:** LL-Misc
- **6065-0000:** LL-Site Map
- **6069-0000:** Total LL Expense (subtotal)

**H. Total Additional Operating Expenses:**
- **6190-0000:** Total Additional Operating Expenses
- **Validation:** Must equal sum of all additional operating expense items

### 4.3 Total Expenses Summary

**Column Name:** Total Expenses
- **Description:** Sum of all operating and additional operating expenses
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes
- **Account Code:** 6199-0000
- **Validation:** Must equal Operating Expenses + Additional Operating Expenses
- **Tolerance:** ±0.05 for rounding

## 5. Net Operating Income (NOI)

**Column Name:** Net Operating Income
- **Description:** Total Income minus Total Expenses
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes
- **Account Code:** 6299-0000
- **Formula:** Total Income - Total Expenses
- **Validation:** Must match calculated value
- **Tolerance:** ±0.10 for rounding

## 6. Other Income/Expenses (Below the Line)

**Account Code Range:** 7000-0000 to 7099-0000

**Standard Line Items:**
- **7010-0000:** Mortgage Interest - Interest paid on property loans
- **7020-0000:** Depreciation - Non-cash depreciation expense
- **7030-0000:** Amortization - Non-cash amortization expense
- **7090-0000:** Total Other Income/Expense (subtotal)

**Column Name:** Total Other Income/Expense
- **Description:** Sum of mortgage interest, depreciation, and amortization
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes
- **Validation:** Must equal sum of line items 7010-7030

## 7. Net Income (Bottom Line)

**Column Name:** Net Income
- **Description:** Net Operating Income minus Other Income/Expenses
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes
- **Account Code:** 9090-0000
- **Formula:** NOI - Total Other Income/Expense
- **Validation:** Must match calculated value
- **Can be Negative:** Yes
- **Tolerance:** ±0.10 for rounding

## 8. Data Validation Rules

### 8.1 Mathematical Validations

1. **Total Income Calculation:**
   - Rule: Sum(All Income Items 4010-4091) = Total Income (4990)
   - Tolerance: ±$0.05
   - Error Level: Critical

2. **Total Operating Expenses Calculation:**
   - Rule: Sum(Property Tax + Insurance + Utilities + Contracted + R&M + Admin) = Total Operating Expenses (5990)
   - Tolerance: ±$0.05
   - Error Level: Critical

3. **Total Additional Operating Expenses Calculation:**
   - Rule: Sum(Off-Site Management + Leasing + Fees + LL Expenses) = Total Additional Operating Expenses (6190)
   - Tolerance: ±$0.05
   - Error Level: Critical

4. **Total Expenses Calculation:**
   - Rule: Total Operating Expenses + Total Additional Operating Expenses = Total Expenses (6199)
   - Tolerance: ±$0.10
   - Error Level: Critical

5. **Net Operating Income Calculation:**
   - Rule: Total Income - Total Expenses = NOI (6299)
   - Tolerance: ±$0.10
   - Error Level: Critical

6. **Net Income Calculation:**
   - Rule: NOI - Total Other Income/Expense = Net Income (9090)
   - Tolerance: ±$0.10
   - Error Level: Critical

7. **Percentage Column Validation:**
   - Rule: Sum of all Period to Date % should equal 100% for income section
   - Tolerance: ±0.5%
   - Error Level: Warning

8. **YTD vs Period Validation (Annual Statements):**
   - Rule: For annual statements, Year to Date Amount should equal Period to Date Amount
   - Tolerance: ±$0.01
   - Error Level: Critical

### 8.2 Data Type Validations

1. **Account Code Format:**
   - Pattern: ####-####
   - Example: 4010-0000, 5105-0000
   - Validation: Must match pattern exactly

2. **Numeric Fields:**
   - All amount fields must be valid decimal numbers
   - Precision: 2 decimal places
   - Can be negative: Yes (for adjustments and net income)
   - Maximum value: 999,999,999.99

3. **Percentage Fields:**
   - Range: -100.00 to 100.00
   - Precision: 2 decimal places
   - Format: Numeric (not percentage symbol)

4. **Date Fields:**
   - Format: MM/DD/YYYY or MMM YYYY
   - Validation: Must be valid date
   - Period End Date must be >= Period Start Date

### 8.3 Logical Validations

1. **Negative Values Check:**
   - Expected negative items: Free Rent, Bad Debt Expense, Co-Tenancy Reduction, Annual Cams (sometimes)
   - Unexpected negative items: Base Rentals, Property Tax, Insurance (flag for review)
   - Action: Flag unexpected negatives for manual review

2. **Zero Values Check:**
   - Some line items may legitimately be zero
   - Flag: If Base Rentals = 0 (Critical)
   - Flag: If Total Income = 0 (Critical)
   - Flag: If major expense categories all = 0 (Warning)

3. **Subtotal Consistency:**
   - All subtotals (ending in -5199, -5299, -5399, -5499, etc.) must equal sum of their component items
   - Error Level: Critical

4. **Period Consistency:**
   - Period to Date amounts should be <= Year to Date amounts
   - Exception: Not applicable for annual statements where PTD = YTD
   - Error Level: Warning

### 8.4 Cross-Property Validations

1. **Account Code Consistency:**
   - Same account codes should have same descriptions across all properties
   - Example: 4010-0000 should always be "Base Rentals"
   - Error Level: Warning

2. **Required Accounts:**
   - Minimum required accounts for valid income statement:
     * 4010-0000 (Base Rentals)
     * 4990-0000 (Total Income)
     * 5010-0000 (Property Tax)
     * 5990-0000 (Total Operating Expenses)
     * 6199-0000 (Total Expenses)
     * 6299-0000 (Net Operating Income)
     * 9090-0000 (Net Income)
   - Error Level: Critical if any missing

3. **Reasonable Value Ranges:**
   - NOI Margin should typically be 30-80% of Total Income
   - If outside range, flag for review
   - Property Insurance typically 0.5-3% of Total Income
   - Property Tax typically 5-15% of Total Income

## 9. Business Rules

### 9.1 Hierarchy Rules

1. **Account Code Hierarchy:**
   - Level 1: Major category (4000-0000, 5000-0000, 6000-0000, 7000-0000, 9000-0000)
   - Level 2: Subcategory (5100-0000, 5200-0000, etc.)
   - Level 3: Line items (5105-0000, 5110-0000, etc.)
   - Level 4: Subtotals (5199-0000, 5299-0000, etc.)

2. **Subtotal Roll-up Logic:**
   - Subtotals must include all line items in their range
   - Example: 5199-0000 includes all 5100-5198 items
   - Subtotals roll up to category totals
   - Category totals roll up to Total Expenses

### 9.2 Treatment of Special Items

1. **Depreciation and Amortization:**
   - These are non-cash expenses
   - Appear below NOI line
   - Should be flagged as "Below the Line" items
   - Do not affect NOI calculation

2. **Mortgage Interest:**
   - Appears below NOI line
   - Property-specific (varies by financing)
   - Does not affect NOI calculation

3. **Annual CAM Reconciliation:**
   - Can be positive (additional charges) or negative (credits)
   - Typically appears at year-end
   - Should reconcile to total CAM charges for the year

4. **Percentage Rent:**
   - May be zero for many months
   - Typically calculated on tenant sales thresholds
   - May show negative if over-accrued and reversed

### 9.3 Period-Specific Rules

1. **Monthly Statements:**
   - Period to Date = Current month only
   - Year to Date = January through current month
   - YTD should be >= PTD (unless first month of year)

2. **Annual Statements:**
   - Period to Date = Full year
   - Year to Date = Same as Period to Date
   - Both columns should match exactly

3. **Multi-Year Comparison:**
   - When comparing multiple years, account codes should be consistent
   - Descriptions may vary slightly but account numbers must match
   - Flag any account code changes between years

## 10. Edge Cases and Special Handling

### 10.1 Missing or Incomplete Data

**Scenario:** Some line items present in one property but not others
- **Handling:** Mark as $0.00 if not present in statement
- **Example:** Some properties have elevator expenses, others don't
- **Action:** Create full line item with zero value

**Scenario:** Subtotal missing but individual items present
- **Handling:** Calculate subtotal from individual items
- **Flag:** Mark as "Calculated" vs "Extracted"
- **Validation:** Ensure calculation is correct

**Scenario:** Page break in middle of section
- **Handling:** Combine data from multiple pages
- **Validation:** Ensure no line items are duplicated or skipped
- **Check:** Verify subtotals match after combining

### 10.2 Formatting Variations

**Scenario:** Negative numbers shown with parentheses vs minus sign
- **Examples:** "(8,089.61)" vs "-8,089.61"
- **Handling:** Standardize to minus sign format
- **Validation:** Ensure proper negative value in database

**Scenario:** Thousand separators (commas)
- **Example:** "2,768,568.46" vs "2768568.46"
- **Handling:** Remove commas, store as pure number
- **Validation:** Ensure no data loss in conversion

**Scenario:** Currency symbols
- **Example:** "$229,422.31" vs "229,422.31"
- **Handling:** Remove currency symbols
- **Assumption:** All amounts in USD

**Scenario:** Percentage symbols in percentage columns
- **Example:** "89.18%" vs "89.18"
- **Handling:** Remove % symbol, store as numeric
- **Format:** Store as decimal (89.18, not 0.8918)

### 10.3 Data Quality Issues

**Scenario:** OCR errors in numbers
- **Common Errors:** 
  * 0 vs O
  * 1 vs l vs I
  * 5 vs S
  * 8 vs B
- **Detection:** Look for impossible values or calculation mismatches
- **Action:** Flag for manual review

**Scenario:** Misaligned columns
- **Issue:** Values from one column bleeding into another
- **Detection:** Check if amounts are in wrong column
- **Validation:** Verify percentages are in valid range (0-100)

**Scenario:** Split line descriptions
- **Example:** Description on one line, amount on next line
- **Handling:** Combine description and match with correct amount
- **Validation:** Ensure account code matches description

## 11. Output Requirements

### 11.1 Primary Data Table: Income Statement Header

**Table Name:** income_statement_header

**Columns:**
1. statement_id (Primary Key, Auto-increment)
2. property_code (Text, 4 chars)
3. property_name (Text)
4. period_start_date (Date)
5. period_end_date (Date)
6. period_type (Text: "Monthly" or "Annual")
7. accounting_basis (Text: "Accrual" or "Cash")
8. report_generation_date (Date, nullable)
9. extraction_date (Timestamp)
10. extraction_confidence_score (Decimal 0-100)
11. data_source_filename (Text)
12. data_source_page_count (Integer)

**Example Row:**
```
statement_id: 1
property_code: esp
property_name: Eastern Shore Plaza (esp)
period_start_date: 2023-12-01
period_end_date: 2023-12-31
period_type: Monthly
accounting_basis: Accrual
report_generation_date: 2025-02-06
extraction_date: 2025-02-10 14:32:18
extraction_confidence_score: 98.5
data_source_filename: ESP_2023_Income_Statement.pdf
data_source_page_count: 3
```

### 11.2 Line Items Data Table: Income Statement Line Items

**Table Name:** income_statement_line_items

**Columns:**
1. line_item_id (Primary Key, Auto-increment)
2. statement_id (Foreign Key to income_statement_header)
3. account_code (Text, format ####-####)
4. account_description (Text)
5. line_category (Text: "INCOME" | "OPERATING_EXPENSE" | "ADDITIONAL_EXPENSE" | "OTHER_EXPENSE" | "SUMMARY")
6. line_subcategory (Text: "Utility" | "Contracted" | "R&M" | etc.)
7. is_subtotal (Boolean)
8. is_total (Boolean)
9. period_to_date_amount (Decimal 12,2)
10. period_to_date_percentage (Decimal 5,2)
11. year_to_date_amount (Decimal 12,2, nullable)
12. year_to_date_percentage (Decimal 5,2, nullable)
13. line_number (Integer - order in statement)
14. extraction_confidence_score (Decimal 0-100)

**Example Rows:**
```
line_item_id: 1
statement_id: 1
account_code: 4010-0000
account_description: Base Rentals
line_category: INCOME
line_subcategory: Primary Income
is_subtotal: false
is_total: false
period_to_date_amount: 229422.31
period_to_date_percentage: 89.18
year_to_date_amount: 2768568.46
year_to_date_percentage: 81.43
line_number: 1
extraction_confidence_score: 99.2

line_item_id: 15
statement_id: 1
account_code: 4990-0000
account_description: TOTAL INCOME
line_category: INCOME
line_subcategory: null
is_subtotal: false
is_total: true
period_to_date_amount: 257255.40
period_to_date_percentage: 100.00
year_to_date_amount: 3399972.96
year_to_date_percentage: 100.00
line_number: 15
extraction_confidence_score: 99.8
```

### 11.3 Summary Metrics Table: Income Statement Summary

**Table Name:** income_statement_summary

**Columns:**
1. summary_id (Primary Key, Auto-increment)
2. statement_id (Foreign Key to income_statement_header)
3. total_income_ptd (Decimal 12,2)
4. total_income_ytd (Decimal 12,2)
5. total_operating_expenses_ptd (Decimal 12,2)
6. total_operating_expenses_ytd (Decimal 12,2)
7. total_additional_expenses_ptd (Decimal 12,2)
8. total_additional_expenses_ytd (Decimal 12,2)
9. total_expenses_ptd (Decimal 12,2)
10. total_expenses_ytd (Decimal 12,2)
11. noi_ptd (Decimal 12,2)
12. noi_ytd (Decimal 12,2)
13. noi_margin_ptd_pct (Decimal 5,2)
14. noi_margin_ytd_pct (Decimal 5,2)
15. mortgage_interest_ptd (Decimal 12,2)
16. mortgage_interest_ytd (Decimal 12,2)
17. depreciation_ptd (Decimal 12,2)
18. depreciation_ytd (Decimal 12,2)
19. amortization_ptd (Decimal 12,2)
20. amortization_ytd (Decimal 12,2)
21. net_income_ptd (Decimal 12,2)
22. net_income_ytd (Decimal 12,2)
23. validation_status (Text: "PASSED" | "WARNING" | "FAILED")
24. validation_notes (Text, nullable)

**Calculated Fields:**
- noi_margin_ptd_pct = (noi_ptd / total_income_ptd) * 100
- noi_margin_ytd_pct = (noi_ytd / total_income_ytd) * 100

### 11.4 CSV Export Format

**Filename Convention:** `{property_code}_{period_start}_{period_end}_income_statement.csv`

**Example:** `esp_2023-12_2023-12_income_statement.csv`

**CSV Columns (in order):**
1. property_code
2. property_name
3. period_start_date
4. period_end_date
5. account_code
6. account_description
7. line_category
8. is_subtotal
9. is_total
10. period_to_date_amount
11. period_to_date_percentage
12. year_to_date_amount
13. year_to_date_percentage
14. extraction_confidence_score

**CSV Requirements:**
- Header row: Yes (column names)
- Delimiter: Comma (,)
- Text qualifier: Double quote (")
- Encoding: UTF-8
- Line ending: CRLF (\r\n)
- Decimal separator: Period (.)
- Thousand separator: None (remove commas)

## 12. Quality Thresholds

### 12.1 Extraction Accuracy

**Minimum Acceptable Accuracy:** 95% of fields correctly extracted
- **Measurement:** Compare extracted values to source document
- **Critical Fields:** Account codes, amounts, totals
- **Non-Critical Fields:** Descriptions (minor spelling variations acceptable)

**Auto-Approve Threshold:** 99% confidence score
- **Criteria:** All validations pass
- **Criteria:** No mathematical mismatches
- **Criteria:** All required fields present
- **Action:** Approve for automatic processing

**Human Review Required:** <95% confidence score
- **Triggers:**
  * Any critical field missing
  * Mathematical validation failure
  * Account code format errors
  * Negative values in unexpected accounts
  * Subtotal mismatches
- **Action:** Queue for manual review

### 12.2 Completeness Thresholds

**Minimum Completeness:** 90% of expected line items present
- **Critical Items Required:**
  * Total Income (4990-0000)
  * Total Operating Expenses (5990-0000)
  * Total Expenses (6199-0000)
  * Net Operating Income (6299-0000)
  * Net Income (9090-0000)
- **Action:** Flag if any critical item missing

**Expected Line Item Count by Property Type:**
- Small Property: 40-60 line items
- Medium Property: 60-80 line items
- Large Property: 80-120 line items

**Completeness Check:**
- Compare line item count to previous periods
- Flag if current count < 80% of previous average
- Investigate missing categories

### 12.3 Consistency Checks

**Period-over-Period Consistency:**
- Account codes should match previous periods
- Large variances (>50%) should be flagged
- New accounts should be noted
- Deleted accounts should be investigated

**Cross-Property Consistency:**
- Same account codes across all properties
- Same descriptions for same account codes
- Flag inconsistencies for review

## 13. Sample Data Examples

### 13.1 Perfect Extraction Example

**Source:** Eastern Shore Plaza, Dec 2023

**Extracted Data:**
```json
{
  "header": {
    "property_code": "esp",
    "property_name": "Eastern Shore Plaza (esp)",
    "period_start_date": "2023-12-01",
    "period_end_date": "2023-12-31",
    "period_type": "Monthly",
    "accounting_basis": "Accrual"
  },
  "income_items": [
    {
      "account_code": "4010-0000",
      "description": "Base Rentals",
      "period_amount": 229422.31,
      "period_pct": 89.18,
      "ytd_amount": 2768568.46,
      "ytd_pct": 81.43
    },
    {
      "account_code": "4020-0000",
      "description": "Tax",
      "period_amount": 5770.07,
      "period_pct": 2.24,
      "ytd_amount": 68793.27,
      "ytd_pct": 2.02
    }
  ],
  "summary": {
    "total_income_ptd": 257255.40,
    "total_income_ytd": 3399972.96,
    "noi_ptd": 73106.12,
    "noi_ytd": 2326704.42,
    "noi_margin_ptd": 28.42,
    "net_income_ptd": -81727.97,
    "net_income_ytd": 736023.07
  },
  "validation": {
    "status": "PASSED",
    "confidence_score": 99.5,
    "checks_passed": 15,
    "checks_failed": 0,
    "warnings": 0
  }
}
```

### 13.2 Example with Warnings

**Issue:** Unusual negative value in Base Rentals

**Validation Output:**
```json
{
  "validation": {
    "status": "WARNING",
    "confidence_score": 92.0,
    "warnings": [
      {
        "field": "4010-0000",
        "description": "Base Rentals",
        "issue": "Unexpected negative value",
        "value": -1234.56,
        "severity": "WARNING",
        "recommendation": "Verify if credit/adjustment is correct"
      }
    ]
  }
}
```

### 13.3 Example with Critical Errors

**Issue:** Total Income calculation mismatch

**Validation Output:**
```json
{
  "validation": {
    "status": "FAILED",
    "confidence_score": 78.5,
    "errors": [
      {
        "check": "total_income_calculation",
        "issue": "Sum of income items does not match Total Income",
        "expected": 257255.40,
        "actual": 257240.00,
        "difference": 15.40,
        "severity": "CRITICAL",
        "action": "REVIEW_REQUIRED"
      }
    ]
  }
}
```

## 14. Extraction Process Workflow

### 14.1 Pre-Processing Steps

1. **Document Reception:**
   - Verify file format (PDF)
   - Check file integrity
   - Log receipt timestamp

2. **Document Analysis:**
   - Identify property from filename or header
   - Determine period type (monthly/annual)
   - Count pages
   - Detect document orientation

3. **OCR/Text Extraction:**
   - Extract all text with position coordinates
   - Maintain spatial relationships
   - Preserve formatting cues (bold, alignment)

### 14.2 Data Extraction Steps

1. **Header Extraction:**
   - Property name and code
   - Period information
   - Accounting basis
   - Report date

2. **Income Section Extraction:**
   - Extract all account codes 4000-4999
   - Capture amounts and percentages
   - Identify subtotals

3. **Expense Section Extraction:**
   - Extract all account codes 5000-6999
   - Organize into categories
   - Calculate subtotals

4. **Below-the-Line Items:**
   - Extract mortgage interest
   - Extract depreciation
   - Extract amortization

5. **Summary Extraction:**
   - Total Income
   - Total Expenses
   - NOI
   - Net Income

### 14.3 Post-Processing Steps

1. **Data Validation:**
   - Run all mathematical checks
   - Verify data types
   - Check for required fields
   - Validate logical relationships

2. **Quality Scoring:**
   - Calculate confidence score per field
   - Calculate overall confidence score
   - Assign validation status

3. **Exception Handling:**
   - Flag warnings
   - Identify critical errors
   - Route for appropriate review

4. **Data Storage:**
   - Insert into database tables
   - Generate CSV exports
   - Create audit trail

5. **Reporting:**
   - Generate extraction report
   - Log metrics
   - Alert on failures

## 15. Advanced Validation Rules

### 15.1 Trend Analysis Validations

**Rule:** Month-over-Month Variance Check
- **Threshold:** >30% change in NOI
- **Action:** Flag for review
- **Exception:** Known seasonal properties

**Rule:** Year-over-Year Comparison
- **Threshold:** >50% change in key metrics
- **Metrics:** Total Income, NOI, Net Income
- **Action:** Highlight for management review

**Rule:** Occupancy-Based Income Check
- **Logic:** Base Rentals should correlate with known occupancy
- **Calculation:** Base Rentals / Expected Rent at 100% = Effective Occupancy %
- **Flag:** If effective occupancy <50% or >105%

### 15.2 Industry Benchmark Validations

**Rule:** Operating Expense Ratio
- **Calculation:** Total Operating Expenses / Total Income
- **Expected Range:** 25-45% for most properties
- **Action:** Flag if outside range

**Rule:** Management Fee Check
- **Expected:** Off-Site Management typically 3-5% of Total Income
- **Action:** Flag if outside range

**Rule:** Property Tax Check
- **Expected:** Property Tax typically 5-15% of Total Income
- **Action:** Flag if significantly outside range

### 15.3 Account Code Sequence Validations

**Rule:** Sequential Account Code Check
- **Logic:** Account codes should follow logical sequence
- **Example:** If 5105-0000 exists, 5100-0000 category should also exist
- **Action:** Flag missing parent categories

**Rule:** Orphaned Subtotals Check
- **Logic:** Every subtotal should have at least one line item
- **Example:** "Total Utility Expense" with no utility items above it
- **Action:** Flag for review

## 16. Error Messages and Codes

### 16.1 Critical Errors (E-series)

- **E001:** Total Income calculation mismatch (difference > $0.10)
- **E002:** Total Expenses calculation mismatch (difference > $0.10)
- **E003:** NOI calculation mismatch (difference > $0.10)
- **E004:** Net Income calculation mismatch (difference > $0.10)
- **E005:** Missing required account code
- **E006:** Invalid account code format
- **E007:** Invalid date format or date range
- **E008:** Duplicate line items detected
- **E009:** Property identification failed
- **E010:** Period identification failed

### 16.2 Warnings (W-series)

- **W001:** Unusual negative value in income account
- **W002:** Zero value in typically non-zero account
- **W003:** Percentage column sum ≠ 100% (tolerance exceeded)
- **W004:** Large period-over-period variance (>50%)
- **W005:** Missing optional field
- **W006:** Low confidence score (<90%) on specific field
- **W007:** Account description inconsistency across properties
- **W008:** Subtotal mismatch (within tolerance but noteworthy)
- **W009:** NOI margin outside typical range
- **W010:** Operating expense ratio outside typical range

### 16.3 Info Messages (I-series)

- **I001:** New account code detected (not in previous periods)
- **I002:** Account code not used in this period (was in previous)
- **I003:** First period for property (no comparison data)
- **I004:** Annual statement detected
- **I005:** Calculated subtotal (not extracted from document)

## 17. Implementation Recommendations

### 17.1 Extraction Tool Requirements

**Must Have:**
- Table detection and extraction
- Column alignment preservation
- Multi-page processing
- Numeric value recognition with decimal precision
- Negative number handling (both - and () formats)

**Should Have:**
- Machine learning for field classification
- Historical data comparison
- Automatic validation
- Exception routing
- Confidence scoring per field

**Nice to Have:**
- Natural language processing for description matching
- Predictive variance flagging
- Automated trend analysis
- Dashboard visualization

### 17.2 Processing Order

1. Extract header information first
2. Extract and validate income section
3. Extract and validate operating expenses
4. Extract and validate additional expenses
5. Extract below-the-line items
6. Validate all totals and calculations
7. Generate summary metrics
8. Run cross-validations
9. Assign quality scores
10. Route for appropriate review/approval

### 17.3 Performance Benchmarks

- **Processing Time:** <60 seconds per statement
- **Accuracy:** >98% for automated extraction
- **Human Review Rate:** <10% of statements
- **Error Detection Rate:** >95% of issues identified automatically

## 18. Glossary of Terms

**NOI (Net Operating Income):** Total Income minus Total Operating Expenses and Additional Operating Expenses, before mortgage interest and depreciation.

**Below the Line:** Expenses that appear after NOI calculation, typically financing costs (mortgage interest) and non-cash expenses (depreciation, amortization).

**CAM (Common Area Maintenance):** Charges to tenants for their share of maintaining common areas.

**Percentage Rent:** Additional rent based on a percentage of tenant sales, usually above a threshold.

**Triple Net (NNN):** Lease structure where tenant pays base rent plus their share of property taxes, insurance, and CAM.

**Accrual Basis:** Accounting method that recognizes revenue when earned and expenses when incurred, regardless of cash flow timing.

**YTD (Year to Date):** Cumulative totals from the beginning of the fiscal year to the current reporting period.

**PTD (Period to Date):** Totals for the specific reporting period only (e.g., one month).

**Operating Expense Ratio:** Total operating expenses divided by total income, expressed as a percentage.

**NOI Margin:** NOI divided by total income, expressed as a percentage - indicates operational efficiency.

---

## Document Version History

- **Version 1.0** - Initial Release - Created comprehensive income statement extraction template with detailed validation rules and data structures.

## Template Usage Notes

This template should be used in conjunction with:
1. OCR/PDF extraction tools
2. Data validation scripts
3. Database schema definitions
4. Quality control procedures
5. Staff training materials

Regular updates should be made based on:
- New property additions
- Changes in accounting practices
- Enhanced validation requirements
- User feedback
- Error pattern analysis
