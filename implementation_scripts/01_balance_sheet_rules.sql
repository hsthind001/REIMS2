-- ============================================================================
-- BALANCE SHEET VALIDATION RULES - COMPLETE IMPLEMENTATION
-- ============================================================================
-- This script implements all 35 Balance Sheet rules from the audit documentation
-- Priority: HIGH - These are fundamental accounting rules
-- ============================================================================

-- Phase 1: Already Implemented (5 rules)
-- BS-1: Fundamental Equation ✓
-- BS-2: Account Code Format ✓
-- BS-33: Current Period Earnings ✓
-- BS-34: Total Capital Calculation ✓

-- Phase 2: Missing Rules (30 rules) - IMPLEMENT BELOW

-- ============================================================================
-- CURRENT ASSETS RULES
-- ============================================================================

-- BS-3: Total Current Assets Composition
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_total_current_assets',
 'Total Current Assets = Sum of all current asset line items',
 'balance_sheet',
 'balance_check',
 'total_current_assets = cash_operating + cash_depository + cash_operating_iv + ar_trade + ar_tenants + prepaid + other_current',
 'Total Current Assets does not equal sum of individual current asset accounts',
 'error',
 true);

-- BS-4: Accounts Receivable - Trade Pattern
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_ar_trade_pattern',
 'A/R Trade should follow expected pattern (typically decreasing)',
 'balance_sheet',
 'trend_check',
 'ar_trade_monthly_change ~ expected_pattern',
 'A/R Trade shows unusual pattern - investigate for collection issues',
 'warning',
 true);

-- BS-5: A/R Tenants Trend
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_ar_tenants_reasonable',
 'A/R Tenants should be reasonable vs monthly revenue (< 2 months)',
 'balance_sheet',
 'range_check',
 'ar_tenants <= monthly_revenue * 2',
 'A/R Tenants balance exceeds 2 months of revenue - collection concern',
 'warning',
 true);

-- ============================================================================
-- PROPERTY & EQUIPMENT RULES
-- ============================================================================

-- BS-6: Land Value Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_land_value_constant',
 'Land value should remain constant unless purchase/sale',
 'balance_sheet',
 'constant_check',
 'land_value_current = land_value_prior',
 'Land value changed without documented transaction',
 'warning',
 true);

-- BS-7: Buildings Value Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_buildings_value_constant',
 'Buildings value should remain constant unless major addition',
 'balance_sheet',
 'constant_check',
 'buildings_value_current = buildings_value_prior',
 'Buildings value changed without documented capital improvement',
 'warning',
 true);

-- BS-8: Accumulated Depreciation - Buildings
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_accum_depr_buildings_increase',
 'Accumulated Depreciation - Buildings should increase monthly (become more negative)',
 'balance_sheet',
 'trend_check',
 'accum_depr_buildings_current <= accum_depr_buildings_prior',
 'Accumulated Depreciation - Buildings did not increase (depreciation missing)',
 'error',
 true);

-- BS-9: Accumulated Depreciation - 15 Year Improvements
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_accum_depr_15yr_increase',
 'Accumulated Depreciation - 15 Year Improvements should increase monthly',
 'balance_sheet',
 'trend_check',
 'accum_depr_15yr_current <= accum_depr_15yr_prior',
 'Accumulated Depreciation - 15 Yr did not increase (depreciation missing)',
 'error',
 true);

-- BS-10: 5-Year Improvements Fully Depreciated Check
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_5yr_fully_depreciated',
 '5-Year Improvements should be constant if fully depreciated',
 'balance_sheet',
 'constant_check',
 'IF accum_depr_5yr = -cost_basis THEN accum_depr_5yr_current = accum_depr_5yr_prior',
 'Fully depreciated 5-year improvements changed value',
 'info',
 true);

-- BS-11: TI/Current Improvements Increases Only
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_ti_current_improvements',
 'Tenant Improvements should only increase (capital invested)',
 'balance_sheet',
 'trend_check',
 'ti_current_improvements_current >= ti_current_improvements_prior',
 'Tenant Improvements decreased without disposal documentation',
 'warning',
 true);

