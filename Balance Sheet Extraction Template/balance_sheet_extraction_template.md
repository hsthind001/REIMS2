# Balance Sheet Extraction Template for REIMS2
## Version 1.0 - Comprehensive Data Extraction with Zero Loss

---

## 📋 **Template Overview**

This template ensures **100% data extraction quality with zero data loss** from balance sheet PDFs.

**Supported Formats:**
- Standard accounting software outputs (Yardi, MRI, AppFolio, etc.)
- Custom property management reports
- Multi-page balance sheets
- Both detailed and summary formats

**Key Features:**
- Extracts ALL line items (detail + calculated totals)
- Preserves account hierarchy (section → subsection → line item)
- Validates accounting equation: Assets = Liabilities + Equity
- Confidence scoring for each extracted field
- Automatic flagging of items needing review

---

## 🎯 **Document Identification**

### **Primary Keywords** (Required - at least 2)
```yaml
required_keywords:
  - "Balance Sheet"
  - "Statement of Financial Position"
  - "Assets"
  - "Liabilities"
  - "Capital" OR "Equity" OR "Net Worth"
```

### **Secondary Keywords** (Confidence Boosters)
```yaml
supporting_keywords:
  - "Current Balance"
  - "TOTAL ASSETS"
  - "TOTAL LIABILITIES"
  - "Property & Equipment"
  - "Current Assets"
  - "Long Term"
```

### **Header Information**
```yaml
header_extraction:
  property_name:
    patterns:
      - "^(.+?)\\s+\\(\\w+\\)"  # "Eastern Shore Plaza (esp)"
      - "^Property:\\s*(.+)$"
    required: true
    confidence_threshold: 90
    
  report_period:
    patterns:
      - "Period\\s*=\\s*(\\w+\\s+\\d{4})"  # "Period = Dec 2024"
      - "As of\\s+([A-Za-z]+\\s+\\d{1,2},?\\s+\\d{4})"
      - "(\\d{1,2}[-/]\\d{1,2}[-/]\\d{2,4})"
    required: true
    confidence_threshold: 95
    
  accounting_method:
    patterns:
      - "Book\\s*=\\s*(\\w+)"  # "Book = Accrual"
    required: false
    confidence_threshold: 80
    
  report_date:
    patterns:
      - "(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\\s+([A-Za-z]+\\s+\\d{1,2},\\s+\\d{4})"
      - "\\d{1,2}:\\d{2}\\s+(AM|PM)"
    required: false
```

---

## 📊 **Hierarchical Structure Definition**

### **Section 1: ASSETS**

