-- Validation Rules Seed Data for Mortgage Statements
-- Comprehensive business logic validation rules for mortgage statements

-- Clear existing mortgage rules (idempotent)
DELETE FROM validation_rules WHERE document_type = 'mortgage_statement';

-- Mortgage Statement Validation Rules (10 rules)
INSERT INTO validation_rules (
    rule_name,
    rule_description,
    document_type,
    rule_type,
    rule_formula,
    error_message,
    severity,
    is_active
) VALUES

-- 1. Principal Balance Reasonableness
(
    'mortgage_principal_reasonable',
    'Principal balance should be positive and less than $100M',
    'mortgage_statement',
    'range_check',
    'principal_balance > 0 AND principal_balance < 100000000',
    'Principal balance is outside reasonable range',
    'warning',
    TRUE
),

-- 2. Payment Calculation
(
    'mortgage_payment_calculation',
    'Total payment = Principal + Interest + Escrow + Fees',
    'mortgage_statement',
    'balance_check',
    'total_payment_due = principal_due + interest_due + tax_escrow_due + insurance_escrow_due + reserve_due + late_fees + other_fees',
    'Payment breakdown does not sum to total payment due (tolerance: $1)',
    'error',
    TRUE
),

-- 3. Escrow Balance Total
(
    'mortgage_escrow_total',
    'Total escrow = Tax + Insurance + Reserve + Other escrows',
    'mortgage_statement',
    'balance_check',
    'total_loan_balance = principal_balance + tax_escrow_balance + insurance_escrow_balance + reserve_balance + other_escrow_balance',
    'Escrow balances do not sum correctly',
    'warning',
    TRUE
),

-- 4. Interest Rate Range
(
    'mortgage_interest_rate_range',
    'Interest rate should be between 0% and 20%',
    'mortgage_statement',
    'range_check',
    'interest_rate >= 0 AND interest_rate <= 20',
    'Interest rate is outside normal commercial mortgage range',
    'warning',
    TRUE
),

-- 5. YTD Totals
(
    'mortgage_ytd_total',
    'YTD total paid = YTD principal + YTD interest',
    'mortgage_statement',
    'balance_check',
    'ytd_total_paid = ytd_principal_paid + ytd_interest_paid',
    'YTD payment totals do not match',
    'warning',
    TRUE
),

-- 6. Principal Reduction Check (Cross-Period)
(
    'mortgage_principal_reduction',
    'Principal paid should reduce principal balance month-over-month',
    'mortgage_statement',
    'cross_period_check',
    'current_principal_balance < prior_principal_balance OR period_number = 1',
    'Principal balance increased unexpectedly (check for refinancing)',
    'info',
    TRUE
),

-- 7. DSCR Minimum Threshold
(
    'mortgage_dscr_minimum',
    'DSCR should be >= 1.20 for healthy debt coverage',
    'mortgage_statement',
    'range_check',
    'dscr >= 1.20',
    'DSCR below 1.20 - potential covenant violation',
    'warning',
    TRUE
),

-- 8. LTV Maximum Threshold
(
    'mortgage_ltv_maximum',
    'LTV should not exceed 80% for commercial properties',
    'mortgage_statement',
    'range_check',
    'ltv_ratio <= 0.80',
    'LTV exceeds 80% - monitor closely',
    'warning',
    TRUE
),

-- 9. Cross-Document Validation: Balance Sheet Long-Term Debt
(
    'mortgage_balance_sheet_reconciliation',
    'Total mortgage principal should match long-term debt on balance sheet',
    'mortgage_statement',
    'cross_document_check',
    'SUM(mortgage_principal_balance) = balance_sheet_long_term_debt',
    'Mortgage balances do not reconcile with balance sheet long-term debt section',
    'error',
    TRUE
),

-- 10. Cross-Document Validation: Income Statement Interest Expense
(
    'mortgage_interest_income_statement_reconciliation',
    'YTD interest paid should match interest expense on income statement',
    'mortgage_statement',
    'cross_document_check',
    'SUM(ytd_interest_paid) = income_statement_interest_expense',
    'Mortgage interest does not match income statement interest expense',
    'warning',
    TRUE
);

-- Query to verify seeding
-- SELECT document_type, COUNT(*) as rule_count, 
--        COUNT(CASE WHEN severity = 'error' THEN 1 END) as errors, 
--        COUNT(CASE WHEN severity = 'warning' THEN 1 END) as warnings,
--        COUNT(CASE WHEN severity = 'info' THEN 1 END) as info
-- FROM validation_rules
-- WHERE document_type = 'mortgage_statement' AND is_active = true
-- GROUP BY document_type;


