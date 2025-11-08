# Rent Roll Extraction Requirements v2.0
**Updated Based on Actual Rent Roll Format Analysis**

## 1. Document Overview
- **Document Type:** Rent Roll (Tenancy Schedule I)
- **Source:** Property Management System
- **Frequency:** Monthly
- **Format:** PDF (native/table format)
- **Properties Covered:** Multiple commercial properties (Hammond Aire Plaza, TCSH, Wendover Commons, Eastern Shore Plaza)
- **Report Date Format:** "As of Date: MM/DD/YYYY"

---

## 2. Column Definitions

### 2.1 Property/Location Information

#### Property Name
- **Column Name:** Property
- **Description:** Name of the commercial property/plaza with abbreviated code in parentheses
- **Data Type:** Text
- **Required:** Yes
- **Format:** "Property Name (code)"
- **Example:** "Hammond Aire Plaza(hmnd)", "The Crossings of Spring Hill (tcsh)"
- **Notes:** May repeat for each tenant and gross rent calculation row

#### Unit Number / Suite
- **Column Name:** Unit(s)
- **Description:** Physical unit identifier
- **Data Type:** Text (may contain letters, hyphens, ranges)
- **Required:** Yes
- **Examples:** 
  - Single unit: "001", "106", "1000"
  - Multiple units: "015, 016", "009-A, 009-B, 009-C"
  - Alphanumeric: "008-B", "0D0", "B-101"
  - Special: "LAND", "COMMON", "Z-ATM"
- **Can be NULL:** No (even vacant units have unit numbers)
- **Notes:** 
  - Must be unique within a property
  - May represent multiple contiguous units
  - Special codes like "LAND" for ground leases

### 2.2 Tenant Information

#### Tenant Name / Lessee
- **Column Name:** Lease
- **Description:** Legal name of tenant or entity description
- **Data Type:** Text
- **Required:** Yes (except for vacant units)
- **Format:** Usually includes legal entity type and may include store/location numbers
- **Examples:** 
  - "CEJR Health Services, LLC (t0000490)"
  - "Subway Real Estate, LLC (t0000508)"
  - "Michaels #3102 / Michaels Stores Inc (t0000526)"
  - "VACANT" (for vacant units)
- **Notes:** 
  - Often includes tenant ID in parentheses (t0000xxx)
  - May include DBA names separated by "/"
  - Multiple names may indicate co-tenants
  - "VACANT" indicates unoccupied space

#### Lease Type
- **Column Name:** Lease Type
- **Description:** Type of lease agreement
- **Data Type:** Text (enumerated values)
- **Required:** Yes
- **Possible Values:**
  - "Retail NNN" (Triple Net - most common)
  - "Retail Gross"
  - "[NAP]-Exp Only" (Non-Assignable Parking - Expense Only)
- **Can be NULL:** Only for vacant units
- **Notes:** NNN means tenant pays proportionate share of taxes, insurance, and CAM

### 2.3 Lease Terms

#### Area / Square Feet
- **Column Name:** Area
- **Description:** Rentable square footage of the unit
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes
- **Format:** Numbers with comma separators (e.g., "20,087.00")
- **Range:** 0.00 to 100,000+
- **Can be NULL:** Only for special cases (e.g., ATM locations, signage)
- **Validation:** 
  - Must be >= 0
  - Typically 100 - 100,000 for retail units
  - 0.00 is valid for parking rights, ATMs, signage leases
- **Notes:** This is the billable square footage

#### Lease From / Start Date
- **Column Name:** Lease From
- **Description:** Date when lease term begins (commencement date)
- **Data Type:** Date
- **Required:** Yes (for active leases)
- **Format:** MM/DD/YYYY
- **Examples:** "04/17/2004", "01/01/2023", "11/29/2013"
- **Can be NULL:** Only if vacant
- **Validation:** 
  - Must be <= report "As of Date"
  - Must be <= Lease To date (if present)

#### Lease To / End Date / Expiration
- **Column Name:** Lease To
- **Description:** Date when lease term ends (expiration date)
- **Data Type:** Date
- **Required:** Conditional
- **Format:** MM/DD/YYYY
- **Examples:** "02/29/2028", "12/31/2025", "06/30/2027"
- **Can be NULL:** Yes (for month-to-month or certain lease types)
- **Validation:** 
  - Must be >= Lease From date
  - Should be >= report "As of Date" for active leases