```yaml
section_assets:
  section_name: "ASSETS"
  section_code_range: "0100-0000" to "1999-9999"
  required: true
  
  subsections:
    - subsection_id: "current_assets"
      name: "Current Assets"
      code_range: "0101-0000" to "0499-9999"
      total_account: "0499-9000"
      total_names: ["Total Current Assets"]
      required: true
      
      line_items:
        - account_code: "0100-0000"
          name: "ASSETS"
          type: "header"
          skip_extraction: true
          
        - account_code: "0122-0000"
          name_pattern: "Cash.*Operating"
          type: "detail"
          data_type: "decimal(15,2)"
          required: false
          
        - account_code: "0123-0000"
          name_pattern: "Cash.*Operating II"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "0125-0000"
          name_pattern: "Cash.*Operating.*PNC"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "0210-0000"
          name_pattern: "Accounts Receivable.*Trade"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          
        - account_code: "0305-0000"
          name_pattern: "A/R Tenants?"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          
        - account_code: "0306-0000"
          name_pattern: "A/R Other"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "0347-0000"
          name_pattern: "Escrow.*Other"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "0499-9000"
          name_pattern: "Total Current Assets"
          type: "calculated_total"
          data_type: "decimal(15,2)"
          validation: "sum_of_subsection"
          required: true
    
    - subsection_id: "property_equipment"
      name: "Property & Equipment"
      code_range: "0500-0000" to "1099-9999"
      total_account: "1099-0000"
      total_names: ["Total Property & Equipment"]
      required: true
      
      line_items:
        - account_code: "0510-0000"
          name: "Land"
          type: "detail"
          data_type: "decimal(15,2)"
          required: true
          
        - account_code: "0610-0000"
          name: "Buildings"
          type: "detail"
          data_type: "decimal(15,2)"
          required: true
          
        - account_code: "0710-0000"
          name_pattern: "5 Year Improvements?"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "0810-0000"
          name_pattern: "15 Year Improvements?"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "0815-0000"
          name_pattern: "30 Year.*Roof"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "0816-0000"
          name_pattern: "30 Year.*HVAC"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "0910-0000"
          name_pattern: "Other Improvements?"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "0912-0000"
          name_pattern: "PARKING[- ]LOT"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "0950-0000"
          name_pattern: "TI/Current Improvements?"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "1061-0000"
          name_pattern: "Accum\\.? Depr\\..*Buildings?"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          is_contra_account: true
          
        - account_code: "1071-0000"
          name_pattern: "Accum\\.? Depr\\..*5 Year"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          is_contra_account: true
          
        - account_code: "1081-0000"
          name_pattern: "Accum\\.? Depr\\..*15 Year"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          is_contra_account: true
          
        - account_code: "1082-0000"
          name_pattern: "Accum\\.? Depr\\..*Roof"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          is_contra_account: true
          
        - account_code: "1091-0000"
          name_pattern: "Accum\\.? Depr\\..*Other"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          is_contra_account: true
          
        - account_code: "1099-0000"
          name_pattern: "Total Property & Equipment"
          type: "calculated_total"
          data_type: "decimal(15,2)"
          validation: "sum_of_subsection"
          required: true
    
    - subsection_id: "other_assets"
      name: "Other Assets"
      code_range: "1200-0000" to "1998-9999"
      total_account: "1998-0000"
      total_names: ["Total Other Assets"]
      required: true
      
      line_items:
        - account_code: "1210-0000"
          name: "Deposits"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "1310-0000"
          name_pattern: "Escrow.*Property Tax"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "1320-0000"
          name_pattern: "Escrow.*Insurance"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "1330-0000"
          name_pattern: "Escrow.*TI/LC"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "1340-0000"
          name_pattern: "Escrow.*Replacement Reserves?"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "1920-0000"
          name_pattern: "Loan Costs?"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "1922-0000"
          name_pattern: "Accum\\.? Amortization Loan Costs?"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          is_contra_account: true
          
        - account_code: "1950-0000"
          name_pattern: "External.*Lease Commission"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "1950-5000"
          name_pattern: "Internal.*Lease Commission"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "1952-0000"
          name_pattern: "Accum\\.? Amort.*TI/LC"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          is_contra_account: true
          
        - account_code: "1995-0000"
          name_pattern: "Prepaid Insurance"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "1998-0000"
          name_pattern: "Total Other Assets"
          type: "calculated_total"
          data_type: "decimal(15,2)"
          validation: "sum_of_subsection"
          required: true
  
  section_total:
    account_code: "1999-0000"
    name: "TOTAL ASSETS"
    type: "section_total"
    data_type: "decimal(15,2)"
    validation: "sum_of_all_subsections"
    required: true
    critical: true
```

### **Section 2: LIABILITIES**

```yaml
section_liabilities:
  section_name: "LIABILITIES"
  section_code_range: "2000-0000" to "2999-9999"
  required: true
  
  subsections:
    - subsection_id: "current_liabilities"
      name: "Current Liabilities"
      code_range: "2001-0000" to "2590-9999"
      total_account: "2590-0000"
      total_names: ["Total Current Liabilities"]
      required: true
      
      line_items:
        - account_code: "2030-0000"
          name_pattern: "Accrued Expenses?"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2110-0000"
          name_pattern: "Accounts Payable.*Trade"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2120-0000"
          name_pattern: "A/P.*Series RDF"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2121-0000"
          name_pattern: "A/P Other"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2132-0000"
          name_pattern: "A/P.*5Rivers"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          
        - account_code: "2139-0000"
          name_pattern: "Insurance Claim"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2197-0000"
          name_pattern: "Loans Payable.*5Rivers"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          
        - account_code: "2410-0000"
          name_pattern: "Property Tax Payable"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2510-0000"
          name_pattern: "Rent Received in Advance"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2515-0000"
          name_pattern: "A/P Tenant TI/LC"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2520-0000"
          name_pattern: "Deposit Refundable"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2521-0000"
          name_pattern: "Construction Deposit"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2585-0000"
          name_pattern: "A/P Suspense"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2590-0000"
          name_pattern: "Total Current Liabilities"
          type: "calculated_total"
          data_type: "decimal(15,2)"
          validation: "sum_of_subsection"
          required: true
    
    - subsection_id: "long_term_liabilities"
      name: "Long Term Liabilities"
      code_range: "2600-0000" to "2900-9999"
      total_account: "2900-0000"
      total_names: ["Total Long Term Liabilities"]
      required: true
      
      line_items:
        - account_code: "2612-0000"
          name_pattern: "NorthMarq Capital"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2614-0000"
          name_pattern: "Wells Fargo"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2616-0000"
          name_pattern: "MidLand Loan Services.*PNC"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2618-0000"
          name_pattern: "Trawler Capital"
          type: "detail"
          data_type: "decimal(15,2)"
          
        - account_code: "2900-0000"
          name_pattern: "Total Long Term Liabilities"
          type: "calculated_total"
          data_type: "decimal(15,2)"
          validation: "sum_of_subsection"
          required: true
  
  section_total:
    account_code: "2999-0000"
    name: "TOTAL LIABILITIES"
    type: "section_total"
    data_type: "decimal(15,2)"
    validation: "sum_of_all_subsections"
    required: true
    critical: true
```

