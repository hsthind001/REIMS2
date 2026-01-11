# REIMS2 Audit Rules Gap Analysis
## Comprehensive Documentation vs Database Implementation

**Prepared:** 2025-12-28
**Database:** REIMS2 PostgreSQL
**Documentation Source:** `/home/hsthind/REIMS Audit Rules/`

---

## EXECUTIVE SUMMARY

### Current Database State
- **validation_rules**: 34 rules implemented
- **extraction_template**: 1 template (mortgage statements)
- **system_config**: 1 config (anomaly threshold)
- **alert_rules**: EMPTY
- **auto_resolution_rules**: EMPTY
- **prevention_rules**: EMPTY
- **materiality_configs**: EMPTY
- **calculated_rules**: EMPTY

### Documentation Coverage
- **Balance Sheet Rules**: 35 rules documented
- **Income Statement Rules**: 27 rules documented
- **Cash Flow Rules**: 23 rules documented
- **Rent Roll Rules**: 11 rules documented
- **Mortgage Statement Rules**: 14 rules documented
- **Cross-Document Reconciliation Rules**: 19 rules documented
- **Forensic Audit Framework Rules**: 85+ rules documented
- **TOTAL DOCUMENTED**: 214+ comprehensive audit rules

### Implementation Gap: 180+ RULES MISSING (84% gap)

---

## PART 1: BALANCE SHEET RULES (35 Rules Documented)

### IMPLEMENTED (5 rules)
✓ `balance_sheet_equation` - Assets = Liabilities + Equity
✓ `balance_sheet_current_assets` - Current Assets sum correctly
✓ `balance_sheet_fixed_assets` - Fixed Assets sum correctly
✓ `balance_sheet_no_negative_cash` - Cash accounts should not be negative
✓ `balance_sheet_no_negative_equity` - Total Equity should not be negative

### MISSING (30 rules)

#### Constants & Invariants (10 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| BS-2 | cash_operating_constant | Cash - Operating = $3,375.45 (constant) | MUST-HAVE |
| BS-6 | land_value_constant | Land value should remain constant unless sold/purchased | MUST-HAVE |
| BS-7 | buildings_value_constant | Buildings value constant unless capex | MUST-HAVE |
| BS-14 | deposits_constant | Deposits should remain constant | NICE-TO-HAVE |
| BS-15 | loan_costs_constant | Loan Costs constant unless refinance | NICE-TO-HAVE |
| BS-17 | accumulated_amort_other_constant | Accumulated Amortisation (Other) constant if fully amortized | NICE-TO-HAVE |
| BS-22 | ap_5rivers_constant | A/P 5Rivers CRE constant unless payment | NICE-TO-HAVE |
| BS-23 | ap_eastchase_constant | A/P Eastchase sec constant | NICE-TO-HAVE |
| BS-24 | loans_payable_5rivers_constant | Loans Payable 5Rivers constant | NICE-TO-HAVE |
| BS-25 | deposit_refundable_constant | Deposit Refundable to Tenant constant | NICE-TO-HAVE |

#### Monthly Changes & Patterns (12 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| BS-4 | ar_trade_monthly_decrease | A/R Trade decreases ~$666-667/month | MUST-HAVE |
| BS-5 | ar_tenants_decreasing_trend | A/R Tenants shows declining pattern | MUST-HAVE |
| BS-8 | buildings_depreciation_monthly | Buildings depreciation ~$46,822/month | MUST-HAVE |
| BS-9 | improvements_15yr_depreciation | 15-year improvements depreciate ~$17,905/month | MUST-HAVE |
| BS-11 | ti_current_improvements_increase | TI/Current improvements increase with capex | MUST-HAVE |
| BS-16 | loan_costs_amortization_monthly | Loan costs amortize ~$2,239/month | MUST-HAVE |
| BS-26 | accrued_expenses_volatility | Accrued expenses vary with timing | NICE-TO-HAVE |
| BS-27 | ap_trade_volatility | A/P Trade varies with vendor activity | NICE-TO-HAVE |
| BS-28 | property_tax_payable_accumulation | Property tax accumulates ~$16,639/month until payment | MUST-HAVE |
| BS-29 | rent_received_advance_changes | Rent received in advance changes with tenant payments | NICE-TO-HAVE |
| BS-18 | external_lease_commission_increases | External lease commissions increase with new leases | NICE-TO-HAVE |
| BS-19 | internal_lease_commission_increases | Internal lease commissions increase with activity | NICE-TO-HAVE |

#### Capital & Equity (8 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| BS-30 | partners_contribution_constant | Partners Contribution constant (initial investment) | MUST-HAVE |
| BS-31 | beginning_equity_constant | Beginning Equity constant for the year | MUST-HAVE |
| BS-32 | distribution_changes | Distributions increase when cash distributed | MUST-HAVE |
| BS-33 | current_period_earnings_accumulation | Current Period Earnings = Cumulative Net Income YTD | MUST-HAVE |
| BS-34 | total_capital_calculation | Total Capital = Contribution + Beg Equity - Distributions + Earnings | MUST-HAVE |
| BS-35 | change_total_capital | Change in Total Capital = Change in Earnings + Change in Distributions | MUST-HAVE |

**SQL Implementation Example for BS-33:**
```sql
INSERT INTO validation_rules (
    rule_name,
    rule_description,
    document_type,
    rule_type,
    rule_formula,
    error_message,
    severity,
    is_active
) VALUES (
    'bs_current_period_earnings_accumulation',
    'Current Period Earnings equals cumulative YTD Net Income from Income Statement',
    'balance_sheet',
    'cross_statement_check',
    'current_period_earnings_bs = ytd_net_income_is',
    'Current Period Earnings on Balance Sheet does not match YTD Net Income from Income Statement',
    'error',
    true
);
```

---

## PART 2: INCOME STATEMENT RULES (27 Rules Documented)

### IMPLEMENTED (6 rules)
✓ `income_statement_total_revenue` - Revenue accounts sum to Total Revenue
✓ `income_statement_total_expenses` - Expense accounts sum to Total Expenses
✓ `income_statement_net_income` - Net Income = Revenue - Expenses
✓ `income_statement_percentages` - Percentages should be reasonable
✓ `income_statement_ytd_consistency` - YTD >= Period amounts
✓ `income_statement_no_negative_revenue` - Revenue should not be negative

### MISSING (21 rules)

#### Fundamental Structure (3 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| IS-1 | income_statement_equation | NET INCOME = TOTAL INCOME - TOTAL EXPENSES - Other Income/Expenses | MUST-HAVE |
| IS-2 | ytd_calculation_formula | Current Period YTD = Prior Period YTD + Current Period PTD | MUST-HAVE |
| IS-3 | ytd_never_decreases | YTD should never decrease (except adjustments) | MUST-HAVE |

#### Revenue Composition (5 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| IS-4 | total_income_composition | TOTAL INCOME = Base Rentals + Interest + Tax + Insurance + CAM + Annual Cams + Percentage Rent + Other | MUST-HAVE |
| IS-5 | constant_reimbursement_components | Tax reimbursement = $15,995.20/month, Insurance = $45,376.34/month | MUST-HAVE |
| IS-6 | variable_income_components | Base rentals vary by occupancy and rent rates | NICE-TO-HAVE |
| IS-7 | cam_pattern | CAM varies by actual expenses and tenant share | NICE-TO-HAVE |
| IS-8 | percentage_rent_threshold | Percentage rent only when tenant sales exceed threshold | NICE-TO-HAVE |

#### Expense Categories (6 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| IS-9 | total_expenses_composition | TOTAL EXPENSES = Operating + Additional Operating | MUST-HAVE |
| IS-10 | property_tax_expense_pattern | Property tax pattern validation | NICE-TO-HAVE |
| IS-11 | property_insurance_expense_pattern | Insurance follows similar pattern to tax | NICE-TO-HAVE |
| IS-12 | offsite_management_fee_4pct | Off-Site Management = 4.00% of Total Income | MUST-HAVE |
| IS-13 | asset_management_fee_1pct | Asset Management = 1.00% of Total Income | MUST-HAVE |
| IS-14 | accounting_fee_0_75pct | Accounting Fee ≈ 0.75% of Total Income | NICE-TO-HAVE |