- **Notes:** 
  - NULL values may indicate month-to-month leases
  - Some leases show long-term dates (e.g., "12/31/2076")

#### Term (Months)
- **Column Name:** Term
- **Description:** Total original lease term in months
- **Data Type:** Integer
- **Required:** Conditional
- **Examples:** 64, 121, 287, 457
- **Can be NULL:** Yes (for month-to-month or when end date is not specified)
- **Validation:** 
  - Should equal months between Lease From and Lease To (±1-2 months tolerance)
  - Typical range: 12 to 600 months
- **Calculation:** Months from start to end of original lease term

#### Tenancy Years
- **Column Name:** Tenancy Years
- **Description:** Years of tenancy as of report date (time in occupancy)
- **Data Type:** Decimal (2 decimal places)
- **Required:** Conditional
- **Examples:** 21.08, 36.67, 0.75, 16.83
- **Can be NULL:** Only for vacant units
- **Validation:** 
  - Should be <= Term in years (within tolerance)
  - Must be >= 0
- **Calculation:** Years from Lease From date to report date

### 2.4 Rent Information

#### Monthly Rent / Base Rent
- **Column Name:** Monthly Rent
- **Description:** Monthly base rent amount (excludes CAM, taxes, insurance in NNN leases)
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes (except vacant)
- **Format:** Numbers with comma separators
- **Examples:** "3,300.00", "13,117.50", "21,500.00"
- **Can be NULL:** Only if vacant
- **Validation:** 
  - Must be >= 0
  - For NNN leases, this is base rent only
- **Notes:** 
  - May be 0.00 for expense-only leases
  - Represents minimum guaranteed rent

#### Monthly Rent/Area (Rent per SF)
- **Column Name:** Monthly Rent/Area
- **Description:** Monthly rent divided by area (price per square foot)
- **Data Type:** Decimal (2 decimal places)
- **Required:** No (calculated field)
- **Examples:** "1.83", "3.06", "0.92"
- **Can be NULL:** Yes (especially when Area is 0)
- **Validation:** Should equal Monthly Rent / Area (±$0.05 tolerance)
- **Calculation:** Monthly Rent ÷ Area
- **Notes:** Key metric for comparing lease rates

#### Annual Rent
- **Column Name:** Annual Rent
- **Description:** Annual base rent amount
- **Data Type:** Decimal (2 decimal places)
- **Required:** Yes (except vacant)
- **Format:** Numbers with comma separators
- **Examples:** "39,600.00", "157,410.00", "268,000.00"
- **Can be NULL:** Only if vacant
- **Validation:** Should equal Monthly Rent × 12 (±2% tolerance)
- **Calculation:** Monthly Rent × 12
- **Notes:** Used for portfolio valuation

#### Annual Rent/Area
- **Column Name:** Annual Rent/Area
- **Description:** Annual rent divided by area
- **Data Type:** Decimal (2 decimal places)
- **Required:** No (calculated field)
- **Examples:** "22.00", "37.00", "15.00"
- **Can be NULL:** Yes
- **Validation:** Should equal Annual Rent / Area or Monthly Rent/Area × 12
- **Calculation:** Annual Rent ÷ Area

#### Annual Rec./Area (Annual Recoveries per Area)
- **Column Name:** Annual Rec./Area
- **Description:** Annual recoverable expenses per square foot
- **Data Type:** Decimal (2 decimal places)
- **Required:** No
- **Examples:** "4.96", "0.00", "3.02"
- **Can be NULL:** Yes
- **Notes:** 
  - Represents CAM, taxes, insurance pass-throughs
  - May be 0.00 for gross leases
  - Important for NNN lease analysis

#### Annual Misc/Area
- **Column Name:** Annual Misc/Area
- **Description:** Annual miscellaneous charges per square foot
- **Data Type:** Decimal (2 decimal places)
- **Required:** No
- **Examples:** "1.48", "0.00", "2.43"
- **Can be NULL:** Yes
- **Notes:** Other charges like percentage rent, storage fees, etc.

### 2.5 Financial Security

