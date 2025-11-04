-- Income Statement Template v1.0 - Part 2: Additional Expenses, Other Expenses, Totals

-- ==============================================================================
-- SECTION 3: ADDITIONAL OPERATING EXPENSES (6000-6199)
-- ==============================================================================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active, expected_sign) VALUES

-- Management Fees
('6010-0000', 'Off Site Management', 'expense', 'additional_expense', 'management', NULL, ARRAY['income_statement'], FALSE, 6010, TRUE, 'positive'),
('6010-5000', 'On-Site Management Fee', 'expense', 'additional_expense', 'management', NULL, ARRAY['income_statement'], FALSE, 6015, TRUE, 'positive'),

-- Taxes
('6012-0000', 'Franchise Tax', 'expense', 'additional_expense', 'taxes', NULL, ARRAY['income_statement'], FALSE, 6012, TRUE, 'positive'),
('6012-5000', 'Pass Thru Entity Tax', 'expense', 'additional_expense', 'taxes', NULL, ARRAY['income_statement'], FALSE, 6012, TRUE, 'positive'),

-- Leasing
('6014-0000', 'Leasing Commissions', 'expense', 'additional_expense', 'leasing', NULL, ARRAY['income_statement'], FALSE, 6014, TRUE, 'positive'),
('6016-0000', 'Tenant Improvements', 'expense', 'additional_expense', 'leasing', NULL, ARRAY['income_statement'], FALSE, 6016, TRUE, 'positive'),

-- Professional Fees
('6020-0000', 'Professional Fees', 'expense', 'additional_expense', 'professional', NULL, ARRAY['income_statement'], FALSE, 6020, TRUE, 'positive'),
('6020-5000', 'Accounting Fee', 'expense', 'additional_expense', 'professional', NULL, ARRAY['income_statement'], FALSE, 6025, TRUE, 'positive'),
('6020-6000', 'Asset Management Fee', 'expense', 'additional_expense', 'professional', NULL, ARRAY['income_statement'], FALSE, 6026, TRUE, 'positive'),
('6020-7000', 'CMF-Construction Management Fee', 'expense', 'additional_expense', 'professional', NULL, ARRAY['income_statement'], FALSE, 6027, TRUE, 'positive'),
('6022-0000', 'Legal Fees / SOS Fee', 'expense', 'additional_expense', 'professional', NULL, ARRAY['income_statement'], FALSE, 6022, TRUE, 'positive'),

-- Bank Charges
('6024-0000', 'Bank Charges', 'expense', 'additional_expense', 'bank_charges', NULL, ARRAY['income_statement'], FALSE, 6024, TRUE, 'positive'),
('6025-0000', 'Bank Control A/c Fee', 'expense', 'additional_expense', 'bank_charges', NULL, ARRAY['income_statement'], FALSE, 6025, TRUE, 'positive'),

-- G. Landlord Expenses (6040-6069)
('6050-0000', 'LL Repairs & Maintenance', 'expense', 'additional_expense', 'landlord', NULL, ARRAY['income_statement'], FALSE, 6050, TRUE, 'positive'),
('6051-0000', 'LL - Plumbing', 'expense', 'additional_expense', 'landlord', NULL, ARRAY['income_statement'], FALSE, 6051, TRUE, 'positive'),
('6052-0000', 'LL - Electrical Repairs', 'expense', 'additional_expense', 'landlord', NULL, ARRAY['income_statement'], FALSE, 6052, TRUE, 'positive'),
('6054-0000', 'LL - HVAC Repairs', 'expense', 'additional_expense', 'landlord', NULL, ARRAY['income_statement'], FALSE, 6054, TRUE, 'positive'),
('6058-0000', 'LL - Vacant Space Expenses', 'expense', 'additional_expense', 'landlord', NULL, ARRAY['income_statement'], FALSE, 6058, TRUE, 'positive'),
('6059-0000', 'LL - General Repairs', 'expense', 'additional_expense', 'landlord', NULL, ARRAY['income_statement'], FALSE, 6059, TRUE, 'positive'),
('6061-0000', 'LL - Electricity', 'expense', 'additional_expense', 'landlord', NULL, ARRAY['income_statement'], FALSE, 6061, TRUE, 'positive'),
('6064-0000', 'LL-Misc', 'expense', 'additional_expense', 'landlord', NULL, ARRAY['income_statement'], FALSE, 6064, TRUE, 'positive'),
('6065-0000', 'LL-Site Map', 'expense', 'additional_expense', 'landlord', NULL, ARRAY['income_statement'], FALSE, 6065, TRUE, 'positive'),
('6069-0000', 'Total LL Expense', 'expense', 'additional_expense', 'landlord', NULL, ARRAY['income_statement'], TRUE, 6069, TRUE, 'positive'),