#### Operating Metrics (7 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| IS-17 | mortgage_interest_decreases | Mortgage interest decreases as principal paid down | MUST-HAVE |
| IS-18 | depreciation_pattern | Depreciation constant or reducing pattern | MUST-HAVE |
| IS-19 | amortization_pattern | Amortization constant or reducing pattern | MUST-HAVE |
| IS-20 | operating_expense_ratio | Operating Expense Ratio = Operating Expenses / Total Income | MUST-HAVE |
| IS-21 | noi_margin | NOI Margin = NOI / Total Income | MUST-HAVE |
| IS-22 | net_income_margin | Net Income Margin = Net Income / Total Income | MUST-HAVE |
| IS-16 | rm_lighting_constant_monthly | R&M Lighting = $4,758.00/month | NICE-TO-HAVE |

**SQL Implementation Example for IS-12:**
```sql
INSERT INTO validation_rules (
    rule_name,
    rule_description,
    document_type,
    rule_type,
    rule_formula,
    error_message,
    severity,
    tolerance_percentage,
    is_active
) VALUES (
    'is_offsite_management_fee_4pct',
    'Off-Site Management Fee should be 4.00% of Total Income',
    'income_statement',
    'percentage_check',
    'offsite_management_fee / total_income = 0.04',
    'Off-Site Management Fee is not 4% of Total Income (tolerance ±0.5%)',
    'warning',
    0.5,
    true
);
```

---

## PART 3: CASH FLOW RULES (23 Rules Documented)

### IMPLEMENTED (14 rules)
✓ `cf_total_income_sum` - Total Income equals sum
✓ `cf_base_rental_percentage` - Base Rentals 70-100% of Total Income
✓ `cf_total_expenses_sum` - Total Expenses calculation
✓ `cf_expense_subtotals` - Operating Expenses subtotals
✓ `cf_noi_calculation` - NOI = Income - Expenses
✓ `cf_noi_percentage` - NOI 60-80% of Income
✓ `cf_noi_positive` - NOI should be positive
✓ `cf_net_income_calculation` - Net Income formula
✓ `cf_cash_flow_calculation` - Cash Flow = Net Income + Adjustments
✓ `cf_cash_account_differences` - Account reconciliation
✓ `cf_total_cash_balance` - Cash differences = Cash Flow
✓ `cash_flow_categories_sum` - Categories sum to net change
✓ `cash_flow_beginning_ending` - Beginning + Change = Ending
✓ `cash_flow_cross_check_balance_sheet` - CF cash matches BS cash

### MISSING (9 rules)

#### Non-Cash Adjustments (3 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| CF-7 | non_cash_expenses_addback | Depreciation + Amortization added back to Net Income | MUST-HAVE |
| CF-7A | total_non_cash_expenses | Total non-cash = Buildings + 15yr + Other + Amort | MUST-HAVE |
| CF-6 | adjustments_balance_sheet_changes | Adjustments = Sum of all non-cash BS account changes | MUST-HAVE |

#### Working Capital Sign Conventions (2 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| CF-8A | current_assets_sign_convention | Asset decrease = positive, increase = negative | MUST-HAVE |
| CF-9A | current_liabilities_sign_convention | Liability increase = positive, decrease = negative | MUST-HAVE |

#### Capital Expenditure (2 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| CF-12 | fixed_asset_additions_negative | Fixed asset additions = negative cash flow | MUST-HAVE |
| CF-12A | capex_cash_outflows | All additions to fixed assets are cash outflows | MUST-HAVE |

#### Escrow & Debt (2 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| CF-13 | escrow_account_changes | Escrow increase = negative, decrease = positive | MUST-HAVE |
| CF-14 | mortgage_principal_payments | Principal payment = negative cash flow | MUST-HAVE |

**SQL Implementation Example for CF-7:**
```sql
INSERT INTO validation_rules (
    rule_name,
    rule_description,
    document_type,
    rule_type,
    rule_formula,
    error_message,
    severity,
    is_active
) VALUES (
    'cf_non_cash_expenses_addback',
    'Non-cash expenses (Depreciation + Amortization) must be added back to Net Income in adjustments',
    'cash_flow',
    'balance_check',
    'depreciation_adjustment + amortization_adjustment = depreciation_expense_is + amortization_expense_is',
    'Depreciation and amortization add-backs do not match Income Statement expenses',
    'error',
    true
);
```

---

## PART 4: RENT ROLL RULES (11 Rules Documented)

### IMPLEMENTED (4 rules)
✓ `rent_roll_occupancy_rate` - Occupancy 0-100%
✓ `rent_roll_total_rent` - Sum of rents matches total
✓ `rent_roll_no_duplicate_units` - Unique units
✓ `rent_roll_valid_lease_dates` - Start < End dates

### MISSING (7 rules)

#### Fundamental Calculations (4 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| RR-1 | total_property_composition | Total Area = Occupied + Vacant (constant) | MUST-HAVE |
| RR-2 | occupancy_rate_calculation | Occupancy = (Occupied / Total) × 100 | MUST-HAVE |
| RR-3 | annual_rent_calculation | Annual Rent = Monthly Rent × 12 | MUST-HAVE |
| RR-4 | monthly_rent_per_sf | Monthly Rent Per SF = Monthly Rent / Area | MUST-HAVE |

#### Cross-Statement Reconciliation (3 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| RR-IS-1 | monthly_rent_to_base_rentals | RR Monthly Rent ≈ IS Base Rentals | MUST-HAVE |
| RR-BS-1 | rr_informs_ar_tenants | A/R Tenants represents uncollected rent from RR | MUST-HAVE |
| RR-BS-2 | rent_received_in_advance | Prepaid rent from tenants on BS | NICE-TO-HAVE |

**SQL Implementation Example for RR-3:**
```sql
INSERT INTO validation_rules (
    rule_name,
    rule_description,
    document_type,
    rule_type,
    rule_formula,
    error_message,
    severity,
    tolerance_percentage,
    is_active
) VALUES (
    'rr_annual_rent_calculation',
    'Annual Rent must equal Monthly Rent × 12',
    'rent_roll',
    'balance_check',
    'annual_rent = monthly_rent * 12',
    'Annual Rent does not equal Monthly Rent × 12 (tolerance ±$1)',
    'error',
    0.01,
    true
);
```

---

## PART 5: MORTGAGE STATEMENT RULES (14 Rules Documented)

### IMPLEMENTED (1 rule via extraction_template)
✓ Mortgage statement extraction template exists

### MISSING (14 rules)

#### Principal Balance Rules (3 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| MS-1 | principal_balance_reduction | Next Month Balance = Current - Principal Due | MUST-HAVE |
| MS-2 | principal_paid_accumulation | Next Month Principal Paid = Current + Principal Due | MUST-HAVE |
| MS-7 | principal_balance_to_bs | MS Principal Balance = BS Mortgage Liability | MUST-HAVE |

#### Payment Composition (4 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| MS-8 | total_payment_composition | Total = Principal + Interest + Tax + Insurance + Reserves | MUST-HAVE |
| MS-9 | constant_monthly_payment | Total Payment constant (e.g., $206,734.24) | MUST-HAVE |
| MS-10 | constant_escrow_components | Tax, Insurance, Reserves constant monthly | MUST-HAVE |
| MS-11 | principal_interest_balance | Principal + Interest = Constant (e.g., $125,629.71) | MUST-HAVE |

#### Escrow Rules (3 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| MS-4 | insurance_escrow_balance | Next Balance = Current + Due - Disbursements | MUST-HAVE |
| MS-5 | tax_escrow_balance | Next Balance = Current + Due - Disbursements | MUST-HAVE |
| MS-6 | reserve_balance | Next Balance = Current + Due - Disbursements | MUST-HAVE |

#### Other Rules (4 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| MS-3 | interest_paid_accumulation | Next Interest Paid = Current + Interest Due | MUST-HAVE |
| MS-12 | late_charge_calculation | Late Charge = Total Payment × 5% | NICE-TO-HAVE |
| MS-13 | ytd_cumulative_tracking | YTD accumulates each month | MUST-HAVE |
| MS-14 | interest_rate_constant | Interest Rate constant unless modification | NICE-TO-HAVE |