#### Security Deposit Received
- **Column Name:** Security Deposit Received
- **Description:** Security deposit amount held by landlord
- **Data Type:** Decimal (2 decimal places)
- **Required:** No
- **Format:** Numbers with comma separators
- **Examples:** "1,661.42", "6,600.00", "2,500.00", "0.00"
- **Can be NULL:** Yes
- **Validation:** 
  - Typically 1-3 months of base rent
  - May be 0.00 for creditworthy tenants
- **Notes:** Held as protection against tenant default

#### LOC Amount/Bank Guarantee
- **Column Name:** LOC Amount/ Bank Guarantee
- **Description:** Letter of Credit amount or bank guarantee value
- **Data Type:** Decimal (2 decimal places)
- **Required:** No
- **Format:** Numbers with comma separators
- **Examples:** "0.00" (most common), specific amounts for larger tenants
- **Can be NULL:** Yes
- **Notes:** 
  - Alternative to cash security deposit
  - More common with national credit tenants
  - Usually 0.00 when security deposit is held

---

## 3. Special Row Types

### 3.1 Gross Rent Rows
- **Identifier:** Row immediately after tenant row, left-aligned
- **Label:** "Gross Rent" in the property column
- **Purpose:** Shows total rent including escalations and additional charges
- **Columns Populated:**
  - Monthly Rent (gross)
  - Monthly Rent/Area (gross)
  - Annual Rent (gross)
  - Annual Rent/Area (gross)
- **All other columns:** Blank
- **Processing:** 
  - Should be captured as separate row type
  - Link to parent tenant row
  - Used for financial analysis
- **Example:**
  ```
  Property: [blank with "Gross Rent" label]
  Monthly Rent: 2,458.15
  Monthly Rent/Area: 3.49
  Annual Rent: 29,497.80
  Annual Rent/Area: 41.96
  ```

### 3.2 Vacant Unit Rows
- **Identifier:** "VACANT" in Lease column
- **Required Fields:** Property, Unit(s), Area
- **Blank Fields:** All financial and date fields
- **Processing:** 
  - Must be captured to calculate occupancy
  - Include in vacancy report
  - Track available space inventory

---

## 4. Summary Sections

### 4.1 Occupancy Summary
Located at end of each property section:

#### First Summary Block
- **Occupied Area:** Total SF of occupied units
- **Vacant Area:** Total SF of vacant units
- **Total:** Sum (should equal 100%)
- **Percentage:** Calculated for each

#### Summary of Lease Types
- **# of Leases:** Count by lease type
- **Total Area:** SF by lease type
- **Categories:** 
  - Retail NNN
  - Retail Gross
  - [NAP]-Exp Only
  - VACANT

#### Final Occupancy Summary (repeated)
- **Total Occupied Area:** SF and %
- **Total Vacant Area:** SF and %
- **Grand Total:** 100%

### 4.2 Summary Data Validation
- Occupied Area + Vacant Area = Grand Total
- Grand Total should equal sum of all individual unit areas
- Percentage calculations should sum to 100%
- Number of leases should match count of active (non-vacant) rows

---

## 5. Business Rules & Validation

### 5.1 Data Validation Rules

#### Financial Validation
1. **Monthly to Annual Rent:** Annual Rent = Monthly Rent × 12 (±2% tolerance)
2. **Rent per SF:** Monthly Rent/Area = Monthly Rent ÷ Area (±$0.05 tolerance)
3. **Security Deposit Range:** Typically 1-3 months of Monthly Rent
4. **Gross Rent >= Base Rent:** Gross rent row should equal or exceed base tenant row
5. **Non-negative Values:** All rent and financial fields must be >= 0

#### Date Validation
1. **Lease Sequence:** Lease From <= Report Date <= Lease To (for active leases)
2. **Term Calculation:** Term (months) ≈ months between Lease From and Lease To (±2 months)
3. **Tenancy Calculation:** Tenancy Years ≈ years from Lease From to Report Date
4. **Future Leases:** Lease From > Report Date indicates future lease (flag as note)

#### Area Validation
1. **Reasonable Range:** Area between 0 and 100,000 SF for retail
2. **Zero Area:** Acceptable only for ATMs, signage, parking rights
3. **Sum Validation:** Sum of all unit areas = Grand Total in summary

#### Tenant Validation
1. **Unique Identifiers:** Each tenant ID (t0000xxx) should be unique per property
2. **Name Consistency:** Tenant name format should be consistent
3. **Vacant Units:** Must have "VACANT" in Lease field, blank financials

