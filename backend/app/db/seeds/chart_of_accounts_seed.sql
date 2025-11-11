-- Comprehensive Chart of Accounts Seed Data
-- Extracted from Wendover Commons and TCSH 2024 Financial Statements  
-- 138 accounts covering all property types with proper categorization and hierarchy
-- Also applicable to ESP and Hammond Aire (using account name mapping)

-- Clear existing data (optional - comment out in production)
-- TRUNCATE TABLE chart_of_accounts CASCADE;

-- ASSETS SECTION
INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active) VALUES
('0100-0000', 'ASSETS', 'asset', 'header', NULL, NULL, ARRAY['balance_sheet'], true, 1, true),
('0101-0000', 'Current Assets', 'asset', 'current_asset', NULL, '0100-0000', ARRAY['balance_sheet'], false, 2, true),
('0122-0000', 'Cash - Operating', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet', 'cash_flow'], false, 3, true),
('0123-0000', 'Cash - Operating II', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet', 'cash_flow'], false, 4, true),
('0125-0000', 'Cash - Operating IV-PNC', 'asset', 'current_asset', 'cash', '0101-0000', ARRAY['balance_sheet', 'cash_flow'], false, 5, true),
('0305-0000', 'A/R Tenants', 'asset', 'current_asset', 'accounts_receivable', '0101-0000', ARRAY['balance_sheet'], false, 6, true),
('0306-0000', 'A/R Other', 'asset', 'current_asset', 'accounts_receivable', '0101-0000', ARRAY['balance_sheet'], false, 7, true),
('0499-9000', 'Total Current Assets', 'asset', 'current_asset', 'total', '0101-0000', ARRAY['balance_sheet'], true, 8, true),

-- Property & Equipment
('0500-0000', 'Property & Equipment', 'asset', 'fixed_asset', NULL, '0100-0000', ARRAY['balance_sheet'], false, 10, true),
('0510-0000', 'Land', 'asset', 'fixed_asset', 'land', '0500-0000', ARRAY['balance_sheet'], false, 11, true),
('0610-0000', 'Buildings', 'asset', 'fixed_asset', 'buildings', '0500-0000', ARRAY['balance_sheet'], false, 12, true),
('0710-0000', '5 Year Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], false, 12, true),
('0810-0000', '15 Year Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], false, 13, true),
('0815-0000', '30 Year - Roof', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], false, 14, true),
('0816-0000', '30 Year - HVAC', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], false, 14, true),
('0910-0000', 'Other Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], false, 15, true),
('0912-0000', 'PARKING-LOT', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], false, 15, true),
('0950-0000', 'TI/Current Improvements', 'asset', 'fixed_asset', 'improvements', '0500-0000', ARRAY['balance_sheet'], false, 16, true),
('1091-0000', 'Accum. Depr.-Other Imp.', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], false, 19, true),
('1061-0000', 'Accum. Depr. - Buildings', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], false, 17, true),
('1071-0000', 'Accum. Depr. 5 Year Impr.', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], false, 18, true),
('1081-0000', 'Accum. Depr. 15 Yr Impr.', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], false, 19, true),
('1082-0000', 'Accum. Depr.-Roof2008', 'asset', 'fixed_asset', 'accumulated_depreciation', '0500-0000', ARRAY['balance_sheet'], false, 20, true),
('1099-0000', 'Total Property & Equipment', 'asset', 'fixed_asset', 'total', '0500-0000', ARRAY['balance_sheet'], true, 21, true),

