"""
Seed data for REIMS2 financial system

Populates:
- Chart of Accounts
- Validation Rules  
- Extraction Templates
"""
import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.chart_of_accounts import ChartOfAccounts
from app.models.validation_rule import ValidationRule
from app.models.extraction_template import ExtractionTemplate


def seed_chart_of_accounts_from_sql(db: Session):
    """
    Seed comprehensive Wendover Commons chart of accounts from SQL file
    This loads ~130 accounts extracted from actual Wendover financial statements
    """
    sql_file_path = os.path.join(
        os.path.dirname(__file__), 
        'seeds', 
        'chart_of_accounts_seed.sql'
    )
    
    if os.path.exists(sql_file_path):
        print(f"Loading chart of accounts from {sql_file_path}")
        with open(sql_file_path, 'r') as f:
            sql_content = f.read()
        
        # Remove comments
        lines = []
        for line in sql_content.split('\n'):
            stripped = line.strip()
            # Skip comment lines
            if not stripped.startswith('--') and stripped:
                lines.append(line)
        
        # Join back and split by semicolons properly
        clean_sql = '\n'.join(lines)
        statements = clean_sql.split(';')
        
        executed_count = 0
        for statement in statements:
            stmt = statement.strip()
            if stmt:
                try:
                    db.execute(text(stmt))
                    executed_count += 1
                except Exception as e:
                    print(f"Warning executing statement: {str(e)[:100]}")
        
        db.commit()
        
        # Count inserted accounts
        count = db.query(ChartOfAccounts).count()
        print(f"✅ Seeded {count} chart of accounts entries from SQL file (executed {executed_count} statements)")
    else:
        print(f"⚠️  SQL seed file not found at {sql_file_path}, using Python seed instead")
        seed_chart_of_accounts(db)


