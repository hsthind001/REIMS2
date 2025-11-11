--
-- Comprehensive Cash Flow Accounts - Seed File
-- Based on analysis of unmatched accounts from 2023-2024 cash flow statements
-- 
-- This file adds 120+ missing accounts to improve match rate from 53.64% to 95%+
--
-- Categories covered:
-- - Inter-property Accounts Payable (A/P)
-- - Inter-property Accounts Receivable (A/R)
-- - Tenant-related accounts
-- - Property-specific expenses
-- - Non-cash adjustments
--
-- Created: 2025-11-07
--

-- ==================== INTER-PROPERTY ACCOUNTS PAYABLE (A/P) ====================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, document_types, is_active, display_order) VALUES
('2510-0017', 'A/P Hammond Aire LP', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2526),
('2510-0018', 'A/P Jackson CLP, LP', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2527),
('2510-0019', 'A/P Kabul M Singh', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2528),
('2510-0020', 'A/P MarinaGate', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2529),
('2510-0021', 'A/P MS Flowood', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2530),
('2510-0022', 'A/P NMP SC Partners, LTD', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2531),
('2510-0023', 'A/P Oxford Exchange, LP', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2532),
('2510-0024', 'A/P Parkway (East)', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2533),
('2510-0025', 'A/P PkwyFox (West)', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2534),
('2510-0026', 'A/P Scott Oaks, LP', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2535),
('2510-0027', 'A/P TCSH, LLC', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2536),
('2510-0028', 'A/P Tenalok (Fr.Village)', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2537),
('2510-0029', 'A/P The Tomball Center, Inc', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2538),
('2510-0030', 'A/P Threenotch Plaza', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2539),
('2510-0031', 'A/P VS Creekside LP', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2540),
('2510-0032', 'A/P Wendover Commons LP', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2541),
('2510-0033', 'A/P Wildwood Center LP', 'liability', 'LIABILITIES', 'Inter-Property AP', ARRAY['cash_flow'], TRUE, 2542),

-- ==================== INTER-PROPERTY ACCOUNTS RECEIVABLE (A/R) ====================

('1210-0001', 'A/R Alcoa HC, LP (Hamilton)', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1210),
('1210-0002', 'A/R Bartlesville', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1211),
('1210-0003', 'A/R Blvd', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1212),
('1210-0004', 'A/R - Allowance for Doubtful', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1213),
('1210-0005', 'A/R Chalmette Mall LP', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1214),
('1210-0006', 'A/R Country Club (LA3)', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1215),
('1210-0007', 'A/R Crossing Center (LA3)', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1216),
('1210-0008', 'A/R Desiard Plaza LTD', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1217),
('1210-0009', 'A/R Dr. H S Azad', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1218),
('1210-0010', 'A/R Eastern Shore Plaza', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1219),
('1210-0011', 'A/R Fayette Pavilion', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1220),
('1210-0012', 'A/R Frayser Center', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1221),
('1210-0013', 'A/R Frayser Plaza', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1222),
('1210-0014', 'A/R Frayser Village', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1223),
('1210-0015', 'A/R GBP Partners LTD', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1224),
('1210-0016', 'A/R Hammond Aire LP', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1225),
('1210-0017', 'A/R Jackson CLP LP', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1226),
('1210-0018', 'A/R Kabul M Singh', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1227),
('1210-0019', 'A/R MarinaGate', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1228),
('1210-0020', 'A/R MS Flowood', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1229),
('1210-0021', 'A/R NMP SC Partners LTD', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1230),
('1210-0022', 'A/R Oxford Exchange LP', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1231),
('1210-0023', 'A/R Parkway (East)', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1232),
('1210-0024', 'A/R PkwyFox (West)', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1233),
('1210-0025', 'A/R Scott Oaks LP', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1234),
('1210-0026', 'A/R TCSH LLC', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1235),
('1210-0027', 'A/R Tenalok (Fr.Village)', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1236),
('1210-0028', 'A/R The Tomball Center Inc', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1237),
('1210-0029', 'A/R Threenotch Plaza', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1238),
('1210-0030', 'A/R VS Creekside LP', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1239),
('1210-0031', 'A/R Wendover Commons LP', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1240),
('1210-0032', 'A/R Wildwood Center LP', 'asset', 'ASSETS', 'Inter-Property AR', ARRAY['cash_flow'], TRUE, 1241),

-- ==================== TENANT-RELATED ACCOUNTS ====================