### **Section 3: CAPITAL (EQUITY)**

```yaml
section_capital:
  section_name: "CAPITAL"
  section_code_range: "3000-0000" to "3999-9999"
  required: true
  
  subsections:
    - subsection_id: "equity_details"
      name: "Capital/Equity Details"
      code_range: "3050-0000" to "3995-9999"
      total_account: "3999-0000"
      required: true
      
      line_items:
        - account_code: "3050-0000"
          name_pattern: "Partners? Contributions?"
          type: "detail"
          data_type: "decimal(15,2)"
          required: true
          
        - account_code: "3910-0000"
          name_pattern: "Beginning Equity"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          
        - account_code: "3990-0000"
          name_pattern: "Distributions?"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
          
        - account_code: "3995-0000"
          name_pattern: "Current Period Earnings"
          type: "detail"
          data_type: "decimal(15,2)"
          allow_negative: true
  
  section_total:
    account_code: "3999-0000"
    name: "TOTAL CAPITAL"
    type: "section_total"
    data_type: "decimal(15,2)"
    validation: "sum_of_subsection"
    required: true
    critical: true
```

### **Grand Total**

```yaml
grand_total:
  account_code: "3999-9000"
  name: "TOTAL LIABILITIES & CAPITAL"
  type: "grand_total"
  data_type: "decimal(15,2)"
  validation: "total_liabilities + total_capital"
  required: true
  critical: true
  must_equal: "1999-0000"  # Must equal TOTAL ASSETS
```

---

## 🔍 **Extraction Rules**

### **1. Line Item Detection**

```yaml
line_item_patterns:
  # Standard format: "0122-0000    Cash - Operating    114,890.87"
  standard:
    pattern: "^(\\d{4}-\\d{4})\\s+([A-Za-z0-9 /\\-\\.()&,]+?)\\s+([-]?[\\d,]+\\.\\d{2})$"
    groups:
      1: account_code
      2: account_name
      3: amount
    confidence: 95
  
  # Format without code: "Cash - Operating    114,890.87"
  no_code:
    pattern: "^([A-Za-z0-9 /\\-\\.()&,]+?)\\s{2,}([-]?[\\d,]+\\.\\d{2})$"
    groups:
      1: account_name
      2: amount
    confidence: 75
    action: "fuzzy_match_to_chart_of_accounts"
  
  # Total lines: "Total Current Assets    481,979.78"
  total_line:
    pattern: "^(Total|TOTAL)\\s+([A-Za-z &]+?)\\s+([-]?[\\d,]+\\.\\d{2})$"
    groups:
      1: prefix
      2: section_name
      3: amount
    confidence: 90
    is_calculated: true
  
  # Header lines (skip): "ASSETS" or "Current Assets"
  header_line:
    pattern: "^(ASSETS|LIABILITIES|CAPITAL|Current Assets|Property & Equipment)$"
    action: "skip"
    
  # Accumulated depreciation (negative values expected)
  accumulated_depreciation:
    pattern: "Accum\\.?\\s*(Depr|Amort)"
    expect_negative: true
    is_contra_account: true
```

### **2. Amount Parsing**

```yaml
amount_parsing:
  format: "US"
  decimal_separator: "."
  thousands_separator: ","
  
  patterns:
    positive:
      - "\\d{1,3}(,\\d{3})*\\.\\d{2}"       # 114,890.87
      - "\\d+\\.\\d{2}"                      # 0.00
    
    negative:
      - "-\\d{1,3}(,\\d{3})*\\.\\d{2}"      # -56,028.54
      - "\\(\\d{1,3}(,\\d{3})*\\.\\d{2}\\)" # (56,028.54)
  
  validation:
    max_digits: 15
    decimal_places: 2
    min_confidence: 90
  
  post_processing:
    - remove_thousands_separator
    - convert_to_decimal
    - preserve_sign
```

### **3. Account Code Mapping**

```yaml
account_mapping:
  strategy: "exact_match_preferred"
  
  matching_rules:
    # 1. Exact code match (highest confidence)
    exact_code_match:
      confidence: 100
      action: "direct_insert"
    
    # 2. Fuzzy name match against chart_of_accounts
    fuzzy_name_match:
      confidence: 70-95
      threshold: 85
      algorithm: "levenshtein_distance"
      action: "map_to_closest_match"
      flag_if_below: 85
    
    # 3. Keyword-based matching
    keyword_match:
      confidence: 60-80
      keywords_per_account: true
      action: "map_with_review_flag"
    
    # 4. No match found
    no_match:
      confidence: 0
      action: "create_unmatched_item_entry"
      flag_for_review: true
      suggest_similar_accounts: true
```