def seed_chart_of_accounts(db: Session):
    """Seed standard chart of accounts"""
    
    accounts = [
        # ASSETS
        {"code": "1000-0000", "name": "ASSETS", "type": "asset", "category": "header", "calculated": True, "order": 1, "docs": ["balance_sheet"]},
        {"code": "1100-0000", "name": "Current Assets", "type": "asset", "category": "current_asset", "parent": "1000-0000", "calculated": True, "order": 2, "docs": ["balance_sheet"]},
        {"code": "1110-0000", "name": "Cash - Operating", "type": "asset", "category": "cash", "parent": "1100-0000", "order": 3, "docs": ["balance_sheet", "cash_flow"]},
        {"code": "1120-0000", "name": "Cash - Reserve", "type": "asset", "category": "cash", "parent": "1100-0000", "order": 4, "docs": ["balance_sheet"]},
        {"code": "1130-0000", "name": "Accounts Receivable", "type": "asset", "category": "receivables", "parent": "1100-0000", "order": 5, "docs": ["balance_sheet"]},
        {"code": "1140-0000", "name": "Prepaid Expenses", "type": "asset", "category": "prepaid", "parent": "1100-0000", "order": 6, "docs": ["balance_sheet"]},
        
        {"code": "1200-0000", "name": "Property & Equipment", "type": "asset", "category": "fixed_asset", "parent": "1000-0000", "calculated": True, "order": 10, "docs": ["balance_sheet"]},
        {"code": "1210-0000", "name": "Land", "type": "asset", "category": "fixed_asset", "parent": "1200-0000", "order": 11, "docs": ["balance_sheet"]},
        {"code": "1220-0000", "name": "Buildings", "type": "asset", "category": "fixed_asset", "parent": "1200-0000", "order": 12, "docs": ["balance_sheet"]},
        {"code": "1230-0000", "name": "Accumulated Depreciation", "type": "asset", "category": "contra_asset", "parent": "1200-0000", "order": 13, "docs": ["balance_sheet"]},
        
        # LIABILITIES
        {"code": "2000-0000", "name": "LIABILITIES", "type": "liability", "category": "header", "calculated": True, "order": 20, "docs": ["balance_sheet"]},
        {"code": "2100-0000", "name": "Current Liabilities", "type": "liability", "category": "current_liability", "parent": "2000-0000", "calculated": True, "order": 21, "docs": ["balance_sheet"]},
        {"code": "2110-0000", "name": "Accounts Payable", "type": "liability", "category": "payables", "parent": "2100-0000", "order": 22, "docs": ["balance_sheet"]},
        {"code": "2120-0000", "name": "Accrued Expenses", "type": "liability", "category": "accrued", "parent": "2100-0000", "order": 23, "docs": ["balance_sheet"]},
        {"code": "2130-0000", "name": "Security Deposits", "type": "liability", "category": "deposits", "parent": "2100-0000", "order": 24, "docs": ["balance_sheet"]},
        
        {"code": "2200-0000", "name": "Long Term Liabilities", "type": "liability", "category": "long_term_liability", "parent": "2000-0000", "calculated": True, "order": 30, "docs": ["balance_sheet"]},
        {"code": "2210-0000", "name": "Mortgage Payable", "type": "liability", "category": "debt", "parent": "2200-0000", "order": 31, "docs": ["balance_sheet"]},
        {"code": "2220-0000", "name": "Notes Payable", "type": "liability", "category": "debt", "parent": "2200-0000", "order": 32, "docs": ["balance_sheet"]},
        
        # EQUITY
        {"code": "3000-0000", "name": "EQUITY/CAPITAL", "type": "equity", "category": "header", "calculated": True, "order": 40, "docs": ["balance_sheet"]},
        {"code": "3100-0000", "name": "Partners Contribution", "type": "equity", "category": "capital", "parent": "3000-0000", "order": 41, "docs": ["balance_sheet"]},
        {"code": "3200-0000", "name": "Beginning Equity", "type": "equity", "category": "retained_earnings", "parent": "3000-0000", "order": 42, "docs": ["balance_sheet"]},
        {"code": "3300-0000", "name": "Current Period Net Income", "type": "equity", "category": "net_income", "parent": "3000-0000", "order": 43, "docs": ["balance_sheet", "income_statement"]},
        {"code": "3400-0000", "name": "Distributions", "type": "equity", "category": "distributions", "parent": "3000-0000", "order": 44, "docs": ["balance_sheet", "cash_flow"]},
        
        # INCOME
        {"code": "4000-0000", "name": "INCOME", "type": "income", "category": "header", "calculated": True, "order": 50, "docs": ["income_statement"]},
        {"code": "4100-0000", "name": "Rental Income", "type": "income", "category": "rental_income", "parent": "4000-0000", "calculated": True, "order": 51, "docs": ["income_statement"]},
        {"code": "4110-0000", "name": "Base Rentals", "type": "income", "category": "rental_income", "parent": "4100-0000", "order": 52, "docs": ["income_statement"]},
        {"code": "4120-0000", "name": "Percentage Rent", "type": "income", "category": "rental_income", "parent": "4100-0000", "order": 53, "docs": ["income_statement"]},
        {"code": "4130-0000", "name": "Parking Income", "type": "income", "category": "rental_income", "parent": "4100-0000", "order": 54, "docs": ["income_statement"]},
        
        {"code": "4200-0000", "name": "Reimbursements", "type": "income", "category": "reimbursements", "parent": "4000-0000", "calculated": True, "order": 60, "docs": ["income_statement"]},
        {"code": "4210-0000", "name": "CAM Reimbursements", "type": "income", "category": "reimbursements", "parent": "4200-0000", "order": 61, "docs": ["income_statement"]},
        {"code": "4220-0000", "name": "Tax Reimbursements", "type": "income", "category": "reimbursements", "parent": "4200-0000", "order": 62, "docs": ["income_statement"]},
        {"code": "4230-0000", "name": "Insurance Reimbursements", "type": "income", "category": "reimbursements", "parent": "4200-0000", "order": 63, "docs": ["income_statement"]},
        
        {"code": "4300-0000", "name": "Other Income", "type": "income", "category": "other_income", "parent": "4000-0000", "order": 70, "docs": ["income_statement"]},
        
        # EXPENSES
        {"code": "5000-0000", "name": "EXPENSES", "type": "expense", "category": "header", "calculated": True, "order": 100, "docs": ["income_statement"]},
        {"code": "5100-0000", "name": "Operating Expenses", "type": "expense", "category": "operating_expense", "parent": "5000-0000", "calculated": True, "order": 101, "docs": ["income_statement"]},
        {"code": "5110-0000", "name": "Property Management Fee", "type": "expense", "category": "operating_expense", "parent": "5100-0000", "order": 102, "docs": ["income_statement"]},
        {"code": "5120-0000", "name": "Repairs & Maintenance", "type": "expense", "category": "operating_expense", "parent": "5100-0000", "order": 103, "docs": ["income_statement"]},
        {"code": "5130-0000", "name": "Utilities", "type": "expense", "category": "operating_expense", "parent": "5100-0000", "order": 104, "docs": ["income_statement"]},
        {"code": "5140-0000", "name": "Insurance", "type": "expense", "category": "operating_expense", "parent": "5100-0000", "order": 105, "docs": ["income_statement"]},
        {"code": "5150-0000", "name": "Property Taxes", "type": "expense", "category": "operating_expense", "parent": "5100-0000", "order": 106, "docs": ["income_statement"]},
        {"code": "5160-0000", "name": "Professional Fees", "type": "expense", "category": "operating_expense", "parent": "5100-0000", "order": 107, "docs": ["income_statement"]},
        
        {"code": "5900-0000", "name": "Net Operating Income", "type": "income", "category": "subtotal", "calculated": True, "formula": "4000-0000 - 5100-0000", "order": 150, "docs": ["income_statement"]},
        
        {"code": "6000-0000", "name": "NON-OPERATING EXPENSES", "type": "expense", "category": "header", "order": 200, "docs": ["income_statement"]},
        {"code": "6100-0000", "name": "Mortgage Interest", "type": "expense", "category": "interest", "parent": "6000-0000", "order": 201, "docs": ["income_statement"]},
        {"code": "6200-0000", "name": "Depreciation", "type": "expense", "category": "depreciation", "parent": "6000-0000", "order": 202, "docs": ["income_statement"]},
        {"code": "6300-0000", "name": "Amortization", "type": "expense", "category": "amortization", "parent": "6000-0000", "order": 203, "docs": ["income_statement"]},
        
        {"code": "9000-0000", "name": "Net Income", "type": "income", "category": "net_income", "calculated": True, "formula": "5900-0000 - 6100-0000 - 6200-0000 - 6300-0000", "order": 300, "docs": ["income_statement"]},
    ]
    
    for acc in accounts:
        existing = db.query(ChartOfAccounts).filter(ChartOfAccounts.account_code == acc["code"]).first()
        if not existing:
            account = ChartOfAccounts(
                account_code=acc["code"],
                account_name=acc["name"],
                account_type=acc["type"],
                category=acc.get("category"),
                subcategory=acc.get("subcategory"),
                parent_account_code=acc.get("parent"),
                document_types=acc.get("docs", []),
                is_calculated=acc.get("calculated", False),
                calculation_formula=acc.get("formula"),
                display_order=acc.get("order"),
                is_active=True
            )
            db.add(account)
    
    db.commit()
    print(f"✅ Seeded {len(accounts)} chart of accounts entries")