**SQL Implementation Example for MS-1:**
```sql
INSERT INTO validation_rules (
    rule_name,
    rule_description,
    document_type,
    rule_type,
    rule_formula,
    error_message,
    severity,
    tolerance_percentage,
    is_active
) VALUES (
    'ms_principal_balance_reduction',
    'Next month principal balance = Current month balance - Current principal due',
    'mortgage_statement',
    'sequential_check',
    'principal_balance_next = principal_balance_current - principal_due_current',
    'Principal balance reduction calculation is incorrect',
    'error',
    0.01,
    true
);
```

---

## PART 6: CROSS-DOCUMENT RECONCILIATION RULES (19 Rules)

### IMPLEMENTED (2 rules)
✓ `cross_net_income_consistency` - Net Income IS = CF
✓ `cross_cash_consistency` - Cash BS = CF

### MISSING (17 rules)

#### Income Statement ↔ Balance Sheet (7 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| IS-BS-2 | current_period_earnings_ytd | BS Current Period Earnings = IS YTD Net Income | MUST-HAVE |
| IS-BS-3 | depreciation_3way | IS Depreciation = BS Accum Depr Change = CF Add-Back | MUST-HAVE |
| IS-BS-4 | amortization_3way | IS Amortization = BS Accum Amort Change = CF Add-Back | MUST-HAVE |
| IS-BS-6 | property_tax_expense_payable | IS Property Tax creates BS Property Tax Payable | MUST-HAVE |
| IS-BS-7 | insurance_expense_prepaid | IS Insurance Expense reduces BS Prepaid Insurance | MUST-HAVE |
| IS-BS-8 | revenue_creates_receivables | IS Revenue creates BS A/R Tenants | MUST-HAVE |
| IS-BS-9 | expenses_create_payables | IS Expenses create BS A/P if not paid | MUST-HAVE |

#### Balance Sheet ↔ Mortgage Statement (5 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| RECON-1 | wells_fargo_balance_match | BS Wells Fargo = MS Principal Balance | MUST-HAVE |
| RECON-2 | escrow_property_tax_match | BS Escrow Tax = MS Tax Escrow Balance | MUST-HAVE |
| RECON-3 | escrow_insurance_match | BS Escrow Insurance = MS Insurance Escrow | MUST-HAVE |
| RECON-4 | escrow_tilc_match | BS Escrow TI/LC = MS Reserve Balance | MUST-HAVE |
| RECON-8 | property_tax_payable_accumulation | BS Tax Payable accumulates = MS Tax Disbursement | MUST-HAVE |

#### Cash Flow ↔ Income Statement (5 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| CF-IS-3 | depreciation_expense_addback | IS Depreciation = CF Depreciation Add-Back | MUST-HAVE |
| CF-IS-4 | amortization_expense_addback | IS Amortization = CF Amortization Add-Back | MUST-HAVE |
| CF-IS-7 | revenue_vs_cash_collections | IS Revenue vs CF A/R adjustment = Cash collected | MUST-HAVE |
| CF-IS-9 | expenses_vs_cash_payments | IS Expense vs CF A/P adjustment = Cash paid | MUST-HAVE |
| CF-IS-11 | capex_not_on_is | CF CapEx does NOT appear on IS (capitalized) | MUST-HAVE |

**SQL Implementation Example for IS-BS-3:**
```sql
INSERT INTO validation_rules (
    rule_name,
    rule_description,
    document_type,
    rule_type,
    rule_formula,
    error_message,
    severity,
    is_active
) VALUES (
    'isbs_depreciation_3way_reconciliation',
    'Depreciation must reconcile across all three statements: IS Expense = BS Accum Depr Change = CF Add-Back',
    'cross_statement',
    'three_way_check',
    'depreciation_expense_is = accum_depreciation_change_bs = depreciation_addback_cf',
    'Depreciation does not reconcile across Income Statement, Balance Sheet, and Cash Flow',
    'error',
    true
);
```

---

## PART 7: FORENSIC AUDIT FRAMEWORK RULES (85+ Rules)

### IMPLEMENTED (0 rules)
None of the forensic audit rules are implemented

### MISSING (85+ rules)

#### Document Completeness (Phase 1 - 5 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| A-1.1 | document_inventory_completeness | All required documents present (>95%) | MUST-HAVE |
| A-1.2 | period_consistency_check | All documents cover same periods | MUST-HAVE |
| A-1.3 | version_control_check | Final versions only, no duplicates | MUST-HAVE |
| A-1.4 | document_date_range_validation | No gaps or overlaps in periods | MUST-HAVE |
| A-1.5 | document_type_coverage | All property types have all doc types | NICE-TO-HAVE |

#### Mathematical Integrity (Phase 2 - 8 rules)
All covered by existing rules but need enhanced materiality thresholds

#### Cross-Document Reconciliation (Phase 3 - 15 rules)
Covered in Part 6 above

#### Rent Roll to Financial Statements (Phase 4 - 12 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| A-4.1 | monthly_rent_to_is_base_rentals | RR Monthly Rent ≈ IS Base Rentals (±5%) | MUST-HAVE |
| A-4.2 | rent_roll_trend_analysis | Changes documented (leases, terminations) | MUST-HAVE |
| A-4.3 | occupancy_rate_verification | Calculated = Reported | MUST-HAVE |
| A-4.4 | tenant_concentration_risk | Top tenant >20% = HIGH RISK | MUST-HAVE |
| A-4.5 | lease_expiration_analysis | 12-month rollover >25% = HIGH RISK | MUST-HAVE |
| A-4.6 | rent_per_sf_analysis | Rent/SF consistent with market | NICE-TO-HAVE |
| A-4.7 | vacant_space_analysis | Vacancy >12 months = RED FLAG | MUST-HAVE |

#### A/R & Collections Analysis (Phase 5 - 8 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| A-5.1 | ar_aging_analysis | DSO <30 days = EXCELLENT | MUST-HAVE |
| A-5.2 | cash_collections_verification | CF A/R adjustment ≈ BS A/R change | MUST-HAVE |
| A-5.3 | revenue_quality_score | Composite score 0-100 | NICE-TO-HAVE |
| A-5.4 | collection_efficiency_ratio | Collections / Revenue | MUST-HAVE |
| A-5.5 | bad_debt_analysis | Write-offs as % of revenue | NICE-TO-HAVE |
| A-5.6 | tenant_payment_patterns | Consistent vs erratic payers | NICE-TO-HAVE |
| A-5.7 | aging_buckets | 0-30, 31-60, 61-90, 91+ days | MUST-HAVE |
| A-5.8 | concentration_collections | Collections from top tenants | NICE-TO-HAVE |

#### Fraud Detection (Phase 6 - 15 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| A-6.1 | benfords_law_analysis | First digit frequency distribution | MUST-HAVE |
| A-6.2 | round_number_analysis | >10% round numbers = RED FLAG | MUST-HAVE |
| A-6.3 | duplicate_payment_detection | Same amount 2+ times = investigate | MUST-HAVE |
| A-6.4 | variance_analysis_pop | >25% variance = investigate | MUST-HAVE |
| A-6.5 | related_party_transactions | Identify related parties | MUST-HAVE |
| A-6.6 | sequential_gap_analysis | Missing check/invoice numbers | MUST-HAVE |
| A-6.7 | journal_entry_testing | Manual entries = higher scrutiny | MUST-HAVE |
| A-6.8 | cash_ratio_analysis | Cash Flow / Net Income ratio | MUST-HAVE |
| A-6.9 | timing_analysis | Weekend/after-hours entries | NICE-TO-HAVE |
| A-6.10 | reversal_pattern_detection | Entry + reversal pattern | MUST-HAVE |
| A-6.11 | vendor_analysis | New vendors, one-time vendors | NICE-TO-HAVE |
| A-6.12 | unusual_transaction_amounts | Amounts just under approval limits | NICE-TO-HAVE |
| A-6.13 | geographic_anomalies | Vendors far from property | NICE-TO-HAVE |
| A-6.14 | category_shifting | Expenses moved between categories | NICE-TO-HAVE |
| A-6.15 | cutoff_testing | Transactions near period end | NICE-TO-HAVE |