-- Other Assets
('1200-0000', 'Other Assets', 'asset', 'other_asset', NULL, '0100-0000', ARRAY['balance_sheet'], false, 30, true),
('1210-0000', 'Deposits', 'asset', 'other_asset', 'deposits', '1200-0000', ARRAY['balance_sheet'], false, 31, true),
('1310-0000', 'Escrow - Property Tax', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], false, 32, true),
('1320-0000', 'Escrow - Insurance', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], false, 32, true),
('1330-0000', 'Escrow - TI/LC', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], false, 32, true),
('1340-0000', 'Escrow - Replacement Reserves', 'asset', 'other_asset', 'escrow', '1200-0000', ARRAY['balance_sheet'], false, 32, true),
('1920-0000', 'Loan Costs', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], false, 33, true),
('1922-0000', 'Accum. Amortization Loan Costs', 'asset', 'other_asset', 'accumulated_amortization', '1200-0000', ARRAY['balance_sheet'], false, 34, true),
('1950-0000', 'External - Lease Commission', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], false, 35, true),
('1950-5000', 'Internal - Lease Commission', 'asset', 'other_asset', 'deferred_costs', '1200-0000', ARRAY['balance_sheet'], false, 36, true),
('1952-0000', 'Accum. Amort - TI/LC', 'asset', 'other_asset', 'accumulated_amortization', '1200-0000', ARRAY['balance_sheet'], false, 37, true),
('1995-0000', 'Prepaid Insurance', 'asset', 'other_asset', 'prepaid', '1200-0000', ARRAY['balance_sheet'], false, 38, true),
('1998-0000', 'Total Other Assets', 'asset', 'other_asset', 'total', '1200-0000', ARRAY['balance_sheet'], true, 39, true),
('1999-0000', 'TOTAL ASSETS', 'asset', 'total', 'total', '0100-0000', ARRAY['balance_sheet'], true, 40, true),

-- LIABILITIES SECTION
('2000-0000', 'LIABILITIES', 'liability', 'header', NULL, NULL, ARRAY['balance_sheet'], true, 50, true),
('2001-0000', 'Current Liabilities', 'liability', 'current_liability', NULL, '2000-0000', ARRAY['balance_sheet'], false, 51, true),
('2030-0000', 'Accrued Expenses', 'liability', 'current_liability', 'accrued', '2001-0000', ARRAY['balance_sheet'], false, 52, true),
('2110-0000', 'Accounts Payable Trade', 'liability', 'current_liability', 'payables', '2001-0000', ARRAY['balance_sheet'], false, 53, true),
('2132-0000', 'A/P 5Rivers CRE, LLC', 'liability', 'current_liability', 'payables', '2001-0000', ARRAY['balance_sheet'], false, 54, true),
('2197-0000', 'Loans Payable 5Rivers', 'liability', 'current_liability', 'short_term_debt', '2001-0000', ARRAY['balance_sheet'], false, 55, true),
('2410-0000', 'Property Tax Payable', 'liability', 'current_liability', 'payables', '2001-0000', ARRAY['balance_sheet'], false, 56, true),
('2510-0000', 'Rent Received in Advance', 'liability', 'current_liability', 'deferred_revenue', '2001-0000', ARRAY['balance_sheet'], false, 57, true),
('2515-0000', 'A/P Tenant TI/LC Obligations', 'liability', 'current_liability', 'payables', '2001-0000', ARRAY['balance_sheet'], false, 58, true),
('2520-0000', 'Deposit Refundable to Tenant', 'liability', 'current_liability', 'deposits', '2001-0000', ARRAY['balance_sheet'], false, 59, true),
('2521-0000', 'Construction Deposit Refundable', 'liability', 'current_liability', 'deposits', '2001-0000', ARRAY['balance_sheet'], false, 60, true),
('2585-0000', 'A/P Suspense', 'liability', 'current_liability', 'payables', '2001-0000', ARRAY['balance_sheet'], false, 60, true),
('2590-0000', 'Total Current Liabilities', 'liability', 'current_liability', 'total', '2001-0000', ARRAY['balance_sheet'], true, 61, true),

-- Long Term Liabilities
('2600-0000', 'Long Term Liabilities', 'liability', 'long_term_liability', NULL, '2000-0000', ARRAY['balance_sheet'], false, 70, true),
('2612-0000', 'NorthMarq Capital', 'liability', 'long_term_liability', 'mortgage', '2600-0000', ARRAY['balance_sheet'], false, 71, true),
('2900-0000', 'Total Long Term Liabilities', 'liability', 'long_term_liability', 'total', '2600-0000', ARRAY['balance_sheet'], true, 72, true),
('2999-0000', 'TOTAL LIABILITIES', 'liability', 'total', 'total', '2000-0000', ARRAY['balance_sheet'], true, 73, true),