def seed_validation_rules(db: Session):
    """Seed business validation rules"""
    
    rules = [
        {
            "name": "balance_sheet_equation",
            "description": "Assets must equal Liabilities + Equity",
            "doc_type": "balance_sheet",
            "rule_type": "balance_check",
            "formula": "total_assets = total_liabilities + total_equity",
            "error_msg": "Balance sheet equation not balanced: Assets ≠ Liabilities + Equity",
            "severity": "error"
        },
        {
            "name": "income_statement_calculation",
            "description": "Net income calculation verification",
            "doc_type": "income_statement",
            "rule_type": "balance_check",
            "formula": "net_income = total_revenue - total_expenses - mortgage_interest - depreciation - amortization",
            "error_msg": "Net income calculation mismatch",
            "severity": "error"
        },
        {
            "name": "noi_calculation",
            "description": "Net Operating Income = Revenue - Operating Expenses",
            "doc_type": "income_statement",
            "rule_type": "balance_check",
            "formula": "noi = total_revenue - operating_expenses",
            "error_msg": "NOI calculation mismatch",
            "severity": "error"
        },
        {
            "name": "occupancy_rate_range",
            "description": "Occupancy rate must be between 0% and 100%",
            "doc_type": "rent_roll",
            "rule_type": "range_check",
            "formula": "occupancy_rate >= 0 AND occupancy_rate <= 100",
            "error_msg": "Occupancy rate must be between 0% and 100%",
            "severity": "error"
        },
        {
            "name": "rent_per_sqft_reasonable",
            "description": "Rent per sqft should be reasonable (>$0, <$200)",
            "doc_type": "rent_roll",
            "rule_type": "range_check",
            "formula": "rent_per_sqft > 0 AND rent_per_sqft < 200",
            "error_msg": "Rent per sqft is outside reasonable range",
            "severity": "warning"
        },
        {
            "name": "cash_flow_balance",
            "description": "Ending cash = Beginning cash + Net cash flow",
            "doc_type": "cash_flow",
            "rule_type": "balance_check",
            "formula": "ending_cash = beginning_cash + net_cash_flow",
            "error_msg": "Cash flow calculation mismatch",
            "severity": "error"
        },
        {
            "name": "total_revenue_positive",
            "description": "Total revenue should be positive",
            "doc_type": "income_statement",
            "rule_type": "range_check",
            "formula": "total_revenue > 0",
            "error_msg": "Total revenue is negative or zero",
            "severity": "warning"
        },
        {
            "name": "expense_ratio_reasonable",
            "description": "Expense ratio should typically be < 80%",
            "doc_type": "income_statement",
            "rule_type": "range_check",
            "formula": "expense_ratio < 0.80",
            "error_msg": "Expense ratio exceeds 80% - may indicate issue",
            "severity": "warning"
        },
        # Rent Roll - Financial Validations (5 new rules)
        {
            "name": "rent_roll_annual_equals_monthly_times_12",
            "description": "Annual rent must equal monthly rent × 12 (±2% tolerance)",
            "doc_type": "rent_roll",
            "rule_type": "balance_check",
            "formula": "abs(annual_rent - (monthly_rent * 12)) / annual_rent <= 0.02",
            "error_msg": "Annual rent does not equal monthly rent × 12 within tolerance",
            "severity": "error"
        },
        {
            "name": "rent_roll_monthly_per_sf_calc",
            "description": "Monthly rent per SF = Monthly rent ÷ Area (±$0.05 tolerance)",
            "doc_type": "rent_roll",
            "rule_type": "balance_check",
            "formula": "abs(monthly_rent_per_sqft - (monthly_rent / unit_area_sqft)) <= 0.05",
            "error_msg": "Monthly rent per SF calculation is incorrect",
            "severity": "warning"
        },
        {
            "name": "rent_roll_annual_per_sf_calc",
            "description": "Annual rent per SF = Annual rent ÷ Area",
            "doc_type": "rent_roll",
            "rule_type": "balance_check",
            "formula": "abs(annual_rent_per_sqft - (annual_rent / unit_area_sqft)) <= 0.10",
            "error_msg": "Annual rent per SF calculation is incorrect",
            "severity": "warning"
        },
        {
            "name": "rent_roll_non_negative_financials",
            "description": "All financial fields must be >= 0",
            "doc_type": "rent_roll",
            "rule_type": "range_check",
            "formula": "monthly_rent >= 0 AND annual_rent >= 0 AND security_deposit >= 0",
            "error_msg": "Financial values must be non-negative",
            "severity": "error"
        },
        {
            "name": "rent_roll_security_deposit_range",
            "description": "Security deposit typically 1-3 months rent",
            "doc_type": "rent_roll",
            "rule_type": "range_check",
            "formula": "security_deposit BETWEEN (monthly_rent * 0.5) AND (monthly_rent * 4)",
            "error_msg": "Security deposit outside typical range (0.5-4 months rent)",
            "severity": "info"
        },
        # Rent Roll - Date Validations (3 new rules)
        {
            "name": "rent_roll_date_sequence",
            "description": "Lease start date must be before end date",
            "doc_type": "rent_roll",
            "rule_type": "date_check",
            "formula": "lease_start_date <= lease_end_date",
            "error_msg": "Lease start date must be before or equal to end date",
            "severity": "error"
        },
        {
            "name": "rent_roll_term_calculation",
            "description": "Term months approximately equals months between dates (±2 months)",
            "doc_type": "rent_roll",
            "rule_type": "calculation_check",
            "formula": "abs(lease_term_months - months_between(lease_start_date, lease_end_date)) <= 2",
            "error_msg": "Lease term months does not match date range",
            "severity": "warning"
        },
        {
            "name": "rent_roll_tenancy_calculation",
            "description": "Tenancy years approximately equals years from start to report date (±0.5 years)",
            "doc_type": "rent_roll",
            "rule_type": "calculation_check",
            "formula": "abs(tenancy_years - years_between(lease_start_date, report_date)) <= 0.5",
            "error_msg": "Tenancy years does not match calculated value",
            "severity": "info"
        },
        # Rent Roll - Area Validations (2 new rules)
        {
            "name": "rent_roll_area_range",
            "description": "Unit area must be within reasonable range (0-100,000 SF)",
            "doc_type": "rent_roll",
            "rule_type": "range_check",
            "formula": "unit_area_sqft >= 0 AND unit_area_sqft <= 100000",
            "error_msg": "Unit area outside reasonable range (0-100,000 SF)",
            "severity": "warning"
        },
        {
            "name": "rent_roll_zero_area_detection",
            "description": "Flag zero-area units (ATM, signage, parking)",
            "doc_type": "rent_roll",
            "rule_type": "detection",
            "formula": "unit_area_sqft = 0",
            "error_msg": "Zero-area unit detected (may be ATM, signage, or parking)",
            "severity": "info"
        },
        # Rent Roll - Edge Case Detection (8 new rules)
        {
            "name": "rent_roll_expired_lease",
            "description": "Flag expired leases (holdover tenants)",
            "doc_type": "rent_roll",
            "rule_type": "detection",
            "formula": "lease_end_date < report_date AND occupancy_status = 'occupied'",
            "error_msg": "Lease expired but tenant still occupying (possible holdover)",
            "severity": "warning"
        },
        {
            "name": "rent_roll_future_lease",
            "description": "Flag future lease start dates",
            "doc_type": "rent_roll",
            "rule_type": "detection",
            "formula": "lease_start_date > report_date",
            "error_msg": "Future lease start date detected",
            "severity": "info"
        },
        {
            "name": "rent_roll_mtm_lease",
            "description": "Flag month-to-month leases (no end date)",
            "doc_type": "rent_roll",
            "rule_type": "detection",
            "formula": "lease_end_date IS NULL AND occupancy_status = 'occupied'",
            "error_msg": "Month-to-month lease detected (no end date)",
            "severity": "info"
        },
        {
            "name": "rent_roll_zero_rent",
            "description": "Flag zero-rent units (expense-only or abatement)",
            "doc_type": "rent_roll",
            "rule_type": "detection",
            "formula": "monthly_rent = 0 AND occupancy_status = 'occupied'",
            "error_msg": "Zero rent detected (expense-only lease or rent abatement)",
            "severity": "info"
        },
        {
            "name": "rent_roll_short_term",
            "description": "Flag short-term leases (< 12 months)",
            "doc_type": "rent_roll",
            "rule_type": "detection",
            "formula": "lease_term_months < 12",
            "error_msg": "Short-term lease detected (< 12 months)",
            "severity": "warning"
        },
        {
            "name": "rent_roll_long_term",
            "description": "Flag very long-term leases (> 20 years / 240 months)",
            "doc_type": "rent_roll",
            "rule_type": "detection",
            "formula": "lease_term_months > 240",
            "error_msg": "Very long-term lease detected (> 20 years, may be ground lease)",
            "severity": "info"
        },
        {
            "name": "rent_roll_unusual_rent_per_sf",
            "description": "Flag unusual rent per SF rates (< $0.50 or > $15.00)",
            "doc_type": "rent_roll",
            "rule_type": "range_check",
            "formula": "monthly_rent_per_sqft < 0.50 OR monthly_rent_per_sqft > 15.00",
            "error_msg": "Unusual rent per SF detected (outside $0.50-$15.00 range)",
            "severity": "warning"
        },
        {
            "name": "rent_roll_multi_unit",
            "description": "Flag multi-unit leases (comma or multiple hyphens in unit number)",
            "doc_type": "rent_roll",
            "rule_type": "detection",
            "formula": "unit_number LIKE '%,%' OR unit_number LIKE '%-%-%'",
            "error_msg": "Multi-unit lease detected",
            "severity": "info"
        },
        # Rent Roll - Special Row Validations (2 new rules)
        {
            "name": "rent_roll_gross_rent_linkage",
            "description": "Gross rent rows must have parent_row_id",
            "doc_type": "rent_roll",
            "rule_type": "required_field",
            "formula": "is_gross_rent_row = false OR parent_row_id IS NOT NULL",
            "error_msg": "Gross rent row missing parent_row_id link",
            "severity": "warning"
        },
        {
            "name": "rent_roll_vacant_validation",
            "description": "Vacant units should have area but no rent",
            "doc_type": "rent_roll",
            "rule_type": "validation",
            "formula": "occupancy_status != 'vacant' OR (unit_area_sqft > 0 AND monthly_rent = 0)",
            "error_msg": "Vacant unit validation failed (should have area, no rent)",
            "severity": "warning"
        }
    ]
    
    for rule in rules:
        existing = db.query(ValidationRule).filter(ValidationRule.rule_name == rule["name"]).first()
        if not existing:
            validation_rule = ValidationRule(
                rule_name=rule["name"],
                rule_description=rule["description"],
                document_type=rule["doc_type"],
                rule_type=rule["rule_type"],
                rule_formula=rule["formula"],
                error_message=rule["error_msg"],
                severity=rule["severity"],
                is_active=True
            )
            db.add(validation_rule)
    
    db.commit()
    print(f"✅ Seeded {len(rules)} validation rules")


