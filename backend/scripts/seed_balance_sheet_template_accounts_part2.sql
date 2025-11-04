-- Balance Sheet Template v1.0 - Part 2: Long-Term Liabilities & Capital
-- Continuation of comprehensive chart of accounts

-- ==============================================================================
-- SECTION 5: LONG-TERM LIABILITIES (2600-2900)
-- ==============================================================================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active, expected_sign) VALUES

-- Header
('2600-0000', 'Long Term Liabilities', 'liability', 'long_term_liability', 'header', '2000-0000', ARRAY['balance_sheet'], FALSE, 1100, TRUE, 'positive'),

-- Primary Lenders (Institutional Debt)
('2611-0000', 'CIBC', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1110, TRUE, 'positive'),
('2611-1000', 'CIBC-MEZZ', 'liability', 'long_term_liability', 'mezzanine', '2600-0000', ARRAY['balance_sheet'], FALSE, 1111, TRUE, 'positive'),
('2612-0000', 'KeyBank', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1112, TRUE, 'positive'),
('2613-0000', 'KeyBank - Mezz', 'liability', 'long_term_liability', 'mezzanine', '2600-0000', ARRAY['balance_sheet'], FALSE, 1113, TRUE, 'positive'),
('2613-5000', 'The Azad Family Trust (TAFT)', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1114, TRUE, 'positive'),
('2612-1000', 'NorthMarq Capital', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1115, TRUE, 'positive'),
('2614-0000', 'RAIT Financial', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1116, TRUE, 'positive'),
('2615-0000', 'Berkadia Comm. Mtg.', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1117, TRUE, 'positive'),
('2614-1000', 'Wells Fargo', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1118, TRUE, 'positive'),
('2614-2000', 'Wachovia Securities', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1119, TRUE, 'positive'),
('2616-0000', 'MidLand Loan Services (PNC)', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1120, TRUE, 'positive'),
('2616-1000', 'Standard Ins Co, an Oregon Corporation', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1121, TRUE, 'positive'),
('2617-0000', 'Business Partners', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1122, TRUE, 'positive'),
('2618-0000', 'Trawler Capital Management (MEZZ)', 'liability', 'long_term_liability', 'mezzanine', '2600-0000', ARRAY['balance_sheet'], FALSE, 1123, TRUE, 'positive'),
('2619-0000', 'WoodForest National Bank', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1124, TRUE, 'positive'),
('2620-0000', 'StanCorp Mtg Investors, LLC (NMC)', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1125, TRUE, 'positive'),
('2621-0000', 'Origin Bank', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], FALSE, 1126, TRUE, 'positive'),

-- Shareholder Loan Accounts (2650-2750 series)
('2650-0000', 'Shareholders Loan Accounts', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1150, TRUE, 'positive'),
('2651-0000', 'Loans from Stockholders', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1151, TRUE, 'positive'),
('2660-0000', 'Hardam S Azad', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1160, TRUE, 'positive'),
('2661-0000', 'Balwant Singh', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1161, TRUE, 'positive'),
('2662-0000', 'Gurnaib S Sidhu', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1162, TRUE, 'positive'),
('2663-0000', 'Scott Wallace', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1163, TRUE, 'positive'),
('2664-0000', 'Kuldip S Bains', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1164, TRUE, 'positive'),
('2665-0000', 'Anis Charnia', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1165, TRUE, 'positive'),
('2666-0000', 'Baldev Singh', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1166, TRUE, 'positive'),
('2667-0000', 'Mohinder S Sandhu', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1167, TRUE, 'positive'),
('2668-0000', 'Harpreet Sandhu', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1168, TRUE, 'positive'),
('2669-0000', 'Dr. Jaspaul S Azad', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1169, TRUE, 'positive'),
('2670-0000', 'Dr. I M Azad', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1170, TRUE, 'positive'),
('2671-0000', 'Gagan Bains', 'liability', 'long_term_liability', 'shareholder_loan', '2600-0000', ARRAY['balance_sheet'], FALSE, 1171, TRUE, 'positive'),