-- EQUITY/CAPITAL SECTION
('3000-0000', 'CAPITAL', 'equity', 'header', NULL, NULL, ARRAY['balance_sheet'], true, 80, true),
('3050-0000', 'Partners Contribution', 'equity', 'capital', 'contributed_capital', '3000-0000', ARRAY['balance_sheet'], false, 81, true),
('3910-0000', 'Beginning Equity', 'equity', 'retained_earnings', 'beginning_balance', '3000-0000', ARRAY['balance_sheet'], false, 82, true),
('3990-0000', 'Distribution', 'equity', 'distributions', 'owner_distributions', '3000-0000', ARRAY['balance_sheet', 'cash_flow'], false, 83, true),
('3995-0000', 'Current Period Earnings', 'equity', 'net_income', 'period_earnings', '3000-0000', ARRAY['balance_sheet', 'income_statement'], true, 84, true),
('3999-0000', 'TOTAL CAPITAL', 'equity', 'total', 'total', '3000-0000', ARRAY['balance_sheet'], true, 85, true),
('3999-9000', 'TOTAL LIABILITIES & CAPITAL', 'equity', 'total', 'total', NULL, ARRAY['balance_sheet'], true, 86, true),

-- INCOME SECTION
('4000-0000', 'INCOME', 'income', 'header', NULL, NULL, ARRAY['income_statement', 'cash_flow'], true, 100, true),

-- Base Rental Income (Template v1.0 - Cash Flow)
('4010-0000', 'Base Rentals', 'income', 'rental_income', 'base_rent', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 101, true),
('4011-0000', 'Holdover Rent', 'income', 'rental_income', 'holdover_rent', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 101.1, true),
('4012-0000', 'Free Rent', 'income', 'rental_income', 'free_rent', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 101.2, true),
('4014-0000', 'Co-Tenancy Adjustment', 'income', 'rental_income', 'cotenancy', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 101.3, true),

-- Other Income (Template v1.0 - Cash Flow)
('4013-0000', 'Management Fee Income', 'income', 'other_income', 'management_fees', '4000-0000', ARRAY['income_statement'], false, 102, true),
('4015-0000', 'Late Fees', 'income', 'other_income', 'late_fees', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 102.1, true),
('4016-0000', 'Parking Income', 'income', 'other_income', 'parking', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 102.2, true),
('4018-0000', 'Interest Income', 'income', 'other_income', 'interest', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 102.3, true),

-- Recovery Income (Template v1.0 - Cash Flow)
('4020-0000', 'Tax', 'income', 'reimbursements', 'tax_reimbursement', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 103, true),
('4030-0000', 'Insurance', 'income', 'reimbursements', 'insurance_reimbursement', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 104, true),
('4040-0000', 'CAM', 'income', 'reimbursements', 'cam_reimbursement', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 105, true),
('4060-0000', 'Annual Cams', 'income', 'reimbursements', 'cam_reimbursement', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 106, true),
('4090-0000', 'Other Income', 'income', 'other_income', 'miscellaneous', '4000-0000', ARRAY['income_statement', 'cash_flow'], false, 107, true),
('4990-0000', 'TOTAL INCOME', 'income', 'total', 'total', '4000-0000', ARRAY['income_statement', 'cash_flow'], true, 108, true),

