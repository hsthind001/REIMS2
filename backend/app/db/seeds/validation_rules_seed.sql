-- Validation Rules Seed Data
-- Comprehensive business logic validation rules for financial statements
-- Sprint 5.1: Financial Data Validation

-- Balance Sheet Rules (5)
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active) VALUES
('balance_sheet_equation', 'Balance Sheet Equation: Assets = Liabilities + Equity', 'balance_sheet', 'balance_check', 'total_assets = total_liabilities + total_equity', 'Assets must equal Liabilities plus Equity', 'error', true),
('balance_sheet_current_assets', 'Current Assets sum correctly', 'balance_sheet', 'sum_check', 'sum(current_asset_accounts) = total_current_assets', 'Sum of current asset accounts doesn''t match total', 'warning', true),
('balance_sheet_fixed_assets', 'Fixed Assets sum correctly', 'balance_sheet', 'sum_check', 'sum(fixed_asset_accounts) = total_fixed_assets', 'Sum of fixed asset accounts doesn''t match total', 'warning', true),
('balance_sheet_no_negative_cash', 'Cash accounts should not be negative', 'balance_sheet', 'range_check', 'cash >= 0', 'Cash balance is negative', 'warning', true),
('balance_sheet_no_negative_equity', 'Total Equity should not be negative', 'balance_sheet', 'range_check', 'total_equity >= 0', 'Total Equity is negative (property may be underwater)', 'warning', true);

-- Income Statement Rules (6)
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active) VALUES
('income_statement_total_revenue', 'Revenue accounts sum to Total Revenue', 'income_statement', 'sum_check', 'sum(revenue_accounts) = total_revenue', 'Sum of revenue accounts doesn''t match total revenue', 'error', true),
('income_statement_total_expenses', 'Expense accounts sum to Total Expenses', 'income_statement', 'sum_check', 'sum(expense_accounts) = total_expenses', 'Sum of expense accounts doesn''t match total expenses', 'error', true),
('income_statement_net_income', 'Net Income = Total Revenue - Total Expenses', 'income_statement', 'balance_check', 'net_income = total_revenue - total_expenses', 'Net Income calculation is incorrect', 'error', true),
('income_statement_percentages', 'Period and YTD percentages should be reasonable', 'income_statement', 'range_check', '-100 <= percentage <= 200', 'Percentage values are out of reasonable range', 'warning', true),
('income_statement_ytd_consistency', 'YTD amounts should be >= Period amounts', 'income_statement', 'range_check', 'ytd_amount >= period_amount', 'YTD amount is less than Period amount', 'warning', true),
('income_statement_no_negative_revenue', 'Revenue accounts should not be negative', 'income_statement', 'range_check', 'revenue >= 0', 'Revenue account has negative amount', 'warning', true);

-- Cash Flow Rules - Template v1.0 Compliant (14 rules)
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active) VALUES
-- Income Validations
('cf_total_income_sum', 'Total Income equals sum of all income line items', 'cash_flow', 'balance_check', 'total_income = sum(income_items)', 'Total Income must equal sum of all income line items', 'error', true),
('cf_base_rental_percentage', 'Base Rentals should be 70-100% of Total Income', 'cash_flow', 'range_check', '70 <= (base_rentals / total_income) * 100 <= 100', 'Base Rentals percentage is outside normal range (70-100%)', 'warning', true),

-- Expense Validations
('cf_total_expenses_sum', 'Total Expenses equals sum of Operating + Additional Expenses', 'cash_flow', 'balance_check', 'total_expenses = total_operating_expenses + total_additional_expenses', 'Total Expenses calculation mismatch', 'error', true),
('cf_expense_subtotals', 'Operating Expenses subtotals should sum correctly', 'cash_flow', 'balance_check', 'operating_expenses = property + utility + contracted + rm + admin', 'Operating Expenses subtotals don''t sum correctly', 'warning', true),

