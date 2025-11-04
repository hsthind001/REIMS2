-- Income Statement Template v1.0 - Comprehensive Chart of Accounts (100+ accounts)
-- Based on Income Statement Extraction Requirements v1.0
-- Covers all income and expense accounts from ESP, HMND, TCSH, WEND properties

-- ==============================================================================
-- SECTION 1: INCOME ACCOUNTS (4000-4999)
-- ==============================================================================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active, expected_sign) VALUES

-- Primary Income
('4010-0000', 'Base Rentals', 'income', 'rental_income', 'base_rent', NULL, ARRAY['income_statement'], FALSE, 4000, TRUE, 'positive'),
('4013-0000', 'Management Fee Income', 'income', 'other_income', 'management_fee', NULL, ARRAY['income_statement'], FALSE, 4001, TRUE, 'positive'),
('4018-0000', 'Interest Income', 'income', 'other_income', 'interest', NULL, ARRAY['income_statement'], FALSE, 4002, TRUE, 'positive'),

-- Reimbursements
('4020-0000', 'Tax', 'income', 'rental_income', 'tax_reimbursement', NULL, ARRAY['income_statement'], FALSE, 4010, TRUE, 'positive'),
('4030-0000', 'Insurance', 'income', 'rental_income', 'insurance_reimbursement', NULL, ARRAY['income_statement'], FALSE, 4011, TRUE, 'positive'),
('4040-0000', 'CAM', 'income', 'rental_income', 'cam_reimbursement', NULL, ARRAY['income_statement'], FALSE, 4012, TRUE, 'positive'),
('4050-0000', 'Percentage Rent', 'income', 'rental_income', 'percentage_rent', NULL, ARRAY['income_statement'], FALSE, 4020, TRUE, 'positive'),
('4055-0000', 'Utilities Reimbursement', 'income', 'rental_income', 'utilities_reimbursement', NULL, ARRAY['income_statement'], FALSE, 4021, TRUE, 'positive'),
('4056-0000', 'Termination Fee Income', 'income', 'other_income', 'termination_fee', NULL, ARRAY['income_statement'], FALSE, 4022, TRUE, 'positive'),
('4060-0000', 'Annual Cams', 'income', 'rental_income', 'annual_cam', NULL, ARRAY['income_statement'], FALSE, 4023, TRUE, 'either'),
('4090-0000', 'Other Income', 'income', 'other_income', 'misc', NULL, ARRAY['income_statement'], FALSE, 4090, TRUE, 'positive'),
('4091-0000', 'End of Day Investment Sweep Int Income', 'income', 'other_income', 'interest', NULL, ARRAY['income_statement'], FALSE, 4091, TRUE, 'positive'),

-- Special Income Adjustments (can be negative)
('4070-0000', 'Holdover Rent', 'income', 'rental_income', 'holdover', NULL, ARRAY['income_statement'], FALSE, 4070, TRUE, 'positive'),
('4075-0000', 'Free Rent', 'income', 'rental_income', 'adjustment', NULL, ARRAY['income_statement'], FALSE, 4075, TRUE, 'negative'),
('4076-0000', 'Co-Tenancy Rent Reduction', 'income', 'rental_income', 'adjustment', NULL, ARRAY['income_statement'], FALSE, 4076, TRUE, 'negative'),
('4080-0000', 'Bad Debt Expense', 'income', 'rental_income', 'adjustment', NULL, ARRAY['income_statement'], FALSE, 4080, TRUE, 'negative'),
('4081-0000', 'Less Bad Debt Write Offs', 'income', 'rental_income', 'adjustment', NULL, ARRAY['income_statement'], FALSE, 4081, TRUE, 'negative'),

-- Total Income
('4990-0000', 'TOTAL INCOME', 'income', 'total', NULL, NULL, ARRAY['income_statement'], TRUE, 4999, TRUE, 'positive')

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
-- SECTION 2: OPERATING EXPENSES (5000-5999)
-- ==============================================================================

INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active, expected_sign) VALUES

-- A. Property Costs (5010-5014)
('5010-0000', 'Property Tax', 'expense', 'operating_expense', 'property_costs', NULL, ARRAY['income_statement'], FALSE, 5010, TRUE, 'positive'),
('5012-0000', 'Property Insurance', 'expense', 'operating_expense', 'property_costs', NULL, ARRAY['income_statement'], FALSE, 5012, TRUE, 'positive'),
('5014-0000', 'Property Tax Savings Consultant', 'expense', 'operating_expense', 'property_costs', NULL, ARRAY['income_statement'], FALSE, 5014, TRUE, 'positive'),

-- B. Utility Expenses (5100-5199)
('5105-0000', 'Electricity Service', 'expense', 'operating_expense', 'utilities', NULL, ARRAY['income_statement'], FALSE, 5105, TRUE, 'positive'),
('5110-0000', 'Gas Service', 'expense', 'operating_expense', 'utilities', NULL, ARRAY['income_statement'], FALSE, 5110, TRUE, 'positive'),
('5115-0000', 'Water & Sewer Service', 'expense', 'operating_expense', 'utilities', NULL, ARRAY['income_statement'], FALSE, 5115, TRUE, 'positive'),
('5125-0000', 'Trash Service', 'expense', 'operating_expense', 'utilities', NULL, ARRAY['income_statement'], FALSE, 5125, TRUE, 'positive'),
('5199-0000', 'Total Utility Expense', 'expense', 'operating_expense', 'utilities', NULL, ARRAY['income_statement'], TRUE, 5199, TRUE, 'positive'),