-- EXPENSES SECTION
('5000-0000', 'EXPENSES', 'expense', 'header', NULL, NULL, ARRAY['income_statement', 'cash_flow'], true, 200, true),
('5001-0000', 'Operating Expenses', 'expense', 'operating_expense', NULL, '5000-0000', ARRAY['income_statement', 'cash_flow'], false, 201, true),
('5010-0000', 'Property Tax', 'expense', 'operating_expense', 'property_tax', '5001-0000', ARRAY['income_statement', 'cash_flow'], false, 202, true),
('5012-0000', 'Property Insurance', 'expense', 'operating_expense', 'insurance', '5001-0000', ARRAY['income_statement', 'cash_flow'], false, 203, true),
('5014-0000', 'Property Tax Savings Consultant', 'expense', 'operating_expense', 'professional_fees', '5001-0000', ARRAY['income_statement', 'cash_flow'], false, 204, true),

-- Utility Expenses
('5040-0000', 'R&M Operating Expenses', 'expense', 'operating_expense', NULL, '5001-0000', ARRAY['income_statement', 'cash_flow'], false, 210, true),
('5090-0000', 'Other Operating Expenses', 'expense', 'operating_expense', 'miscellaneous', '5001-0000', ARRAY['income_statement', 'cash_flow'], false, 211, true),
('5100-0000', 'Utility Expense', 'expense', 'operating_expense', 'utilities', '5040-0000', ARRAY['income_statement', 'cash_flow'], false, 211, true),
('5105-0000', 'Electricity Service', 'expense', 'operating_expense', 'utilities', '5100-0000', ARRAY['income_statement', 'cash_flow'], false, 212, true),
('5115-0000', 'Water & Sewer Service', 'expense', 'operating_expense', 'utilities', '5100-0000', ARRAY['income_statement', 'cash_flow'], false, 213, true),
('5125-0000', 'Trash Service', 'expense', 'operating_expense', 'utilities', '5100-0000', ARRAY['income_statement', 'cash_flow'], false, 214, true),
('5199-0000', 'Total Utility Expense', 'expense', 'operating_expense', 'utilities', '5100-0000', ARRAY['income_statement', 'cash_flow'], true, 215, true),

-- Contracted Services
('5200-0000', 'Contracted Expense', 'expense', 'operating_expense', 'contracted_services', '5040-0000', ARRAY['income_statement', 'cash_flow'], false, 220, true),
('5210-0000', 'Contract - Parking Lot Sweeping', 'expense', 'operating_expense', 'contracted_services', '5200-0000', ARRAY['income_statement', 'cash_flow'], false, 221, true),
('5215-0000', 'Contract - Building Pressure Washing', 'expense', 'operating_expense', 'contracted_services', '5200-0000', ARRAY['income_statement', 'cash_flow'], false, 222, true),
('5220-0000', 'Contract - Sidewalk Pressure Washing', 'expense', 'operating_expense', 'contracted_services', '5200-0000', ARRAY['income_statement', 'cash_flow'], false, 223, true),
('5225-0000', 'Contract - Snow Removal & Ice Melt', 'expense', 'operating_expense', 'contracted_services', '5200-0000', ARRAY['income_statement', 'cash_flow'], false, 224, true),
('5230-0000', 'Contract - Landscaping', 'expense', 'operating_expense', 'contracted_services', '5200-0000', ARRAY['income_statement', 'cash_flow'], false, 225, true),
('5235-0000', 'Contract - Janitorial/Portering', 'expense', 'operating_expense', 'contracted_services', '5200-0000', ARRAY['income_statement', 'cash_flow'], false, 226, true),
('5240-0000', 'Contract - Fire Safety Monitoring', 'expense', 'operating_expense', 'contracted_services', '5200-0000', ARRAY['income_statement', 'cash_flow'], false, 227, true),
('5245-0000', 'Contract - Pest Control', 'expense', 'operating_expense', 'contracted_services', '5200-0000', ARRAY['income_statement', 'cash_flow'], false, 228, true),
('5299-0000', 'Total Contracted Expenses', 'expense', 'operating_expense', 'contracted_services', '5200-0000', ARRAY['income_statement', 'cash_flow'], true, 229, true),