### 5.2 Edge Cases & Special Handling

#### Month-to-Month Leases
- **Indicators:** 
  - Lease To date may be NULL
  - Term months may be NULL
  - Short recent tenancy
- **Processing:** 
  - Flag as "MTM" lease type
  - Set estimated end date as Report Date + 1 month
  - Note in remarks

#### Expired Leases
- **Indicators:** Lease To < Report Date but still listed
- **Processing:**
  - Flag as "Holdover"
  - Note actual status
  - Verify if truly active or should be vacant

#### Long-Term Ground Leases
- **Indicators:** 
  - Very long terms (20+ years)
  - May have Area = 0.00
  - Unit labeled "LAND"
  - Lease type may be "[NAP]-Exp Only"
- **Processing:**
  - Capture as special lease type
  - Note terms

#### Spaces with Zero Rent
- **Scenarios:**
  - Expense-only leases
  - Temporary rent abatement
  - Special arrangements (e.g., Bank ATMs)
- **Processing:**
  - Verify this is intentional
  - Document reason in notes
  - Still include in occupancy calculations

#### Units with Multiple Tenant Names
- **Example:** "Haison Lam and Huong Thi-BichNguyen/ Elite Nails"
- **Processing:**
  - Store complete name as single string
  - May parse into primary/secondary if needed
  - Note co-tenancy in remarks

#### Multi-Unit Leases
- **Example:** "015, 016" or "009-A, 009-B, 009-C"
- **Processing:**
  - Store as single record with combined unit identifier
  - Area should reflect total of all units
  - Note multi-unit lease in remarks

#### Special Unit Types
- **ATM Locations:** Unit like "Z-ATM", Area = 0.00
- **Common Areas:** Unit = "COMMON", may show as vacant or special use
- **Signage:** May have dedicated unit number
- **Processing:** 
  - Capture as-is
  - Flag special unit type
  - May exclude from typical occupancy calculations

---

## 6. Output Requirements

### 6.1 CSV Structure

#### Primary Lease Data File: `{PropertyCode}_RentRoll_{YYYYMMDD}.csv`

**Required Columns (in order):**
1. property_name
2. property_code
3. report_date
4. unit_number
5. tenant_name
6. tenant_id
7. lease_type
8. area_sqft
9. lease_from_date
10. lease_to_date
11. term_months
12. tenancy_years
13. monthly_rent
14. monthly_rent_per_sf
15. annual_rent
16. annual_rent_per_sf
17. annual_recoveries_per_sf
18. annual_misc_per_sf
19. security_deposit
20. loc_bank_guarantee
21. is_vacant
22. is_gross_rent_row
23. parent_row_id (for gross rent rows)
24. notes

**Optional/Calculated Columns:**
25. gross_monthly_rent (from gross rent row)
26. gross_annual_rent (from gross rent row)
27. lease_status (Active/Expired/MTM/Future)
28. months_remaining
29. expiration_year
30. total_annual_revenue (rent + recoveries + misc)

#### Summary Data File: `{PropertyCode}_Summary_{YYYYMMDD}.csv`

**Columns:**
1. property_name
2. property_code
3. report_date
4. total_area_sqft
5. occupied_area_sqft
6. vacant_area_sqft
7. occupancy_percentage
8. vacancy_percentage
9. number_of_leases
10. number_vacant_units
11. total_monthly_rent
12. total_annual_rent
13. average_rent_per_sf_monthly
14. average_rent_per_sf_annual

#### Lease Type Summary File: `{PropertyCode}_LeaseTypes_{YYYYMMDD}.csv`

**Columns:**
1. property_name
2. property_code
3. report_date
4. lease_type
5. number_of_leases
6. total_area_sqft
7. total_annual_rent

### 6.2 Required vs Optional Fields

#### Must Always Be Present (Cannot be NULL):
- property_name
- property_code
- report_date
- unit_number
- area_sqft (can be 0.00)
- is_vacant (boolean)
- is_gross_rent_row (boolean)

#### Required for Active Leases (NULL only if vacant):
- tenant_name
- lease_type
- lease_from_date
- monthly_rent
- annual_rent

