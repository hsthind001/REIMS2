-- Expense Accounts (5xxx-9xxx) - Complete Chart of Accounts
-- Part 2: Operating & Additional Expenses

-- OPERATING EXPENSES (5xxx)
INSERT INTO chart_of_accounts (account_code, account_name, account_type, category, subcategory, parent_account_code, document_types, is_calculated, display_order, is_active) VALUES
('5001-0000', 'Operating Expenses', 'expense', 'operating_expense', NULL, NULL, ARRAY['income_statement'], FALSE, 4000, TRUE),
('5010-0000', 'Property Tax', 'expense', 'operating_expense', 'property_tax', '5001-0000', ARRAY['income_statement'], FALSE, 4001, TRUE),
('5012-0000', 'Property Insurance', 'expense', 'operating_expense', 'insurance', '5001-0000', ARRAY['income_statement'], FALSE, 4002, TRUE),
('5014-0000', 'Property Tax Savings Consultant', 'expense', 'operating_expense', 'property_tax', '5001-0000', ARRAY['income_statement'], FALSE, 4003, TRUE),
('5040-0000', 'R&M Operating Expenses', 'expense', 'operating_expense', 'maintenance', '5001-0000', ARRAY['income_statement'], FALSE, 4010, TRUE),
('5090-0000', 'Other Operating Expenses', 'expense', 'operating_expense', 'other', '5001-0000', ARRAY['income_statement'], FALSE, 4020, TRUE),

-- Utilities (5100-5199)
('5100-0000', 'Utility Expense', 'expense', 'operating_expense', 'utilities', '5001-0000', ARRAY['income_statement'], FALSE, 4100, TRUE),
('5105-0000', 'Electricity Service', 'expense', 'operating_expense', 'utilities', '5100-0000', ARRAY['income_statement'], FALSE, 4101, TRUE),
('5110-0000', 'Gas Service', 'expense', 'operating_expense', 'utilities', '5100-0000', ARRAY['income_statement'], FALSE, 4102, TRUE),
('5115-0000', 'Water & Sewer Service', 'expense', 'operating_expense', 'utilities', '5100-0000', ARRAY['income_statement'], FALSE, 4103, TRUE),
('5125-0000', 'Trash Service', 'expense', 'operating_expense', 'utilities', '5100-0000', ARRAY['income_statement'], FALSE, 4104, TRUE),
('5199-0000', 'Total Utility Expense', 'expense', 'operating_expense', 'utilities', NULL, ARRAY['income_statement'], TRUE, 4199, TRUE),

-- Contracted Expenses (5200-5299)
('5200-0000', 'Contracted Expense', 'expense', 'operating_expense', 'contracted', '5001-0000', ARRAY['income_statement'], FALSE, 4200, TRUE),
('5210-0000', 'Contract - Parking Lot Sweeping', 'expense', 'operating_expense', 'contracted', '5200-0000', ARRAY['income_statement'], FALSE, 4201, TRUE),
('5215-0000', 'Contract - Building Pressure Washing', 'expense', 'operating_expense', 'contracted', '5200-0000', ARRAY['income_statement'], FALSE, 4202, TRUE),
('5220-0000', 'Contract - Sidewalk Pressure Washing', 'expense', 'operating_expense', 'contracted', '5200-0000', ARRAY['income_statement'], FALSE, 4203, TRUE),
('5225-0000', 'Contract - Snow Removal & Ice Melt', 'expense', 'operating_expense', 'contracted', '5200-0000', ARRAY['income_statement'], FALSE, 4204, TRUE),
('5230-0000', 'Contract - Landscaping', 'expense', 'operating_expense', 'contracted', '5200-0000', ARRAY['income_statement'], FALSE, 4205, TRUE),
('5235-0000', 'Contract - Janitorial/Portering', 'expense', 'operating_expense', 'contracted', '5200-0000', ARRAY['income_statement'], FALSE, 4206, TRUE),
('5240-0000', 'Contract - Fire Safety Monitoring', 'expense', 'operating_expense', 'contracted', '5200-0000', ARRAY['income_statement'], FALSE, 4207, TRUE),
('5245-0000', 'Contract - Pest Control', 'expense', 'operating_expense', 'contracted', '5200-0000', ARRAY['income_statement'], FALSE, 4208, TRUE),
('5255-0000', 'Contract - Security', 'expense', 'operating_expense', 'contracted', '5200-0000', ARRAY['income_statement'], FALSE, 4209, TRUE),
('5270-0000', 'Contract - Plumbing', 'expense', 'operating_expense', 'contracted', '5200-0000', ARRAY['income_statement'], FALSE, 4210, TRUE),
('5275-0000', 'Contract - Elevator', 'expense', 'operating_expense', 'contracted', '5200-0000', ARRAY['income_statement'], FALSE, 4211, TRUE),
('5299-0000', 'Total Contracted Expenses', 'expense', 'operating_expense', 'contracted', NULL, ARRAY['income_statement'], TRUE, 4299, TRUE),

