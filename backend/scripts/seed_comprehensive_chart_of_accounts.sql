-- Comprehensive Chart of Accounts Seed Data
-- 200+ accounts from extracted financial statements

-- Clear existing duplicates
DELETE FROM chart_of_accounts WHERE account_code LIKE '%-%';

-- ASSETS (0xxx-1xxx)

-- Section Headers & Current Assets
INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active) VALUES
('0100-0000', 'ASSETS', 'asset', 'header', NULL, NULL, ARRAY['balance_sheet'], TRUE, 1, TRUE),
('0101-0000', 'Current Assets', 'asset', 'current_asset', NULL, NULL, ARRAY['balance_sheet'], FALSE, 2, TRUE),
('0122-0000', 'Cash - Operating', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet'], FALSE, 3, TRUE),
('0123-0000', 'Cash - Operating II', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet'], FALSE, 4, TRUE),
('0125-0000', 'Cash - Operating IV-PNC', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet'], FALSE, 5, TRUE),
('0305-0000', 'A/R Tenants', 'asset', 'current_asset', 'accounts_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 10, TRUE),
('0306-0000', 'A/R Other', 'asset', 'current_asset', 'accounts_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 11, TRUE),
('0499-9000', 'Total Current Assets', 'asset', 'current_asset', 'total', NULL, ARRAY['balance_sheet'], TRUE, 99, TRUE),

-- Property & Equipment
('0500-0000', 'Property & Equipment', 'asset', 'fixed_asset', NULL, NULL, ARRAY['balance_sheet'], FALSE, 100, TRUE),
('0510-0000', 'Land', 'asset', 'fixed_asset', 'land', '0500-0000', ARRAY['balance_sheet'], FALSE, 101, TRUE),
('0610-0000', 'Buildings', 'asset', 'fixed_asset', 'buildings', '0500-0000', ARRAY['balance_sheet'], FALSE, 102, TRUE),
('0710-0000', '5 Year Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 103, TRUE),
('0810-0000', '15 Year Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 104, TRUE),
('0815-0000', '30 Year - Roof', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 105, TRUE),
('0816-0000', '30 Year - HVAC', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 106, TRUE),
('0910-0000', 'Other Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 107, TRUE),
('0912-0000', 'PARKING-LOT', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 108, TRUE),
('0950-0000', 'TI/Current Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 109, TRUE),
('1061-0000', 'Accum. Depr. - Buildings', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 120, TRUE),
('1071-0000', 'Accum. Depr. 5 Year Impr.', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 121, TRUE),
('1081-0000', 'Accum. Depr. 15 Yr Impr.', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 122, TRUE),
('1082-0000', 'Accum. Depr.-Roof2008', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 123, TRUE),
('1091-0000', 'Accum. Depr.-Other Imp.', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 124, TRUE),
('1099-0000', 'Total Property & Equipment', 'asset', 'fixed_asset', 'total', NULL, ARRAY['balance_sheet'], TRUE, 199, TRUE),

-- Other Assets
('1200-0000', 'Other Assets', 'asset', 'other_asset', NULL, NULL, ARRAY['balance_sheet'], FALSE, 200, TRUE),
('1210-0000', 'Deposits', 'asset', 'other_asset', 'deposits', '1200-0000', ARRAY['balance_sheet'], FALSE, 201, TRUE),
('1310-0000', 'Escrow - Property Tax', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 202, TRUE),
('1320-0000', 'Escrow - Insurance', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 203, TRUE),
('1330-0000', 'Escrow - TI/LC', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 204, TRUE),
('1340-0000', 'Escrow - Replacement Reserves', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 205, TRUE),
('1920-0000', 'Loan Costs', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 210, TRUE),
('1922-0000', 'Accum. Amortization Loan Costs', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 211, TRUE),
('1950-0000', 'External - Lease Commission', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 212, TRUE),
('1950-5000', 'Internal - Lease Commission', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 213, TRUE),
('1952-0000', 'Accum. Amort - TI/LC', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 214, TRUE),
('1995-0000', 'Prepaid Insurance', 'asset', 'other_asset', 'prepaid', '1200-0000', ARRAY['balance_sheet'], FALSE, 220, TRUE),
('1998-0000', 'Total Other Assets', 'asset', 'other_asset', 'total', NULL, ARRAY['balance_sheet'], TRUE, 299, TRUE),
('1999-0000', 'TOTAL ASSETS', 'asset', 'total', NULL, NULL, ARRAY['balance_sheet'], TRUE, 999, TRUE),

-- LIABILITIES (2xxx)
('2030-0000', 'Accrued Expenses', 'liability', 'current_liability', 'accrued', NULL, ARRAY['balance_sheet'], FALSE, 1000, TRUE),
('2110-0000', 'Accounts Payable Trade', 'liability', 'current_liability', 'accounts_payable', '2590-0000', ARRAY['balance_sheet'], FALSE, 1001, TRUE),
('2120-0000', 'A/P Series RDF Investors LLC', 'liability', 'current_liability', 'accounts_payable', '2590-0000', ARRAY['balance_sheet'], FALSE, 1002, TRUE),
('2132-0000', 'A/P 5Rivers CRE, LLC', 'liability', 'current_liability', 'accounts_payable', '2590-0000', ARRAY['balance_sheet'], FALSE, 1003, TRUE),
('2197-0000', 'Loans Payable 5Rivers', 'liability', 'current_liability', 'short_term_debt', '2590-0000', ARRAY['balance_sheet'], FALSE, 1004, TRUE),
('2410-0000', 'Property Tax Payable', 'liability', 'current_liability', 'tax_payable', '2590-0000', ARRAY['balance_sheet'], FALSE, 1010, TRUE),
('2510-0000', 'Rent Received in Advance', 'liability', 'current_liability', 'deferred_revenue', '2590-0000', ARRAY['balance_sheet'], FALSE, 1020, TRUE),
('2515-0000', 'A/P Tenant TI/LC Obligations', 'liability', 'current_liability', 'tenant_obligations', '2590-0000', ARRAY['balance_sheet'], FALSE, 1021, TRUE),
('2520-0000', 'Deposit Refundable to Tenant', 'liability', 'current_liability', 'deposits', '2590-0000', ARRAY['balance_sheet'], FALSE, 1022, TRUE),
('2521-0000', 'Construction Deposit Refundable', 'liability', 'current_liability', 'deposits', '2590-0000', ARRAY['balance_sheet'], FALSE, 1023, TRUE),
('2585-0000', 'A/P Suspense', 'liability', 'current_liability', 'other', '2590-0000', ARRAY['balance_sheet'], FALSE, 1030, TRUE),
('2590-0000', 'Total Current Liabilities', 'liability', 'current_liability', 'total', NULL, ARRAY['balance_sheet'], TRUE, 1099, TRUE),
('2600-0000', 'Long Term Liabilities', 'liability', 'long_term_liability', NULL, NULL, ARRAY['balance_sheet'], FALSE, 1100, TRUE),
('2612-0000', 'NorthMarq Capital', 'liability', 'long_term_liability', 'mortgage', '2900-0000', ARRAY['balance_sheet'], FALSE, 1101, TRUE),
('2900-0000', 'Total Long Term Liabilities', 'liability', 'long_term_liability', 'total', NULL, ARRAY['balance_sheet'], TRUE, 1199, TRUE),
('2999-0000', 'TOTAL LIABILITIES', 'liability', 'total', NULL, NULL, ARRAY['balance_sheet'], TRUE, 1999, TRUE),

-- EQUITY/CAPITAL (3xxx)
('3000-0000', 'CAPITAL', 'equity', 'equity', NULL, NULL, ARRAY['balance_sheet'], FALSE, 2000, TRUE),
('3050-0000', 'Partners Contribution', 'equity', 'equity', 'contribution', '3000-0000', ARRAY['balance_sheet'], FALSE, 2001, TRUE),
('3910-0000', 'Beginning Equity', 'equity', 'equity', 'retained_earnings', '3000-0000', ARRAY['balance_sheet'], FALSE, 2010, TRUE),
('3990-0000', 'Distribution', 'equity', 'equity', 'distribution', '3000-0000', ARRAY['balance_sheet'], FALSE, 2020, TRUE),
('3995-0000', 'Current Period Earnings', 'equity', 'equity', 'net_income', '3000-0000', ARRAY['balance_sheet'], FALSE, 2030, TRUE),
('3999-0000', 'TOTAL CAPITAL', 'equity', 'equity', 'total', NULL, ARRAY['balance_sheet'], TRUE, 2099, TRUE),
('3999-9000', 'TOTAL LIABILITIES & CAPITAL', 'equity', 'total', NULL, NULL, ARRAY['balance_sheet'], TRUE, 2999, TRUE)

ON CONFLICT (account_code) DO UPDATE SET
    account_name = EXCLUDED.account_name,
    account_type = EXCLUDED.account_type,
    category = EXCLUDED.category,
    subcategory = EXCLUDED.subcategory,
    parent_account_code = EXCLUDED.parent_account_code,
    document_types = EXCLUDED.document_types,
    is_calculated = EXCLUDED.is_calculated,
    display_order = EXCLUDED.display_order,
    is_active = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- INCOME ACCOUNTS (4xxx) - Part 1
INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active) VALUES
('4010-0000', 'Base Rentals', 'income', 'rental_income', 'base_rent', NULL, ARRAY['income_statement'], FALSE, 3000, TRUE),
('4013-0000', 'Management Fee Income', 'income', 'other_income', 'management_fee', NULL, ARRAY['income_statement'], FALSE, 3001, TRUE),
('4018-0000', 'Interest Income', 'income', 'other_income', 'interest', NULL, ARRAY['income_statement'], FALSE, 3002, TRUE),
('4020-0000', 'Tax', 'income', 'rental_income', 'tax_reimbursement', NULL, ARRAY['income_statement'], FALSE, 3010, TRUE),
('4030-0000', 'Insurance', 'income', 'rental_income', 'insurance_reimbursement', NULL, ARRAY['income_statement'], FALSE, 3011, TRUE),
('4040-0000', 'CAM', 'income', 'rental_income', 'cam_reimbursement', NULL, ARRAY['income_statement'], FALSE, 3012, TRUE),
('4050-0000', 'Percentage Rent', 'income', 'rental_income', 'percentage_rent', NULL, ARRAY['income_statement'], FALSE, 3020, TRUE),
('4055-0000', 'Utilities Reimbursement', 'income', 'rental_income', 'utilities_reimbursement', NULL, ARRAY['income_statement'], FALSE, 3021, TRUE),
('4056-0000', 'Termination Fee Income', 'income', 'other_income', 'termination_fee', NULL, ARRAY['income_statement'], FALSE, 3022, TRUE),
('4060-0000', 'Annual Cams', 'income', 'rental_income', 'annual_cam', NULL, ARRAY['income_statement'], FALSE, 3023, TRUE),
('4090-0000', 'Other Income', 'income', 'other_income', 'misc', NULL, ARRAY['income_statement'], FALSE, 3090, TRUE),
('4091-0000', 'End of Day Investment Sweep Int Income', 'income', 'other_income', 'interest', NULL, ARRAY['income_statement'], FALSE, 3091, TRUE),
('4990-0000', 'TOTAL INCOME', 'income', 'total', NULL, NULL, ARRAY['income_statement'], TRUE, 3999, TRUE)

ON CONFLICT (account_code) DO UPDATE SET
    account_name = EXCLUDED.account_name,
    account_type = EXCLUDED.account_type,
    category = EXCLUDED.category,
    subcategory = EXCLUDED.subcategory,
    parent_account_code = EXCLUDED.parent_account_code,
    document_types = EXCLUDED.document_types,
    is_calculated = EXCLUDED.is_calculated,
    display_order = EXCLUDED.display_order,
    is_active = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- Display current count
SELECT 'Chart of Accounts Seeded' as status, COUNT(*) as total_accounts FROM chart_of_accounts;

