-- Balance Sheet Template v1.0 - Comprehensive Chart of Accounts (200+ accounts)
-- Based on Balance Sheet Extraction Requirements v1.0
-- Covers all accounts from ESP, HMND, TCSH, WEND properties

-- ==============================================================================
-- SECTION 1: CURRENT ASSETS (0100-0499)
-- ==============================================================================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active, expected_sign) VALUES

-- Header
('0100-0000', 'ASSETS', 'asset', 'header', NULL, NULL, ARRAY['balance_sheet'], TRUE, 1, TRUE, 'positive'),
('0101-0000', 'Current Assets', 'asset', 'current_asset', 'header', '0100-0000', ARRAY['balance_sheet'], FALSE, 2, TRUE, 'positive'),

-- Cash Accounts (0122-0125 series)
('0120-0000', 'Cash on Hand', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet'], FALSE, 10, TRUE, 'positive'),
('0121-0000', 'Cash - Savings', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet'], FALSE, 11, TRUE, 'positive'),
('0122-0000', 'Cash - Operating', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet'], FALSE, 12, TRUE, 'either'),
('0123-0000', 'Cash - Operating II', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet'], FALSE, 13, TRUE, 'positive'),
('0124-0000', 'Cash - Operating III WF', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet'], FALSE, 14, TRUE, 'positive'),
('0125-0000', 'Cash - Operating IV-PNC', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet'], FALSE, 15, TRUE, 'positive'),
('0126-0000', 'Cash - Depository - PNC', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet'], FALSE, 16, TRUE, 'positive'),
('0127-0000', 'Cash - Escrow - PNC', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet'], FALSE, 17, TRUE, 'positive'),
('0199-0000', 'Non-Cash (Adjustments)', 'asset', 'current_asset', 'adjustments', '0101-0000', ARRAY['balance_sheet'], FALSE, 19, TRUE, 'either'),

-- Receivables (0210-0347 series)
('0210-0000', 'Accounts Receivables - Trade', 'asset', 'current_asset', 'accounts_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 30, TRUE, 'positive'),
('0305-0000', 'A/R Tenants', 'asset', 'current_asset', 'accounts_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 40, TRUE, 'positive'),
('0306-0000', 'A/R - Allowance for Doubtful', 'asset', 'current_asset', 'accounts_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 41, TRUE, 'negative'),
('0307-0000', 'A/R Other', 'asset', 'current_asset', 'accounts_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 42, TRUE, 'positive'),
('0310-0000', 'Title Escrow/Lender App', 'asset', 'current_asset', 'accounts_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 43, TRUE, 'positive'),

-- Inter-Company Receivables (0315-0345 series)
('0315-0000', 'A/R Eastern Shore Plaza', 'asset', 'current_asset', 'intercompany_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 50, TRUE, 'positive'),
('0316-0000', 'A/R Frayser Village', 'asset', 'current_asset', 'intercompany_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 51, TRUE, 'positive'),
('0317-0000', 'A/R Hammond Aire LP', 'asset', 'current_asset', 'intercompany_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 52, TRUE, 'positive'),
('0318-0000', 'A/R TCSH, LP', 'asset', 'current_asset', 'intercompany_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 53, TRUE, 'positive'),
('0319-0000', 'A/R Wendover Commons LP', 'asset', 'current_asset', 'intercompany_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 54, TRUE, 'positive'),
('0320-0000', 'A/R Oxford Exchange, LP', 'asset', 'current_asset', 'intercompany_receivable', '0101-0000', ARRAY['balance_sheet'], FALSE, 55, TRUE, 'positive'),

-- Other Current Asset Items
('0347-0000', 'Escrow - Other', 'asset', 'current_asset', 'escrow', '0101-0000', ARRAY['balance_sheet'], FALSE, 80, TRUE, 'positive'),

-- Subtotal
('0499-9000', 'Total Current Assets', 'asset', 'current_asset', 'total', '0101-0000', ARRAY['balance_sheet'], TRUE, 99, TRUE, 'positive')

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
-- SECTION 2: PROPERTY & EQUIPMENT (0500-1099)
-- ==============================================================================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active, expected_sign) VALUES

-- Header
('0500-0000', 'Property & Equipment', 'asset', 'fixed_asset', 'header', '0100-0000', ARRAY['balance_sheet'], FALSE, 100, TRUE, 'positive'),

-- Fixed Assets - Gross Values
('0510-0000', 'Land', 'asset', 'fixed_asset', 'land', '0500-0000', ARRAY['balance_sheet'], FALSE, 110, TRUE, 'positive'),
('0610-0000', 'Buildings', 'asset', 'fixed_asset', 'buildings', '0500-0000', ARRAY['balance_sheet'], FALSE, 120, TRUE, 'positive'),

-- Improvements
('0710-0000', '5 Year Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 130, TRUE, 'positive'),
('0715-0000', '7 Year - Signage', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 131, TRUE, 'positive'),
('0810-0000', '15 Year Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 140, TRUE, 'positive'),
('0815-0000', '30 Year - Roof', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 141, TRUE, 'positive'),
('0816-0000', '30 Year - HVAC', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 142, TRUE, 'positive'),
('0910-0000', 'Other Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 150, TRUE, 'positive'),
('0912-0000', 'PARKING-LOT', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 151, TRUE, 'positive'),
('0950-0000', 'TI/Current Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 160, TRUE, 'positive'),
('0955-0000', 'White box / Spec Suites Major', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], FALSE, 161, TRUE, 'positive'),

-- Accumulated Depreciation (Contra-Asset Accounts)
('1061-0000', 'Accum. Depr. - Buildings', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 170, TRUE, 'negative'),
('1071-0000', 'Accum. Depr. 5 Year Impr.', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 171, TRUE, 'negative'),
('1081-0000', 'Accum. Depr. 15 Yr Impr.', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 172, TRUE, 'negative'),
('1082-0000', 'Accum. Depr.-15Yr-09Remodel', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 173, TRUE, 'negative'),
('1083-0000', 'Accum. Depr.-Roof2008', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 174, TRUE, 'negative'),
('1084-0000', 'Accum. Depr.-PL-2009', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 175, TRUE, 'negative'),
('1085-0000', 'Accum. Amort 2016ParkingLot7yrs', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 176, TRUE, 'negative'),
('1086-0000', 'Accum. Amort Roof 15 yrs 2016', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 177, TRUE, 'negative'),
('1087-0000', 'Accum. Amort 2017 Parking Lot 7 yrs', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 178, TRUE, 'negative'),
('1088-0000', 'Accum. Amort HVAC 30 yrs', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 179, TRUE, 'negative'),
('1091-0000', 'Accum. Depr.-Other Imp.', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], FALSE, 180, TRUE, 'negative'),

-- Subtotal
('1099-0000', 'Total Property & Equipment', 'asset', 'fixed_asset', 'total', '0500-0000', ARRAY['balance_sheet'], TRUE, 199, TRUE, 'positive')

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
-- SECTION 3: OTHER ASSETS (1200-1998)
-- ==============================================================================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active, expected_sign) VALUES

-- Header
('1200-0000', 'Other Assets', 'asset', 'other_asset', 'header', '0100-0000', ARRAY['balance_sheet'], FALSE, 200, TRUE, 'positive'),

-- Deposits
('1210-0000', 'Deposits', 'asset', 'other_asset', 'deposits', '1200-0000', ARRAY['balance_sheet'], FALSE, 210, TRUE, 'positive'),

-- Escrow Accounts (1310-1340 series)
('1310-0000', 'Escrow - Property Tax', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 220, TRUE, 'positive'),
('1320-0000', 'Escrow - Insurance', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 221, TRUE, 'positive'),
('1330-0000', 'Escrow - TI/LC', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 222, TRUE, 'positive'),
('1330-1000', 'Escrow TI/LC Kroger', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 223, TRUE, 'positive'),
('1330-1001', 'Escrow TI/LC SavALot', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 224, TRUE, 'positive'),
('1330-2000', 'Escrow - TI/LC acct 2', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 225, TRUE, 'positive'),
('1340-0000', 'Escrow - Replacement Reserves', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 226, TRUE, 'positive'),
('1341-0000', 'Escrow-Insurance Loss Reserve', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 227, TRUE, 'positive'),
('1342-0000', 'Escrow - Sweep Account', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], FALSE, 228, TRUE, 'positive'),

-- Intangible Assets (1910-1922 series)
('1910-0000', 'Organization Cost', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 240, TRUE, 'positive'),
('1911-0000', 'Accum. Amortization Org. Cost', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 241, TRUE, 'negative'),
('1920-0000', 'Loan Costs', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 242, TRUE, 'positive'),
('1922-0000', 'Accum. Amortization Loan Costs', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 243, TRUE, 'negative'),
('1923-0000', 'Accumulated Amortisation', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 244, TRUE, 'negative'),
('1924-0000', 'Closing Costs', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 245, TRUE, 'positive'),
('1925-0000', 'Loan Costs - Consolidated', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 246, TRUE, 'positive'),

-- Leasing Costs (1950-1952 series)
('1950-0000', 'External - Lease Commission', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 250, TRUE, 'positive'),
('1950-5000', 'Internal - Lease Commission', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 251, TRUE, 'positive'),
('1952-0000', 'Accum. Amort - TI/LC', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], FALSE, 252, TRUE, 'negative'),

-- Prepaid & Other (1995-1997 series)
('1995-0000', 'Prepaid Insurance', 'asset', 'other_asset', 'prepaid', '1200-0000', ARRAY['balance_sheet'], FALSE, 260, TRUE, 'positive'),
('1997-0000', 'Prepaid Expenses', 'asset', 'other_asset', 'prepaid', '1200-0000', ARRAY['balance_sheet'], FALSE, 261, TRUE, 'positive'),
('1997-1000', '1031 Intermediary Escrow', 'asset', 'other_asset', 'other', '1200-0000', ARRAY['balance_sheet'], FALSE, 262, TRUE, 'positive'),
('1997-2000', 'Sales Contract', 'asset', 'other_asset', 'other', '1200-0000', ARRAY['balance_sheet'], FALSE, 263, TRUE, 'positive'),
('1997-3000', 'Selling Cost', 'asset', 'other_asset', 'other', '1200-0000', ARRAY['balance_sheet'], FALSE, 264, TRUE, 'positive'),
('1997-4000', 'Other Receivables', 'asset', 'other_asset', 'other', '1200-0000', ARRAY['balance_sheet'], FALSE, 265, TRUE, 'positive'),
('1997-5000', 'Receivable from Nuveen-Fayette', 'asset', 'other_asset', 'other', '1200-0000', ARRAY['balance_sheet'], FALSE, 266, TRUE, 'positive'),

-- Subtotal
('1998-0000', 'Total Other Assets', 'asset', 'other_asset', 'total', '1200-0000', ARRAY['balance_sheet'], TRUE, 299, TRUE, 'positive'),

-- TOTAL ASSETS
('1999-0000', 'TOTAL ASSETS', 'asset', 'total', NULL, '0100-0000', ARRAY['balance_sheet'], TRUE, 999, TRUE, 'positive')

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
-- SECTION 4: CURRENT LIABILITIES (2001-2590)
-- ==============================================================================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active, expected_sign) VALUES

-- Header
('2000-0000', 'LIABILITIES', 'liability', 'header', NULL, NULL, ARRAY['balance_sheet'], FALSE, 1000, TRUE, 'positive'),
('2001-0000', 'Current Liabilities', 'liability', 'current_liability', 'header', '2000-0000', ARRAY['balance_sheet'], FALSE, 1001, TRUE, 'positive'),

-- Accrued & Payables
('2030-0000', 'Accrued Expenses', 'liability', 'current_liability', 'accrued', '2001-0000', ARRAY['balance_sheet'], FALSE, 1010, TRUE, 'positive'),
('2035-0000', 'Due to Seller', 'liability', 'current_liability', 'accrued', '2001-0000', ARRAY['balance_sheet'], FALSE, 1011, TRUE, 'positive'),
('2110-0000', 'Accounts Payable Trade', 'liability', 'current_liability', 'accounts_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1020, TRUE, 'positive'),
('2120-0000', 'A/P Series RDF Investors LLC', 'liability', 'current_liability', 'accounts_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1021, TRUE, 'positive'),
('2121-0000', 'A/P Other', 'liability', 'current_liability', 'accounts_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1022, TRUE, 'positive'),
('2131-0000', 'A/P Com Realty (Do not Use)', 'liability', 'current_liability', 'accounts_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1023, FALSE, 'positive'),
('2132-0000', 'A/P 5Rivers CRE, LLC', 'liability', 'current_liability', 'accounts_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1024, TRUE, 'positive'),

-- Inter-Company Payables (2135-2180 series)
('2135-0000', 'A/P Frayser Village', 'liability', 'current_liability', 'intercompany_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1030, TRUE, 'positive'),
('2136-0000', 'A/P Eastern Shore Plaza', 'liability', 'current_liability', 'intercompany_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1031, TRUE, 'positive'),
('2137-0000', 'A/P TCSH, LLC', 'liability', 'current_liability', 'intercompany_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1032, TRUE, 'positive'),
('2138-0000', 'A/P Oxford Exchange, LP', 'liability', 'current_liability', 'intercompany_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1033, TRUE, 'positive'),
('2139-0000', 'A/P Wendover Commons LP', 'liability', 'current_liability', 'intercompany_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1034, TRUE, 'positive'),
('2140-0000', 'A/P Hammond Aire LP', 'liability', 'current_liability', 'intercompany_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1035, TRUE, 'positive'),

-- Other Current Liabilities
('2139-0001', 'Insurance Claim', 'liability', 'current_liability', 'other', '2001-0000', ARRAY['balance_sheet'], FALSE, 1045, TRUE, 'positive'),
('2197-0000', 'Loans Payable 5Rivers', 'liability', 'current_liability', 'short_term_debt', '2001-0000', ARRAY['balance_sheet'], FALSE, 1050, TRUE, 'positive'),
('2410-0000', 'Property Tax Payable', 'liability', 'current_liability', 'tax_payable', '2001-0000', ARRAY['balance_sheet'], FALSE, 1060, TRUE, 'positive'),
('2411-0000', 'Current Portion of LTD', 'liability', 'current_liability', 'short_term_debt', '2001-0000', ARRAY['balance_sheet'], FALSE, 1061, TRUE, 'positive'),

-- Tenant-Related Liabilities
('2510-0000', 'Rent Received in Advance', 'liability', 'current_liability', 'deferred_revenue', '2001-0000', ARRAY['balance_sheet'], FALSE, 1070, TRUE, 'positive'),
('2515-0000', 'A/P Tenant TI/LC Obligations', 'liability', 'current_liability', 'tenant_obligations', '2001-0000', ARRAY['balance_sheet'], FALSE, 1071, TRUE, 'positive'),
('2520-0000', 'Deposit Refundable to Tenant', 'liability', 'current_liability', 'deposits', '2001-0000', ARRAY['balance_sheet'], FALSE, 1072, TRUE, 'positive'),
('2521-0000', 'Construction Deposit Refundable', 'liability', 'current_liability', 'deposits', '2001-0000', ARRAY['balance_sheet'], FALSE, 1073, TRUE, 'positive'),
('2522-0000', 'Deposit Clearing (System Use)', 'liability', 'current_liability', 'deposits', '2001-0000', ARRAY['balance_sheet'], FALSE, 1074, TRUE, 'positive'),
('2523-0000', 'Partners'' GFDs/Deposit', 'liability', 'current_liability', 'deposits', '2001-0000', ARRAY['balance_sheet'], FALSE, 1075, TRUE, 'positive'),

-- Suspense & Other
('2585-0000', 'A/P Suspense', 'liability', 'current_liability', 'other', '2001-0000', ARRAY['balance_sheet'], FALSE, 1080, TRUE, 'positive'),
('2586-0000', 'A/P 1031 Exchange', 'liability', 'current_liability', 'other', '2001-0000', ARRAY['balance_sheet'], FALSE, 1081, TRUE, 'positive'),
('2587-0000', 'A/P Data Center Entity', 'liability', 'current_liability', 'other', '2001-0000', ARRAY['balance_sheet'], FALSE, 1082, TRUE, 'positive'),

-- Subtotal
('2590-0000', 'Total Current Liabilities', 'liability', 'current_liability', 'total', '2001-0000', ARRAY['balance_sheet'], TRUE, 1099, TRUE, 'positive')

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

-- Continue in next part due to length...

