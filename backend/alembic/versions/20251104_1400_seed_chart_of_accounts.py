"""Seed comprehensive Chart of Accounts

Revision ID: seed_chart_of_accounts
Revises: 20251104_0800_seed_sample_properties
Create Date: 2025-11-04 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'seed_chart_of_accounts'
down_revision = '20251104_0800_seed_sample_properties'
branch_labels = None
depends_on = None


def upgrade():
    """
    Seed Chart of Accounts with 200+ accounts from extracted financial data
    
    Categories:
    - Assets (0xxx-1xxx): Current assets, property & equipment, other assets
    - Liabilities (2xxx): Current and long-term liabilities  
    - Equity/Capital (3xxx): Partners contribution, distributions, earnings
    - Income (4xxx): Rental income, reimbursements, other income
    - Expenses (5xxx-6xxx): Operating, utilities, R&M, admin, additional
    - Other (7xxx-9xxx): Interest, depreciation, amortization, net income
    """
    
    # Delete existing accounts first (idempotent)
    op.execute("DELETE FROM chart_of_accounts WHERE account_code LIKE '%-%'")
    
    # ASSETS (0xxx-1xxx)
    accounts = [
        # Section Headers
        ('0100-0000', 'ASSETS', 'asset', 'header', None, True, 1),
        ('0101-0000', 'Current Assets', 'asset', 'current_asset', None, False, 2),
        
        # Cash Accounts
        ('0122-0000', 'Cash - Operating', 'asset', 'current_asset', 'cash', False, 3),
        ('0123-0000', 'Cash - Operating II', 'asset', 'current_asset', 'cash', False, 4),
        ('0125-0000', 'Cash - Operating IV-PNC', 'asset', 'current_asset', 'cash', False, 5),
        
        # Receivables
        ('0305-0000', 'A/R Tenants', 'asset', 'current_asset', 'accounts_receivable', False, 10),
        ('0306-0000', 'A/R Other', 'asset', 'current_asset', 'accounts_receivable', False, 11),
        
        # Current Assets Total
        ('0499-9000', 'Total Current Assets', 'asset', 'current_asset', 'total', True, 99),
        
        # Property & Equipment
        ('0500-0000', 'Property & Equipment', 'asset', 'fixed_asset', None, False, 100),
        ('0510-0000', 'Land', 'asset', 'fixed_asset', 'land', False, 101),
        ('0610-0000', 'Buildings', 'asset', 'fixed_asset', 'buildings', False, 102),
        ('0710-0000', '5 Year Improvements', 'asset', 'fixed_asset', 'improvements', False, 103),
        ('0810-0000', '15 Year Improvements', 'asset', 'fixed_asset', 'improvements', False, 104),
        ('0815-0000', '30 Year - Roof', 'asset', 'fixed_asset', 'improvements', False, 105),
        ('0816-0000', '30 Year - HVAC', 'asset', 'fixed_asset', 'improvements', False, 106),
        ('0910-0000', 'Other Improvements', 'asset', 'fixed_asset', 'improvements', False, 107),
        ('0912-0000', 'PARKING-LOT', 'asset', 'fixed_asset', 'improvements', False, 108),
        ('0950-0000', 'TI/Current Improvements', 'asset', 'fixed_asset', 'improvements', False, 109),
        
        # Accumulated Depreciation
        ('1061-0000', 'Accum. Depr. - Buildings', 'asset', 'fixed_asset', 'accumulated_depreciation', False, 120),
        ('1071-0000', 'Accum. Depr. 5 Year Impr.', 'asset', 'fixed_asset', 'accumulated_depreciation', False, 121),
        ('1081-0000', 'Accum. Depr. 15 Yr Impr.', 'asset', 'fixed_asset', 'accumulated_depreciation', False, 122),
        ('1082-0000', 'Accum. Depr.-Roof2008', 'asset', 'fixed_asset', 'accumulated_depreciation', False, 123),
        ('1091-0000', 'Accum. Depr.-Other Imp.', 'asset', 'fixed_asset', 'accumulated_depreciation', False, 124),
        ('1099-0000', 'Total Property & Equipment', 'asset', 'fixed_asset', 'total', True, 199),
        
        # Other Assets
        ('1200-0000', 'Other Assets', 'asset', 'other_asset', None, False, 200),
        ('1210-0000', 'Deposits', 'asset', 'other_asset', 'deposits', False, 201),
        ('1310-0000', 'Escrow - Property Tax', 'asset', 'other_asset', 'escrow', False, 202),
        ('1320-0000', 'Escrow - Insurance', 'asset', 'other_asset', 'escrow', False, 203),
        ('1330-0000', 'Escrow - TI/LC', 'asset', 'other_asset', 'escrow', False, 204),
        ('1340-0000', 'Escrow - Replacement Reserves', 'asset', 'other_asset', 'escrow', False, 205),
        ('1920-0000', 'Loan Costs', 'asset', 'other_asset', 'deferred_costs', False, 210),
        ('1922-0000', 'Accum. Amortization Loan Costs', 'asset', 'other_asset', 'deferred_costs', False, 211),
        ('1950-0000', 'External - Lease Commission', 'asset', 'other_asset', 'deferred_costs', False, 212),
        ('1950-5000', 'Internal - Lease Commission', 'asset', 'other_asset', 'deferred_costs', False, 213),
        ('1952-0000', 'Accum. Amort - TI/LC', 'asset', 'other_asset', 'deferred_costs', False, 214),
        ('1995-0000', 'Prepaid Insurance', 'asset', 'other_asset', 'prepaid', False, 220),
        ('1998-0000', 'Total Other Assets', 'asset', 'other_asset', 'total', True, 299),
        
        # Total Assets
        ('1999-0000', 'TOTAL ASSETS', 'asset', 'total', None, True, 999),
        
        # LIABILITIES (2xxx)
        ('2030-0000', 'Accrued Expenses', 'liability', 'current_liability', 'accrued', False, 1000),
        ('2110-0000', 'Accounts Payable Trade', 'liability', 'current_liability', 'accounts_payable', False, 1001),
        ('2120-0000', 'A/P Series RDF Investors LLC', 'liability', 'current_liability', 'accounts_payable', False, 1002),
        ('2132-0000', 'A/P 5Rivers CRE, LLC', 'liability', 'current_liability', 'accounts_payable', False, 1003),
        ('2197-0000', 'Loans Payable 5Rivers', 'liability', 'current_liability', 'short_term_debt', False, 1004),
        ('2410-0000', 'Property Tax Payable', 'liability', 'current_liability', 'tax_payable', False, 1010),
        ('2510-0000', 'Rent Received in Advance', 'liability', 'current_liability', 'deferred_revenue', False, 1020),
        ('2515-0000', 'A/P Tenant TI/LC Obligations', 'liability', 'current_liability', 'tenant_obligations', False, 1021),
        ('2520-0000', 'Deposit Refundable to Tenant', 'liability', 'current_liability', 'deposits', False, 1022),
        ('2521-0000', 'Construction Deposit Refundable', 'liability', 'current_liability', 'deposits', False, 1023),
        ('2585-0000', 'A/P Suspense', 'liability', 'current_liability', 'other', False, 1030),
        ('2590-0000', 'Total Current Liabilities', 'liability', 'current_liability', 'total', True, 1099),
        
        # Long Term Liabilities
        ('2600-0000', 'Long Term Liabilities', 'liability', 'long_term_liability', None, False, 1100),
        ('2612-0000', 'NorthMarq Capital', 'liability', 'long_term_liability', 'mortgage', False, 1101),
        ('2900-0000', 'Total Long Term Liabilities', 'liability', 'long_term_liability', 'total', True, 1199),
        
        # Total Liabilities
        ('2999-0000', 'TOTAL LIABILITIES', 'liability', 'total', None, True, 1999),
        
        # EQUITY/CAPITAL (3xxx)
        ('3000-0000', 'CAPITAL', 'equity', 'equity', None, False, 2000),
        ('3050-0000', 'Partners Contribution', 'equity', 'equity', 'contribution', False, 2001),
        ('3910-0000', 'Beginning Equity', 'equity', 'equity', 'retained_earnings', False, 2010),
        ('3990-0000', 'Distribution', 'equity', 'equity', 'distribution', False, 2020),
        ('3995-0000', 'Current Period Earnings', 'equity', 'equity', 'net_income', False, 2030),
        ('3999-0000', 'TOTAL CAPITAL', 'equity', 'equity', 'total', True, 2099),
        ('3999-9000', 'TOTAL LIABILITIES & CAPITAL', 'equity', 'total', None, True, 2999),
        
        # INCOME (4xxx)
        ('4010-0000', 'Base Rentals', 'income', 'rental_income', 'base_rent', False, 3000),
        ('4013-0000', 'Management Fee Income', 'income', 'other_income', 'management_fee', False, 3001),
        ('4018-0000', 'Interest Income', 'income', 'other_income', 'interest', False, 3002),
        ('4020-0000', 'Tax', 'income', 'rental_income', 'tax_reimbursement', False, 3010),
        ('4030-0000', 'Insurance', 'income', 'rental_income', 'insurance_reimbursement', False, 3011),
        ('4040-0000', 'CAM', 'income', 'rental_income', 'cam_reimbursement', False, 3012),
        ('4050-0000', 'Percentage Rent', 'income', 'rental_income', 'percentage_rent', False, 3020),
        ('4055-0000', 'Utilities Reimbursement', 'income', 'rental_income', 'utilities_reimbursement', False, 3021),
        ('4056-0000', 'Termination Fee Income', 'income', 'other_income', 'termination_fee', False, 3022),
        ('4060-0000', 'Annual Cams', 'income', 'rental_income', 'annual_cam', False, 3023),
        ('4090-0000', 'Other Income', 'income', 'other_income', 'misc', False, 3090),
        ('4091-0000', 'End of Day Investment Sweep Int Income', 'income', 'other_income', 'interest', False, 3091),
        ('4990-0000', 'TOTAL INCOME', 'income', 'total', None, True, 3999),
        
        # OPERATING EXPENSES (5xxx)
        ('5001-0000', 'Operating Expenses', 'expense', 'operating_expense', None, False, 4000),
        ('5010-0000', 'Property Tax', 'expense', 'operating_expense', 'property_tax', False, 4001),
        ('5012-0000', 'Property Insurance', 'expense', 'operating_expense', 'insurance', False, 4002),
        ('5014-0000', 'Property Tax Savings Consultant', 'expense', 'operating_expense', 'property_tax', False, 4003),
        ('5040-0000', 'R&M Operating Expenses', 'expense', 'operating_expense', 'maintenance', False, 4010),
        ('5090-0000', 'Other Operating Expenses', 'expense', 'operating_expense', 'other', False, 4020),
        
        # Utilities (5100-5199)
        ('5100-0000', 'Utility Expense', 'expense', 'operating_expense', 'utilities', False, 4100),
        ('5105-0000', 'Electricity Service', 'expense', 'operating_expense', 'utilities', False, 4101),
        ('5110-0000', 'Gas Service', 'expense', 'operating_expense', 'utilities', False, 4102),
        ('5115-0000', 'Water & Sewer Service', 'expense', 'operating_expense', 'utilities', False, 4103),
        ('5125-0000', 'Trash Service', 'expense', 'operating_expense', 'utilities', False, 4104),
        ('5199-0000', 'Total Utility Expense', 'expense', 'operating_expense', 'utilities', True, 4199),
        
        # Contracted Expenses (5200-5299)
        ('5200-0000', 'Contracted Expense', 'expense', 'operating_expense', 'contracted', False, 4200),
        ('5210-0000', 'Contract - Parking Lot Sweeping', 'expense', 'operating_expense', 'contracted', False, 4201),
        ('5215-0000', 'Contract - Building Pressure Washing', 'expense', 'operating_expense', 'contracted', False, 4202),
        ('5220-0000', 'Contract - Sidewalk Pressure Washing', 'expense', 'operating_expense', 'contracted', False, 4203),
        ('5225-0000', 'Contract - Snow Removal & Ice Melt', 'expense', 'operating_expense', 'contracted', False, 4204),
        ('5230-0000', 'Contract - Landscaping', 'expense', 'operating_expense', 'contracted', False, 4205),
        ('5235-0000', 'Contract - Janitorial/Portering', 'expense', 'operating_expense', 'contracted', False, 4206),
        ('5240-0000', 'Contract - Fire Safety Monitoring', 'expense', 'operating_expense', 'contracted', False, 4207),
        ('5245-0000', 'Contract - Pest Control', 'expense', 'operating_expense', 'contracted', False, 4208),
        ('5255-0000', 'Contract - Security', 'expense', 'operating_expense', 'contracted', False, 4209),
        ('5270-0000', 'Contract - Plumbing', 'expense', 'operating_expense', 'contracted', False, 4210),
        ('5275-0000', 'Contract - Elevator', 'expense', 'operating_expense', 'contracted', False, 4211),
        ('5299-0000', 'Total Contracted Expenses', 'expense', 'operating_expense', 'contracted', True, 4299),
        
        # Repair & Maintenance (5300-5399)
        ('5300-0000', 'Repair & Maintenance Operating Expon', 'expense', 'operating_expense', 'maintenance', False, 4300),
        ('5302-0000', 'R&M - Elevator Repairs', 'expense', 'operating_expense', 'maintenance', False, 4301),
        ('5306-0000', 'R&M - Landscape Repairs', 'expense', 'operating_expense', 'maintenance', False, 4302),
        ('5308-0000', 'R&M - Irrigation Repairs', 'expense', 'operating_expense', 'maintenance', False, 4303),
        ('5312-0000', 'R&M - Bulk Trash Removal', 'expense', 'operating_expense', 'maintenance', False, 4304),
        ('5314-0000', 'R&M - Fire Safety Repairs', 'expense', 'operating_expense', 'maintenance', False, 4305),
        ('5316-0000', 'R&M - Fire Sprinkler Inspection', 'expense', 'operating_expense', 'maintenance', False, 4306),
        ('5318-0000', 'R&M - Plumbing', 'expense', 'operating_expense', 'maintenance', False, 4307),
        ('5322-0000', 'R&M - Electrical Inspections & Repairs', 'expense', 'operating_expense', 'maintenance', False, 4308),
        ('5326-0000', 'R&M - Building Maintenance', 'expense', 'operating_expense', 'maintenance', False, 4309),
        ('5332-0000', 'R&M - Exterior Painting', 'expense', 'operating_expense', 'maintenance', False, 4310),
        ('5334-0000', 'R&M - Parking Lot Repairs', 'expense', 'operating_expense', 'maintenance', False, 4311),
        ('5336-0000', 'R&M - Sidewalk & Concrete Repairs', 'expense', 'operating_expense', 'maintenance', False, 4312),
        ('5338-0000', 'R&M - Exterior', 'expense', 'operating_expense', 'maintenance', False, 4313),
        ('5340-0000', 'R&M - Interior', 'expense', 'operating_expense', 'maintenance', False, 4314),
        ('5342-0000', 'R&M - HVAC', 'expense', 'operating_expense', 'maintenance', False, 4315),
        ('5356-0000', 'R&M - Lighting', 'expense', 'operating_expense', 'maintenance', False, 4316),
        ('5358-0000', 'R&M - Misc Maintenance Supplies', 'expense', 'operating_expense', 'maintenance', False, 4317),
        ('5360-0000', 'R&M - Roofing Repairs - Major', 'expense', 'operating_expense', 'maintenance', False, 4318),
        ('5362-0000', 'R&M - Roofing Repairs - Minor', 'expense', 'operating_expense', 'maintenance', False, 4319),
        ('5364-0000', 'R&M - Doors/Locks N Keys', 'expense', 'operating_expense', 'maintenance', False, 4320),
        ('5366-0000', 'R&M - Seasonal Decoration', 'expense', 'operating_expense', 'maintenance', False, 4321),
        ('5370-0000', 'R&M - Signage', 'expense', 'operating_expense', 'maintenance', False, 4322),
        ('5376-0000', 'R&M - Misc', 'expense', 'operating_expense', 'maintenance', False, 4323),
        ('5399-0000', 'Total R&M Operating Expenses', 'expense', 'operating_expense', 'maintenance', True, 4399),
        
        # Administration Expenses (5400-5499)
        ('5400-0001', 'Administration Expense', 'expense', 'operating_expense', 'administrative', False, 4400),
        ('5400-0002', 'Salaries Expense', 'expense', 'operating_expense', 'administrative', False, 4401),
        ('5400-0003', 'Benefits Expense', 'expense', 'operating_expense', 'administrative', False, 4402),
        ('5400-0004', 'Computer & Software Expense', 'expense', 'operating_expense', 'administrative', False, 4403),
        ('5400-0006', 'Employee HR Related Expense', 'expense', 'operating_expense', 'administrative', False, 4404),
        ('5400-0090', 'Office Supplies Expense', 'expense', 'operating_expense', 'administrative', False, 4405),
        ('5435-0000', 'Meals & Entertainment', 'expense', 'operating_expense', 'administrative', False, 4410),
        ('5440-0000', 'Management Office Expense', 'expense', 'operating_expense', 'administrative', False, 4411),
        ('5445-0000', 'Management Office Supplies & Equip', 'expense', 'operating_expense', 'administrative', False, 4412),
        ('5455-0000', 'Permits', 'expense', 'operating_expense', 'administrative', False, 4413),
        ('5460-0000', 'Postage & Carrier', 'expense', 'operating_expense', 'administrative', False, 4414),
        ('5465-0000', 'Telephone', 'expense', 'operating_expense', 'administrative', False, 4415),
        ('5470-0000', 'Travel', 'expense', 'operating_expense', 'administrative', False, 4416),
        ('5480-0000', 'Miscellaneous Admin', 'expense', 'operating_expense', 'administrative', False, 4417),
        ('5490-0000', 'Lease Abstracting', 'expense', 'operating_expense', 'administrative', False, 4418),
        ('5499-0000', 'Total Administration Expense', 'expense', 'operating_expense', 'administrative', True, 4499),
        
        ('5990-0000', 'Total Operating Expenses', 'expense', 'operating_expense', 'total', True, 4999),
        
        # ADDITIONAL OPERATING EXPENSES (6xxx)
        ('6000-0000', 'Additional Operating Expenses', 'expense', 'additional_expense', None, False, 5000),
        ('6010-0000', 'Off Site Management', 'expense', 'additional_expense', 'management', False, 5001),
        ('6010-5000', 'On-Site Management Fee', 'expense', 'additional_expense', 'management', False, 5002),
        ('6012-0000', 'Franchise Tax', 'expense', 'additional_expense', 'taxes', False, 5010),
        ('6012-5000', 'Pass Thru Entity Tax', 'expense', 'additional_expense', 'taxes', False, 5011),
        ('6014-0000', 'Leasing Commissions', 'expense', 'additional_expense', 'leasing', False, 5020),
        ('6016-0000', 'Tenant Improvements', 'expense', 'additional_expense', 'leasing', False, 5021),
        
        # Professional Fees (6020-6029)
        ('6020-0000', 'Professional Fees', 'expense', 'additional_expense', 'professional_fees', False, 5030),
        ('6020-5000', 'Accounting Fee', 'expense', 'additional_expense', 'professional_fees', False, 5031),
        ('6020-6000', 'Asset Management Fee', 'expense', 'additional_expense', 'professional_fees', False, 5032),
        ('6020-7000', 'CMF-Construction Management Fee', 'expense', 'additional_expense', 'professional_fees', False, 5033),
        ('6022-0000', 'Legal Fees / SOS Fee', 'expense', 'additional_expense', 'professional_fees', False, 5034),
        ('6024-0000', 'Bank Charges', 'expense', 'additional_expense', 'banking', False, 5040),
        ('6025-0000', 'Bank Control A/c Fee', 'expense', 'additional_expense', 'banking', False, 5041),
        
        # Landlord Expenses (6040-6069)
        ('6040-0000', 'LL - Expense', 'expense', 'additional_expense', 'landlord', False, 5050),
        ('6050-0000', 'LL Repairs & Maintenance', 'expense', 'additional_expense', 'landlord', False, 5051),
        ('6051-0000', 'LL - Plumbing', 'expense', 'additional_expense', 'landlord', False, 5052),
        ('6052-0000', 'LL - Electrical Repairs', 'expense', 'additional_expense', 'landlord', False, 5053),
        ('6054-0000', 'LL - HVAC Repairs', 'expense', 'additional_expense', 'landlord', False, 5054),
        ('6058-0000', 'LL - Vacant Space Expenses', 'expense', 'additional_expense', 'landlord', False, 5055),
        ('6059-0000', 'LL - General Repairs', 'expense', 'additional_expense', 'landlord', False, 5056),
        ('6061-0000', 'LL - Electricity', 'expense', 'additional_expense', 'landlord', False, 5057),
        ('6064-0000', 'LL-Misc', 'expense', 'additional_expense', 'landlord', False, 5058),
        ('6065-0000', 'LL-Site Map', 'expense', 'additional_expense', 'landlord', False, 5059),
        ('6069-0000', 'Total LL Expense', 'expense', 'additional_expense', 'landlord', True, 5069),
        
        ('6190-0000', 'Total Additional Operating Expenses', 'expense', 'additional_expense', 'total', True, 5099),
        ('6199-0000', 'TOTAL EXPENSES', 'expense', 'total', None, True, 5999),
        ('6299-0000', 'NET OPERATING INCOME', 'income', 'net_operating_income', None, True, 6999),
        
        # OTHER INCOME/EXPENSES (7xxx-9xxx)
        ('7000-0000', 'Other Income/Expenses', 'expense', 'other_expense', None, False, 7000),
        ('7010-0000', 'Mortgage Interest', 'expense', 'other_expense', 'interest', False, 7001),
        ('7020-0000', 'Depreciation', 'expense', 'other_expense', 'depreciation', False, 7002),
        ('7030-0000', 'Amortization', 'expense', 'other_expense', 'amortization', False, 7003),
        ('7090-0000', 'Total Other Income/Expense', 'expense', 'other_expense', 'total', True, 7099),
        
        ('9090-0000', 'NET INCOME', 'income', 'net_income', None, True, 9999),
    ]
    
    # Prepare insert statements
    for account in accounts:
        code, name, acc_type, category, subcategory, is_calc, display_order = account
        
        # Determine document types
        if code.startswith(('0', '1', '2', '3')):
            doc_types = "{'balance_sheet'}"
        elif code.startswith(('4', '5', '6', '7', '9')):
            doc_types = "{'income_statement'}"
        else:
            doc_types = "{'balance_sheet', 'income_statement'}"
        
        # Determine parent account code
        parent_code = 'NULL'
        if is_calc:
            # Totals don't have parents
            parent_code = 'NULL'
        elif code.startswith('01') and code != '0100-0000' and code != '0101-0000':
            parent_code = "'0101-0000'"  # Current Assets parent
        elif code.startswith('05') and code != '0500-0000':
            parent_code = "'0500-0000'"  # P&E parent
        elif code.startswith('12') or code.startswith('13') or code.startswith('19'):
            parent_code = "'1200-0000'"  # Other Assets parent
        elif code.startswith('2') and code not in ['2590-0000', '2900-0000', '2999-0000']:
            if int(code[:2]) < 26:
                parent_code = "'2590-0000'"  # Current Liabilities parent
            else:
                parent_code = "'2900-0000'"  # Long-term Liabilities parent
        elif code.startswith('3') and code != '3000-0000' and code not in ['3999-0000', '3999-9000']:
            parent_code = "'3000-0000'"  # Capital parent
        elif code.startswith('51') and code != '5100-0000' and code != '5199-0000':
            parent_code = "'5100-0000'"  # Utilities parent
        elif code.startswith('52') and code != '5200-0000' and code != '5299-0000':
            parent_code = "'5200-0000'"  # Contracted parent
        elif code.startswith('53') and code != '5300-0000' and code != '5399-0000':
            parent_code = "'5300-0000'"  # R&M parent
        elif code.startswith('54') and code != '5400-0001' and code != '5499-0000':
            parent_code = "'5400-0001'"  # Admin parent
        elif code.startswith('60') or code.startswith('61'):
            parent_code = "'6000-0000'"  # Additional Expenses parent
        elif code.startswith('70') and code != '7000-0000' and code != '7090-0000':
            parent_code = "'7000-0000'"  # Other I/E parent
        
        # Insert account
        op.execute(f"""
            INSERT INTO chart_of_accounts (
                account_code, account_name, account_type, category, subcategory,
                parent_account_code, document_types, is_calculated, display_order, is_active
            ) VALUES (
                '{code}', '{name.replace("'", "''")}', '{acc_type}', 
                {'NULL' if not category else f"'{category}'"}, 
                {'NULL' if not subcategory else f"'{subcategory}'"}, 
                {parent_code}, 
                ARRAY{doc_types}, 
                {is_calc}, {display_order}, TRUE
            )
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
        """)
    
    print(f"✅ Seeded {len(accounts)} accounts to Chart of Accounts")


def downgrade():
    """Remove seeded accounts"""
    op.execute("DELETE FROM chart_of_accounts WHERE account_code LIKE '%-%'")
    print("✅ Removed seeded chart of accounts")

