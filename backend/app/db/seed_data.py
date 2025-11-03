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
                    "unit_number", "tenant_name", "lease_start", "lease_end",
                    "sqft", "monthly_rent", "annual_rent", "rent_per_sqft"
                ],
                "required_columns": ["unit_number", "tenant_name", "monthly_rent"],
                "calculations": {
                    "annual_rent": "monthly_rent * 12",
                    "rent_per_sqft": "annual_rent / sqft"
                }
            },
            "keywords": ["rent roll", "tenant", "lease", "unit", "expiration", "occupancy"],
            "rules": {
                "is_table": True,
                "detect_headers": True,
                "multi_page": True
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
    print("✅ Database seeding completed!")