#### Debt Service & Liquidity (Phase 7 - 8 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| A-7.1 | debt_service_coverage_ratio | DSCR = NOI / Debt Service (≥1.25) | MUST-HAVE |
| A-7.2 | debt_to_value_ratio | LTV = Mortgage / Value (≤75%) | MUST-HAVE |
| A-7.3 | interest_coverage_ratio | ICR = NOI / Interest (≥3.0) | MUST-HAVE |
| A-7.4 | current_ratio | Current Assets / Current Liabilities (≥2.0) | MUST-HAVE |
| A-7.5 | quick_ratio | (Cash + A/R) / Current Liabilities (≥1.0) | MUST-HAVE |
| A-7.6 | cash_burn_rate | Months of runway if negative CF | MUST-HAVE |
| A-7.7 | covenant_compliance_tracking | All lender covenants met | MUST-HAVE |
| A-7.8 | liquidity_stress_testing | Worst-case scenario analysis | NICE-TO-HAVE |

#### Performance Metrics (Phase 8 - 6 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| A-8.1 | same_store_sales_growth | YoY growth for properties held >12 months | MUST-HAVE |
| A-8.2 | noi_margin | NOI / Revenue (benchmarks by type) | MUST-HAVE |
| A-8.3 | operating_expense_ratio | OpEx / Revenue | MUST-HAVE |
| A-8.4 | capex_as_pct_revenue | CapEx / Revenue (5-10% normal) | MUST-HAVE |
| A-8.5 | revenue_per_sf | Annual revenue / Total SF | NICE-TO-HAVE |
| A-8.6 | noi_per_sf | Annual NOI / Total SF | NICE-TO-HAVE |

#### Materiality & Thresholds (Phase 9 - 8 rules)
| Rule ID | Rule Name | Description | Criticality |
|---------|-----------|-------------|-------------|
| A-10.1 | overall_materiality_quantitative | 0.5-1% of Assets, 3-5% of NI, 1-2% of Revenue | MUST-HAVE |
| A-10.2 | overall_materiality_qualitative | Covenant violations, tax impacts | MUST-HAVE |
| A-10.3 | line_item_materiality | 5-10% of overall materiality | MUST-HAVE |
| A-10.4 | fraud_threshold_zero | ANY fraud irregularity investigated | MUST-HAVE |
| A-10.5 | performance_materiality | 50-75% of overall materiality | NICE-TO-HAVE |
| A-10.6 | clearly_trivial_threshold | Items clearly below materiality | NICE-TO-HAVE |
| A-10.7 | accumulated_misstatement | Sum of uncorrected items < materiality | MUST-HAVE |
| A-10.8 | specific_account_thresholds | Cash, Revenue = lower thresholds | NICE-TO-HAVE |

---

## PART 8: CALCULATED & DERIVED RULES (New Category Needed)

### Tables Needed in Database
Currently MISSING these tables:
- `calculated_rules` - For computed metrics
- `materiality_configs` - For threshold management
- `alert_rules` - For automated alerting
- `auto_resolution_rules` - For auto-corrections
- `prevention_rules` - For data entry validation

### Calculated Rules Examples (20+ needed)

#### Financial Ratios
| Rule ID | Rule Name | Formula | Criticality |
|---------|-----------|---------|-------------|
| CALC-1 | current_ratio | Current Assets / Current Liabilities | MUST-HAVE |
| CALC-2 | quick_ratio | (Cash + A/R) / Current Liabilities | MUST-HAVE |
| CALC-3 | debt_to_equity | Total Debt / Total Equity | MUST-HAVE |
| CALC-4 | dscr | NOI / Annual Debt Service | MUST-HAVE |
| CALC-5 | ltv_ratio | Mortgage Balance / Property Value | MUST-HAVE |
| CALC-6 | noi_margin | NOI / Total Revenue × 100 | MUST-HAVE |
| CALC-7 | operating_expense_ratio | OpEx / Revenue × 100 | MUST-HAVE |
| CALC-8 | net_income_margin | Net Income / Revenue × 100 | MUST-HAVE |
| CALC-9 | cash_conversion_ratio | Operating Cash Flow / Net Income | MUST-HAVE |
| CALC-10 | capex_ratio | Annual CapEx / Annual Revenue × 100 | MUST-HAVE |

#### Collection Metrics
| CALC-11 | days_sales_outstanding | (A/R / Monthly Revenue) × 30 | MUST-HAVE |
| CALC-12 | collection_effectiveness | Cash Collected / Revenue Recognized | MUST-HAVE |
| CALC-13 | ar_turnover | Annual Revenue / Average A/R | NICE-TO-HAVE |

#### Property Performance
| CALC-14 | revenue_per_sf | Annual Revenue / Total SF | MUST-HAVE |
| CALC-15 | noi_per_sf | Annual NOI / Total SF | MUST-HAVE |
| CALC-16 | effective_rent_per_sf | (Base Rent + Recoveries) / Total SF | NICE-TO-HAVE |
| CALC-17 | occupancy_percentage | Occupied SF / Total SF × 100 | MUST-HAVE |
| CALC-18 | economic_occupancy | Collected Rent / Potential Rent × 100 | NICE-TO-HAVE |

#### Tenant Metrics
| CALC-19 | tenant_concentration_top5 | Sum(Top 5 Tenant Rents) / Total Rent × 100 | MUST-HAVE |
| CALC-20 | weighted_avg_lease_term | Σ(Remaining Term × Rent) / Total Rent | NICE-TO-HAVE |

**SQL Implementation for calculated_rules table:**
```sql
CREATE TABLE IF NOT EXISTS calculated_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) UNIQUE NOT NULL,
    rule_description TEXT NOT NULL,
    calculation_formula TEXT NOT NULL,
    result_type VARCHAR(50), -- 'ratio', 'percentage', 'currency', 'days'
    benchmark_min DECIMAL(15,4),
    benchmark_max DECIMAL(15,4),
    benchmark_source VARCHAR(100), -- 'industry', 'property_type', 'custom'
    severity VARCHAR(20) DEFAULT 'warning',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Example insert
INSERT INTO calculated_rules (
    rule_name,
    rule_description,
    calculation_formula,
    result_type,
    benchmark_min,
    benchmark_max,
    benchmark_source,
    severity
) VALUES (
    'dscr_calculation',
    'Debt Service Coverage Ratio - must be ≥1.25 for covenant compliance',
    'noi_annual / (principal_payments_annual + interest_payments_annual)',
    'ratio',
    1.25,
    999.99,
    'lender_covenant',
    'error'
);
```

---

## PART 9: ALERT RULES (Currently Empty Table)

### Alert Rules Needed (15+ rules)

#### Critical Financial Alerts
| Alert ID | Alert Name | Trigger Condition | Criticality |
|----------|-----------|-------------------|-------------|
| ALT-1 | balance_sheet_out_of_balance | Assets ≠ Liabilities + Equity | CRITICAL |
| ALT-2 | negative_cash_balance | Any cash account < 0 | CRITICAL |
| ALT-3 | dscr_below_covenant | DSCR < 1.25 | CRITICAL |
| ALT-4 | cash_runway_low | <3 months runway if negative CF | CRITICAL |
| ALT-5 | major_tenant_default | Tenant >10% rent > 60 days past due | CRITICAL |

#### Warning Alerts
| ALT-6 | dso_increasing | DSO increased >10 days month-over-month | WARNING |
| ALT-7 | vacancy_increasing | Occupancy decreased >5% | WARNING |
| ALT-8 | noi_margin_declining | NOI margin decreased >5% YoY | WARNING |
| ALT-9 | capex_exceeds_threshold | CapEx >10% of revenue in period | WARNING |
| ALT-10 | lease_expiration_imminent | >25% rent expires in 12 months | WARNING |

#### Data Quality Alerts
| ALT-11 | missing_documents | Document completeness <95% | WARNING |
| ALT-12 | validation_failures | >5 validation rule failures | WARNING |
| ALT-13 | extraction_low_confidence | Extraction confidence <80% | WARNING |
| ALT-14 | reconciliation_variance | Cross-statement variance >5% | WARNING |
| ALT-15 | anomaly_detected | Statistical anomaly in any metric | WARNING |