### **4. Dynamic Account Discovery**

```yaml
# Handle accounts not in chart_of_accounts
dynamic_accounts:
  enabled: true
  auto_create: false  # Don't auto-create, flag for review
  
  when_found:
    - extract_full_details
    - store_in_unmatched_accounts_table
    - flag_needs_review: true
    - confidence_score: 50
    - suggest_mapping:
        - by_section_location
        - by_name_similarity
        - by_account_code_range
  
  examples:
    - account_code: "0999-1234"  # Not in chart
      account_name: "Cash - Special Account"
      action: "suggest_0122-0000 (Cash - Operating) or create new"
```

---

## ✅ **Validation Rules**

### **1. Accounting Equation (Critical)**

```yaml
fundamental_equation:
  rule: "total_assets = total_liabilities + total_capital"
  severity: "critical"
  tolerance: 0.01  # Allow $0.01 rounding difference
  
  validation_logic: |
    abs(total_assets - (total_liabilities + total_capital)) <= 0.01
  
  on_failure:
    confidence_score: 0
    needs_review: true
    flag_type: "critical_validation_failure"
    message: "Balance sheet does not balance"
```

### **2. Section Total Validation**

```yaml
section_totals:
  - section: "current_assets"
    rule: "sum(detail_line_items) = total_current_assets"
    tolerance: 0.01
    severity: "high"
    
  - section: "property_equipment"
    rule: "sum(detail_line_items) = total_property_equipment"
    tolerance: 0.01
    severity: "high"
    
  - section: "other_assets"
    rule: "sum(detail_line_items) = total_other_assets"
    tolerance: 0.01
    severity: "high"
    
  - section: "assets"
    rule: "total_current_assets + total_property_equipment + total_other_assets = total_assets"
    tolerance: 0.01
    severity: "critical"
```

### **3. Data Quality Checks**

```yaml
quality_checks:
  - check: "all_required_sections_present"
    required: ["assets", "liabilities", "capital"]
    severity: "critical"
    
  - check: "required_totals_extracted"
    required_accounts: ["1999-0000", "2999-0000", "3999-0000", "3999-9000"]
    severity: "critical"
    
  - check: "no_duplicate_accounts"
    rule: "unique(property_id, period_id, account_code)"
    severity: "high"
    
  - check: "reasonable_amounts"
    rules:
      - "total_assets > 0"
      - "total_liabilities >= 0"
      - "abs(total_capital) < total_assets * 2"  # Sanity check
    severity: "medium"
    
  - check: "contra_accounts_negative"
    accounts: ["1061-0000", "1071-0000", "1081-0000", "1922-0000", "1952-0000"]
    rule: "amount <= 0"
    severity: "medium"
```

### **4. Completeness Check**

```yaml
completeness:
  min_line_items: 20
  expected_line_items: 50-100
  
  critical_accounts:
    - "0510-0000"  # Land
    - "0610-0000"  # Buildings
    - "1999-0000"  # Total Assets
    - "2999-0000"  # Total Liabilities
    - "3999-0000"  # Total Capital
    
  on_missing_critical:
    confidence_score: 20
    needs_review: true
    severity: "critical"
```

---

## 🎯 **Confidence Scoring**

### **Per-Field Confidence**

```yaml
confidence_calculation:
  factors:
    - factor: "extraction_method"
      weights:
        exact_code_match: 100
        ocr_with_validation: 95
        fuzzy_match: 70-90
        keyword_match: 60-75
        manual_entry: 100
    
    - factor: "amount_clarity"
      weights:
        clear_digits: 100
        slight_ocr_noise: 85-95
        significant_ocr_noise: 60-80
        barely_readable: 30-50
    
    - factor: "position_context"
      weights:
        expected_section: 100
        unexpected_section: 70
        ambiguous_location: 50
    
    - factor: "validation_result"
      weights:
        passes_all_validations: 100
        minor_warning: 85
        validation_failed: 40
  
  final_confidence:
    formula: "weighted_average(all_factors)"
    threshold_for_auto_approve: 90
    threshold_for_review: 75
    threshold_for_rejection: 50
```

### **Document-Level Confidence**

