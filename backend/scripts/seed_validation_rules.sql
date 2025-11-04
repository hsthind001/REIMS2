-- Seed Validation Rules for Financial Data Quality

-- Clear existing rules (idempotent)
DELETE FROM validation_rules;

-- Insert 8 business logic validation rules

INSERT INTO validation_rules (
    rule_name, rule_description, document_type, rule_type, rule_formula, 
    error_message, severity, is_active
) VALUES

-- 1. Balance Sheet Equation
(
    'balance_sheet_equation',
    'Verifies the fundamental accounting equation: Assets = Liabilities + Equity',
    'balance_sheet',
    'balance_check',
    'total_assets = total_liabilities + total_equity',
    'Balance sheet equation not balanced: Assets != Liabilities + Equity (tolerance: 1%)',
    'error',
    TRUE
),

-- 2. Balance Sheet Subtotals
(
    'balance_sheet_subtotals',
    'Verifies that current assets + non-current assets = total assets',
    'balance_sheet',
    'balance_check',
    'current_assets + non_current_assets = total_assets',
    'Asset subtotals do not match total assets',
    'warning',
    TRUE
),

-- 3. Income Statement Net Income Calculation
(
    'income_statement_calculation',
    'Verifies: Net Income = Total Revenue - Total Expenses - Interest - Depreciation - Amortization',
    'income_statement',
    'balance_check',
    'net_income = total_revenue - total_expenses - mortgage_interest - depreciation - amortization',
    'Net income calculation mismatch (tolerance: 1%)',
    'error',
    TRUE
),

-- 4. Net Operating Income (NOI) Calculation
(
    'noi_calculation',
    'Verifies: NOI = Total Revenue - Total Operating Expenses',
    'income_statement',
    'balance_check',
    'noi = total_revenue - total_operating_expenses',
    'Net operating income (NOI) calculation error',
    'error',
    TRUE
),

-- 5. Occupancy Rate Range Check
(
    'occupancy_rate_range',
    'Occupancy rate must be between 0% and 100%',
    'rent_roll',
    'range_check',
    'occupancy_rate >= 0 AND occupancy_rate <= 100',
    'Occupancy rate must be between 0% and 100%',
    'error',
    TRUE
),

-- 6. Rent Roll Total Calculation
(
    'rent_roll_total_rent',
    'Total annual rent should equal sum of individual tenant rents',
    'rent_roll',
    'balance_check',
    'total_annual_rent = SUM(tenant_annual_rents)',
    'Total rent does not match sum of tenant rents',
    'warning',
    TRUE
),

-- 7. Cash Flow Balance
(
    'cash_flow_balance',
    'Net cash flow = Operating + Investing + Financing activities',
    'cash_flow',
    'balance_check',
    'net_cash_flow = operating_cash_flow + investing_cash_flow + financing_cash_flow',
    'Cash flow statement does not balance',
    'error',
    TRUE
),

-- 8. Cash Flow Beginning/Ending Balance
(
    'cash_flow_ending_balance',
    'Ending cash balance = Beginning cash balance + Net cash flow',
    'cash_flow',
    'balance_check',
    'ending_cash_balance = beginning_cash_balance + net_cash_flow',
    'Cash flow ending balance calculation error',
    'error',
    TRUE
);

-- Display seeded rules
SELECT 'Validation Rules Seeded' as status, COUNT(*) as total_rules FROM validation_rules;
SELECT rule_name, document_type, severity FROM validation_rules ORDER BY id;

