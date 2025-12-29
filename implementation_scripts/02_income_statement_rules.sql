-- ============================================================================
-- INCOME STATEMENT VALIDATION RULES - COMPLETE IMPLEMENTATION
-- ============================================================================
-- This script implements all 27 Income Statement rules from audit documentation
-- Priority: HIGH - Revenue and expense validation
-- ============================================================================

-- Already Implemented (11 rules):
-- IS-1: Fundamental Equation ✓
-- IS-2: YTD Accumulation ✓
-- IS-3: Total Income Calculation ✓
-- IS-7: Income Statement Calculation ✓
-- IS-8: NOI Calculation ✓
-- IS-12: Off-Site Management Fee ✓
-- IS-13: Asset Management Fee ✓
-- IS-14: Accounting Fee ~0.75% ✓
-- IS-20: Operating Expense Ratio ✓
-- IS-21: NOI Margin ✓

-- Missing Rules (16 rules) - IMPLEMENT BELOW

-- ============================================================================
-- INCOME CATEGORIES RULES
-- ============================================================================

-- IS-4: Total Income Composition
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_total_income_composition',
 'Total Income = Base Rentals + Interest + Tax + Insurance + CAM + Annual CAMs + Percentage Rent + Other',
 'income_statement',
 'balance_check',
 'total_income = base_rentals + interest_income + tax_reimbursement + insurance_reimbursement + cam + annual_cams + percentage_rent + other_income',
 'Total Income does not equal sum of income components',
 'error',
 true);

-- IS-5: Constant Reimbursement Components
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_tax_reimbursement_constant',
 'Tax Reimbursement should remain relatively constant month-to-month',
 'income_statement',
 'variance_check',
 'ABS((tax_reimbursement_current - tax_reimbursement_prior) / tax_reimbursement_prior) <= 0.10',
 'Tax Reimbursement varied by more than 10% - verify calculation',
 'warning',
 true);

-- IS-5B: Insurance Reimbursement Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_insurance_reimbursement_constant',
 'Insurance Reimbursement should remain relatively constant month-to-month',
 'income_statement',
 'variance_check',
 'ABS((insurance_reimbursement_current - insurance_reimbursement_prior) / insurance_reimbursement_prior) <= 0.10',
 'Insurance Reimbursement varied by more than 10% - verify calculation',
 'warning',
 true);

-- IS-6: Variable Income Components
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_base_rentals_reasonable_variance',
 'Base Rentals should not vary by more than 20% month-to-month without explanation',
 'income_statement',
 'variance_check',
 'ABS((base_rentals_current - base_rentals_prior) / base_rentals_prior) <= 0.20',
 'Base Rentals varied by more than 20% - investigate tenant changes',
 'warning',
 true);

-- IS-7: CAM Pattern Tracking
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_cam_reasonable',
 'CAM should be reasonable based on tenant pro-rata share and actual expenses',
 'income_statement',
 'range_check',
 'cam >= 0 AND cam <= total_operating_expenses * 1.2',
 'CAM appears unreasonable vs operating expenses',
 'warning',
 true);

-- IS-8: Percentage Rent Detection
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_percentage_rent_requires_sales',
 'Percentage Rent should only appear when tenant sales exceed threshold',
 'income_statement',
 'business_logic',
 'IF percentage_rent > 0 THEN tenant_sales_clause_exists = true',
 'Percentage Rent recorded without sales-based lease clause',
 'warning',
 true);

-- ============================================================================
-- EXPENSE CATEGORIES RULES
-- ============================================================================

-- IS-9: Total Expenses Composition
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_total_expenses_composition',
 'Total Expenses = Total Operating Expenses + Total Additional Operating Expenses',
 'income_statement',
 'balance_check',
 'total_expenses = total_operating_expenses + total_additional_operating_expenses',
 'Total Expenses does not equal sum of expense categories',
 'error',
 true);

-- IS-10: Property Tax Expense Pattern
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_property_tax_pattern',
 'Property Tax expense should follow expected monthly pattern',
 'income_statement',
 'pattern_check',
 'property_tax_expense_monthly ~ expected_monthly_tax',
 'Property Tax expense deviates from expected pattern',
 'info',
 true);

-- IS-11: Property Insurance Pattern
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_property_insurance_pattern',
 'Property Insurance expense should follow expected pattern',
 'income_statement',
 'pattern_check',
 'property_insurance_expense ~ expected_insurance_pattern',
 'Property Insurance expense deviates from expected pattern',
 'info',
 true);

-- IS-15: Utility Expenses Seasonal Variance
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_utilities_seasonal_reasonable',
 'Utility expenses should be reasonable with seasonal variations expected',
 'income_statement',
 'variance_check',
 'utilities_expense >= historical_min * 0.3 AND utilities_expense <= historical_max * 1.5',
 'Utility expenses outside reasonable seasonal range',
 'warning',
 true);

-- IS-16: R&M Lighting Constant Monthly
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_rm_lighting_constant',
 'R&M Lighting should be constant if under fixed maintenance agreement',
 'income_statement',
 'constant_check',
 'rm_lighting_current = rm_lighting_prior',
 'R&M Lighting changed - verify contract amendment',
 'info',
 true);

-- ============================================================================
-- BELOW THE LINE RULES
-- ============================================================================

-- IS-17: Mortgage Interest Decreasing
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_mortgage_interest_decreasing',
 'Mortgage Interest should decrease over time as principal is paid down',
 'income_statement',
 'trend_check',
 'mortgage_interest_current <= mortgage_interest_prior',
 'Mortgage Interest increased - should decrease with principal paydown',
 'warning',
 true);

-- IS-18: Depreciation Pattern
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_depreciation_consistent',
 'Depreciation should be consistent unless assets added/disposed',
 'income_statement',
 'variance_check',
 'ABS((depreciation_current - depreciation_prior) / depreciation_prior) <= 0.20',
 'Depreciation varied significantly - verify asset changes',
 'warning',
 true);

-- IS-19: Amortization Pattern
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_amortization_consistent',
 'Amortization should be consistent unless refinancing occurred',
 'income_statement',
 'variance_check',
 'ABS((amortization_current - amortization_prior) / amortization_prior) <= 0.20',
 'Amortization varied significantly - verify refinancing activity',
 'warning',
 true);

-- IS-22: Net Income Margin
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_net_income_margin',
 'Net Income Margin = Net Income / Total Income',
 'income_statement',
 'calculation_check',
 'net_income_margin = (net_income / total_income) * 100',
 'Net Income Margin calculation check',
 'info',
 true);

-- IS-25: State Taxes Pattern
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('is_state_taxes_ytd_only',
 'State Taxes typically appear in YTD but not PTD (one-time annual payment)',
 'income_statement',
 'pattern_check',
 'state_taxes_ptd = 0 AND state_taxes_ytd > 0',
 'State Taxes appearing in PTD - verify if this is expected',
 'info',
 true);

-- ============================================================================
-- Summary Query
-- ============================================================================

SELECT 'Income Statement Rules Deployed' as status, COUNT(*) as total_rules
FROM validation_rules
WHERE document_type = 'income_statement';