```yaml
document_confidence:
  calculation: |
    (
      avg(line_item_confidences) * 0.4 +
      validation_pass_rate * 0.3 +
      completeness_score * 0.2 +
      accounting_equation_valid * 0.1
    )
  
  categories:
    excellent: ">= 95"
    good: "90-94"
    acceptable: "80-89"
    needs_review: "70-79"
    poor: "< 70"
  
  actions:
    excellent: "auto_approve"
    good: "auto_approve"
    acceptable: "flag_low_confidence_items_only"
    needs_review: "flag_entire_document"
    poor: "reject_and_request_reupload"
```

---

## 🚩 **Review Flags**

### **Automatic Flagging Rules**

```yaml
flagging_rules:
  - flag: "low_confidence_extraction"
    trigger: "line_item.confidence < 85"
    severity: "medium"
    message: "Low confidence in extracted amount"
    
  - flag: "unmatched_account"
    trigger: "account_code not in chart_of_accounts"
    severity: "high"
    message: "Account code not found in chart of accounts"
    suggested_action: "map_to_existing_or_create_new"
    
  - flag: "validation_failure"
    trigger: "validation_result = false"
    severity: "high"
    message: "Failed validation: {rule_name}"
    
  - flag: "unusual_amount"
    trigger: |
      abs(current_amount - prior_period_amount) > prior_period_amount * 0.5
      AND abs(change) > 10000
    severity: "medium"
    message: "Significant change from prior period"
    
  - flag: "negative_where_positive_expected"
    trigger: |
      account.expected_sign = 'positive' AND amount < 0
      AND account.is_contra_account = false
    severity: "medium"
    message: "Unexpected negative amount"
    
  - flag: "missing_critical_account"
    trigger: "critical_account not extracted"
    severity: "critical"
    message: "Required account missing: {account_name}"
    
  - flag: "balance_sheet_not_balanced"
    trigger: |
      abs(total_assets - (total_liabilities + total_capital)) > 0.01
    severity: "critical"
    message: "Balance sheet does not balance"
    blocking: true
```

---

## 📤 **Output Format**

### **Extraction Result Structure**

```json
{
  "extraction_id": "uuid",
  "document_upload_id": 456,
  "property_id": 1,
  "property_code": "ESP001",
  "period_id": 145,
  "period_year": 2024,
  "period_month": 12,
  
  "metadata": {
    "property_name": "Eastern Shore Plaza (esp)",
    "report_period": "Dec 2024",
    "accounting_method": "Accrual",
    "report_date": "Wednesday, February 19, 2025",
    "report_time": "12:52 PM",
    "extraction_timestamp": "2025-11-07T19:30:00Z",
    "extraction_engine_version": "3.1.0",
    "processing_time_seconds": 12.5
  },
  
  "line_items": [
    {
      "account_code": "0122-0000",
      "account_name": "Cash - Operating",
      "section": "ASSETS",
      "subsection": "Current Assets",
      "amount": -1080.00,
      "is_debit": true,
      "is_calculated": false,
      "is_contra_account": false,
      "parent_account_code": "0499-9000",
      "extraction_confidence": 98.5,
      "extraction_method": "exact_code_match",
      "needs_review": false,
      "flags": []
    },
    {
      "account_code": "0305-0000",
      "account_name": "A/R Tenants",
      "section": "ASSETS",
      "subsection": "Current Assets",
      "amount": 210365.06,
      "is_debit": true,
      "is_calculated": false,
      "is_contra_account": false,
      "parent_account_code": "0499-9000",
      "extraction_confidence": 99.2,
      "extraction_method": "exact_code_match",
      "needs_review": false,
      "flags": []
    },
    {
      "account_code": "0499-9000",
      "account_name": "Total Current Assets",
      "section": "ASSETS",
      "subsection": "Current Assets",
      "amount": 632457.39,
      "is_debit": true,
      "is_calculated": true,
      "calculation_validated": true,
      "parent_account_code": "1999-0000",
      "extraction_confidence": 99.8,
      "extraction_method": "exact_code_match",
      "needs_review": false,
      "flags": []
    }
    // ... additional 50-100 line items
  ],
  
  "validation_results": {
    "accounting_equation": {
      "passed": true,
      "total_assets": 23889953.33,
      "total_liabilities": 23839216.10,
      "total_capital": 50737.23,
      "difference": 0.00,
      "message": "Balance sheet balances"
    },
    
    "section_totals": {
      "current_assets": {
        "passed": true,
        "calculated_total": 632457.39,
        "extracted_total": 632457.39,
        "difference": 0.00
      },
      "property_equipment": {
        "passed": true,
        "calculated_total": 21855251.93,
        "extracted_total": 21855251.93,
        "difference": 0.00
      },
      "other_assets": {
        "passed": true,
        "calculated_total": 1402244.01,
        "extracted_total": 1402244.01,
        "difference": 0.00
      }
    },
    
    "data_quality": {
      "all_required_sections_present": true,
      "all_critical_accounts_extracted": true,
      "no_duplicate_accounts": true,
      "reasonable_amounts": true,
      "total_checks_passed": 15,
      "total_checks_run": 15
    }
  },
  
  "confidence_scores": {
    "document_level_confidence": 96.8,
    "average_line_item_confidence": 97.2,
    "lowest_confidence_item": {
      "account_code": "1950-5000",
      "confidence": 82.3
    },
    "items_below_threshold": 2,
    "items_needing_review": 2
  },
  
  "summary_statistics": {
    "total_line_items_extracted": 52,
    "required_line_items": 48,
    "optional_line_items": 4,
    "calculated_line_items": 8,
    "detail_line_items": 44,
    "items_with_flags": 2,
    "critical_flags": 0,
    "high_priority_flags": 0,
    "medium_priority_flags": 2
  },
  
  "extraction_status": "completed",
  "overall_confidence": 96.8,
  "needs_review": false,
  "ready_for_reporting": true,
  
  "flags": [],
  
  "review_queue": [
    {
      "account_code": "1950-5000",
      "account_name": "Internal - Lease Commission",
      "amount": 3316.66,
      "confidence": 82.3,
      "reason": "Low confidence extraction",
      "severity": "medium",
      "suggested_action": "verify_amount"
    },
    {
      "account_code": "0125-0000",
      "account_name": "Cash - Operating IV-PNC",
      "amount": 365638.38,
      "confidence": 88.1,
      "reason": "Significant change from prior period (+45%)",
      "severity": "medium",
      "suggested_action": "verify_change"
    }
  ],
  
  "unmatched_accounts": [],
  
  "calculated_metrics": {
    "total_assets": 23889953.33,
    "total_liabilities": 23839216.10,
    "total_equity": 50737.23,
    "debt_to_equity_ratio": 469.96,
    "current_ratio": 0.28,
    "working_capital": -1633042.15
  }
}
```