#### May Be Missing (Acceptable NULLs):
- lease_to_date (MTM leases)
- term_months (MTM or indefinite)
- monthly_rent_per_sf (if area is 0)
- annual_recoveries_per_sf
- annual_misc_per_sf
- security_deposit
- loc_bank_guarantee
- tenant_id

#### Flag for Review if Missing:
- lease_to_date (for non-MTM leases)
- tenancy_years
- Any calculated field that should derive from other fields

---

## 7. Quality Thresholds

### 7.1 Extraction Accuracy Targets

#### Field-Level Accuracy
- **Critical Fields (Financial, Dates, Area):** 99.5% accuracy required
- **Name Fields (Property, Tenant):** 98% accuracy acceptable
- **Calculated Fields:** 100% accuracy (should be recalculated)
- **Overall:** Minimum 98% field accuracy

#### Record Completeness
- **Active Leases:** 100% of required fields must be present
- **Vacant Units:** 90% completeness acceptable (many fields legitimately NULL)
- **Summary Data:** 100% accuracy required

#### Data Consistency
- **Financial Math:** 99% of calculations must validate
- **Date Logic:** 100% of date sequences must be valid
- **Summary Totals:** 100% must reconcile to detail records

### 7.2 Auto-Approval Criteria

**Automatically Approve if ALL conditions met:**
1. Overall field accuracy >= 99%
2. All critical fields >= 99.5% accuracy
3. All financial validations pass
4. All date validations pass
5. Summary totals reconcile to details
6. No data loss (record count matches)

**Require Human Review if ANY condition:**
1. Overall field accuracy < 98%
2. Any critical field < 99% accuracy
3. >5% of financial validations fail
4. Any summary totals don't reconcile
5. Suspected missing records
6. Unusual patterns or anomalies detected

### 7.3 Completeness Metrics

#### By Section
- **Tenant Data Section:** 95% minimum completeness
- **Vacant Unit Section:** 90% minimum completeness
- **Summary Section:** 100% required
- **Overall Document:** 95% minimum

#### Critical Completeness Checks
1. All units accounted for (no gaps in unit numbers)
2. Occupied + Vacant area = Total area
3. Number of records matches expected count
4. All properties in multi-property report extracted

---

## 8. Data Quality Checks & Flags

### 8.1 Automatic Quality Flags

#### CRITICAL (Must Fix)
- **Missing required field** - Required field is NULL for active lease
- **Math error** - Financial calculation doesn't validate
- **Date logic error** - Invalid date sequence
- **Duplicate unit** - Same unit number appears twice for same property
- **Summary mismatch** - Totals don't reconcile

#### WARNING (Review Recommended)
- **Expired lease active** - Lease To < Report Date but shows as occupied
- **Unusual rent** - Rent per SF outside typical range ($0.50 - $15.00)
- **Missing security deposit** - New lease with no deposit
- **Short term** - Lease term < 12 months
- **Very long term** - Lease term > 20 years (except ground leases)
- **Large vacant space** - Vacant unit > 10,000 SF
- **Zero rent** - Active lease with $0 rent (verify if intentional)

#### INFO (Notation Only)
- **Future lease** - Lease From > Report Date
- **Month-to-month** - Lease To is NULL
- **Multi-unit lease** - Multiple units in Unit field
- **Special unit** - Unit type is ATM, COMMON, LAND, etc.
- **Gross rent calculated** - Gross rent row present

### 8.2 Validation Report Structure

For each extraction, generate validation report with:

#### Header Section
- Property name(s)
- Report date
- Extraction date/time
- Total records extracted
- Overall quality score

#### Validation Results
- Field accuracy by column
- Records with critical flags
- Records with warnings
- Missing/incomplete records

#### Summary Section
- Financial totals validation
- Occupancy validation
- Record count validation
- Pass/Fail status
- Recommendation (Auto-approve / Human review needed)

---

## 9. Sample Data & Test Cases

### 9.1 Perfect Extraction Example

