# REIMS2 Data Validation Rules - Comprehensive Reference
## Real Estate Income & Management System - Project REIMS2

---

## Table of Contents
1. [Income Statement Validation Rules](#income-statement-validation-rules)
2. [Cross-Document Validation Rules](#cross-document-validation-rules)
3. [Data Quality Standards](#data-quality-standards)
4. [Automated vs Manual Review Criteria](#automated-vs-manual-review-criteria)

---

## Income Statement Validation Rules

### 1. Mathematical Calculation Validations (Critical)

#### Rule 1.1: Total Income Calculation
**Rule ID:** IS-CALC-001  
**Priority:** CRITICAL  
**Formula:** Sum(All Income Line Items 4010-4091) = Total Income (4990-0000)  
**Tolerance:** ±$0.05  
**Example:**
```
Base Rentals (4010):        $229,422.31
Tax (4020):                 $  5,770.07
Insurance (4030):           $  4,811.99
CAM (4040):                 $ 24,202.38
Annual Cams (4060):         $ -8,089.61
Other Income (4090):        $      0.00
Interest Income (4091):     $    576.51
-----------------------------------
Calculated Total:           $256,693.65
Reported Total (4990):      $257,255.40
Difference:                 $   561.75
Status:                     ❌ FAILED (>$0.05)
Action:                     Review and correct
```

#### Rule 1.2: Total Operating Expenses Calculation
**Rule ID:** IS-CALC-002  
**Priority:** CRITICAL  
**Formula:** Sum(Property Tax + Insurance + Utilities + Contracted + R&M + Admin) = Total Operating Expenses (5990-0000)  
**Tolerance:** ±$0.05  

**Components:**
- Property Tax (5010-0000)
- Property Insurance (5012-0000)
- Total Utility Expense (5199-0000)
- Total Contracted Expenses (5299-0000)
- Total R&M Operating Expenses (5399-0000)
- Total Administration Expense (5499-0000)

**Validation:**
```python
def validate_operating_expenses(data):
    components = [
        data['5010-0000'],  # Property Tax
        data['5012-0000'],  # Insurance
        data['5199-0000'],  # Utilities
        data['5299-0000'],  # Contracted
        data['5399-0000'],  # R&M
        data['5499-0000']   # Admin
    ]
    calculated = sum(components)
    reported = data['5990-0000']
    difference = abs(calculated - reported)
    
    if difference <= 0.05:
        return "PASSED"
    elif difference <= 1.00:
        return "WARNING"
    else:
        return "FAILED"
```

#### Rule 1.3: Total Additional Operating Expenses Calculation
**Rule ID:** IS-CALC-003  
**Priority:** CRITICAL  
**Formula:** Sum(Off-Site Management + Franchise Tax + Leasing + Fees + LL Expenses) = Total Additional Operating Expenses (6190-0000)  
**Tolerance:** ±$0.05  

#### Rule 1.4: Total Expenses Calculation
**Rule ID:** IS-CALC-004  
**Priority:** CRITICAL  
**Formula:** Total Operating Expenses (5990) + Total Additional Operating Expenses (6190) = Total Expenses (6199)  
**Tolerance:** ±$0.10  

**Example:**
```
Total Operating Expenses (5990):      $154,071.40
Total Additional Expenses (6190):     $ 30,077.88
-------------------------------------------
Calculated Total Expenses:            $184,149.28
Reported Total Expenses (6199):       $184,149.28
Difference:                           $0.00
Status:                               ✅ PASSED
```

#### Rule 1.5: Net Operating Income (NOI) Calculation
**Rule ID:** IS-CALC-005  
**Priority:** CRITICAL  
**Formula:** Total Income (4990) - Total Expenses (6199) = Net Operating Income (6299)  
**Tolerance:** ±$0.10  

**Example:**
```
Total Income (4990):          $3,426,774.19
Total Expenses (6199):        $1,338,869.05
--------------------------------------
Calculated NOI:               $2,087,905.14
Reported NOI (6299):          $2,087,905.14
Difference:                   $0.00
NOI Margin:                   60.93%
Status:                       ✅ PASSED
```

#### Rule 1.6: Net Income Calculation
**Rule ID:** IS-CALC-006  
**Priority:** CRITICAL  
**Formula:** NOI (6299) - Total Other Income/Expense (7090) = Net Income (9090)  
**Tolerance:** ±$0.10  

**Components of Other Income/Expense:**
- Mortgage Interest (7010-0000)
- Depreciation (7020-0000)
- Amortization (7030-0000)

**Example:**
```
Net Operating Income (6299):      $2,087,905.14
Mortgage Interest (7010):         $1,060,287.25
Depreciation (7020):              $  791,282.97
Amortization (7030):              $   26,875.20
----------------------------------------
Total Other Expense (7090):       $1,878,445.42
Calculated Net Income:            $  209,459.72
Reported Net Income (9090):       $  209,459.72
Difference:                       $0.00
Status:                           ✅ PASSED
```

### 2. Percentage Column Validations (High Priority)

#### Rule 2.1: Income Percentages Sum
**Rule ID:** IS-PCT-001  
**Priority:** HIGH  
**Rule:** Sum of all Period to Date percentages in income section = 100%  
**Tolerance:** ±0.5%  

**Example:**
```
Base Rentals:         79.55%
Tax:                   1.97%
Insurance:             2.77%
CAM:                  10.01%
Percentage Rent:      -1.16%
Annual Cams:           7.01%
Other Income:          0.00%
Interest:              0.00%
--------------------------
Total:                100.15%
Status:               ⚠️ WARNING (>100%)
```

#### Rule 2.2: Individual Percentage Validation
**Rule ID:** IS-PCT-002  
**Priority:** MEDIUM  
**Rule:** Each line item percentage = (Line Item Amount / Total) × 100  
**Tolerance:** ±0.01%  

**Example Validation:**
```python
def validate_percentage(line_amount, total_amount, reported_pct):
    calculated_pct = (line_amount / total_amount) * 100
    difference = abs(calculated_pct - reported_pct)
    
    if difference <= 0.01:
        return "PASSED"
    elif difference <= 0.05:
        return "WARNING"
    else:
        return "FAILED"
```

### 3. Period vs Year-to-Date Consistency (High Priority)

#### Rule 3.1: Monthly Statement YTD Check
**Rule ID:** IS-YTD-001  
**Priority:** HIGH  
**Rule:** For monthly statements, Year to Date Amount >= Period to Date Amount  
**Exception:** First month of year where they may be equal  

**Example:**
```
Period to Date (December):    $229,422.31
Year to Date:                 $2,768,568.46
Ratio:                        12.06x
Status:                       ✅ PASSED (YTD > PTD)
```

#### Rule 3.2: Annual Statement Consistency
**Rule ID:** IS-YTD-002  
**Priority:** CRITICAL  
**Rule:** For annual statements, Year to Date Amount = Period to Date Amount  
**Tolerance:** ±$0.01  

**Example:**
```
Period to Date (Annual):      $2,726,029.62
Year to Date:                 $2,726,029.62
Difference:                   $0.00
Status:                       ✅ PASSED
```

### 4. Account Code Format Validations (Critical)

#### Rule 4.1: Account Code Pattern
**Rule ID:** IS-ACC-001  
**Priority:** CRITICAL  
**Pattern:** `####-####` (4 digits, hyphen, 4 digits)  
**Examples:**
- ✅ Valid: `4010-0000`, `5105-0000`, `6299-0000`
- ❌ Invalid: `4010`, `4010-0`, `4010-00000`, `401-0000`

**Validation:**
```python
import re

def validate_account_code(code):
    pattern = r'^\d{4}-\d{4}$'
    if re.match(pattern, code):
        return "PASSED"
    else:
        return "FAILED"
```

#### Rule 4.2: Account Code Range Validation
**Rule ID:** IS-ACC-002  
**Priority:** HIGH  
**Rule:** Account codes must fall within defined ranges:
- **4000-4999:** Income accounts
- **5000-5999:** Operating expenses
- **6000-6199:** Additional operating expenses
- **7000-7099:** Other income/expenses (below the line)
- **9000-9099:** Summary accounts

### 5. Value Range and Reasonableness Checks (Medium Priority)

#### Rule 5.1: Negative Value Validation
**Rule ID:** IS-VAL-001  
**Priority:** MEDIUM  
**Rule:** Negative values are expected only in specific accounts  

**Expected Negative Accounts:**
- Free Rent (typically negative adjustment)
- Co-Tenancy Rent Reduction
- Bad Debt Expense
- Annual Cams (when credits issued)
- Percentage Rent (if reversed)

**Unexpected Negative Accounts (Flag for Review):**
- Base Rentals (4010-0000)
- Property Tax (5010-0000)
- Property Insurance (5012-0000)
- Most operating expenses

**Example:**
```
Account: 4010-0000 (Base Rentals)
Amount: -$5,000.00
Status: ❌ FLAG - Unexpected negative in Base Rentals
Action: Manual review required
```

#### Rule 5.2: Zero Value Validation
**Rule ID:** IS-VAL-002  
**Priority:** LOW  
**Rule:** Zero values are acceptable but notable in certain accounts  

**Critical if Zero:**
- Base Rentals (4010-0000) → ❌ Critical Error
- Total Income (4990-0000) → ❌ Critical Error
- Total Expenses (6199-0000) → ⚠️ Warning

**Commonly Zero (OK):**
- Percentage Rent (most months)
- Termination Fee Income
- Many R&M line items
- Various contracted services

#### Rule 5.3: NOI Margin Reasonableness
**Rule ID:** IS-VAL-003  
**Priority:** MEDIUM  
**Rule:** NOI Margin = (NOI / Total Income) × 100  
**Expected Range:** 30% - 80% for most commercial properties  

**Interpretation:**
- < 30%: ⚠️ Low margin - high operating costs
- 30-50%: ✅ Typical range
- 50-70%: ✅ Good performance
- 70-80%: ✅ Excellent performance
- > 80%: ⚠️ Unusually high - verify accuracy

**Example:**
```
Total Income:         $3,426,774.19
NOI:                  $2,087,905.14
NOI Margin:           60.93%
Status:               ✅ Within expected range
```

#### Rule 5.4: Operating Expense Ratio
**Rule ID:** IS-VAL-004  
**Priority:** MEDIUM  
**Rule:** Operating Expense Ratio = (Total Operating Expenses / Total Income) × 100  
**Expected Range:** 25% - 45% for most properties  

**Example:**
```
Total Income:                 $3,426,774.19
Total Operating Expenses:     $1,121,922.50
Operating Expense Ratio:      32.74%
Status:                       ✅ Within expected range
```

### 6. Subtotal Validations (High Priority)

#### Rule 6.1: Utility Expense Subtotal
**Rule ID:** IS-SUB-001  
**Priority:** HIGH  
**Formula:** Sum(Electricity + Gas + Water + Trash + Other) = Total Utility Expense (5199-0000)  
**Tolerance:** ±$0.01  

#### Rule 6.2: Contracted Expense Subtotal
**Rule ID:** IS-SUB-002  
**Priority:** HIGH  
**Formula:** Sum(All Contracted Service Items 5210-5290) = Total Contracted Expenses (5299-0000)  
**Tolerance:** ±$0.01  

#### Rule 6.3: R&M Expense Subtotal
**Rule ID:** IS-SUB-003  
**Priority:** HIGH  
**Formula:** Sum(All R&M Items 5300-5398) = Total R&M Operating Expenses (5399-0000)  
**Tolerance:** ±$0.01  

#### Rule 6.4: Administration Expense Subtotal
**Rule ID:** IS-SUB-004  
**Priority:** HIGH  
**Formula:** Sum(All Admin Items 5400-5498) = Total Administration Expense (5499-0000)  
**Tolerance:** ±$0.01  

#### Rule 6.5: Landlord Expense Subtotal
**Rule ID:** IS-SUB-005  
**Priority:** HIGH  
**Formula:** Sum(All LL Expense Items 6050-6068) = Total LL Expense (6069-0000)  
**Tolerance:** ±$0.01  

### 7. Data Type and Format Validations (Critical)

#### Rule 7.1: Numeric Field Validation
**Rule ID:** IS-TYP-001  
**Priority:** CRITICAL  
**Requirements:**
- All amount fields must be valid decimal numbers
- Precision: 2 decimal places required
- Format: No currency symbols, no commas in stored value
- Range: -999,999,999.99 to 999,999,999.99

**Examples:**
```
✅ Valid:   229422.31, -8089.61, 0.00
❌ Invalid: $229,422.31, 229422, "N/A", null (when amount expected)
```

#### Rule 7.2: Date Format Validation
**Rule ID:** IS-TYP-002  
**Priority:** CRITICAL  
**Accepted Formats:**
- MM/DD/YYYY (e.g., 12/31/2023)
- MMM YYYY (e.g., Dec 2023)
- Full: Month DD, YYYY (e.g., December 31, 2023)

**Validation:**
```python
from datetime import datetime

def validate_date(date_str):
    formats = ['%m/%d/%Y', '%b %Y', '%B %d, %Y']
    for fmt in formats:
        try:
            datetime.strptime(date_str, fmt)
            return "PASSED"
        except ValueError:
            continue
    return "FAILED"
```

#### Rule 7.3: Property Code Validation
**Rule ID:** IS-TYP-003  
**Priority:** HIGH  
**Requirements:**
- Length: 2-4 characters
- Format: Lowercase letters
- Must match known property codes

**Valid Codes:**
```
esp   → Eastern Shore Plaza
hmnd  → Hammond Aire Plaza
tcsh  → The Crossings of Spring Hill
wend  → Wendover Commons
```

### 8. Cross-Period Validations (Medium Priority)

#### Rule 8.1: Period-over-Period Variance
**Rule ID:** IS-CMP-001  
**Priority:** MEDIUM  
**Rule:** Flag if key metrics vary by >30% month-over-month  

**Key Metrics to Compare:**
- Base Rentals
- Total Income
- NOI
- Net Income

**Example:**
```
Base Rentals (Previous Month):   $225,000.00
Base Rentals (Current Month):    $295,000.00
Change:                          +31.1%
Status:                          ⚠️ WARNING - Large increase
Action:                          Review for accuracy
```

#### Rule 8.2: Year-over-Year Variance
**Rule ID:** IS-CMP-002  
**Priority:** MEDIUM  
**Rule:** Flag if key metrics vary by >50% year-over-year  

### 9. Required Fields Validation (Critical)

#### Rule 9.1: Mandatory Header Fields
**Rule ID:** IS-REQ-001  
**Priority:** CRITICAL  
**Required Fields:**
- Property Code
- Property Name
- Period Start Date
- Period End Date
- Accounting Basis

**Validation:**
```python
def validate_required_headers(data):
    required = [
        'property_code',
        'property_name',
        'period_start_date',
        'period_end_date',
        'accounting_basis'
    ]
    
    missing = [field for field in required if not data.get(field)]
    
    if missing:
        return f"FAILED - Missing: {', '.join(missing)}"
    return "PASSED"
```

#### Rule 9.2: Mandatory Account Codes
**Rule ID:** IS-REQ-002  
**Priority:** CRITICAL  
**Required Accounts (Must be present):**
- 4010-0000: Base Rentals
- 4990-0000: Total Income
- 5010-0000: Property Tax
- 5990-0000: Total Operating Expenses
- 6199-0000: Total Expenses
- 6299-0000: Net Operating Income
- 9090-0000: Net Income

---

## Cross-Document Validation Rules

### 10. Rent Roll to Income Statement Reconciliation

#### Rule 10.1: Base Rental Reconciliation
**Rule ID:** RR-IS-001  
**Priority:** HIGH  
**Rule:** Sum of Rent Roll annual rents should approximate Income Statement Base Rentals  
**Tolerance:** ±5%  

**Formula:**
```
Rent Roll Check:
Sum(All Unit Monthly Rents) × 12 = Expected Annual Rent

Income Statement Check:
Account 4010-0000 (Base Rentals) = Reported Annual Rent

Comparison:
|Expected - Reported| / Expected ≤ 5%
```

**Example:**
```
Rent Roll:
  Total Monthly Rent:         $225,000.00
  Annualized:                 $2,700,000.00

Income Statement:
  Base Rentals (Annual):      $2,726,029.62

Variance:                     +0.96%
Status:                       ✅ PASSED (within 5%)
```

#### Rule 10.2: Occupancy Correlation
**Rule ID:** RR-IS-002  
**Priority:** MEDIUM  
**Rule:** Rent Roll occupancy should correlate with Income Statement rental income  

**Formula:**
```
Economic Occupancy = (Actual Rent Collected / Potential Rent at 100%) × 100

Comparison:
If Rent Roll shows 85% physical occupancy,
Income Statement Base Rentals should reflect similar economic occupancy
```

#### Rule 10.3: Lease Change Impact
**Rule ID:** RR-IS-003  
**Priority:** LOW  
**Rule:** New leases in Rent Roll should appear in subsequent Income Statements  

**Validation:**
- Track lease commencement dates from Rent Roll
- Verify rent increase appears in Income Statement for that month/period
- Flag discrepancies for review

---

## Data Quality Standards

### 11. Confidence Scoring System

#### Rule 11.1: Field-Level Confidence Scoring
**Rule ID:** QA-CONF-001  
**Priority:** HIGH  

**Confidence Tiers:**
- **95-100%:** High confidence - Auto-approve
- **90-94%:** Medium confidence - Spot check
- **85-89%:** Low confidence - Review required
- **<85%:** Very low confidence - Manual extraction required

**Factors Affecting Confidence:**
- OCR quality score
- Field format match
- Calculation validation pass/fail
- Historical data comparison

#### Rule 11.2: Document-Level Quality Score
**Rule ID:** QA-CONF-002  
**Priority:** HIGH  

**Formula:**
```
Document Score = (
    Field Extraction Score × 0.40 +
    Calculation Validation Score × 0.40 +
    Data Consistency Score × 0.20
) × 100
```

**Thresholds:**
- **≥99%:** Auto-approve and process
- **95-98%:** Auto-approve with audit sample
- **90-94%:** Supervisor review required
- **<90%:** Full manual review required

### 12. Extraction Completeness Standards

#### Rule 12.1: Minimum Line Item Count
**Rule ID:** QA-COMP-001  
**Priority:** MEDIUM  

**Expected Ranges by Property Type:**
- Small Property: 40-60 line items
- Medium Property: 60-80 line items
- Large Property: 80-120 line items

**Validation:**
```python
def validate_line_item_count(extracted_items, property_type):
    ranges = {
        'small': (40, 60),
        'medium': (60, 80),
        'large': (80, 120)
    }
    
    min_items, max_items = ranges.get(property_type, (40, 120))
    count = len(extracted_items)
    
    if min_items <= count <= max_items:
        return "PASSED"
    elif count < min_items * 0.8:
        return "FAILED - Too few items"
    else:
        return "WARNING - Outside typical range"
```

#### Rule 12.2: Critical Sections Completeness
**Rule ID:** QA-COMP-002  
**Priority:** CRITICAL  

**Required Sections:**
- ✅ Income section (4000-4999)
- ✅ Operating Expenses section (5000-5999)
- ✅ Additional Operating Expenses section (6000-6199)
- ✅ Other Income/Expenses section (7000-7099)
- ✅ Net Income summary (9090-0000)

**Validation:**
```
If any required section is completely missing → CRITICAL FAILURE
If section has <50% of expected accounts → WARNING
If section has 50-90% of expected accounts → REVIEW REQUIRED
If section has >90% of expected accounts → PASSED
```

---

## Automated vs Manual Review Criteria

### 13. Automatic Approval Criteria

#### Rule 13.1: Auto-Approve Conditions
**Rule ID:** AUTO-001  
**Priority:** HIGH  

**ALL of the following must be true:**
1. Overall confidence score ≥99%
2. All critical calculations pass (±tolerance)
3. No unexpected negative values in key accounts
4. All required fields present
5. All subtotals match component sums
6. Account codes properly formatted
7. No period-over-period variance >30% (or variance explained)

**If all conditions met:**
- Status: AUTO-APPROVED
- Action: Process immediately
- Audit: Random sample (5%)

### 14. Manual Review Triggers

#### Rule 14.1: Mandatory Manual Review
**Rule ID:** REVIEW-001  
**Priority:** CRITICAL  

**Manual review REQUIRED if ANY of:**
1. Overall confidence score <90%
2. Any critical calculation fails validation
3. Total Income = $0 or missing
4. NOI calculation mismatch >$1.00
5. Base Rentals negative or zero
6. More than 3 unexpected negative values
7. Missing any required account code
8. Account code format errors

#### Rule 14.2: Supervisor Escalation
**Rule ID:** REVIEW-002  
**Priority:** HIGH  

**Escalate to supervisor if:**
1. Manual review cannot resolve discrepancy
2. Period-over-period variance >50%
3. Year-over-year variance >100%
4. NOI margin <20% or >90%
5. Multiple validation failures (>5)
6. Pattern of errors across multiple properties
7. Suspected data corruption

### 15. Exception Handling

#### Rule 15.1: Known Exception Types
**Rule ID:** EXC-001  
**Priority:** MEDIUM  

**Approved Exceptions:**

**Exception Type 1: Property Under Renovation**
- May have: Zero or very low income
- May have: High LL expenses
- May have: Negative Net Income
- Approval: Document renovation period

**Exception Type 2: Property Sale/Purchase**
- May have: Unusual one-time fees
- May have: Prorated period amounts
- May have: Adjusted accounting entries
- Approval: Document transaction details

**Exception Type 3: Lease-Up Period**
- May have: Below-market income
- May have: High leasing commissions
- May have: High tenant improvement costs
- Approval: Track lease-up progress

**Exception Type 4: Annual Reconciliation**
- May have: Large Annual CAM adjustments (positive or negative)
- May have: Tax assessment changes
- May have: Insurance reimbursement adjustments
- Approval: Verify reconciliation documentation

---

## Validation Rule Priority Summary

### Critical Rules (Must Pass)
- All mathematical calculations (IS-CALC-001 through IS-CALC-006)
- Account code format (IS-ACC-001)
- Required fields present (IS-REQ-001, IS-REQ-002)
- Data type validations (IS-TYP-001, IS-TYP-002)
- All subtotals match (IS-SUB-001 through IS-SUB-005)

### High Priority Rules (Should Pass)
- Percentage column validations (IS-PCT-001, IS-PCT-002)
- Period vs YTD consistency (IS-YTD-001, IS-YTD-002)
- Account code range validation (IS-ACC-002)
- Subtotal consistency checks
- Cross-document reconciliation (RR-IS-001)

### Medium Priority Rules (Flag if Failed)
- Value range and reasonableness (IS-VAL-001 through IS-VAL-004)
- Period-over-period variance (IS-CMP-001)
- Line item count validation (QA-COMP-001)

### Low Priority Rules (Informational)
- Zero value notifications (IS-VAL-002)
- Year-over-year variance (IS-CMP-002)
- Lease change impact tracking (RR-IS-003)

---

## Implementation Checklist

### Pre-Processing Phase
- [ ] Verify PDF file integrity
- [ ] Extract text with position coordinates
- [ ] Identify property from header
- [ ] Determine period type (monthly/annual)
- [ ] Count pages and verify completeness

### Extraction Phase
- [ ] Extract property header information
- [ ] Extract all income line items (4000 series)
- [ ] Extract all operating expenses (5000 series)
- [ ] Extract additional expenses (6000 series)
- [ ] Extract other income/expenses (7000 series)
- [ ] Extract summary accounts (9000 series)

### Validation Phase
- [ ] Run all mathematical calculations (Critical)
- [ ] Verify all account code formats (Critical)
- [ ] Check all required fields present (Critical)
- [ ] Validate percentage columns (High)
- [ ] Check period vs YTD consistency (High)
- [ ] Verify subtotals match components (High)
- [ ] Check value ranges and reasonableness (Medium)
- [ ] Compare to previous periods (Medium)

### Quality Assurance Phase
- [ ] Calculate field-level confidence scores
- [ ] Calculate document-level quality score
- [ ] Determine approval routing (Auto/Manual/Escalation)
- [ ] Generate validation report
- [ ] Flag exceptions for review
- [ ] Document any approved exceptions

### Post-Processing Phase
- [ ] Insert data into database
- [ ] Generate CSV exports
- [ ] Create audit trail entries
- [ ] Update dashboard metrics
- [ ] Send notifications (if needed)
- [ ] Archive source documents

---

## Validation Report Template

### Sample Validation Report
```
====================================
INCOME STATEMENT VALIDATION REPORT
====================================

Property: Eastern Shore Plaza (esp)
Period: December 2023
Document: ESP_2023_Income_Statement.pdf
Extracted: 2025-02-10 14:32:18
Validated: 2025-02-10 14:35:45

OVERALL STATUS: ✅ PASSED
Quality Score: 98.5%
Confidence: 99.2%

------------------------------------
CRITICAL VALIDATIONS (All must pass)
------------------------------------
✅ Total Income Calculation     (IS-CALC-001)
✅ Total Expenses Calculation   (IS-CALC-004)
✅ NOI Calculation              (IS-CALC-005)
✅ Net Income Calculation       (IS-CALC-006)
✅ Account Code Formats         (IS-ACC-001)
✅ Required Fields Present      (IS-REQ-001)
✅ Required Accounts Present    (IS-REQ-002)

------------------------------------
HIGH PRIORITY VALIDATIONS
------------------------------------
⚠️  Income Percentages Sum       (IS-PCT-001) - 100.15% (Expected 100%)
✅ Period vs YTD Consistency    (IS-YTD-001)
✅ Utility Subtotal             (IS-SUB-001)
✅ Contracted Subtotal          (IS-SUB-002)
✅ R&M Subtotal                 (IS-SUB-003)
✅ Admin Subtotal               (IS-SUB-004)

------------------------------------
MEDIUM PRIORITY CHECKS
------------------------------------
✅ NOI Margin                   (IS-VAL-003) - 60.93% (Good)
✅ Operating Expense Ratio      (IS-VAL-004) - 32.74% (Normal)
✅ No unexpected negatives      (IS-VAL-001)
⚠️  Period variance              (IS-CMP-001) - Base Rentals +8.2%

------------------------------------
SUMMARY METRICS
------------------------------------
Total Income:             $3,426,774.19
Total Expenses:           $1,338,869.05
Net Operating Income:     $2,087,905.14
NOI Margin:               60.93%
Net Income:               $  209,459.72

Line Items Extracted:     87
Line Items Validated:     87
Validation Pass Rate:     98.9%

------------------------------------
WARNINGS (1)
------------------------------------
W001: Income percentages sum to 100.15% (expected 100.00%)
      Impact: Minor - within tolerance
      Action: Accepted

------------------------------------
RECOMMENDATION
------------------------------------
Status:  AUTO-APPROVED
Action:  Process immediately
Audit:   Include in random 5% sample

Validated by: Automated System
Review:       Not required (Score >99%)
Approved:     2025-02-10 14:35:45

====================================
```

---

*Document Version: 1.0*  
*Last Updated: February 2025*  
*Project: REIMS2*  
*Classification: Internal Use*
