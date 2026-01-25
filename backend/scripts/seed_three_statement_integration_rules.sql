-- Validation Rules Seed Data for Three Statement Integration
-- Complete financial statement integration validation rules
-- These rules ensure Balance Sheet, Income Statement, and Cash Flow are properly connected

-- Clear existing three statement integration rules (idempotent)
DELETE FROM validation_rules WHERE document_type = 'three_statement_integration';

-- Three Statement Integration Rules (23 rules)
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

-- CRITICAL TIE-OUTS

-- 1. Fundamental Connection
(
    '3s_1_fundamental_connection',
    'The three financial statements are completely interconnected',
    'three_statement_integration',
    'meta_check',
    'IS → BS (earnings) → CF (cash movements)',
    'Financial statements must be properly integrated',
    'info',
    TRUE
),

-- 2. Integration Flow Overview
(
    '3s_2_integration_flow',
    'Income Statement flows to Balance Sheet equity, which flows to Cash Flow',
    'three_statement_integration',
    'flow_check',
    'IS (Net Income) → BS (Current Period Earnings) → CF (Net Income start)',
    'Statement integration flow must be maintained',
    'info',
    TRUE
),

-- NET INCOME: THE CENTRAL LINK

-- 3. Net Income Flows to Balance Sheet Equity
(
    '3s_3_net_income_to_equity',
    'IS Net Income must equal change in BS Current Period Earnings',
    'three_statement_integration',
    'balance_check',
    'IS.net_income = BS.current_period_earnings_change',
    'Net Income does not match Balance Sheet earnings change',
    'critical',
    TRUE
),

-- 4. Net Income Starts Cash Flow Statement
(
    '3s_4_net_income_start_cf',
    'IS Net Income is the starting point of the Cash Flow Statement',
    'three_statement_integration',
    'reconciliation',
    'IS.net_income = CF.net_income_start',
    'Net Income mismatch between Income Statement and Cash Flow Statement',
    'critical',
    TRUE
),

-- DEPRECIATION: THREE-WAY RECONCILIATION

-- 5. Depreciation Flow Through All Three Statements
(
    '3s_5_depreciation_three_way',
    'Depreciation must flow correctly: IS expense → CF add-back → BS accumulated depreciation',
    'three_statement_integration',
    'three_way_reconciliation',
    'IS.depreciation_expense = CF.depreciation_addback = BS.accum_depr_change',
    'Depreciation does not reconcile across all three statements',
    'high',
    TRUE
),

-- 6. Complete Depreciation Reconciliation
(
    '3s_6_complete_depreciation',
    'All depreciation components (buildings, improvements, other) must reconcile',
    'three_statement_integration',
    'detailed_reconciliation',
    'SUM(IS.depr_components) = SUM(CF.depr_addbacks) = SUM(BS.accum_depr_changes)',
    'Complete depreciation reconciliation failed',
    'high',
    TRUE
),

-- AMORTIZATION: THREE-WAY RECONCILIATION

-- 7. Amortization Flow Through All Three Statements
(
    '3s_7_amortization_flow',
    'Amortization must flow: IS expense → CF add-back → BS accumulated amortization',
    'three_statement_integration',
    'three_way_reconciliation',
    'IS.amortization_expense = CF.amortization_addback = BS.accum_amort_change',
    'Amortization does not reconcile across statements',
    'medium',
    TRUE
),

-- CASH: THE ULTIMATE RECONCILIATION

-- 8. Cash Flow Statement Reconciles Balance Sheet Cash Changes
(
    '3s_8_cash_flow_reconciliation',
    'CF cash flow must equal BS ending cash minus BS beginning cash',
    'three_statement_integration',
    'balance_check',
    'CF.cash_flow = BS.ending_cash - BS.beginning_cash',
    'Cash flow does not reconcile with balance sheet cash changes',
    'critical',
    TRUE
),

-- 9. Cash Components Match Balance Sheet
(
    '3s_9_cash_components',
    'Individual cash account balances must match between CF and BS',
    'three_statement_integration',
    'component_match',
    'CF.cash_components = BS.cash_components',
    'Cash component balances do not match between statements',
    'high',
    TRUE
),

-- WORKING CAPITAL: THREE-WAY RECONCILIATION

-- 10. Accounts Receivable Three-Way
(
    '3s_10_ar_three_way',
    'AR reconciliation: IS revenue → BS AR balance → CF AR adjustment',
    'three_statement_integration',
    'working_capital_reconciliation',
    'IS.revenue - CF.ar_adjustment = cash_collected',
    'Accounts Receivable does not reconcile across statements',
    'medium',
    TRUE
),

-- 11. Accounts Payable Three-Way
(
    '3s_11_ap_three_way',
    'AP reconciliation: IS expenses → BS AP balance → CF AP adjustment',
    'three_statement_integration',
    'working_capital_reconciliation',
    'IS.expenses - CF.ap_adjustment = cash_paid',
    'Accounts Payable does not reconcile across statements',
    'medium',
    TRUE
),

-- SPECIFIC FLOWS