```csv
property_name,property_code,report_date,unit_number,tenant_name,tenant_id,lease_type,area_sqft,lease_from_date,lease_to_date,term_months,tenancy_years,monthly_rent,monthly_rent_per_sf,annual_rent,annual_rent_per_sf,annual_recoveries_per_sf,annual_misc_per_sf,security_deposit,loc_bank_guarantee,is_vacant,is_gross_rent_row,parent_row_id,notes
"Hammond Aire Plaza","hmnd","2025-04-30","001","Haison Lam and Huong Thi-BichNguyen/ Elite Nails","t0000507","Retail NNN",703.00,"2004-04-17","2028-02-29",287,21.08,2167.58,3.08,26010.96,37.00,4.96,1.48,1661.42,0.00,FALSE,FALSE,,
"Hammond Aire Plaza","hmnd","2025-04-30","001",,,,703.00,,,,21.08,2458.15,3.49,29497.80,41.96,,,,,,FALSE,TRUE,1,"Gross Rent"
"Hammond Aire Plaza","hmnd","2025-04-30","002-A","Subway Real Estate, LLC","t0000508","Retail NNN",1312.00,"1988-09-19","2026-09-30",457,36.67,4536.00,3.46,54432.00,41.49,4.96,0.00,1093.33,0.00,FALSE,FALSE,,
```

### 9.2 Vacant Unit Example

```csv
property_name,property_code,report_date,unit_number,tenant_name,tenant_id,lease_type,area_sqft,lease_from_date,lease_to_date,term_months,tenancy_years,monthly_rent,monthly_rent_per_sf,annual_rent,annual_rent_per_sf,annual_recoveries_per_sf,annual_misc_per_sf,security_deposit,loc_bank_guarantee,is_vacant,is_gross_rent_row,parent_row_id,notes
"Hammond Aire Plaza","hmnd","2025-04-30","020","VACANT",,,,,,,,1149.00,,,,,,,,,TRUE,FALSE,,"Vacant unit available for lease"
```

### 9.3 Edge Case Examples

#### Multi-Unit Lease
```csv
"Hammond Aire Plaza","hmnd","2025-04-30","009-A, 009-B, 009-C","Jimmy Jazz Delmont LLC","t0000543","Retail NNN",10135.00,"2020-02-01","2025-09-30",68,5.25,16159.54,1.79,217902.48,21.50,4.96,0.00,0.00,0.00,FALSE,FALSE,,"Multi-unit lease"
```

#### Zero-Area Lease (ATM)
```csv
"Wendover Commons","wend","2025-04-30","Z-ATM","Bank of America, National Association","t0000506","Retail NNN",0.00,"2018-11-01","2028-10-31",120,6.50,1375.00,0.00,16500.00,0.00,0.00,0.00,0.00,0.00,FALSE,FALSE,,"ATM location - no square footage"
```

#### Month-to-Month Lease
```csv
"Eastern Shore Plaza","esp","2025-04-30","108","Sport Clips / AMJaCo","t0000300","Retail NNN",1600.00,"2013-01-01",,,12.33,2581.33,1.61,30975.96,19.36,4.49,0.00,0.00,0.00,FALSE,FALSE,,"Month-to-month lease"
```

---

## 10. Processing Workflow

### 10.1 Extraction Steps

1. **Document Identification**
   - Verify document type (Tenancy Schedule I)
   - Extract property name(s)
   - Extract report date ("As of Date")
   - Identify page count

2. **Table Detection**
   - Locate main data table
   - Identify column headers
   - Map columns to expected fields
   - Note any non-standard columns

3. **Row Classification**
   - Classify each row as:
     - Regular lease row
     - Gross rent row
     - Vacant unit row
     - Summary row
     - Header/footer
   - Link gross rent rows to parent lease rows

4. **Data Extraction**
   - Extract all fields per row
   - Parse dates, numbers, text appropriately
   - Handle multi-line cells
   - Preserve special characters and formatting

5. **Calculation & Derivation**
   - Calculate missing fields if derivable
   - Compute occupancy metrics
   - Aggregate summary statistics
   - Flag derived vs. extracted fields

6. **Validation**
   - Run all validation rules
   - Generate quality flags
   - Calculate accuracy scores
   - Check data completeness

7. **Output Generation**
   - Create CSV files per specification
   - Generate validation report
   - Create human-readable summary
   - Package for delivery

### 10.2 Error Handling

#### Missing Data
- **Action:** Note missing field, use NULL
- **Flag:** WARNING if optional, CRITICAL if required
- **Recovery:** Attempt calculation if derivable

#### Malformed Data
- **Action:** Capture as-is, flag for review
- **Flag:** WARNING
- **Recovery:** Apply data cleansing rules if confident