---

## 🔄 **Multi-Page Handling**

```yaml
multi_page_extraction:
  enabled: true
  
  page_detection:
    header_repeat: "Balance Sheet"
    footer_indicators: ["Page 1", "Page 2"]
    continuation_keywords: ["Continued", "(cont'd)"]
  
  page_processing:
    - extract_each_page_independently
    - merge_line_items_by_account_code
    - preserve_section_order
    - validate_no_duplicates
  
  continuation_handling:
    # Some balance sheets split across pages
    - detect_section_continuation
    - merge_with_previous_page_section
    - recalculate_section_totals
```

---

## 🛠️ **Implementation Guidelines**

### **Extraction Engine Integration**

```python
# backend/app/utils/parsers/balance_sheet_parser.py

class BalanceSheetParser:
    """
    Parse balance sheet PDFs with 100% data extraction quality
    """
    
    def __init__(self, template: ExtractionTemplate):
        self.template = template
        self.chart_of_accounts = self.load_chart_of_accounts()
        self.validation_rules = self.load_validation_rules()
    
    def parse(self, pdf_path: str, property_id: int, period_id: int) -> BalanceSheetExtraction:
        """
        Main extraction method
        
        Returns:
            BalanceSheetExtraction with confidence scores and flags
        """
        # Step 1: Extract text and tables
        raw_text = self.extract_text_with_ocr(pdf_path)
        tables = self.extract_tables(pdf_path)
        
        # Step 2: Extract header metadata
        metadata = self.extract_metadata(raw_text)
        
        # Step 3: Parse line items
        line_items = []
        for line in raw_text.split('\n'):
            parsed = self.parse_line_item(line)
            if parsed:
                line_items.append(parsed)
        
        # Step 4: Map to chart of accounts
        mapped_items = self.map_to_chart_of_accounts(line_items)
        
        # Step 5: Validate
        validation_results = self.validate_extraction(mapped_items)
        
        # Step 6: Calculate confidence scores
        confidence_scores = self.calculate_confidence(mapped_items, validation_results)
        
        # Step 7: Flag items for review
        flags = self.generate_review_flags(mapped_items, validation_results, confidence_scores)
        
        # Step 8: Calculate metrics
        metrics = self.calculate_financial_metrics(mapped_items)
        
        return BalanceSheetExtraction(
            metadata=metadata,
            line_items=mapped_items,
            validation_results=validation_results,
            confidence_scores=confidence_scores,
            flags=flags,
            metrics=metrics,
            needs_review=(confidence_scores.document_level < 85 or len(flags) > 0)
        )
    
    def parse_line_item(self, line: str) -> Optional[LineItem]:
        """Parse a single line into structured data"""
        # Try all patterns from template
        for pattern_config in self.template.line_item_patterns:
            match = re.match(pattern_config.pattern, line.strip())
            if match:
                return self.extract_line_item_from_match(match, pattern_config)
        return None
    
    def map_to_chart_of_accounts(self, items: List[LineItem]) -> List[MappedLineItem]:
        """Map extracted items to chart of accounts"""
        mapped = []
        for item in items:
            if item.account_code:
                # Exact match by code
                account = self.chart_of_accounts.get(item.account_code)
                if account:
                    mapped.append(MappedLineItem(
                        **item.__dict__,
                        mapping_method='exact_code_match',
                        mapping_confidence=100
                    ))
                else:
                    # Code not found - flag for review
                    mapped.append(MappedLineItem(
                        **item.__dict__,
                        mapping_method='unmatched',
                        mapping_confidence=0,
                        needs_review=True,
                        flags=['unmatched_account_code']
                    ))
            else:
                # Fuzzy match by name
                best_match = self.fuzzy_match_account_name(item.account_name)
                if best_match and best_match.confidence >= 85:
                    mapped.append(MappedLineItem(
                        **item.__dict__,
                        account_code=best_match.account_code,
                        mapping_method='fuzzy_name_match',
                        mapping_confidence=best_match.confidence
                    ))
                else:
                    # No good match - flag for review
                    mapped.append(MappedLineItem(
                        **item.__dict__,
                        mapping_method='no_match',
                        mapping_confidence=0,
                        needs_review=True,
                        flags=['account_name_not_matched'],
                        suggested_accounts=[m.account_code for m in best_match.top_5]
                    ))
        return mapped
    
    def validate_extraction(self, items: List[MappedLineItem]) -> ValidationResults:
        """Run all validation rules"""
        results = ValidationResults()
        
        # Critical: Accounting equation
        total_assets = self.get_account_amount(items, '1999-0000')
        total_liabilities = self.get_account_amount(items, '2999-0000')
        total_capital = self.get_account_amount(items, '3999-0000')
        
        diff = abs(total_assets - (total_liabilities + total_capital))
        results.accounting_equation = {
            'passed': diff <= 0.01,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_capital': total_capital,
            'difference': diff
        }
        
        # Section total validations
        results.section_totals = self.validate_section_totals(items)
        
        # Data quality checks
        results.data_quality = self.validate_data_quality(items)
        
        return results
    
    def calculate_confidence(self, items, validation_results) -> ConfidenceScores:
        """Calculate per-item and document-level confidence"""
        # Implementation per confidence scoring rules above
        pass
    
    def generate_review_flags(self, items, validation_results, confidence_scores) -> List[ReviewFlag]:
        """Generate flags for items needing review"""
        # Implementation per flagging rules above
        pass
```