-- 12. Property Tax Flow Through All Statements
(
    '3s_12_property_tax_flow',
    'Property tax flows: IS expense → BS payable → CF payment',
    'three_statement_integration',
    'specific_flow_check',
    'IS.property_tax_expense = BS.property_tax_payable_change + CF.property_tax_payment',
    'Property tax does not flow correctly through statements',
    'medium',
    TRUE
),

-- 13. CapEx Flow Through Statements
(
    '3s_13_capex_flow',
    'Capital expenditures: CF cash outflow → BS fixed assets increase',
    'three_statement_integration',
    'investing_flow',
    'CF.capex_outflow = BS.fixed_assets_increase',
    'Capital expenditures do not match fixed asset increases',
    'high',
    TRUE
),

-- 14. CapEx to Future Depreciation Link
(
    '3s_14_capex_depr_link',
    'Capital expenditures create assets that will be depreciated in future periods',
    'three_statement_integration',
    'inter_period_link',
    'CF.capex (Year 1) → BS.asset (Year 1) → IS.depreciation (Years 2-N)',
    'CapEx to depreciation linkage verification',
    'info',
    TRUE
),

-- 15. Mortgage Principal Flow
(
    '3s_15_mortgage_principal_flow',
    'Mortgage principal: CF cash payment → BS liability decrease (no IS impact)',
    'three_statement_integration',
    'financing_flow',
    'CF.mortgage_principal_payment = BS.mortgage_liability_decrease',
    'Mortgage principal payments do not match liability reduction',
    'high',
    TRUE
),

-- 16. Mortgage Interest Flow
(
    '3s_16_mortgage_interest_flow',
    'Mortgage interest: IS expense → CF implicit in net income (no adjustment needed)',
    'three_statement_integration',
    'expense_flow',
    'IS.mortgage_interest_expense (already in net income, no CF adjustment)',
    'Mortgage interest flow verification',
    'medium',
    TRUE
),

-- 17. Escrow Flow Through Statements
(
    '3s_17_escrow_flow',
    'Escrow accounts: BS asset balances → CF funding/releases',
    'three_statement_integration',
    'asset_flow',
    'CF.escrow_adjustments = BS.escrow_balance_changes',
    'Escrow flows do not reconcile between statements',
    'medium',
    TRUE
),

-- EQUITY CHANGES

-- 18. Distributions Flow Through Statements
(
    '3s_18_distributions_flow',
    'Distributions: CF cash outflow → BS equity decrease (no IS impact)',
    'three_statement_integration',
    'equity_flow',
    'CF.distributions = BS.distribution_increase',
    'Distributions do not match between CF and BS',
    'high',
    TRUE
),

-- 19. Complete Equity Reconciliation
(
    '3s_19_equity_reconciliation',
    'Total capital = contributions + beginning equity + net income - distributions',
    'three_statement_integration',
    'equity_formula',
    'BS.total_capital = BS.contributions + BS.beg_equity + IS.net_income - CF.distributions',
    'Equity section does not reconcile properly',
    'critical',
    TRUE
),

-- COMPREHENSIVE RECONCILIATIONS

-- 20. Monthly Complete Reconciliation
(
    '3s_20_monthly_recon_meta',
    'All three statements reconcile completely for the monthly period',
    'three_statement_integration',
    'comprehensive_check',
    'All monthly flows verified: IS → BS → CF integration',
    'Monthly period reconciliation incomplete',
    'info',
    TRUE
),

-- 21. Year-to-Date Complete Integration
(
    '3s_21_ytd_recon_meta',
    'Year-to-date cumulative reconciliation across all three statements',
    'three_statement_integration',
    'comprehensive_check',
    'YTD IS flows to YTD BS changes flows to YTD CF movements',
    'YTD reconciliation incomplete',
    'info',
    TRUE
),

-- GOLDEN RULES

-- 22. The Golden Rules of Integration
(
    '3s_22_golden_rules',
    'Fundamental accounting principles: (1) Assets = Liabilities + Equity, (2) Net Income → Equity, (3) CF reconciles cash, (4) Non-cash items circle back',
    'three_statement_integration',
    'fundamental_principles',
    '(1) BS equation, (2) NI flow, (3) Cash recon, (4) Depreciation cycle, (5) Working capital bridge, (6) CapEx→Depreciation, (7) Principal≠Expense, (8) Every $ traced',
    'One or more golden rules of integration violated',
    'critical',
    TRUE
),

-- DEPRECIATION ALIAS (for backward compatibility)

-- 23. Depreciation Alias Check
(
    '3s_5_depreciation_alias',
    'Depreciation alias/alternate verification (same as 3S-5)',
    'three_statement_integration',
    'three_way_reconciliation',
    'IS.depreciation = CF.depreciation_addback = BS.accum_depr_change',
    'Depreciation reconciliation failed (alias check)',
    'info',
    TRUE
);

-- Query to verify seeding
SELECT document_type, COUNT(*) as rule_count, 
       COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical, 
       COUNT(CASE WHEN severity = 'high' THEN 1 END) as high,
       COUNT(CASE WHEN severity = 'medium' THEN 1 END) as medium,
       COUNT(CASE WHEN severity = 'info' THEN 1 END) as info
FROM validation_rules
WHERE document_type = 'three_statement_integration' AND is_active = true
GROUP BY document_type;