-- Repair & Maintenance
('5300-0000', 'Repair & Maintenance Operating Expon', 'expense', 'operating_expense', 'repairs_maintenance', '5040-0000', ARRAY['income_statement', 'cash_flow'], false, 230, true),
('5312-0000', 'R&M - Bulk Trash Removal', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 231, true),
('5314-0000', 'R&M - Fire Safety Repairs', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 232, true),
('5316-0000', 'R&M - Fire Sprinkler Inspection', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 233, true),
('5318-0000', 'R&M - Plumbing', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 234, true),
('5326-0000', 'R&M - Building Maintenance', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 235, true),
('5332-0000', 'R&M - Exterior Painting', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 236, true),
('5334-0000', 'R&M - Parking Lot Repairs', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 237, true),
('5342-0000', 'R&M - HVAC', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 238, true),
('5356-0000', 'R&M - Lighting', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 237, true),
('5362-0000', 'R&M - Roofing Repairs - Minor', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 238, true),
('5364-0000', 'R&M - Doors/Locks N Keys', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 239, true),
('5366-0000', 'R&M - Seasonal Decoration', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 240, true),
('5370-0000', 'R&M - Signage', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 241, true),
('5376-0000', 'R&M - Misc', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], false, 242, true),
('5399-0000', 'Total R&M Operating Expenses', 'expense', 'operating_expense', 'repairs_maintenance', '5300-0000', ARRAY['income_statement', 'cash_flow'], true, 243, true),

