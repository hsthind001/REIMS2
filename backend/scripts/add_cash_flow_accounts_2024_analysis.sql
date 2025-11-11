--
-- Add Missing Cash Flow Accounts to Chart of Accounts
-- Based on analysis of 188 unmatched accounts from 2023-2024 cash flow statements
-- 
-- These are cash flow specific accounts for:
-- - Non-cash adjustments (depreciation, amortization)
-- - Escrow accounts
-- - Inter-property accounts payable/receivable
-- - Property-specific expense categories
--

-- ==================== ADJUSTMENTS & NON-CASH ITEMS ====================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, document_types, is_active, display_order) VALUES
('9100-0000', 'Non-Cash (Adjustments)', 'expense', 'ADJUSTMENTS', 'Cash Flow Adjustments', ARRAY['cash_flow'], TRUE, 9100),
('9110-0000', 'Accumulated Depreciation', 'expense', 'ADJUSTMENTS', 'Cash Flow Adjustments', ARRAY['cash_flow', 'balance_sheet'], TRUE, 9110),
('9111-0000', 'Accumulated Dep', 'expense', 'ADJUSTMENTS', 'Cash Flow Adjustments', ARRAY['cash_flow'], TRUE, 9111),
('9120-0000', 'Accumulated Amortisation', 'expense', 'ADJUSTMENTS', 'Cash Flow Adjustments', ARRAY['cash_flow'], TRUE, 9120),
('9900-0000', 'UN-Used - FUTURE Use', 'expense', 'OTHER', 'Placeholder', ARRAY['cash_flow'], TRUE, 9900),

-- ==================== ESCROW ACCOUNTS ====================

('1350-0000', 'Escrow - Other', 'asset', 'ASSETS', 'Escrow Accounts', ARRAY['balance_sheet', 'cash_flow'], TRUE, 1350),

-- ==================== ACQUISITION & DEVELOPMENT ====================

('6041-0000', 'Acquisitions Software', 'expense', 'EXPENSES', 'Leasing Expenses', ARRAY['cash_flow'], TRUE, 6041),
('6042-0000', 'Acquisition Surveys', 'expense', 'EXPENSES', 'Leasing Expenses', ARRAY['cash_flow'], TRUE, 6042),
('6043-0000', 'Acquisitions Expense', 'expense', 'EXPENSES', 'Leasing Expenses', ARRAY['cash_flow'], TRUE, 6043),

-- ==================== ADVERTISING ====================

('5411-0000', 'Advertising - Digital', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5411),
('5412-0000', 'Advertising - Printed Media', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5412),
('5413-0000', 'Advertising - Other', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5413),

-- ==================== ADMINISTRATIVE SERVICES ====================

('5421-0000', 'Answering Service', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5421),
('4090-0000', 'Admin Fee Income', 'income', 'INCOME', 'Other Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4090),

-- ==================== INTER-PROPERTY ACCOUNTS PAYABLE ====================
-- Note: These are consolidation accounts for multi-property portfolios

('2510-0001', 'A/P ALCOA HC, LP (Hamilton)', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2510),
('2510-0002', 'A/P Bartleslville', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2511),
('2510-0003', 'A/P Boulevard (LA3)', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2512),
('2510-0004', 'A/P Chalmette Mall, LP', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2513),
('2510-0005', 'A/P Com Realty (Do not Use)', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], FALSE, 2514),
('2510-0006', 'A/P CountryClub (LA3)', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2515),
('2510-0007', 'A/P Crossing Center (LA3)', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2516),
('2510-0008', 'A/P Desiard Plaza, LTD', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2517),
('2510-0009', 'A/P Dr. H S Azad', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2518),
('2510-0010', 'A/P Eastern Shore Plaza', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2519),
('2510-0011', 'A/P Fayette Pavilion', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2520),
('2510-0012', 'A/P Frayser Center', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2521),
('2510-0013', 'A/P Frayser Plaza', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2522),
('2510-0014', 'A/P Frayser Village', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2523),
('2510-0015', 'A/P GBP Partners, LTD', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2524),
('2510-0016', 'Anis Charnia', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2525)

ON CONFLICT (account_code) DO NOTHING;

-- Create summary stats
SELECT 'Cash flow accounts added successfully' as result;
SELECT COUNT(*) as new_accounts_added FROM chart_of_accounts WHERE account_code LIKE '9%' OR account_code LIKE '2510-%';