**SQL Implementation for alert_rules table:**
```sql
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    alert_name VARCHAR(100) UNIQUE NOT NULL,
    alert_description TEXT NOT NULL,
    trigger_condition TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL, -- 'critical', 'warning', 'info'
    notification_method VARCHAR(50), -- 'email', 'dashboard', 'sms'
    notification_recipients TEXT, -- JSON array of user IDs/emails
    auto_escalate BOOLEAN DEFAULT false,
    escalation_delay_hours INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Example insert
INSERT INTO alert_rules (
    alert_name,
    alert_description,
    trigger_condition,
    severity,
    notification_method,
    auto_escalate,
    escalation_delay_hours
) VALUES (
    'balance_sheet_out_of_balance',
    'CRITICAL: Balance Sheet does not balance',
    'ABS(total_assets - (total_liabilities + total_equity)) > 0.01',
    'critical',
    'email,dashboard',
    true,
    1
);
```

---

## PART 10: IMPLEMENTATION PRIORITIES

### Phase 1: Critical Must-Have Rules (First 30 Days)
**Goal:** Ensure mathematical integrity and basic cross-statement reconciliation

1. **Balance Sheet** (10 rules)
   - BS-33: Current Period Earnings accumulation
   - BS-34: Total Capital calculation
   - BS-8: Buildings depreciation monthly
   - BS-9: 15-year improvements depreciation
   - BS-16: Loan costs amortization
   - BS-28: Property tax payable accumulation
   - BS-4: A/R Trade monthly pattern
   - BS-5: A/R Tenants trend
   - BS-30: Partners contribution constant
   - BS-31: Beginning equity constant

2. **Income Statement** (8 rules)
   - IS-1: Income statement equation
   - IS-2: YTD calculation formula
   - IS-4: Total income composition
   - IS-12: Off-site management 4%
   - IS-13: Asset management 1%
   - IS-17: Mortgage interest decreases
   - IS-20: Operating expense ratio
   - IS-21: NOI margin

3. **Cash Flow** (5 rules)
   - CF-7: Non-cash expenses add-back
   - CF-8A: Current assets sign convention
   - CF-9A: Current liabilities sign convention
   - CF-12: Fixed asset additions
   - CF-14: Mortgage principal payments

4. **Rent Roll** (4 rules)
   - RR-1: Total property composition
   - RR-2: Occupancy rate calculation
   - RR-3: Annual rent calculation
   - RR-IS-1: Monthly rent to base rentals

5. **Mortgage Statement** (6 rules)
   - MS-1: Principal balance reduction
   - MS-7: Principal balance to BS
   - MS-8: Total payment composition
   - MS-9: Constant monthly payment
   - MS-4: Insurance escrow balance
   - MS-5: Tax escrow balance

6. **Cross-Document** (7 rules)
   - IS-BS-2: Current period earnings = YTD
   - IS-BS-3: Depreciation 3-way
   - IS-BS-4: Amortization 3-way
   - RECON-1: Wells Fargo balance match
   - RECON-2: Escrow tax match
   - RECON-3: Escrow insurance match
   - CF-IS-3: Depreciation add-back

**Total Phase 1: 40 critical rules**

### Phase 2: Important Nice-to-Have Rules (Days 31-60)

1. **Calculated Rules** (10 rules)
   - CALC-1 through CALC-10: All financial ratios

2. **Alert Rules** (10 rules)
   - ALT-1 through ALT-10: Critical and warning alerts

3. **Forensic - Document Quality** (5 rules)
   - A-1.1 through A-1.5: Document completeness

4. **Forensic - Collections** (5 rules)
   - A-5.1, A-5.2, A-5.4, A-5.7: A/R aging and DSO

5. **Forensic - Debt Service** (5 rules)
   - A-7.1 through A-7.5: DSCR, LTV, liquidity ratios

**Total Phase 2: 35 rules**

### Phase 3: Advanced Forensic Rules (Days 61-90)

1. **Fraud Detection** (15 rules)
   - A-6.1 through A-6.8: Benford's Law, duplicates, variances

2. **Performance Metrics** (6 rules)
   - A-8.1 through A-8.6: Growth, margins, efficiency

3. **Tenant Analysis** (7 rules)
   - A-4.4 through A-4.7: Concentration, expirations, vacancy

4. **Materiality Framework** (8 rules)
   - A-10.1 through A-10.8: Threshold management

**Total Phase 3: 36 rules**

### Phase 4: Enhancement & Automation (Days 91-120)

1. **Auto-Resolution Rules** (10 rules)
   - Common correction patterns
   - Data entry validations
   - Automatic reconciliations

2. **Prevention Rules** (10 rules)
   - Pre-upload validation
   - Real-time data entry checks
   - Template compliance

3. **Advanced Calculations** (10 rules)
   - Weighted metrics
   - Trend analysis
   - Predictive indicators

**Total Phase 4: 30 rules**

---

## PART 11: SQL IMPLEMENTATION SCRIPTS

### Create Missing Tables

```sql
-- 1. Calculated Rules Table
CREATE TABLE IF NOT EXISTS calculated_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) UNIQUE NOT NULL,
    rule_description TEXT NOT NULL,
    calculation_formula TEXT NOT NULL,
    result_type VARCHAR(50) NOT NULL,
    benchmark_min DECIMAL(15,4),
    benchmark_max DECIMAL(15,4),
    benchmark_source VARCHAR(100),
    severity VARCHAR(20) DEFAULT 'warning',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Alert Rules Table
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    alert_name VARCHAR(100) UNIQUE NOT NULL,
    alert_description TEXT NOT NULL,
    trigger_condition TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    notification_method VARCHAR(50),
    notification_recipients TEXT,
    auto_escalate BOOLEAN DEFAULT false,
    escalation_delay_hours INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Materiality Configs Table
CREATE TABLE IF NOT EXISTS materiality_configs (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id),
    config_name VARCHAR(100) NOT NULL,
    config_description TEXT,
    base_metric VARCHAR(50) NOT NULL, -- 'total_assets', 'net_income', 'revenue'
    percentage DECIMAL(5,2) NOT NULL,
    minimum_amount DECIMAL(15,2),
    maximum_amount DECIMAL(15,2),
    applies_to VARCHAR(50), -- 'overall', 'line_item', 'fraud'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Auto Resolution Rules Table
CREATE TABLE IF NOT EXISTS auto_resolution_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) UNIQUE NOT NULL,
    rule_description TEXT NOT NULL,
    error_pattern TEXT NOT NULL,
    resolution_action TEXT NOT NULL,
    requires_approval BOOLEAN DEFAULT false,
    auto_execute BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Prevention Rules Table
CREATE TABLE IF NOT EXISTS prevention_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) UNIQUE NOT NULL,
    rule_description TEXT NOT NULL,
    validation_stage VARCHAR(50) NOT NULL, -- 'pre_upload', 'extraction', 'data_entry'
    validation_formula TEXT NOT NULL,
    block_on_failure BOOLEAN DEFAULT false,
    severity VARCHAR(20) DEFAULT 'warning',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Rule Execution Log Table
CREATE TABLE IF NOT EXISTS rule_execution_log (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER,
    rule_type VARCHAR(50) NOT NULL, -- 'validation', 'calculated', 'alert'
    execution_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    property_id INTEGER REFERENCES properties(id),
    period_id INTEGER REFERENCES financial_periods(id),
    status VARCHAR(20) NOT NULL, -- 'pass', 'fail', 'warning', 'error'
    result_value DECIMAL(15,4),
    expected_value DECIMAL(15,4),
    variance DECIMAL(15,4),
    variance_percentage DECIMAL(8,4),
    error_message TEXT,
    details JSONB
);

CREATE INDEX idx_rule_execution_property ON rule_execution_log(property_id, execution_timestamp);
CREATE INDEX idx_rule_execution_status ON rule_execution_log(status);

-- 7. Enhance validation_rules table with additional fields
ALTER TABLE validation_rules ADD COLUMN IF NOT EXISTS tolerance_percentage DECIMAL(5,2);
ALTER TABLE validation_rules ADD COLUMN IF NOT EXISTS tolerance_absolute DECIMAL(15,2);
ALTER TABLE validation_rules ADD COLUMN IF NOT EXISTS applies_to_document_types TEXT[];
ALTER TABLE validation_rules ADD COLUMN IF NOT EXISTS requires_cross_period BOOLEAN DEFAULT false;
ALTER TABLE validation_rules ADD COLUMN IF NOT EXISTS execution_order INTEGER;
ALTER TABLE validation_rules ADD COLUMN IF NOT EXISTS parent_rule_id INTEGER;
```