-- BS-12: 30-Year Roof Asset Tracking
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_roof_asset_tracking',
 '30-Year Roof value should only increase with capital improvements',
 'balance_sheet',
 'trend_check',
 'roof_30yr_current >= roof_30yr_prior',
 '30-Year Roof value decreased without documented disposal',
 'warning',
 true);

-- BS-13: Fixed Assets - HVAC Addition Tracking
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_hvac_asset_tracking',
 'Fixed Assets - HVAC should only increase with new equipment',
 'balance_sheet',
 'trend_check',
 'hvac_fixed_assets_current >= hvac_fixed_assets_prior',
 'HVAC assets decreased without documented disposal',
 'warning',
 true);

-- ============================================================================
-- OTHER ASSETS RULES
-- ============================================================================

-- BS-14: Deposits Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_deposits_constant',
 'Deposits should remain constant unless new deposit made',
 'balance_sheet',
 'constant_check',
 'deposits_current = deposits_prior',
 'Deposits changed without documented transaction',
 'warning',
 true);

-- BS-15: Loan Costs Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_loan_costs_constant',
 'Loan Costs should remain constant unless refinancing',
 'balance_sheet',
 'constant_check',
 'loan_costs_current = loan_costs_prior',
 'Loan Costs changed without documented refinancing',
 'error',
 true);

-- BS-16: Accumulated Amortization - Loan Costs
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_accum_amort_loan_costs',
 'Loan Costs amortize monthly (accumulated amortization increases)',
 'balance_sheet',
 'trend_check',
 'accum_amort_loan_costs_current <= accum_amort_loan_costs_prior',
 'Accumulated Amortization - Loan Costs did not increase',
 'error',
 true);

-- BS-17: Accumulated Amortisation Other Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_accum_amort_other_constant',
 'Accumulated Amortisation (Other) should be constant if fully amortized',
 'balance_sheet',
 'constant_check',
 'accum_amort_other_current = accum_amort_other_prior',
 'Accumulated Amortisation (Other) changed - should be fully amortized',
 'info',
 true);

-- BS-18: External Lease Commission Tracking
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_external_lease_commission',
 'External lease commissions increase when new leases are signed',
 'balance_sheet',
 'trend_check',
 'external_lease_commission_current >= external_lease_commission_prior',
 'External lease commission decreased without explanation',
 'info',
 true);

-- BS-19: Internal Lease Commission Tracking
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_internal_lease_commission',
 'Internal lease commissions increase with new leasing activity',
 'balance_sheet',
 'trend_check',
 'internal_lease_commission_current >= internal_lease_commission_prior',
 'Internal lease commission decreased without explanation',
 'info',
 true);

-- BS-20: Prepaid Insurance Tracking
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_prepaid_insurance_reasonable',
 'Prepaid insurance should be reasonable (< 12 months of insurance expense)',
 'balance_sheet',
 'range_check',
 'prepaid_insurance <= monthly_insurance_expense * 12',
 'Prepaid insurance exceeds 12 months - verify payment',
 'warning',
 true);

-- BS-21: Prepaid Expenses Reasonable
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_prepaid_expenses_reasonable',
 'Prepaid expenses should be reasonable (< 6 months of expenses)',
 'balance_sheet',
 'range_check',
 'prepaid_expenses <= monthly_expenses * 6',
 'Prepaid expenses exceed 6 months - verify validity',
 'warning',
 true);

-- ============================================================================
-- CURRENT LIABILITIES RULES
-- ============================================================================

-- BS-22: A/P 5Rivers CRE Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_ap_5rivers_constant',
 'A/P 5Rivers CRE should remain constant unless payment/new charge',
 'balance_sheet',
 'constant_check',
 'ap_5rivers_current = ap_5rivers_prior',
 'A/P 5Rivers changed without documented transaction',
 'info',
 true);

-- BS-23: A/P Eastchase Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_ap_eastchase_constant',
 'A/P Eastchase should remain constant unless payment/new charge',
 'balance_sheet',
 'constant_check',
 'ap_eastchase_current = ap_eastchase_prior',
 'A/P Eastchase changed without documented transaction',
 'info',
 true);