#### Structural Issues
- **Action:** Document issue, extract what's possible
- **Flag:** CRITICAL
- **Recovery:** May require manual intervention

#### Ambiguous Data
- **Action:** Extract multiple interpretations if needed
- **Flag:** INFO
- **Recovery:** Present options for human decision

---

## 11. Expected Data Ranges & Patterns

### 11.1 Typical Value Ranges

| Field | Minimum | Typical Range | Maximum | Notes |
|-------|---------|---------------|---------|-------|
| Area (SF) | 0 | 1,000 - 25,000 | 100,000+ | Anchors can be larger |
| Monthly Rent | $0 | $2,000 - $25,000 | $75,000+ | Varies by size |
| Rent per SF/Month | $0.50 | $1.50 - $4.00 | $15.00 | Higher in prime locations |
| Annual Rent per SF | $6.00 | $18.00 - $48.00 | $180.00 | = Monthly × 12 |
| Term (months) | 12 | 60 - 120 | 840 | Ground leases can be 50+ years |
| Tenancy Years | 0.08 | 3 - 15 | 40+ | Established tenants |
| Security Deposit | $0 | 1-2 months rent | 3 months rent | Credit tenants may have $0 |
| Occupancy % | 75% | 90% - 98% | 100% | <85% is concern |

### 11.2 Common Patterns

#### Tenant Name Patterns
- National chains: "Company Name, Inc." or "Company Name LLC"
- Franchises: "Franchisee Name / Brand Name"
- Local: "Owner Name / DBA Name"
- Always includes legal entity type (Inc., LLC, Corp., etc.)
- Often includes tenant ID in parentheses

#### Unit Numbering Patterns
- Sequential numbers: 001, 002, 003...
- Building-Section format: 1000, 1001, 1002... (building 1)
- Letter suffixes for subdivisions: 008-A, 008-B, 008-C
- Special codes: 0D0, 0G0, 0F0 (internal codes)
- Multi-unit: "009-A, 009-B, 009-C"

#### Date Patterns
- Lease start dates often on month boundaries (1st or last day)
- Many leases start on same dates (property opening, major renovation)
- End dates often align to calendar year-end (12/31)
- Terms often in 5-year increments (60, 120, 180 months)

---

## 12. Technology Requirements

### 12.1 Extraction Technology

#### Recommended Approach
- **Primary:** Table extraction from native PDF
- **OCR:** Only if scanned document
- **Format:** Structured table recognition
- **Libraries:** PyMuPDF, pdfplumber, Camelot, or Tabula

#### Accuracy Requirements
- **Native PDF Tables:** 99%+ accuracy expected
- **OCR Documents:** 95%+ accuracy acceptable
- **Manual Verification:** Required if < 95%

### 12.2 Output Format Standards