### Seed Phase 1 Critical Rules

```sql
-- Balance Sheet Rules Phase 1
INSERT INTO validation_rules (
    rule_name, rule_description, document_type, rule_type,
    rule_formula, error_message, severity, tolerance_percentage, is_active
) VALUES
-- BS-33
('bs_current_period_earnings_accumulation',
 'Current Period Earnings equals cumulative YTD Net Income from Income Statement',
 'balance_sheet', 'cross_statement_check',
 'current_period_earnings_bs = ytd_net_income_is',
 'Current Period Earnings on Balance Sheet does not match YTD Net Income',
 'error', 0.1, true),

-- BS-34
('bs_total_capital_calculation',
 'Total Capital = Partners Contribution + Beginning Equity - Distributions + Current Period Earnings',
 'balance_sheet', 'balance_check',
 'total_capital = partners_contribution + beginning_equity - distributions + current_period_earnings',
 'Total Capital calculation is incorrect',
 'error', 0.01, true),

-- BS-8
('bs_buildings_depreciation_monthly',
 'Buildings depreciation should be consistent monthly (approximately $46,822/month)',
 'balance_sheet', 'sequential_check',
 'accum_depr_buildings_change ≈ -46822 per month',
 'Buildings depreciation pattern is inconsistent',
 'warning', 5.0, true),

-- BS-9
('bs_15yr_improvements_depreciation_monthly',
 '15-year improvements depreciation should be consistent (approximately $17,905/month)',
 'balance_sheet', 'sequential_check',
 'accum_depr_15yr_change ≈ -17905 per month',
 '15-year improvements depreciation pattern is inconsistent',
 'warning', 5.0, true),

-- BS-16
('bs_loan_costs_amortization_monthly',
 'Loan costs should amortize consistently (approximately $2,239/month)',
 'balance_sheet', 'sequential_check',
 'accum_amort_loan_costs_change ≈ -2239 per month',
 'Loan costs amortization pattern is inconsistent',
 'warning', 5.0, true);

-- Income Statement Rules Phase 1
INSERT INTO validation_rules (
    rule_name, rule_description, document_type, rule_type,
    rule_formula, error_message, severity, tolerance_percentage, is_active
) VALUES
-- IS-12
('is_offsite_management_fee_4pct',
 'Off-Site Management Fee should be 4.00% of Total Income',
 'income_statement', 'percentage_check',
 'offsite_management_fee / total_income = 0.04',
 'Off-Site Management Fee is not 4% of Total Income',
 'warning', 0.5, true),

-- IS-13
('is_asset_management_fee_1pct',
 'Asset Management Fee should be 1.00% of Total Income',
 'income_statement', 'percentage_check',
 'asset_management_fee / total_income = 0.01',
 'Asset Management Fee is not 1% of Total Income',
 'warning', 0.5, true),

-- IS-20
('is_operating_expense_ratio',
 'Operating Expense Ratio = Operating Expenses / Total Income (should be 30-50%)',
 'income_statement', 'ratio_check',
 '0.30 <= (operating_expenses / total_income) <= 0.50',
 'Operating Expense Ratio is outside normal range',
 'warning', NULL, true),

-- IS-21
('is_noi_margin',
 'NOI Margin = NOI / Total Income (should be 50-70%)',
 'income_statement', 'ratio_check',
 '0.50 <= (noi / total_income) <= 0.70',
 'NOI Margin is outside normal range',
 'warning', NULL, true);

-- Rent Roll Rules Phase 1
INSERT INTO validation_rules (
    rule_name, rule_description, document_type, rule_type,
    rule_formula, error_message, severity, tolerance_percentage, is_active
) VALUES
-- RR-1
('rr_total_property_composition',
 'Total Area = Occupied Area + Vacant Area (must remain constant)',
 'rent_roll', 'balance_check',
 'total_area_sqft = occupied_area_sqft + vacant_area_sqft',
 'Total property area does not equal occupied plus vacant',
 'error', 0.01, true),

-- RR-2
('rr_occupancy_rate_calculation',
 'Occupancy Rate = (Occupied Area / Total Area) × 100',
 'rent_roll', 'balance_check',
 'occupancy_rate = (occupied_area_sqft / total_area_sqft) * 100',
 'Occupancy rate calculation is incorrect',
 'error', 0.1, true),

-- RR-3
('rr_annual_rent_calculation',
 'Annual Rent = Monthly Rent × 12',
 'rent_roll', 'balance_check',
 'annual_rent = monthly_rent * 12',
 'Annual rent calculation is incorrect',
 'error', 0.01, true),

-- RR-IS-1
('rr_monthly_rent_to_is_base_rentals',
 'Rent Roll Monthly Rent should approximate IS Base Rentals (adjusted for period)',
 'rent_roll', 'cross_statement_check',
 'ABS((monthly_rent_rr * period_months) - base_rentals_is) / base_rentals_is <= 0.05',
 'Rent Roll monthly rent does not reconcile with Income Statement base rentals',
 'warning', 5.0, true);

-- Mortgage Statement Rules Phase 1
INSERT INTO validation_rules (
    rule_name, rule_description, document_type, rule_type,
    rule_formula, error_message, severity, tolerance_percentage, is_active
) VALUES
-- MS-1
('ms_principal_balance_reduction',
 'Next month principal balance = Current balance - Current principal due',
 'mortgage_statement', 'sequential_check',
 'principal_balance_next = principal_balance_current - principal_due_current',
 'Principal balance reduction calculation is incorrect',
 'error', 0.01, true),

-- MS-7
('ms_principal_balance_to_bs',
 'Mortgage Statement Principal Balance = Balance Sheet Mortgage Liability',
 'mortgage_statement', 'cross_statement_check',
 'principal_balance_ms = mortgage_liability_bs',
 'Mortgage principal balance does not match Balance Sheet liability',
 'error', 0.01, true),

-- MS-8
('ms_total_payment_composition',
 'Total Payment = Principal + Interest + Tax Escrow + Insurance Escrow + Reserves',
 'mortgage_statement', 'balance_check',
 'total_payment = principal_due + interest_due + tax_due + insurance_due + reserves_due',
 'Total payment composition is incorrect',
 'error', 0.01, true);
```

### Seed Calculated Rules Phase 2

```sql
INSERT INTO calculated_rules (
    rule_name, rule_description, calculation_formula,
    result_type, benchmark_min, benchmark_max, benchmark_source, severity
) VALUES
-- Financial Ratios
('calc_current_ratio',
 'Current Ratio = Current Assets / Current Liabilities (should be ≥2.0)',
 'current_assets / current_liabilities',
 'ratio', 2.0, 999.99, 'industry', 'warning'),

('calc_quick_ratio',
 'Quick Ratio = (Cash + A/R) / Current Liabilities (should be ≥1.0)',
 '(cash + ar_tenants) / current_liabilities',
 'ratio', 1.0, 999.99, 'industry', 'warning'),

('calc_dscr',
 'Debt Service Coverage Ratio = NOI / Annual Debt Service (must be ≥1.25)',
 'noi_annual / (principal_annual + interest_annual)',
 'ratio', 1.25, 999.99, 'lender_covenant', 'error'),

('calc_ltv_ratio',
 'Loan-to-Value Ratio = Mortgage Balance / Property Value (should be ≤75%)',
 'mortgage_balance / property_value * 100',
 'percentage', 0.0, 75.0, 'lender_covenant', 'warning'),

('calc_noi_margin',
 'NOI Margin = NOI / Total Revenue × 100 (benchmarks vary by property type)',
 'noi / total_revenue * 100',
 'percentage', 50.0, 70.0, 'property_type', 'info'),

('calc_dso',
 'Days Sales Outstanding = (A/R / Monthly Revenue) × 30 (should be <30 days)',
 '(ar_tenants / monthly_revenue) * 30',
 'days', 0.0, 30.0, 'industry', 'warning'),

('calc_cash_conversion_ratio',
 'Cash Conversion Ratio = Operating Cash Flow / Net Income (normal 0.9-1.2)',
 'operating_cash_flow / net_income',
 'ratio', 0.9, 1.2, 'industry', 'info');
```