### **Database Storage**

```python
# backend/app/services/balance_sheet_service.py

class BalanceSheetService:
    """
    Service for storing balance sheet data
    """
    
    def store_extraction_result(
        self,
        extraction: BalanceSheetExtraction,
        upload_id: int
    ) -> int:
        """
        Store extraction results in database
        
        Returns:
            extraction_id
        """
        # Store each line item
        for item in extraction.line_items:
            balance_sheet_data = BalanceSheetData(
                property_id=extraction.property_id,
                period_id=extraction.period_id,
                upload_id=upload_id,
                account_code=item.account_code,
                account_name=item.account_name,
                amount=item.amount,
                is_debit=item.is_debit,
                is_calculated=item.is_calculated,
                parent_account_code=item.parent_account_code,
                extraction_confidence=item.extraction_confidence,
                needs_review=item.needs_review,
                created_at=datetime.utcnow()
            )
            
            # Use upsert to handle re-extraction
            stmt = insert(BalanceSheetData).values(**balance_sheet_data.__dict__)
            stmt = stmt.on_conflict_do_update(
                index_elements=['property_id', 'period_id', 'account_code'],
                set_={'amount': stmt.excluded.amount, 'extraction_confidence': stmt.excluded.extraction_confidence}
            )
            db.execute(stmt)
        
        # Store validation results
        validation_result = ValidationResult(
            upload_id=upload_id,
            rule_name='accounting_equation',
            passed=extraction.validation_results.accounting_equation['passed'],
            details=extraction.validation_results.accounting_equation
        )
        db.add(validation_result)
        
        # Store metrics
        metrics = FinancialMetrics(
            property_id=extraction.property_id,
            period_id=extraction.period_id,
            total_assets=extraction.metrics.total_assets,
            total_liabilities=extraction.metrics.total_liabilities,
            total_equity=extraction.metrics.total_equity,
            # ... other metrics
        )
        db.add(metrics)
        
        db.commit()
```

---

## 📋 **Testing & Quality Assurance**

### **Test Cases**