def seed_extraction_templates(db: Session):
    """Seed PDF extraction templates"""
    
    templates = [
        {
            "name": "standard_balance_sheet",
            "doc_type": "balance_sheet",
            "structure": {
                "sections": [
                    {
                        "name": "ASSETS",
                        "subsections": ["Current Assets", "Property & Equipment", "Other Assets"]
                    },
                    {
                        "name": "LIABILITIES",
                        "subsections": ["Current Liabilities", "Long Term Liabilities"]
                    },
                    {
                        "name": "CAPITAL",
                        "subsections": ["Partners Contribution", "Beginning Equity", "Distribution"]
                    }
                ],
                "required_fields": ["total_assets", "total_liabilities", "total_capital"],
                "validation": "total_assets = total_liabilities + total_capital"
            },
            "keywords": ["balance sheet", "statement of financial position", "assets", "liabilities", "equity", "capital"],
            "rules": {
                "table_detection": "camelot",
                "text_extraction": "pymupdf",
                "line_item_matching": "keyword_fuzzy"
            },
            "is_default": True
        },
        {
            "name": "standard_income_statement",
            "doc_type": "income_statement",
            "structure": {
                "sections": [
                    {"name": "INCOME", "subsections": ["Rental Income", "Reimbursements", "Other Income"]},
                    {"name": "EXPENSES", "subsections": ["Operating Expenses"]},
                    {"name": "NON-OPERATING", "subsections": ["Interest", "Depreciation"]}
                ],
                "required_fields": ["total_revenue", "total_expenses", "net_income"],
                "calculated_fields": {
                    "noi": "total_revenue - operating_expenses",
                    "net_income": "noi - interest - depreciation - amortization"
                }
            },
            "keywords": ["income statement", "profit and loss", "p&l", "revenue", "expenses", "net income"],
            "rules": {
                "has_period_column": True,
                "has_ytd_column": True,
                "percentage_columns": True
            },
            "is_default": True
        },
        {
            "name": "standard_cash_flow",
            "doc_type": "cash_flow",
            "structure": {
                "sections": [
                    {"name": "Operating Activities", "category": "operating"},
                    {"name": "Investing Activities", "category": "investing"},
                    {"name": "Financing Activities", "category": "financing"}
                ],
                "required_fields": ["beginning_cash", "ending_cash", "net_cash_flow"]
            },
            "keywords": ["cash flow", "statement of cash flows", "operating activities", "investing activities", "financing activities"],
            "rules": {
                "detect_cash_categories": True
            },
            "is_default": True
        },
        {
            "name": "standard_rent_roll",
            "doc_type": "rent_roll",
            "structure": {
                "columns": [
                    # Core identification (6)
                    "property_name", "property_code", "report_date",
                    "unit_number", "tenant_name", "tenant_id",
                    
                    # Lease details (5)
                    "lease_type", "lease_start_date", "lease_end_date",
                    "lease_term_months", "tenancy_years",
                    
                    # Space (1)
                    "unit_area_sqft",
                    
                    # Base rent (4)
                    "monthly_rent", "monthly_rent_per_sqft",
                    "annual_rent", "annual_rent_per_sqft",
                    
                    # Additional charges (2)
                    "annual_recoveries_per_sf", "annual_misc_per_sf",
                    
                    # Security (2)
                    "security_deposit", "loc_amount",
                    
                    # Status flags (5)
                    "is_vacant", "is_gross_rent_row", "parent_row_id",
                    "occupancy_status", "lease_status", "notes"
                ],
                "required_columns": [
                    "property_name", "property_code", "report_date",
                    "unit_number", "unit_area_sqft", "is_vacant"
                ],
                "calculated_fields": {
                    "annual_rent": "monthly_rent * 12",
                    "monthly_rent_per_sqft": "monthly_rent / unit_area_sqft",
                    "annual_rent_per_sqft": "annual_rent / unit_area_sqft",
                    "tenancy_years": "years from lease_start_date to report_date"
                },
                "field_mappings": {
                    "Unit(s)": "unit_number",
                    "Lease": "tenant_name",
                    "Lease Type": "lease_type",
                    "Area": "unit_area_sqft",
                    "Lease From": "lease_start_date",
                    "Lease To": "lease_end_date",
                    "Term": "lease_term_months",
                    "Tenancy Years": "tenancy_years",
                    "Monthly Rent": "monthly_rent",
                    "Monthly Rent/Area": "monthly_rent_per_sqft",
                    "Annual Rent": "annual_rent",
                    "Annual Rent/Area": "annual_rent_per_sqft",
                    "Annual Rec./Area": "annual_recoveries_per_sf",
                    "Annual Misc/Area": "annual_misc_per_sf",
                    "Security Deposit Received": "security_deposit",
                    "LOC Amount/ Bank Guarantee": "loc_amount"
                }
            },
            "keywords": [
                "rent roll", "tenant", "lease", "unit", "expiration", "occupancy",
                "tenancy schedule", "tenant roster", "lease expiration", "occupancy report",
                "rent schedule", "tenant list", "lease schedule"
            ],
            "rules": {
                "is_table": True,
                "detect_headers": True,
                "multi_page": True,
                "handle_gross_rent_rows": True,
                "detect_vacant_units": True,
                "extract_tenant_ids": True,
                "tenant_id_pattern": r'\(t(\d+)\)',
                "parse_multi_unit_leases": True,
                "detect_special_units": True,
                "special_unit_keywords": ["ATM", "LAND", "COMMON", "SIGN"],
                "validation_on_extract": True,
                "extract_summary_section": True
            },
            "is_default": True
        },
        {
            "name": "standard_mortgage_statement",
            "doc_type": "mortgage_statement",
            "structure": {
                "field_patterns": {
                    "loan_number": {
                        "patterns": [
                            r"Loan\s+Number\s*:?\s*([0-9]{6,})",
                            r"Loan\s+#\s*:?\s*([0-9]{6,})",
                            r"LOAN\s+INFORMATION.*?Loan\s+Number\s*:?\s*([0-9]{6,})",
                            r"Account\s+(?:Number|#|No\.?)\s*:?\s*([A-Z0-9\-]{4,})",
                            r"Loan\s+ID\s*:?\s*([A-Z0-9\-]+)"
                        ],
                        "field_type": "text",
                        "required": True
                    },
                    "statement_date": {
                        "patterns": [
                            r"LOAN\s+INFORMATION\s+As\s+of\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})",
                            r"PAYMENT\s+INFORMATION\s+As\s+of\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})",
                            r"As\s+of\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})",
                            r"Statement\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
                            r"Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})"
                        ],
                        "field_type": "date",
                        "required": True
                    },
                    "principal_balance": {
                        "patterns": [
                            r"Principal\s+Balance\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Outstanding\s+Principal\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Current\s+Principal\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Unpaid\s+Principal\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                        ],
                        "field_type": "currency",
                        "required": True
                    },
                    "interest_rate": {
                        "patterns": [
                            r"Interest\s+Rate\s*:?\s*(\d+\.?\d*)\s*%",
                            r"Rate\s*:?\s*(\d+\.?\d*)\s*%",
                            r"(\d+\.?\d*)\s*%\s+Interest"
                        ],
                        "field_type": "percentage",
                        "required": False
                    },
                    "monthly_payment": {
                        "patterns": [
                            r"Monthly\s+Payment\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Payment\s+Amount\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Total\s+Payment\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                        ],
                        "field_type": "currency",
                        "required": False
                    },
                    "principal_due": {
                        "patterns": [
                            r"Current\s+Principal\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"PAYMENT\s+INFORMATION.*?Current\s+Principal\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Principal\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Principal\s+Payment\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                        ],
                        "field_type": "currency",
                        "required": False
                    },
                    "interest_due": {
                        "patterns": [
                            r"Current\s+Interest\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"PAYMENT\s+INFORMATION.*?Current\s+Interest\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Interest\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Interest\s+Payment\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                        ],
                        "field_type": "currency",
                        "required": False
                    },
                    "payment_due_date": {
                        "patterns": [
                            r"Payment\s+Due\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
                            r"Due\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})"
                        ],
                        "field_type": "date",
                        "required": False
                    },
                    "maturity_date": {
                        "patterns": [
                            r"Maturity\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
                            r"Final\s+Payment\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})"
                        ],
                        "field_type": "date",
                        "required": False
                    },
                    "ytd_principal_paid": {
                        "patterns": [
                            r"YEAR\s+TO\s+DATE.*?Principal\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"YTD.*?Principal\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Year\s+to\s+Date\s+Principal\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                        ],
                        "field_type": "currency",
                        "required": False
                    },
                    "ytd_interest_paid": {
                        "patterns": [
                            r"YEAR\s+TO\s+DATE.*?Interest\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"YTD.*?Interest\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Year\s+to\s+Date\s+Interest\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                        ],
                        "field_type": "currency",
                        "required": False
                    },
                    "tax_escrow_balance": {
                        "patterns": [
                            r"Tax\s+Escrow\s+Balance\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Escrow\s+for\s+Taxes\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                        ],
                        "field_type": "currency",
                        "required": False
                    },
                    "insurance_escrow_balance": {
                        "patterns": [
                            r"Insurance\s+Escrow\s+Balance\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                            r"Escrow\s+for\s+Insurance\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                        ],
                        "field_type": "currency",
                        "required": False
                    },
                    "borrower_name": {
                        "patterns": [
                            r"Borrower\s*:?\s*(.+?)(?:\n|$)",
                            r"Account\s+Holder\s*:?\s*(.+?)(?:\n|$)"
                        ],
                        "field_type": "text",
                        "required": False
                    },
                    "property_address": {
                        "patterns": [
                            r"Property\s+Address\s*:?\s*(.+?)(?:\n|$)",
                            r"Collateral\s+Address\s*:?\s*(.+?)(?:\n|$)"
                        ],
                        "field_type": "text",
                        "required": False
                    }
                },
                "required_fields": ["loan_number", "statement_date", "principal_balance"],
                "lender_patterns": {
                    "wells_fargo": ["Wells Fargo", "Wells Fargo Bank", "WF"],
                    "bank_of_america": ["Bank of America", "BofA", "BOA"],
                    "chase": ["Chase", "JPMorgan Chase", "JP Morgan"],
                    "citibank": ["Citibank", "Citi"],
                    "us_bank": ["U.S. Bank", "US Bank"]
                }
            },
            "keywords": [
                "mortgage statement",
                "loan statement",
                "mortgage account",
                "principal balance",
                "interest rate",
                "monthly payment",
                "escrow",
                "statement date",
                "payment due date",
                "ytd principal",
                "ytd interest"
            ],
            "rules": {
                "extraction_method": "field_patterns",
                "confidence_threshold": 60,
                "required_fields_count": 3
            },
            "is_default": True
        }
    ]
    
    for tmpl in templates:
        existing = db.query(ExtractionTemplate).filter(ExtractionTemplate.template_name == tmpl["name"]).first()
        if not existing:
            template = ExtractionTemplate(
                template_name=tmpl["name"],
                document_type=tmpl["doc_type"],
                template_structure=tmpl["structure"],
                keywords=tmpl["keywords"],
                extraction_rules=tmpl.get("rules", {}),
                is_default=tmpl.get("is_default", False)
            )
            db.add(template)
    
    db.commit()
    print(f"✅ Seeded {len(templates)} extraction templates")


def seed_all(db: Session, use_sql_seed: bool = True):
    """
    Seed all initial data
    
    Args:
        use_sql_seed: If True, load comprehensive Wendover accounts from SQL file.
                     If False, use Python-defined accounts.
    """
    print("Starting database seeding...")
    if use_sql_seed:
        seed_chart_of_accounts_from_sql(db)
    else:
        seed_chart_of_accounts(db)
    seed_validation_rules(db)
    seed_extraction_templates(db)
    try:
        from app.db.seeds.forensic_calculated_rules_seed import seed_calculated_rules
        seed_calculated_rules()
    except Exception as exc:
        print(f"⚠️  Calculated rules seeding skipped: {exc}")
    print("✅ Database seeding completed!")