-- C. Contracted Expenses (5200-5299)
('5210-0000', 'Contract - Parking Lot Sweeping', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], FALSE, 5210, TRUE, 'positive'),
('5215-0000', 'Contract - Building Pressure Washing', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], FALSE, 5215, TRUE, 'positive'),
('5220-0000', 'Contract - Sidewalk Pressure Washing', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], FALSE, 5220, TRUE, 'positive'),
('5225-0000', 'Contract - Snow Removal & Ice Melt', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], FALSE, 5225, TRUE, 'positive'),
('5230-0000', 'Contract - Landscaping', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], FALSE, 5230, TRUE, 'positive'),
('5235-0000', 'Contract - Janitorial/Portering', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], FALSE, 5235, TRUE, 'positive'),
('5240-0000', 'Contract - Fire Safety Monitoring', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], FALSE, 5240, TRUE, 'positive'),
('5245-0000', 'Contract - Pest Control', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], FALSE, 5245, TRUE, 'positive'),
('5255-0000', 'Contract - Security', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], FALSE, 5255, TRUE, 'positive'),
('5270-0000', 'Contract - Plumbing', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], FALSE, 5270, TRUE, 'positive'),
('5275-0000', 'Contract - Elevator', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], FALSE, 5275, TRUE, 'positive'),
('5299-0000', 'Total Contracted Expenses', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], TRUE, 5299, TRUE, 'positive'),

-- D. Repair & Maintenance (5300-5399) - 23 accounts
('5302-0000', 'R&M - Elevator Repairs', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5302, TRUE, 'positive'),
('5306-0000', 'R&M - Landscape Repairs', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5306, TRUE, 'positive'),
('5308-0000', 'R&M - Irrigation Repairs', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5308, TRUE, 'positive'),
('5312-0000', 'R&M - Bulk Trash Removal', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5312, TRUE, 'positive'),
('5314-0000', 'R&M - Fire Safety Repairs', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5314, TRUE, 'positive'),
('5316-0000', 'R&M - Fire Sprinkler Inspection', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5316, TRUE, 'positive'),
('5318-0000', 'R&M - Plumbing', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5318, TRUE, 'positive'),
('5322-0000', 'R&M - Electrical Inspections & Repairs', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5322, TRUE, 'positive'),
('5326-0000', 'R&M - Building Maintenance', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5326, TRUE, 'positive'),
('5332-0000', 'R&M - Exterior Painting', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5332, TRUE, 'positive'),
('5334-0000', 'R&M - Parking Lot Repairs', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5334, TRUE, 'positive'),
('5336-0000', 'R&M - Sidewalk & Concrete Repairs', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5336, TRUE, 'positive'),
('5338-0000', 'R&M - Exterior', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5338, TRUE, 'positive'),
('5340-0000', 'R&M - Interior', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5340, TRUE, 'positive'),
('5342-0000', 'R&M - HVAC', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5342, TRUE, 'positive'),
('5356-0000', 'R&M - Lighting', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5356, TRUE, 'positive'),
('5358-0000', 'R&M - Misc Maintenance Supplies', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5358, TRUE, 'positive'),
('5360-0000', 'R&M - Roofing Repairs - Major', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5360, TRUE, 'positive'),
('5362-0000', 'R&M - Roofing Repairs - Minor', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5362, TRUE, 'positive'),
('5364-0000', 'R&M - Doors/Locks N Keys', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5364, TRUE, 'positive'),
('5366-0000', 'R&M - Seasonal Decoration', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5366, TRUE, 'positive'),
('5370-0000', 'R&M - Pylon Signs', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5370, TRUE, 'positive'),
('5376-0000', 'R&M - Misc', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], FALSE, 5376, TRUE, 'positive'),
('5399-0000', 'Total R&M Operating Expenses', 'expense', 'operating_expense', 'repair_maintenance', NULL, ARRAY['income_statement'], TRUE, 5399, TRUE, 'positive'),

-- E. Administration Expenses (5400-5499)
('5400-0002', 'Salaries Expense', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5402, TRUE, 'positive'),
('5400-0003', 'Benefits Expense', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5403, TRUE, 'positive'),
('5400-0004', 'Computer & Software Expense', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5404, TRUE, 'positive'),
('5400-0006', 'Employee HR Related Expense', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5406, TRUE, 'positive'),
('5400-0090', 'Office Supplies Expense', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5409, TRUE, 'positive'),
('5435-0000', 'Meals & Entertainment', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5435, TRUE, 'positive'),
('5440-0000', 'Management Office Expense', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5440, TRUE, 'positive'),
('5445-0000', 'Management Office Supplies & Equip', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5445, TRUE, 'positive'),
('5455-0000', 'Permits', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5455, TRUE, 'positive'),
('5460-0000', 'Postage & Carrier', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5460, TRUE, 'positive'),
('5465-0000', 'Telephone', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5465, TRUE, 'positive'),
('5470-0000', 'Travel', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5470, TRUE, 'positive'),
('5490-0000', 'Lease Abstracting', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], FALSE, 5490, TRUE, 'positive'),
('5499-0000', 'Total Administration Expense', 'expense', 'operating_expense', 'administration', NULL, ARRAY['income_statement'], TRUE, 5499, TRUE, 'positive'),

-- F. Total Operating Expenses
('5990-0000', 'Total Operating Expenses', 'expense', 'operating_expense', 'total', NULL, ARRAY['income_statement'], TRUE, 5999, TRUE, 'positive')

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

-- Continue in part 2...