-- BS-24: Loans Payable 5Rivers Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_loans_payable_5rivers',
 'Loans Payable 5Rivers should remain constant unless payment/advance',
 'balance_sheet',
 'constant_check',
 'loans_payable_5rivers_current = loans_payable_5rivers_prior',
 'Loans Payable 5Rivers changed without documented transaction',
 'warning',
 true);

-- BS-25: Deposit Refundable to Tenant Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_deposit_refundable_tenant',
 'Deposit Refundable to Tenant should only change with new/departing tenants',
 'balance_sheet',
 'change_tracking',
 'deposit_refundable_tenant_change requires tenant_move_in OR tenant_move_out',
 'Tenant deposit changed without tenant activity',
 'warning',
 true);

-- BS-26: Accrued Expenses Volatility
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_accrued_expenses_range',
 'Accrued expenses should be within reasonable range based on historical patterns',
 'balance_sheet',
 'range_check',
 'accrued_expenses >= historical_min * 0.5 AND accrued_expenses <= historical_max * 1.5',
 'Accrued expenses outside normal range - verify accuracy',
 'info',
 true);

-- BS-27: Accounts Payable Trade Volatility
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_ap_trade_reasonable',
 'Accounts Payable Trade should be reasonable vs monthly expenses',
 'balance_sheet',
 'range_check',
 'ap_trade <= monthly_operating_expenses * 2',
 'A/P Trade exceeds 2 months of expenses - payment delay concern',
 'warning',
 true);

-- BS-28: Property Tax Payable Accumulation
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_property_tax_payable_accum',
 'Property Tax Payable accumulates until payment is made',
 'balance_sheet',
 'calculation_check',
 'property_tax_payable_current = property_tax_payable_prior + monthly_tax_expense - tax_payments',
 'Property Tax Payable accumulation does not match expected pattern',
 'error',
 true);

-- BS-29: Rent Received in Advance Reasonable
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_rent_received_advance',
 'Rent Received in Advance should be reasonable (< 2 months of rent)',
 'balance_sheet',
 'range_check',
 'rent_received_advance <= monthly_rent_revenue * 2',
 'Rent Received in Advance exceeds 2 months - verify tenant prepayments',
 'info',
 true);

-- ============================================================================
-- CAPITAL RULES
-- ============================================================================

-- BS-30: Partners Contribution Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_partners_contribution_constant',
 'Partners Contribution should remain constant unless new capital injection',
 'balance_sheet',
 'constant_check',
 'partners_contribution_current = partners_contribution_prior',
 'Partners Contribution changed without documented capital event',
 'error',
 true);

-- BS-31: Beginning Equity Constant
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_beginning_equity_constant',
 'Beginning Equity should remain constant for the year',
 'balance_sheet',
 'constant_check',
 'beginning_equity_current = beginning_equity_prior',
 'Beginning Equity changed mid-year - should be constant',
 'error',
 true);

-- BS-32: Distribution Tracking
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_distribution_tracking',
 'Distributions should only increase (become more negative) when cash is distributed',
 'balance_sheet',
 'trend_check',
 'distribution_current <= distribution_prior',
 'Distribution decreased - should only become more negative',
 'error',
 true);

-- BS-35: Change in Total Capital
INSERT INTO validation_rules (rule_name, rule_description, document_type, rule_type, rule_formula, error_message, severity, is_active)
VALUES
('bs_change_total_capital',
 'Change in Total Capital = Change in Current Period Earnings + Change in Distribution',
 'balance_sheet',
 'calculation_check',
 '(total_capital_current - total_capital_prior) = (current_earnings_current - current_earnings_prior) + (distribution_current - distribution_prior)',
 'Total Capital change does not reconcile to earnings and distributions',
 'error',
 true);

-- ============================================================================
-- Summary Query
-- ============================================================================

SELECT 'Balance Sheet Rules Deployed' as status, COUNT(*) as total_rules
FROM validation_rules
WHERE document_type = 'balance_sheet';