-- Repair & Maintenance (5300-5399)
('5300-0000', 'Repair & Maintenance Operating Expon', 'expense', 'operating_expense', 'maintenance', '5001-0000', ARRAY['income_statement'], FALSE, 4300, TRUE),
('5302-0000', 'R&M - Elevator Repairs', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4301, TRUE),
('5306-0000', 'R&M - Landscape Repairs', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4302, TRUE),
('5308-0000', 'R&M - Irrigation Repairs', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4303, TRUE),
('5312-0000', 'R&M - Bulk Trash Removal', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4304, TRUE),
('5314-0000', 'R&M - Fire Safety Repairs', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4305, TRUE),
('5316-0000', 'R&M - Fire Sprinkler Inspection', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4306, TRUE),
('5318-0000', 'R&M - Plumbing', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4307, TRUE),
('5322-0000', 'R&M - Electrical Inspections & Repairs', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4308, TRUE),
('5326-0000', 'R&M - Building Maintenance', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4309, TRUE),
('5332-0000', 'R&M - Exterior Painting', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4310, TRUE),
('5334-0000', 'R&M - Parking Lot Repairs', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4311, TRUE),
('5336-0000', 'R&M - Sidewalk & Concrete Repairs', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4312, TRUE),
('5338-0000', 'R&M - Exterior', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4313, TRUE),
('5340-0000', 'R&M - Interior', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4314, TRUE),
('5342-0000', 'R&M - HVAC', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4315, TRUE),
('5356-0000', 'R&M - Lighting', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4316, TRUE),
('5358-0000', 'R&M - Misc Maintenance Supplies', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4317, TRUE),
('5360-0000', 'R&M - Roofing Repairs - Major', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4318, TRUE),
('5362-0000', 'R&M - Roofing Repairs - Minor', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4319, TRUE),
('5364-0000', 'R&M - Doors/Locks N Keys', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4320, TRUE),
('5366-0000', 'R&M - Seasonal Decoration', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4321, TRUE),
('5370-0000', 'R&M - Signage', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4322, TRUE),
('5376-0000', 'R&M - Misc', 'expense', 'operating_expense', 'maintenance', '5300-0000', ARRAY['income_statement'], FALSE, 4323, TRUE),
('5399-0000', 'Total R&M Operating Expenses', 'expense', 'operating_expense', 'maintenance', NULL, ARRAY['income_statement'], TRUE, 4399, TRUE),