-- H. Total Additional Operating Expenses
('6190-0000', 'Total Additional Operating Expenses', 'expense', 'additional_expense', 'total', NULL, ARRAY['income_statement'], TRUE, 6190, TRUE, 'positive'),

-- Total Expenses
('6199-0000', 'TOTAL EXPENSES', 'expense', 'total', NULL, NULL, ARRAY['income_statement'], TRUE, 6199, TRUE, 'positive')

ON CONFLICT (account_code) DO UPDATE SET
    account_name = EXCLUDED.account_name,
    account_type = EXCLUDED.account_type,
    category = EXCLUDED.category,
    subcategory = EXCLUDED.subcategory,
    parent_account_code = EXCLUDED.parent_account_code,
    document_types = EXCLUDED.document_types,
    is_calculated = EXCLUDED.is_calculated,
    display_order = EXCLUDED.display_order,
    expected_sign = EXCLUDED.expected_sign,
    is_active = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- ==============================================================================
-- SECTION 4: NET OPERATING INCOME & OTHER EXPENSES
-- ==============================================================================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active, expected_sign) VALUES

-- Net Operating Income (NOI)
('6299-0000', 'NET OPERATING INCOME', 'income', 'noi', NULL, NULL, ARRAY['income_statement'], TRUE, 6299, TRUE, 'positive'),

-- Other Income/Expenses (Below the Line) - 7000 series
('7010-0000', 'Mortgage Interest', 'expense', 'other_expense', 'interest', NULL, ARRAY['income_statement'], FALSE, 7010, TRUE, 'positive'),
('7020-0000', 'Depreciation', 'expense', 'other_expense', 'depreciation', NULL, ARRAY['income_statement'], FALSE, 7020, TRUE, 'positive'),
('7030-0000', 'Amortization', 'expense', 'other_expense', 'amortization', NULL, ARRAY['income_statement'], FALSE, 7030, TRUE, 'positive'),
('7090-0000', 'Total Other Income/Expense', 'expense', 'other_expense', 'total', NULL, ARRAY['income_statement'], TRUE, 7090, TRUE, 'positive'),

-- Net Income (Bottom Line)
('9090-0000', 'NET INCOME', 'income', 'net_income', NULL, NULL, ARRAY['income_statement'], TRUE, 9090, TRUE, 'either')

ON CONFLICT (account_code) DO UPDATE SET
    account_name = EXCLUDED.account_name,
    account_type = EXCLUDED.account_type,
    category = EXCLUDED.category,
    subcategory = EXCLUDED.subcategory,
    parent_account_code = EXCLUDED.parent_account_code,
    document_types = EXCLUDED.document_types,
    is_calculated = EXCLUDED.is_calculated,
    display_order = EXCLUDED.display_order,
    expected_sign = EXCLUDED.expected_sign,
    is_active = TRUE,
    updated_at = CURRENT_TIMESTAMP;

-- ==============================================================================
-- SUMMARY
-- ==============================================================================

-- Display seeded account counts
SELECT 
    'Income Statement Template v1.0 Accounts Seeded' as status,
    COUNT(*) as total_accounts,
    COUNT(*) FILTER (WHERE is_active = TRUE) as active_accounts,
    COUNT(*) FILTER (WHERE is_calculated = TRUE) as calculated_accounts
FROM chart_of_accounts 
WHERE document_types @> ARRAY['income_statement'];

SELECT 
    category,
    subcategory,
    COUNT(*) as account_count
FROM chart_of_accounts
WHERE document_types @> ARRAY['income_statement'] AND is_active = TRUE
GROUP BY category, subcategory
ORDER BY category, subcategory;