### Seed Alert Rules Phase 2

```sql
INSERT INTO alert_rules (
    alert_name, alert_description, trigger_condition,
    severity, notification_method, auto_escalate, escalation_delay_hours
) VALUES
-- Critical Alerts
('alert_balance_sheet_out_of_balance',
 'CRITICAL: Balance Sheet does not balance',
 'ABS(total_assets - (total_liabilities + total_equity)) > 0.01',
 'critical', 'email,dashboard', true, 1),

('alert_negative_cash',
 'CRITICAL: Negative cash balance detected',
 'total_cash < 0',
 'critical', 'email,dashboard', true, 1),

('alert_dscr_below_covenant',
 'CRITICAL: DSCR below lender covenant requirement',
 'dscr < 1.25',
 'critical', 'email,dashboard', true, 2),

('alert_cash_runway_critical',
 'CRITICAL: Less than 3 months cash runway',
 'cash_runway_months < 3',
 'critical', 'email,dashboard', true, 4),

-- Warning Alerts
('alert_dso_increasing',
 'WARNING: Days Sales Outstanding increased significantly',
 'dso_current - dso_prior > 10',
 'warning', 'dashboard', false, NULL),

('alert_vacancy_increasing',
 'WARNING: Occupancy decreased significantly',
 'occupancy_current - occupancy_prior < -5',
 'warning', 'dashboard', false, NULL),

('alert_validation_failures',
 'WARNING: Multiple validation rule failures',
 'validation_failure_count > 5',
 'warning', 'email,dashboard', false, NULL);
```

---

## PART 12: TESTING & VALIDATION PLAN

### Unit Testing Requirements

For each implemented rule:

1. **Positive Test**: Rule passes with valid data
2. **Negative Test**: Rule fails with invalid data
3. **Edge Case Test**: Rule handles boundary conditions
4. **Performance Test**: Rule executes within acceptable time

Example test cases:

```sql
-- Test BS-33: Current Period Earnings Accumulation
-- Positive Test
WITH test_data AS (
    SELECT
        1000000.00 AS current_period_earnings_bs,
        1000000.00 AS ytd_net_income_is
)
SELECT
    'BS-33 Positive Test' AS test_name,
    ABS(current_period_earnings_bs - ytd_net_income_is) <= 1000 AS passed
FROM test_data;

-- Negative Test
WITH test_data AS (
    SELECT
        1000000.00 AS current_period_earnings_bs,
        950000.00 AS ytd_net_income_is
)
SELECT
    'BS-33 Negative Test' AS test_name,
    ABS(current_period_earnings_bs - ytd_net_income_is) > 1000 AS passed
FROM test_data;
```

### Integration Testing

Test cross-statement rules with actual data:

```sql
-- Integration Test: Depreciation 3-Way Reconciliation
SELECT
    p.property_name,
    fp.period_year,
    fp.period_month,
    -- Income Statement
    is_depr.period_amount AS depreciation_is,
    -- Balance Sheet
    bs_depr_current.amount - bs_depr_prior.amount AS depreciation_bs_change,
    -- Cash Flow
    cf_depr.period_amount AS depreciation_cf_addback,
    -- Validation
    CASE
        WHEN ABS(is_depr.period_amount - (bs_depr_current.amount - bs_depr_prior.amount)) <= 100
         AND ABS(is_depr.period_amount - cf_depr.period_amount) <= 100
        THEN 'PASS'
        ELSE 'FAIL'
    END AS test_result
FROM properties p
JOIN financial_periods fp ON p.id = fp.property_id
JOIN income_statement_data is_depr ON fp.id = is_depr.period_id
    AND is_depr.account_code = 'DEPR'
JOIN balance_sheet_data bs_depr_current ON fp.id = bs_depr_current.period_id
    AND bs_depr_current.account_code = 'ACCUM_DEPR'
-- Add joins for prior period and cash flow
WHERE p.property_code = 'ESP001'
  AND fp.period_year = 2025
  AND fp.period_month = 9;
```

---

## PART 13: PRIORITIZATION MATRIX

### Criticality Scoring

Rules are scored on three dimensions:

1. **Financial Impact** (1-10)
   - 10 = Affects bottom line, equity, or covenant compliance
   - 5 = Affects operating metrics
   - 1 = Informational only

2. **Fraud Risk** (1-10)
   - 10 = High fraud detection/prevention value
   - 5 = Moderate fraud indicator
   - 1 = Low fraud risk

3. **Implementation Complexity** (1-10)
   - 10 = Very complex (multiple cross-statement dependencies)
   - 5 = Moderate (single statement with calculations)
   - 1 = Simple (direct comparison)

### Top 50 Rules by Priority Score

| Rank | Rule ID | Rule Name | Financial | Fraud | Complexity | Total | Status |
|------|---------|-----------|-----------|-------|------------|-------|--------|
| 1 | BS-1 | balance_sheet_equation | 10 | 10 | 1 | 21 | ✓ IMPLEMENTED |
| 2 | IS-BS-2 | current_period_earnings_ytd | 10 | 8 | 3 | 21 | ✗ MISSING |
| 3 | IS-BS-3 | depreciation_3way | 10 | 7 | 5 | 22 | ✗ MISSING |
| 4 | RECON-1 | wells_fargo_balance_match | 10 | 8 | 2 | 20 | ✗ MISSING |
| 5 | MS-1 | principal_balance_reduction | 10 | 8 | 3 | 21 | ✗ MISSING |
| 6 | CALC-3 | dscr_calculation | 10 | 5 | 4 | 19 | ✗ MISSING |
| 7 | A-6.1 | benfords_law_analysis | 5 | 10 | 6 | 21 | ✗ MISSING |
| 8 | A-6.2 | round_number_analysis | 5 | 10 | 3 | 18 | ✗ MISSING |
| 9 | A-5.1 | ar_aging_analysis | 8 | 7 | 4 | 19 | ✗ MISSING |
| 10 | IS-12 | offsite_management_4pct | 8 | 6 | 2 | 16 | ✗ MISSING |
| 11 | RR-IS-1 | monthly_rent_to_base_rentals | 9 | 7 | 4 | 20 | ✗ MISSING |
| 12 | BS-33 | current_period_earnings_accum | 10 | 6 | 3 | 19 | ✗ MISSING |
| 13 | ALT-1 | balance_sheet_out_of_balance | 10 | 8 | 2 | 20 | ✗ MISSING |
| 14 | ALT-3 | dscr_below_covenant | 10 | 5 | 3 | 18 | ✗ MISSING |
| 15 | A-4.4 | tenant_concentration_risk | 8 | 6 | 3 | 17 | ✗ MISSING |

*(Full matrix continues...)*

---

## PART 14: IMPLEMENTATION ROADMAP

### Quarter 1 (Months 1-3): Foundation
**Goal:** Implement 40 critical must-have rules

**Month 1:**
- Set up missing database tables
- Implement 15 Balance Sheet rules
- Implement 10 Income Statement rules
- Create rule execution framework
- Build testing suite

**Month 2:**
- Implement 5 Cash Flow rules
- Implement 4 Rent Roll rules
- Implement 6 Mortgage Statement rules
- Develop cross-statement reconciliation engine

**Month 3:**
- Implement 7 cross-document rules
- Complete Phase 1 testing
- Deploy to production
- Train users on new validation reports

### Quarter 2 (Months 4-6): Enhancement
**Goal:** Add calculated rules and alerting

**Month 4:**
- Implement 10 calculated rules (ratios)
- Build calculation engine
- Create ratio dashboard

**Month 5:**
- Implement 10 alert rules
- Build notification system
- Configure alert workflows

**Month 6:**
- Add 5 document completeness rules
- Add 5 A/R aging rules
- Add 5 debt service rules
- Q2 testing and deployment

### Quarter 3 (Months 7-9): Advanced Features
**Goal:** Forensic audit and fraud detection

**Month 7:**
- Implement Benford's Law analysis
- Implement round number detection
- Implement duplicate payment detection