-- NOI Validations
('cf_noi_calculation', 'NOI = Total Income - Total Expenses', 'cash_flow', 'balance_check', 'noi = total_income - total_expenses', 'Net Operating Income must equal Total Income - Total Expenses', 'error', true),
('cf_noi_percentage', 'NOI should be 60-80% of Total Income', 'cash_flow', 'range_check', '60 <= (noi / total_income) * 100 <= 80', 'NOI percentage is outside normal range (60-80%)', 'warning', true),
('cf_noi_positive', 'NOI should generally be positive', 'cash_flow', 'range_check', 'noi > 0', 'Net Operating Income is negative', 'warning', true),

-- Net Income Validation
('cf_net_income_calculation', 'Net Income = NOI - (Mortgage Interest + Depreciation + Amortization)', 'cash_flow', 'balance_check', 'net_income = noi - mortgage_interest - depreciation - amortization', 'Net Income calculation is incorrect', 'error', true),

-- Cash Flow Validations
('cf_cash_flow_calculation', 'Cash Flow = Net Income + Total Adjustments', 'cash_flow', 'balance_check', 'cash_flow = net_income + total_adjustments', 'Cash Flow calculation mismatch', 'error', true),
('cf_cash_account_differences', 'Each cash account difference = ending - beginning', 'cash_flow', 'balance_check', 'difference = ending_balance - beginning_balance', 'Cash account reconciliation mismatch', 'error', true),
('cf_total_cash_balance', 'Sum of cash account differences should equal Cash Flow', 'cash_flow', 'balance_check', 'sum(differences) = cash_flow', 'Total cash account differences don''t equal Cash Flow', 'error', true),

-- Legacy Rules (kept for backward compatibility)
('cash_flow_categories_sum', 'Operating + Investing + Financing = Net Change in Cash', 'cash_flow', 'balance_check', 'operating + investing + financing = net_change', 'Cash flow categories don''t sum to net change', 'error', true),
('cash_flow_beginning_ending', 'Beginning Cash + Net Change = Ending Cash', 'cash_flow', 'balance_check', 'beginning_cash + net_change = ending_cash', 'Beginning + Net Change doesn''t equal Ending Cash', 'error', true),
('cash_flow_cross_check_balance_sheet', 'Ending Cash (CF) should match Cash (BS)', 'cash_flow', 'cross_statement_check', 'ending_cash_cf = cash_bs', 'Ending Cash on Cash Flow doesn''t match Cash on Balance Sheet', 'warning', true);

-- Rent Roll Rules (4)
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active) VALUES
('rent_roll_occupancy_rate', 'Occupancy rate should be between 0-100%', 'rent_roll', 'range_check', '0 <= occupancy_rate <= 100', 'Occupancy rate is out of valid range (0-100%)', 'error', true),
('rent_roll_total_rent', 'Sum of tenant rents should match total', 'rent_roll', 'sum_check', 'sum(monthly_rent) = total_monthly_rent', 'Sum of individual tenant rents doesn''t match total', 'warning', true),
('rent_roll_no_duplicate_units', 'Each unit should appear only once', 'rent_roll', 'uniqueness_check', 'unit_number unique per period', 'Duplicate unit numbers found in rent roll', 'error', true),
('rent_roll_valid_lease_dates', 'Lease start date must be before end date', 'rent_roll', 'date_check', 'lease_start_date < lease_end_date', 'Lease start date is not before end date', 'warning', true);

-- Cross-Statement Rules (2)
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active) VALUES
('cross_net_income_consistency', 'Net Income should be consistent across Income Statement and Cash Flow', 'cross_statement', 'cross_statement_check', 'net_income_is = net_income_cf', 'Net Income differs between Income Statement and Cash Flow', 'warning', true),
('cross_cash_consistency', 'Cash balance should match across Balance Sheet and Cash Flow', 'cross_statement', 'cross_statement_check', 'cash_bs = ending_cash_cf', 'Cash balance differs between Balance Sheet and Cash Flow', 'warning', true);

-- Query to verify seeding
-- SELECT document_type, COUNT(*) as rule_count, COUNT(CASE WHEN severity = 'error' THEN 1 END) as errors, COUNT(CASE WHEN severity = 'warning' THEN 1 END) as warnings
-- FROM validation_rules
-- WHERE is_active = true
-- GROUP BY document_type
-- ORDER BY document_type;