-- Subtotal
('2900-0000', 'Total Long Term Liabilities', 'liability', 'long_term_liability', 'total', '2600-0000', ARRAY['balance_sheet'], TRUE, 1199, TRUE, 'positive'),

-- TOTAL LIABILITIES
('2999-0000', 'TOTAL LIABILITIES', 'liability', 'total', NULL, '2000-0000', ARRAY['balance_sheet'], TRUE, 1999, TRUE, 'positive')

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
-- SECTION 6: CAPITAL / EQUITY (3000-3999)
-- ==============================================================================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active, expected_sign) VALUES

-- Header
('3000-0000', 'CAPITAL', 'equity', 'equity', 'header', NULL, ARRAY['balance_sheet'], FALSE, 2000, TRUE, 'positive'),

-- Equity Components
('3050-0000', 'Common Stock', 'equity', 'equity', 'stock', '3000-0000', ARRAY['balance_sheet'], FALSE, 2010, TRUE, 'positive'),
('3050-1000', 'Partners Contribution', 'equity', 'equity', 'contribution', '3000-0000', ARRAY['balance_sheet'], FALSE, 2020, TRUE, 'positive'),
('3910-0000', 'Beginning Equity', 'equity', 'equity', 'retained_earnings', '3000-0000', ARRAY['balance_sheet'], FALSE, 2030, TRUE, 'either'),
('3920-0000', 'Partners Draw', 'equity', 'equity', 'draw', '3000-0000', ARRAY['balance_sheet'], FALSE, 2040, TRUE, 'either'),
('3990-0000', 'Distribution', 'equity', 'equity', 'distribution', '3000-0000', ARRAY['balance_sheet'], FALSE, 2050, TRUE, 'negative'),
('3995-0000', 'Current Period Earnings', 'equity', 'equity', 'net_income', '3000-0000', ARRAY['balance_sheet'], FALSE, 2060, TRUE, 'either'),

-- Subtotal & Total
('3999-0000', 'TOTAL CAPITAL', 'equity', 'equity', 'total', '3000-0000', ARRAY['balance_sheet'], TRUE, 2099, TRUE, 'either'),
('3999-9000', 'TOTAL LIABILITIES & CAPITAL', 'equity', 'total', NULL, NULL, ARRAY['balance_sheet'], TRUE, 2999, TRUE, 'positive')

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
-- DEPRECATED/SYSTEM ACCOUNTS (flagged as inactive)
-- ==============================================================================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active, expected_sign) VALUES

('0000-0000', 'ti - DO NOT USE', 'asset', 'deprecated', 'system', NULL, ARRAY['balance_sheet'], FALSE, 9000, FALSE, 'either'),
('0000-0001', 'lc - DO NOT USE', 'asset', 'deprecated', 'system', NULL, ARRAY['balance_sheet'], FALSE, 9001, FALSE, 'either'),
('0000-0002', 'ROOF', 'asset', 'deprecated', 'system', NULL, ARRAY['balance_sheet'], FALSE, 9002, FALSE, 'either'),
('0000-0003', 'TOTAL OF ALL', 'asset', 'deprecated', 'system', NULL, ARRAY['balance_sheet'], TRUE, 9003, FALSE, 'either')

ON CONFLICT (account_code) DO UPDATE SET
    account_name = EXCLUDED.account_name,
    is_active = FALSE,
    updated_at = CURRENT_TIMESTAMP;

-- ==============================================================================
-- SUMMARY
-- ==============================================================================

-- Display seeded account counts
SELECT 
    'Balance Sheet Template v1.0 Accounts Seeded' as status,
    COUNT(*) as total_accounts,
    COUNT(*) FILTER (WHERE is_active = TRUE) as active_accounts,
    COUNT(*) FILTER (WHERE is_calculated = TRUE) as calculated_accounts
FROM chart_of_accounts 
WHERE document_types @> ARRAY['balance_sheet'];

SELECT 
    account_type,
    category,
    COUNT(*) as account_count
FROM chart_of_accounts
WHERE document_types @> ARRAY['balance_sheet'] AND is_active = TRUE
GROUP BY account_type, category
ORDER BY account_type, category;