-- Administration
('5400-0001', 'Administration Expense', 'expense', 'operating_expense', 'administrative', '5001-0000', ARRAY['income_statement', 'cash_flow'], false, 250, true),
('5400-0002', 'Salaries Expense', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement', 'cash_flow'], false, 251, true),
('5400-0003', 'Benefits Expense', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement', 'cash_flow'], false, 252, true),
('5400-0004', 'Computer & Software Expense', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement', 'cash_flow'], false, 253, true),
('5435-0000', 'Meals & Entertainment', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement', 'cash_flow'], false, 254, true),
('5470-0000', 'Travel', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement', 'cash_flow'], false, 255, true),
('5490-0000', 'Lease Abstracting', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement', 'cash_flow'], false, 256, true),
('5499-0000', 'Total Administration Expense', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement', 'cash_flow'], true, 257, true),
('5990-0000', 'Total Operating Expenses', 'expense', 'operating_expense', 'total', '5001-0000', ARRAY['income_statement', 'cash_flow'], true, 258, true),

-- Additional Operating Expenses
('6000-0000', 'Additional Operating Expenses', 'expense', 'operating_expense', NULL, '5000-0000', ARRAY['income_statement', 'cash_flow'], false, 300, true),

-- Management Fees (Template v1.0 - Cash Flow)
('6010-0000', 'Off Site Management', 'expense', 'operating_expense', 'management', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 301, true),

-- Professional Fees (Template v1.0 - Cash Flow)
('6020-0000', 'Professional Fees', 'expense', 'operating_expense', 'professional_fees', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 302, true),
('6020-5000', 'Accounting Fee', 'expense', 'operating_expense', 'professional_fees', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 303, true),
('6020-6000', 'Asset Management Fee', 'expense', 'operating_expense', 'professional_fees', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 304, true),
('6020-7000', 'CMF-Construction Management Fee', 'expense', 'operating_expense', 'professional_fees', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 305, true),

-- Taxes & Fees (Template v1.0 - Cash Flow)
('6021-0000', 'Franchise Tax', 'expense', 'operating_expense', 'tax_fees', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 305.5, true),
('6021-5000', 'Pass-Through Entity Tax', 'expense', 'operating_expense', 'tax_fees', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 305.6, true),
('6022-0000', 'Legal Fees / SOS Fee', 'expense', 'operating_expense', 'professional_fees', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 306, true),
('6024-0000', 'Bank Charges', 'expense', 'operating_expense', 'banking', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 307, true),
('6024-5000', 'Bank Control Fee', 'expense', 'operating_expense', 'banking', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 307.5, true),

-- Leasing Costs (Template v1.0 - Cash Flow)
('6030-0000', 'Leasing Commissions', 'expense', 'operating_expense', 'leasing', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 307.8, true),
('6032-0000', 'Tenant Improvements', 'expense', 'operating_expense', 'leasing', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 307.9, true),

-- Landlord Expenses (Template v1.0 - Cash Flow)
('6040-0000', 'LL - Expense', 'expense', 'operating_expense', 'landlord_expense', '6000-0000', ARRAY['income_statement', 'cash_flow'], false, 308, true),
('6041-0000', 'LL - Repairs', 'expense', 'operating_expense', 'landlord_expense', '6040-0000', ARRAY['income_statement', 'cash_flow'], false, 308.1, true),
('6042-0000', 'LL - HVAC', 'expense', 'operating_expense', 'landlord_expense', '6040-0000', ARRAY['income_statement', 'cash_flow'], false, 308.2, true),
('6043-0000', 'LL - Vacant Space Utilities', 'expense', 'operating_expense', 'landlord_expense', '6040-0000', ARRAY['income_statement', 'cash_flow'], false, 308.3, true),
('6044-0000', 'LL - Tenant Allowance', 'expense', 'operating_expense', 'landlord_expense', '6040-0000', ARRAY['income_statement', 'cash_flow'], false, 308.4, true),
('6065-0000', 'LL - Site Map', 'expense', 'operating_expense', 'landlord_expense', '6040-0000', ARRAY['income_statement', 'cash_flow'], false, 309, true),
('6069-0000', 'Total LL Expense', 'expense', 'operating_expense', 'landlord_expense', '6040-0000', ARRAY['income_statement', 'cash_flow'], true, 310, true),
('6190-0000', 'Total Additional Operating Expenses', 'expense', 'operating_expense', 'total', '6000-0000', ARRAY['income_statement', 'cash_flow'], true, 311, true),
('6199-0000', 'TOTAL EXPENSES', 'expense', 'total', 'total', '5000-0000', ARRAY['income_statement', 'cash_flow'], true, 312, true),
('6299-0000', 'NET OPERATING INCOME', 'income', 'net_operating_income', 'noi', NULL, ARRAY['income_statement', 'cash_flow'], true, 313, true),

-- Other Income/Expenses (Non-Operating)
('7000-0000', 'Other Income/Expenses', 'expense', 'non_operating', NULL, NULL, ARRAY['income_statement'], false, 400, true),
('7010-0000', 'Mortgage Interest', 'expense', 'non_operating', 'interest', '7000-0000', ARRAY['income_statement', 'cash_flow'], false, 401, true),
('7020-0000', 'Depreciation', 'expense', 'non_operating', 'depreciation', '7000-0000', ARRAY['income_statement'], false, 402, true),
('7030-0000', 'Amortization', 'expense', 'non_operating', 'amortization', '7000-0000', ARRAY['income_statement'], false, 403, true),
('7090-0000', 'Total Other Income/Expense', 'expense', 'non_operating', 'total', '7000-0000', ARRAY['income_statement'], true, 404, true),
('9090-0000', 'NET INCOME', 'income', 'net_income', 'net_income', NULL, ARRAY['income_statement', 'balance_sheet'], true, 500, true);

-- Mark all calculated/total fields
UPDATE chart_of_accounts SET is_calculated = true 
WHERE account_name LIKE 'Total%' 
   OR account_name LIKE '%Total' 
   OR account_name LIKE 'TOTAL%'
   OR account_name = 'NET OPERATING INCOME'
   OR account_name = 'NET INCOME'
   OR account_code IN ('0100-0000', '2000-0000', '3000-0000', '4000-0000', '5000-0000', '7000-0000');

-- Verification query
SELECT 
    account_type,
    COUNT(*) as count,
    COUNT(CASE WHEN is_calculated = true THEN 1 END) as calculated_count
FROM chart_of_accounts 
GROUP BY account_type
ORDER BY account_type;