-- Administration Expenses (5400-5499)
('5400-0001', 'Administration Expense', 'expense', 'operating_expense', 'administrative', '5001-0000', ARRAY['income_statement'], FALSE, 4400, TRUE),
('5400-0002', 'Salaries Expense', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4401, TRUE),
('5400-0003', 'Benefits Expense', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4402, TRUE),
('5400-0004', 'Computer & Software Expense', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4403, TRUE),
('5400-0006', 'Employee HR Related Expense', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4404, TRUE),
('5400-0090', 'Office Supplies Expense', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4405, TRUE),
('5435-0000', 'Meals & Entertainment', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4410, TRUE),
('5440-0000', 'Management Office Expense', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4411, TRUE),
('5445-0000', 'Management Office Supplies & Equip', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4412, TRUE),
('5455-0000', 'Permits', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4413, TRUE),
('5460-0000', 'Postage & Carrier', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4414, TRUE),
('5465-0000', 'Telephone', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4415, TRUE),
('5470-0000', 'Travel', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4416, TRUE),
('5480-0000', 'Miscellaneous Admin', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4417, TRUE),
('5490-0000', 'Lease Abstracting', 'expense', 'operating_expense', 'administrative', '5400-0001', ARRAY['income_statement'], FALSE, 4418, TRUE),
('5499-0000', 'Total Administration Expense', 'expense', 'operating_expense', 'administrative', NULL, ARRAY['income_statement'], TRUE, 4499, TRUE),
('5990-0000', 'Total Operating Expenses', 'expense', 'operating_expense', 'total', NULL, ARRAY['income_statement'], TRUE, 4999, TRUE),

-- ADDITIONAL OPERATING EXPENSES (6xxx)
('6000-0000', 'Additional Operating Expenses', 'expense', 'additional_expense', NULL, NULL, ARRAY['income_statement'], FALSE, 5000, TRUE),
('6010-0000', 'Off Site Management', 'expense', 'additional_expense', 'management', '6000-0000', ARRAY['income_statement'], FALSE, 5001, TRUE),
('6010-5000', 'On-Site Management Fee', 'expense', 'additional_expense', 'management', '6000-0000', ARRAY['income_statement'], FALSE, 5002, TRUE),
('6012-0000', 'Franchise Tax', 'expense', 'additional_expense', 'taxes', '6000-0000', ARRAY['income_statement'], FALSE, 5010, TRUE),
('6012-5000', 'Pass Thru Entity Tax', 'expense', 'additional_expense', 'taxes', '6000-0000', ARRAY['income_statement'], FALSE, 5011, TRUE),
('6014-0000', 'Leasing Commissions', 'expense', 'additional_expense', 'leasing', '6000-0000', ARRAY['income_statement'], FALSE, 5020, TRUE),
('6016-0000', 'Tenant Improvements', 'expense', 'additional_expense', 'leasing', '6000-0000', ARRAY['income_statement'], FALSE, 5021, TRUE),
('6020-0000', 'Professional Fees', 'expense', 'additional_expense', 'professional_fees', '6000-0000', ARRAY['income_statement'], FALSE, 5030, TRUE),
('6020-5000', 'Accounting Fee', 'expense', 'additional_expense', 'professional_fees', '6000-0000', ARRAY['income_statement'], FALSE, 5031, TRUE),
('6020-6000', 'Asset Management Fee', 'expense', 'additional_expense', 'professional_fees', '6000-0000', ARRAY['income_statement'], FALSE, 5032, TRUE),
('6020-7000', 'CMF-Construction Management Fee', 'expense', 'additional_expense', 'professional_fees', '6000-0000', ARRAY['income_statement'], FALSE, 5033, TRUE),
('6022-0000', 'Legal Fees / SOS Fee', 'expense', 'additional_expense', 'professional_fees', '6000-0000', ARRAY['income_statement'], FALSE, 5034, TRUE),
('6024-0000', 'Bank Charges', 'expense', 'additional_expense', 'banking', '6000-0000', ARRAY['income_statement'], FALSE, 5040, TRUE),
('6025-0000', 'Bank Control A/c Fee', 'expense', 'additional_expense', 'banking', '6000-0000', ARRAY['income_statement'], FALSE, 5041, TRUE),
('6040-0000', 'LL - Expense', 'expense', 'additional_expense', 'landlord', '6000-0000', ARRAY['income_statement'], FALSE, 5050, TRUE),
('6050-0000', 'LL Repairs & Maintenance', 'expense', 'additional_expense', 'landlord', '6000-0000', ARRAY['income_statement'], FALSE, 5051, TRUE),
('6051-0000', 'LL - Plumbing', 'expense', 'additional_expense', 'landlord', '6000-0000', ARRAY['income_statement'], FALSE, 5052, TRUE),
('6052-0000', 'LL - Electrical Repairs', 'expense', 'additional_expense', 'landlord', '6000-0000', ARRAY['income_statement'], FALSE, 5053, TRUE),
('6054-0000', 'LL - HVAC Repairs', 'expense', 'additional_expense', 'landlord', '6000-0000', ARRAY['income_statement'], FALSE, 5054, TRUE),
('6058-0000', 'LL - Vacant Space Expenses', 'expense', 'additional_expense', 'landlord', '6000-0000', ARRAY['income_statement'], FALSE, 5055, TRUE),
('6059-0000', 'LL - General Repairs', 'expense', 'additional_expense', 'landlord', '6000-0000', ARRAY['income_statement'], FALSE, 5056, TRUE),
('6061-0000', 'LL - Electricity', 'expense', 'additional_expense', 'landlord', '6000-0000', ARRAY['income_statement'], FALSE, 5057, TRUE),
('6064-0000', 'LL-Misc', 'expense', 'additional_expense', 'landlord', '6000-0000', ARRAY['income_statement'], FALSE, 5058, TRUE),
('6065-0000', 'LL-Site Map', 'expense', 'additional_expense', 'landlord', '6000-0000', ARRAY['income_statement'], FALSE, 5059, TRUE),
('6069-0000', 'Total LL Expense', 'expense', 'additional_expense', 'landlord', NULL, ARRAY['income_statement'], TRUE, 5069, TRUE),
('6190-0000', 'Total Additional Operating Expenses', 'expense', 'additional_expense', 'total', NULL, ARRAY['income_statement'], TRUE, 5099, TRUE),
('6199-0000', 'TOTAL EXPENSES', 'expense', 'total', NULL, NULL, ARRAY['income_statement'], TRUE, 5999, TRUE),
('6299-0000', 'NET OPERATING INCOME', 'income', 'net_operating_income', NULL, NULL, ARRAY['income_statement'], TRUE, 6999, TRUE),