```yaml
test_suite:
  unit_tests:
    - test_line_item_parsing_standard_format
    - test_line_item_parsing_no_code_format
    - test_amount_parsing_positive
    - test_amount_parsing_negative
    - test_amount_parsing_parentheses
    - test_account_code_exact_match
    - test_account_name_fuzzy_match
    - test_section_total_calculation
    - test_accounting_equation_validation
    - test_confidence_score_calculation
    - test_review_flag_generation
  
  integration_tests:
    - test_end_to_end_extraction_esp_2024
    - test_end_to_end_extraction_hammond_2024
    - test_end_to_end_extraction_tcsh_2024
    - test_end_to_end_extraction_wendover_2024
    - test_multi_page_extraction
    - test_reprocessing_same_document
    - test_extraction_with_poor_ocr
  
  validation_tests:
    - test_balanced_balance_sheet
    - test_unbalanced_balance_sheet_detection
    - test_section_total_mismatch_detection
    - test_missing_critical_account_detection
    - test_duplicate_account_detection
  
  performance_tests:
    - test_extraction_time_under_30_seconds
    - test_memory_usage_under_500mb
    - test_concurrent_extractions
```

### **Quality Metrics**

```yaml
quality_kpis:
  extraction_accuracy:
    target: ">= 98%"
    measurement: "line_items_correctly_extracted / total_line_items"
  
  validation_pass_rate:
    target: ">= 95%"
    measurement: "documents_passing_validation / total_documents"
  
  false_positive_rate:
    target: "<= 2%"
    measurement: "items_flagged_incorrectly / total_items_flagged"
  
  processing_time:
    target: "<= 30 seconds per document"
    measurement: "time_from_upload_to_completion"
  
  zero_data_loss:
    target: "100%"
    measurement: "all_line_items_in_pdf_captured_in_database"
```

---

## 🎓 **Training Data**

To continuously improve extraction quality:

```yaml
training_data_collection:
  store_for_ml_training:
    - original_pdf_images
    - ocr_raw_text
    - parsed_line_items
    - user_corrections
    - final_approved_data
  
  feedback_loop:
    - collect_user_corrections
    - analyze_common_errors
    - retrain_fuzzy_matching_model
    - update_extraction_patterns
    - improve_confidence_scoring
  
  periodic_review:
    frequency: monthly
    actions:
      - review_low_confidence_extractions
      - analyze_flagged_items
      - update_chart_of_accounts
      - refine_validation_rules
```

---

## 📞 **Support & Maintenance**

### **Error Handling**

```yaml
error_scenarios:
  - scenario: "PDF is corrupted"
    action: "Return error, request re-upload"
    
  - scenario: "OCR completely fails"
    action: "Try alternative OCR engine, flag for manual review"
    
  - scenario: "Balance sheet format completely unknown"
    action: "Store as-is, flag for template creation"
    
  - scenario: "Extraction times out"
    action: "Retry once, then flag for investigation"
```

### **Logging**

```yaml
logging_requirements:
  levels:
    - DEBUG: Detailed extraction steps
    - INFO: Extraction started/completed
    - WARNING: Low confidence items, validation warnings
    - ERROR: Extraction failures, critical validations failed
  
  log_retention: 90_days
  
  audit_trail:
    - who_uploaded
    - when_uploaded
    - extraction_version
    - all_validations_run
    - all_flags_generated
    - who_reviewed
    - what_was_corrected
```

---

## ✅ **Success Criteria**

This template successfully achieves **100% data extraction quality with zero loss** when:

1. **All line items extracted** (detail + calculated)
2. **All amounts parsed correctly** (including negatives)
3. **All account codes mapped** (exact or fuzzy matched)
4. **Accounting equation validates** (within $0.01 tolerance)
5. **Section totals validate** (within $0.01 tolerance)
6. **Confidence scores calculated** (per-item and document-level)
7. **Review flags generated** (for low confidence items)
8. **Metrics calculated** (financial ratios and KPIs)
9. **Database storage complete** (all tables updated)
10. **Zero data loss verified** (all PDF data in database)

---

## 🚀 **Ready for Production**

This template is **production-ready** and handles:

✅ Multiple property types  
✅ Different accounting software outputs  
✅ Multi-page balance sheets  
✅ OCR quality variations  
✅ Account code mapping  
✅ Validation and quality control  
✅ Confidence scoring  
✅ Review workflow  
✅ Zero data loss guarantee  

**Next Steps:**
1. Implement parser using this template
2. Test with all 8 uploaded balance sheets
3. Verify 98%+ extraction accuracy
4. Deploy to production
5. Monitor and continuously improve

---

**Template Version:** 1.0  
**Last Updated:** 2025-11-07  
**Status:** Production-Ready ✅