**Month 8:**
- Add variance analysis
- Add related party detection
- Add sequential gap analysis

**Month 9:**
- Performance metrics implementation
- Tenant analysis rules
- Materiality framework
- Q3 testing and deployment

### Quarter 4 (Months 10-12): Automation
**Goal:** Auto-resolution and prevention

**Month 10:**
- Implement auto-resolution rules
- Build correction workflows
- Add approval mechanisms

**Month 11:**
- Implement prevention rules
- Add pre-upload validation
- Real-time data entry checks

**Month 12:**
- Advanced calculations
- Trend analysis
- Predictive indicators
- Year-end testing and optimization

---

## PART 15: MONITORING & REPORTING

### KPIs for Rule Implementation

Track these metrics monthly:

1. **Coverage Metrics**
   - Rules implemented vs documented: Currently 34/214 (16%)
   - Target Month 3: 74/214 (35%)
   - Target Month 6: 109/214 (51%)
   - Target Month 12: 214/214 (100%)

2. **Execution Metrics**
   - Average rule execution time
   - Rules passing vs failing
   - Most frequently failing rules
   - Alert generation rate

3. **Data Quality Metrics**
   - Document completeness %
   - Extraction confidence average
   - Cross-statement reconciliation %
   - Anomaly detection rate

4. **Business Impact**
   - Errors caught before reporting
   - Time saved in manual review
   - Covenant compliance tracking
   - Fraud incidents detected

### Dashboard Requirements

Executive dashboard should show:

1. **Overall Health Score** (0-100)
   - Mathematical integrity: XX%
   - Cross-statement reconciliation: XX%
   - Data completeness: XX%
   - Anomaly-free score: XX%

2. **Top 10 Issues**
   - Ranked by financial impact
   - Status: Open/In Progress/Resolved
   - Assigned owner
   - Days open

3. **Trend Charts**
   - Rules passing over time
   - Data quality improving
   - Processing time decreasing
   - Coverage expanding

4. **Property Comparison**
   - Score by property
   - Benchmark against portfolio avg
   - Identify outliers

---

## APPENDIX A: COMPLETE RULE CATALOG

### All 214+ Documented Rules

| Category | Subcategory | Count | Implemented | Missing | Priority |
|----------|-------------|-------|-------------|---------|----------|
| Balance Sheet | Fundamental | 5 | 5 | 0 | ✓ Complete |
| Balance Sheet | Constants | 10 | 0 | 10 | High |
| Balance Sheet | Monthly Patterns | 12 | 0 | 12 | High |
| Balance Sheet | Capital & Equity | 8 | 0 | 8 | High |
| Income Statement | Fundamental | 6 | 6 | 0 | ✓ Complete |
| Income Statement | Structure | 3 | 0 | 3 | High |
| Income Statement | Revenue | 5 | 1 | 4 | High |
| Income Statement | Expenses | 6 | 1 | 5 | Medium |
| Income Statement | Metrics | 7 | 0 | 7 | Medium |
| Cash Flow | Fundamental | 14 | 14 | 0 | ✓ Complete |
| Cash Flow | Adjustments | 3 | 0 | 3 | High |
| Cash Flow | Sign Conventions | 2 | 0 | 2 | High |
| Cash Flow | CapEx | 2 | 0 | 2 | High |
| Cash Flow | Escrow & Debt | 2 | 0 | 2 | High |
| Rent Roll | Fundamental | 4 | 4 | 0 | ✓ Complete |
| Rent Roll | Calculations | 4 | 0 | 4 | High |
| Rent Roll | Cross-Statement | 3 | 0 | 3 | High |
| Mortgage | Principal | 3 | 0 | 3 | High |
| Mortgage | Payment | 4 | 0 | 4 | High |
| Mortgage | Escrow | 3 | 0 | 3 | High |
| Mortgage | Other | 4 | 0 | 4 | Medium |
| Cross-Document | IS-BS | 7 | 1 | 6 | High |
| Cross-Document | BS-MS | 5 | 0 | 5 | High |
| Cross-Document | CF-IS | 5 | 1 | 4 | High |
| Forensic | Document Quality | 5 | 0 | 5 | Medium |
| Forensic | Collections | 8 | 0 | 8 | Medium |
| Forensic | Fraud Detection | 15 | 0 | 15 | Medium |
| Forensic | Debt Service | 8 | 0 | 8 | High |
| Forensic | Performance | 6 | 0 | 6 | Low |
| Forensic | Materiality | 8 | 1 | 7 | Medium |
| Calculated | Financial Ratios | 10 | 0 | 10 | High |
| Calculated | Collections | 3 | 0 | 3 | Medium |
| Calculated | Property Perf | 5 | 0 | 5 | Medium |
| Calculated | Tenant Metrics | 2 | 0 | 2 | Low |
| Alerts | Critical | 5 | 0 | 5 | High |
| Alerts | Warning | 5 | 0 | 5 | Medium |
| Alerts | Data Quality | 5 | 0 | 5 | Medium |
| **TOTAL** | | **214** | **34** | **180** | |

---

## APPENDIX B: SAMPLE OUTPUT FORMATS

### Validation Report Format

```
VALIDATION REPORT
Property: Eastern Shore Plaza (ESP001)
Period: October 2025
Generated: 2025-12-28 10:30:45

═══════════════════════════════════════════════════════════════

OVERALL SCORE: 87/100 (GOOD)

Mathematical Integrity:     100% ✓ (35/35 rules passed)
Cross-Statement Recon:       85% ⚠ (17/20 rules passed)
Data Quality:                90% ✓ (27/30 rules passed)
Forensic Indicators:         75% ⚠ (60/80 rules passed)

═══════════════════════════════════════════════════════════════

CRITICAL ISSUES (Must Fix): 0

═══════════════════════════════════════════════════════════════

WARNING ISSUES (Should Fix): 3

1. OFF-SITE MANAGEMENT FEE VARIANCE
   Rule: IS-12 (offsite_management_fee_4pct)
   Expected: $22,657.67 (4.00% of Total Income)
   Actual: $23,100.00
   Variance: $442.33 (1.95%)
   Status: Warning
   Recommendation: Verify fee calculation or document variance

2. DEPRECIATION 3-WAY RECONCILIATION
   Rule: IS-BS-3 (depreciation_3way)
   IS Depreciation: $64,812.62
   BS Change: $64,812.62 ✓
   CF Add-Back: $64,727.14
   Variance: $85.48
   Status: Warning (within tolerance)
   Recommendation: Review minor variance

3. DAYS SALES OUTSTANDING INCREASE
   Rule: A-5.1 (ar_aging_analysis)
   Prior DSO: 26 days
   Current DSO: 29 days
   Change: +3 days
   Status: Warning
   Recommendation: Monitor collections closely

═══════════════════════════════════════════════════════════════

INFORMATIONAL: 5 items
[Details...]

═══════════════════════════════════════════════════════════════
```

---

## CONCLUSION

This gap analysis reveals:

1. **Only 16% of documented audit rules are implemented** in the REIMS2 database
2. **180+ rules are missing**, including critical cross-statement reconciliation and forensic audit capabilities
3. **5 database tables are empty** that should contain important rule configurations
4. **A phased 12-month implementation plan** can close this gap systematically

### Immediate Actions Required

1. **Week 1:** Review and approve this gap analysis
2. **Week 2:** Prioritize Phase 1 rules (40 critical rules)
3. **Week 3:** Create missing database tables
4. **Week 4:** Begin Phase 1 implementation

### Expected Benefits

After full implementation:
- **99%+ mathematical accuracy** in financial statements
- **Automated cross-statement reconciliation** across all documents
- **Real-time fraud detection** using forensic audit techniques
- **Proactive alerting** for covenant compliance and financial risks
- **Comprehensive audit trail** for all validation checks
- **Reduced manual review time** by 60-80%

### Risk of Not Implementing

Without these rules:
- Financial errors may go undetected
- Covenant violations may occur without warning
- Fraud schemes may not be caught
- Manual review remains time-intensive and error-prone
- Audit costs remain high
- Regulatory compliance at risk

---

**Document Version:** 1.0
**Created:** 2025-12-28
**Next Review:** 2026-01-28
**Owner:** REIMS2 Development Team