-- OTHER INCOME/EXPENSES (7xxx-9xxx)
('7000-0000', 'Other Income/Expenses', 'expense', 'other_expense', NULL, NULL, ARRAY['income_statement'], FALSE, 7000, TRUE),
('7010-0000', 'Mortgage Interest', 'expense', 'other_expense', 'interest', '7000-0000', ARRAY['income_statement'], FALSE, 7001, TRUE),
('7020-0000', 'Depreciation', 'expense', 'other_expense', 'depreciation', '7000-0000', ARRAY['income_statement'], FALSE, 7002, TRUE),
('7030-0000', 'Amortization', 'expense', 'other_expense', 'amortization', '7000-0000', ARRAY['income_statement'], FALSE, 7003, TRUE),
('7090-0000', 'Total Other Income/Expense', 'expense', 'other_expense', 'total', NULL, ARRAY['income_statement'], TRUE, 7099, TRUE),
('9090-0000', 'NET INCOME', 'income', 'net_income', NULL, NULL, ARRAY['income_statement'], TRUE, 9999, TRUE)

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

-- Display final count and breakdown
SELECT 'Chart of Accounts Update Complete' as status;
SELECT account_type, COUNT(*) as count FROM chart_of_accounts WHERE is_active = TRUE GROUP BY account_type ORDER BY account_type;
SELECT COUNT(*) as total_accounts, COUNT(CASE WHEN is_calculated = TRUE THEN 1 END) as calculated_accounts FROM chart_of_accounts WHERE is_active = TRUE;