#### CSV Requirements
- **Encoding:** UTF-8
- **Delimiter:** Comma (,)
- **Quote Character:** Double quote (")
- **Escape Character:** Backslash (\)
- **Line Terminator:** CRLF (\r\n)
- **Headers:** First row
- **Empty Values:** Empty string or NULL keyword

#### Date Format
- **Standard:** ISO 8601 (YYYY-MM-DD)
- **Alternative:** MM/DD/YYYY (if required by system)
- **Consistency:** Use same format throughout file

#### Number Format
- **Decimals:** 2 places for currency, SF calculations
- **No Separators:** Remove commas from numbers in CSV
- **Negative Numbers:** Use minus sign (-), not parentheses
- **NULL Values:** Empty field or "NULL" keyword

---

## 13. Delivery Requirements

### 13.1 File Naming Convention

**Format:** `{PropertyCode}_{ReportType}_{YYYYMMDD}_{Version}.csv`

**Examples:**
- `HMND_RentRoll_20250430_v1.csv`
- `HMND_Summary_20250430_v1.csv`
- `TCSH_RentRoll_20250430_v1.csv`
- `ALL_Properties_Combined_20250430_v1.csv`

### 13.2 Package Contents

For each rent roll extraction, deliver:

1. **Data Files** (CSV):
   - Property rent roll detail file(s)
   - Property summary file(s)
   - Lease type summary file(s)
   - Combined/consolidated file (if multi-property)

2. **Validation Report** (PDF or TXT):
   - Extraction summary
   - Quality scores by field
   - Validation results
   - Flagged issues
   - Recommendations

3. **Source Document** (PDF):
   - Original rent roll file
   - Annotated version showing extracted regions (optional)

4. **Metadata File** (JSON):
   - Extraction timestamp
   - Software/version used
   - Confidence scores
   - Processing notes

### 13.3 Quality Certification

Each delivery includes certification:
- Overall extraction accuracy percentage
- Pass/Fail validation status
- Human review required: Yes/No
- Extractor signature (person/system)
- Date/time of extraction

---

## 14. Version Control & Updates

### 14.1 Template Version History

**v2.0 - Current (2025-05-23)**
- Complete rewrite based on actual rent roll analysis
- Added gross rent row handling
- Enhanced validation rules
- Added comprehensive examples
- Detailed edge cases
- Expanded quality metrics

**v1.0 - Previous**
- Initial template (incomplete)
- Basic field definitions only

### 14.2 Change Management

When rent roll format changes:
1. Document format changes
2. Update field definitions
3. Modify validation rules
4. Update test cases
5. Increment version number
6. Notify all stakeholders

---

## APPENDIX A: Quick Reference Checklist

### Pre-Extraction Checklist
- [ ] Document type verified (Tenancy Schedule I)
- [ ] Report date identified
- [ ] Property/properties identified
- [ ] Page count confirmed
- [ ] Table structure assessed

### During Extraction
- [ ] All column headers mapped
- [ ] Regular lease rows extracted
- [ ] Gross rent rows identified and linked
- [ ] Vacant units captured
- [ ] Summary section extracted
- [ ] Special cases flagged

### Post-Extraction Validation
- [ ] Record count matches expected
- [ ] All financial calculations validate
- [ ] All date sequences valid
- [ ] Summary totals reconcile
- [ ] No duplicate units
- [ ] Quality score calculated
- [ ] Validation report generated

### Final Delivery
- [ ] All CSV files created
- [ ] File naming convention followed
- [ ] Validation report included
- [ ] Source document attached
- [ ] Metadata file generated
- [ ] Quality certification completed

---

## APPENDIX B: Common Error Patterns & Solutions

### Error: Annual Rent ≠ Monthly Rent × 12
- **Cause:** Rounding differences, data entry error, or gross vs. base rent confusion
- **Solution:** Flag for review, use Monthly × 12 as canonical value
- **Tolerance:** ±2% acceptable

### Error: Lease To Date < Report Date
- **Cause:** Expired lease still occupying, holdover tenant
- **Solution:** Flag as "Holdover", extract as-is, note in remarks

### Error: Missing Tenant ID
- **Cause:** New tenant not yet in system, data entry incomplete
- **Solution:** Extract without ID, flag for follow-up

### Error: Duplicate Unit Numbers
- **Cause:** Data error, units subdivided, multi-property confusion
- **Solution:** Check if same property, flag as CRITICAL for review

### Error: Occupancy % ≠ 100%
- **Cause:** Math error, missing units, incorrect area calculations
- **Solution:** Verify: (Occupied + Vacant) = Total, flag if not reconciled

---

## APPENDIX C: Glossary

**Retail NNN (Triple Net):** Lease where tenant pays base rent plus proportionate share of property taxes, insurance, and common area maintenance

**Gross Rent:** Total rent including base rent plus any escalations, percentage rent, or additional charges

**CAM (Common Area Maintenance):** Operating expenses for common areas that tenants pay proportionately

**Rentable Square Feet:** Area used for rent calculation, may include proportionate share of common areas

**Anchor Tenant:** Large tenant (usually 20,000+ SF) that draws traffic to a retail center

**Inline Tenant:** Smaller tenant in shopping center between anchor tenants

**Ground Lease:** Long-term lease of land only, tenant owns improvements

**MTM (Month-to-Month):** Lease with no fixed end date, either party can terminate with notice

**Holdover:** Tenant remaining in space after lease expiration

**Dark Store:** Tenant paying rent but not operating (closed but still obligated)

**Lease Commencement:** Date when rent obligations begin (may differ from occupancy date)

**Lease Expiration:** Date when lease term ends

**LOC (Letter of Credit):** Bank guarantee usable as security in lieu of cash deposit

**Percentage Rent:** Additional rent based on tenant's sales exceeding threshold

**Base Year:** Year used as baseline for expense calculations in some lease structures