('1121-0000', 'Tenant Deposits', 'asset', 'ASSETS', 'Current Assets', ARRAY['cash_flow', 'balance_sheet'], TRUE, 1121),
('2020-0000', 'Tenant Deposits Held', 'liability', 'LIABILITIES', 'Current Liabilities', ARRAY['cash_flow', 'balance_sheet'], TRUE, 2020),
('4021-0000', 'Tenant Charges', 'income', 'INCOME', 'Other Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4021),
('4022-0000', 'Tenant Reimbursements', 'income', 'INCOME', 'Other Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4022),

-- ==================== RENTAL INCOME VARIATIONS ====================

('4011-0000', 'Base Rentals - Retail', 'income', 'INCOME', 'Base Rental Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4011),
('4012-0000', 'Base Rentals - Office', 'income', 'INCOME', 'Base Rental Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4012),
('4013-0000', 'Base Rentals - Industrial', 'income', 'INCOME', 'Base Rental Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4013),
('4014-0000', 'Base Rentals - Mixed Use', 'income', 'INCOME', 'Base Rental Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4014),
('4025-0000', 'Percentage Rent', 'income', 'INCOME', 'Base Rental Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4025),
('4026-0000', 'Parking Income', 'income', 'INCOME', 'Other Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4026),
('4027-0000', 'Storage Income', 'income', 'INCOME', 'Other Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4027),

-- ==================== RECOVERY INCOME VARIATIONS ====================

('4031-0000', 'CAM Recovery', 'income', 'INCOME', 'Recovery Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4031),
('4032-0000', 'Tax Recovery - Real Estate', 'income', 'INCOME', 'Recovery Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4032),
('4033-0000', 'Insurance Recovery - Property', 'income', 'INCOME', 'Recovery Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4033),
('4034-0000', 'Utility Recovery', 'income', 'INCOME', 'Recovery Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4034),
('4035-0000', 'Management Fee Recovery', 'income', 'INCOME', 'Recovery Income', ARRAY['cash_flow', 'income_statement'], TRUE, 4035),

-- ==================== PROPERTY EXPENSES ====================

('5211-0000', 'Property Management Fee - On-site', 'expense', 'EXPENSES', 'Property Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5211),
('5212-0000', 'Property Management Fee - Off-site', 'expense', 'EXPENSES', 'Property Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5212),
('5221-0000', 'Janitorial - Contract', 'expense', 'EXPENSES', 'Property Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5221),
('5222-0000', 'Janitorial - Supplies', 'expense', 'EXPENSES', 'Property Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5222),
('5231-0000', 'Security - Contract', 'expense', 'EXPENSES', 'Property Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5231),
('5232-0000', 'Security - Equipment', 'expense', 'EXPENSES', 'Property Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5232),
('5241-0000', 'Landscaping - Contract', 'expense', 'EXPENSES', 'Property Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5241),
('5242-0000', 'Landscaping - Materials', 'expense', 'EXPENSES', 'Property Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5242),
('5251-0000', 'Snow Removal', 'expense', 'EXPENSES', 'Property Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5251),
('5252-0000', 'Pest Control', 'expense', 'EXPENSES', 'Property Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5252),
('5253-0000', 'Parking Lot Maintenance', 'expense', 'EXPENSES', 'Property Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5253),

-- ==================== UTILITY EXPENSES ====================

('5311-0000', 'Electric - Common Area', 'expense', 'EXPENSES', 'Utility Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5311),
('5312-0000', 'Electric - Tenant Billback', 'expense', 'EXPENSES', 'Utility Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5312),
('5321-0000', 'Gas - Heating', 'expense', 'EXPENSES', 'Utility Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5321),
('5322-0000', 'Gas - Common Area', 'expense', 'EXPENSES', 'Utility Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5322),
('5331-0000', 'Water - Common Area', 'expense', 'EXPENSES', 'Utility Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5331),
('5332-0000', 'Water - Irrigation', 'expense', 'EXPENSES', 'Utility Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5332),
('5333-0000', 'Sewer', 'expense', 'EXPENSES', 'Utility Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5333),
('5341-0000', 'Trash - Collection', 'expense', 'EXPENSES', 'Utility Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5341),
('5342-0000', 'Trash - Dumpster Rental', 'expense', 'EXPENSES', 'Utility Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 5342),

-- ==================== REPAIR & MAINTENANCE ====================

('5511-0000', 'R&M - HVAC', 'expense', 'EXPENSES', 'Repair & Maintenance', ARRAY['cash_flow', 'income_statement'], TRUE, 5511),
('5512-0000', 'R&M - Plumbing', 'expense', 'EXPENSES', 'Repair & Maintenance', ARRAY['cash_flow', 'income_statement'], TRUE, 5512),
('5513-0000', 'R&M - Electrical', 'expense', 'EXPENSES', 'Repair & Maintenance', ARRAY['cash_flow', 'income_statement'], TRUE, 5513),
('5514-0000', 'R&M - Roof', 'expense', 'EXPENSES', 'Repair & Maintenance', ARRAY['cash_flow', 'income_statement'], TRUE, 5514),
('5515-0000', 'R&M - Structural', 'expense', 'EXPENSES', 'Repair & Maintenance', ARRAY['cash_flow', 'income_statement'], TRUE, 5515),
('5516-0000', 'R&M - Painting', 'expense', 'EXPENSES', 'Repair & Maintenance', ARRAY['cash_flow', 'income_statement'], TRUE, 5516),
('5517-0000', 'R&M - Flooring', 'expense', 'EXPENSES', 'Repair & Maintenance', ARRAY['cash_flow', 'income_statement'], TRUE, 5517),
('5518-0000', 'R&M - Parking Lot', 'expense', 'EXPENSES', 'Repair & Maintenance', ARRAY['cash_flow', 'income_statement'], TRUE, 5518),
('5519-0000', 'R&M - Signage', 'expense', 'EXPENSES', 'Repair & Maintenance', ARRAY['cash_flow', 'income_statement'], TRUE, 5519),
('5520-0000', 'R&M - Supplies', 'expense', 'EXPENSES', 'Repair & Maintenance', ARRAY['cash_flow', 'income_statement'], TRUE, 5520),

-- ==================== ADMINISTRATIVE EXPENSES ====================

('5431-0000', 'Office Supplies', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5431),
('5432-0000', 'Office Equipment', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5432),
('5433-0000', 'Postage & Delivery', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5433),
('5434-0000', 'Telephone', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5434),
('5435-0000', 'Internet', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5435),
('5436-0000', 'Software & IT', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5436),
('5437-0000', 'Bank Charges', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5437),
('5438-0000', 'Credit Card Fees', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5438),
('5439-0000', 'Dues & Subscriptions', 'expense', 'EXPENSES', 'Administration', ARRAY['cash_flow', 'income_statement'], TRUE, 5439),

-- ==================== INSURANCE ====================

('5611-0000', 'Insurance - Property', 'expense', 'EXPENSES', 'Insurance', ARRAY['cash_flow', 'income_statement'], TRUE, 5611),
('5612-0000', 'Insurance - Liability', 'expense', 'EXPENSES', 'Insurance', ARRAY['cash_flow', 'income_statement'], TRUE, 5612),
('5613-0000', 'Insurance - Umbrella', 'expense', 'EXPENSES', 'Insurance', ARRAY['cash_flow', 'income_statement'], TRUE, 5613),
('5614-0000', 'Insurance - Flood', 'expense', 'EXPENSES', 'Insurance', ARRAY['cash_flow', 'income_statement'], TRUE, 5614),
('5615-0000', 'Insurance - Workers Comp', 'expense', 'EXPENSES', 'Insurance', ARRAY['cash_flow', 'income_statement'], TRUE, 5615),

-- ==================== PROFESSIONAL FEES ====================

('5711-0000', 'Legal - General', 'expense', 'EXPENSES', 'Professional Fees', ARRAY['cash_flow', 'income_statement'], TRUE, 5711),
('5712-0000', 'Legal - Litigation', 'expense', 'EXPENSES', 'Professional Fees', ARRAY['cash_flow', 'income_statement'], TRUE, 5712),
('5713-0000', 'Accounting - Tax Prep', 'expense', 'EXPENSES', 'Professional Fees', ARRAY['cash_flow', 'income_statement'], TRUE, 5713),
('5714-0000', 'Accounting - Audit', 'expense', 'EXPENSES', 'Professional Fees', ARRAY['cash_flow', 'income_statement'], TRUE, 5714),
('5715-0000', 'Consulting', 'expense', 'EXPENSES', 'Professional Fees', ARRAY['cash_flow', 'income_statement'], TRUE, 5715),
('5716-0000', 'Engineering', 'expense', 'EXPENSES', 'Professional Fees', ARRAY['cash_flow', 'income_statement'], TRUE, 5716),
('5717-0000', 'Appraisal Fees', 'expense', 'EXPENSES', 'Professional Fees', ARRAY['cash_flow', 'income_statement'], TRUE, 5717),

-- ==================== LEASING EXPENSES ====================

('6051-0000', 'Leasing Commissions - New', 'expense', 'EXPENSES', 'Leasing Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 6051),
('6052-0000', 'Leasing Commissions - Renewal', 'expense', 'EXPENSES', 'Leasing Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 6052),
('6053-0000', 'Tenant Improvements', 'expense', 'EXPENSES', 'Leasing Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 6053),
('6054-0000', 'Lease Buyout', 'expense', 'EXPENSES', 'Leasing Expenses', ARRAY['cash_flow', 'income_statement'], TRUE, 6054),

-- ==================== CAPITAL EXPENSES ====================

('7010-0000', 'Capital Improvements - Building', 'expense', 'CAPITAL', 'Capital Expenditures', ARRAY['cash_flow'], TRUE, 7010),
('7020-0000', 'Capital Improvements - Roof', 'expense', 'CAPITAL', 'Capital Expenditures', ARRAY['cash_flow'], TRUE, 7020),
('7030-0000', 'Capital Improvements - HVAC', 'expense', 'CAPITAL', 'Capital Expenditures', ARRAY['cash_flow'], TRUE, 7030),
('7040-0000', 'Capital Improvements - Parking', 'expense', 'CAPITAL', 'Capital Expenditures', ARRAY['cash_flow'], TRUE, 7040),
('7050-0000', 'Capital Improvements - Landscaping', 'expense', 'CAPITAL', 'Capital Expenditures', ARRAY['cash_flow'], TRUE, 7050)

ON CONFLICT (account_code) DO NOTHING;

-- Create summary stats
SELECT 'Comprehensive cash flow accounts added successfully' as result;
SELECT COUNT(*) as total_cash_flow_accounts FROM chart_of_accounts WHERE 'cash_flow' = ANY(document_types);

