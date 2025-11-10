"""
Pytest configuration and shared fixtures
"""
import pytest
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.db.database import Base
from app.models.user import User
from app.models.property import Property
from app.models.chart_of_accounts import ChartOfAccounts
from app.models.financial_period import FinancialPeriod
from app.core.security import get_password_hash

# Use Docker PostgreSQL (from docker-compose)
# Use separate test database name to avoid conflicts
TEST_DATABASE_URL = "postgresql://reims:reims@localhost:5432/reims_test"

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Apply CHECK constraints manually (since they're not in metadata)
    with test_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        try:
            # Add CHECK constraints from migration
            conn.execute(text("""
                ALTER TABLE properties 
                DROP CONSTRAINT IF EXISTS ck_properties_status;
                
                ALTER TABLE properties
                ADD CONSTRAINT ck_properties_status 
                CHECK (status IN ('active', 'sold', 'under_contract'));
                
                ALTER TABLE financial_periods
                DROP CONSTRAINT IF EXISTS ck_financial_periods_month;
                
                ALTER TABLE financial_periods
                ADD CONSTRAINT ck_financial_periods_month
                CHECK (period_month BETWEEN 1 AND 12);
                
                ALTER TABLE financial_periods
                DROP CONSTRAINT IF EXISTS ck_financial_periods_quarter;
                
                ALTER TABLE financial_periods
                ADD CONSTRAINT ck_financial_periods_quarter
                CHECK (fiscal_quarter IS NULL OR (fiscal_quarter BETWEEN 1 AND 4));
            """))
        except:
            pass  # Constraints might not exist yet
    
    # Create session
    session = TestingSessionLocal()
    
    yield session
    
    # Rollback and close
    session.rollback()
    session.close()
    
    # Drop all tables
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def test_user(db_session):
    """Create a test user for authentication"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_user(db_session):
    """Create an admin test user"""
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
        is_superuser=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def sample_properties(db_session, test_user):
    """Create sample properties for testing"""
    properties = [
        Property(
            property_code="ESP",
            property_name="Esplanade",
            property_type="Retail",
            address="1401 Esplanade Drive",
            city="Kenner",
            state="LA",
            zip_code="70065",
            total_area_sqft=Decimal("452750.00"),
            acquisition_date=date(2019, 1, 15),
            status="active",
            created_by=test_user.id
        ),
        Property(
            property_code="WEND",
            property_name="Wendover Place",
            property_type="Office",
            address="4370 Georgetown Square",
            city="Atlanta",
            state="GA",
            zip_code="30338",
            total_area_sqft=Decimal("128000.00"),
            acquisition_date=date(2018, 6, 1),
            status="active",
            created_by=test_user.id
        ),
        Property(
            property_code="TCSH",
            property_name="Town Center at Stonecrest",
            property_type="Mixed-Use",
            address="2929 Turner Hill Road",
            city="Lithonia",
            state="GA",
            zip_code="30038",
            total_area_sqft=Decimal("350000.00"),
            acquisition_date=date(2020, 3, 10),
            status="active",
            created_by=test_user.id
        ),
        Property(
            property_code="HMND",
            property_name="Hammond Square",
            property_type="Retail",
            address="2441 Southwest Railroad Avenue",
            city="Hammond",
            state="LA",
            zip_code="70403",
            total_area_sqft=Decimal("285000.00"),
            acquisition_date=date(2017, 9, 20),
            status="active",
            created_by=test_user.id
        )
    ]
    
    for prop in properties:
        db_session.add(prop)
    db_session.commit()
    
    # Refresh to get IDs
    for prop in properties:
        db_session.refresh(prop)
    
    return properties


@pytest.fixture(scope="function")
def sample_chart_of_accounts(db_session):
    """Create sample chart of accounts for testing"""
    accounts = [
        # Current Assets
        ChartOfAccounts(
            account_code="0122-0000",
            account_name="Cash - Operating",
            account_type="asset",
            category="current_asset",
            subcategory="cash",
            display_order=10,
            document_types=["balance_sheet", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="0123-0000",
            account_name="Cash - Capital Improvements",
            account_type="asset",
            category="current_asset",
            subcategory="cash",
            display_order=11,
            document_types=["balance_sheet", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="0210-0000",
            account_name="Tenant Receivables",
            account_type="asset",
            category="current_asset",
            subcategory="accounts_receivable",
            display_order=20,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="0305-0000",
            account_name="A/R Tenants",
            account_type="asset",
            category="current_asset",
            subcategory="accounts_receivable",
            display_order=21,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="0499-9000",
            account_name="Total Current Assets",
            account_type="asset",
            category="current_asset",
            is_calculated=True,
            display_order=99,
            document_types=["balance_sheet"]
        ),
        # Property & Equipment
        ChartOfAccounts(
            account_code="0510-0000",
            account_name="Land",
            account_type="asset",
            category="fixed_asset",
            subcategory="property",
            display_order=200,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="0610-0000",
            account_name="Buildings",
            account_type="asset",
            category="fixed_asset",
            subcategory="property",
            display_order=210,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="1061-0000",
            account_name="Accumulated Depreciation - Buildings",
            account_type="asset",
            category="fixed_asset",
            subcategory="depreciation",
            display_order=220,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="1099-0000",
            account_name="Total Property & Equipment",
            account_type="asset",
            category="fixed_asset",
            is_calculated=True,
            display_order=299,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="1999-0000",
            account_name="TOTAL ASSETS",
            account_type="asset",
            category="asset",
            is_calculated=True,
            display_order=999,
            document_types=["balance_sheet"]
        ),
        # Current Liabilities
        ChartOfAccounts(
            account_code="1100-0000",
            account_name="Accounts Payable",
            account_type="liability",
            category="current_liability",
            subcategory="payables",
            display_order=1010,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="2197-0000",
            account_name="Current Portion Long-Term Debt",
            account_type="liability",
            category="current_liability",
            subcategory="debt",
            display_order=1050,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="2590-0000",
            account_name="Total Current Liabilities",
            account_type="liability",
            category="current_liability",
            is_calculated=True,
            display_order=1099,
            document_types=["balance_sheet"]
        ),
        # Long-term Liabilities
        ChartOfAccounts(
            account_code="2611-0000",
            account_name="Senior Debt - KeyBank",
            account_type="liability",
            category="long_term_liability",
            subcategory="institutional_debt",
            display_order=1500,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="2613-0000",
            account_name="Mezzanine Debt - KeyBank",
            account_type="liability",
            category="long_term_liability",
            subcategory="mezzanine_debt",
            display_order=1550,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="2618-0000",
            account_name="Mezzanine Debt - Trawler",
            account_type="liability",
            category="long_term_liability",
            subcategory="mezzanine_debt",
            display_order=1560,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="2900-0000",
            account_name="Total Long-term Liabilities",
            account_type="liability",
            category="long_term_liability",
            is_calculated=True,
            display_order=1899,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="2999-0000",
            account_name="TOTAL LIABILITIES",
            account_type="liability",
            category="liability",
            is_calculated=True,
            display_order=1999,
            document_types=["balance_sheet"]
        ),
        # Equity
        ChartOfAccounts(
            account_code="3050-1000",
            account_name="Partners Contribution",
            account_type="equity",
            category="equity",
            subcategory="capital",
            display_order=2010,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="3910-0000",
            account_name="Beginning Equity",
            account_type="equity",
            category="equity",
            subcategory="retained_earnings",
            display_order=2020,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="3995-0000",
            account_name="Current Period Earnings",
            account_type="equity",
            category="equity",
            subcategory="retained_earnings",
            display_order=2030,
            document_types=["balance_sheet"]
        ),
        ChartOfAccounts(
            account_code="3999-0000",
            account_name="TOTAL EQUITY",
            account_type="equity",
            category="equity",
            is_calculated=True,
            display_order=2099,
            document_types=["balance_sheet"]
        ),
        # Income
        ChartOfAccounts(
            account_code="4010-0000",
            account_name="Base Rentals",
            account_type="income",
            category="rental_income",
            subcategory="base_rent",
            display_order=4010,
            document_types=["income_statement", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="4020-0000",
            account_name="Percentage Rent",
            account_type="income",
            category="rental_income",
            subcategory="percentage_rent",
            display_order=4020,
            document_types=["income_statement", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="4030-0000",
            account_name="CAM Recoveries",
            account_type="income",
            category="reimbursement_income",
            subcategory="cam",
            display_order=4030,
            document_types=["income_statement", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="4999-0000",
            account_name="Total Revenue",
            account_type="income",
            category="income",
            is_calculated=True,
            display_order=4999,
            document_types=["income_statement", "cash_flow"]
        ),
        # Operating Expenses
        ChartOfAccounts(
            account_code="6010-0000",
            account_name="Property Taxes",
            account_type="expense",
            category="operating_expense",
            subcategory="taxes",
            display_order=6010,
            document_types=["income_statement", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="6020-0000",
            account_name="Insurance",
            account_type="expense",
            category="operating_expense",
            subcategory="insurance",
            display_order=6020,
            document_types=["income_statement", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="6100-0000",
            account_name="Utilities",
            account_type="expense",
            category="operating_expense",
            subcategory="utilities",
            display_order=6100,
            document_types=["income_statement", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="6200-0000",
            account_name="Repairs & Maintenance",
            account_type="expense",
            category="operating_expense",
            subcategory="maintenance",
            display_order=6200,
            document_types=["income_statement", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="6300-0000",
            account_name="Management Fees",
            account_type="expense",
            category="operating_expense",
            subcategory="management",
            display_order=6300,
            document_types=["income_statement", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="6299-0000",
            account_name="Net Operating Income (NOI)",
            account_type="income",
            category="performance",
            is_calculated=True,
            display_order=6299,
            document_types=["income_statement", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="8999-0000",
            account_name="Total Expenses",
            account_type="expense",
            category="expense",
            is_calculated=True,
            display_order=8999,
            document_types=["income_statement", "cash_flow"]
        ),
        ChartOfAccounts(
            account_code="9090-0000",
            account_name="Net Income",
            account_type="income",
            category="performance",
            is_calculated=True,
            display_order=9090,
            document_types=["income_statement", "cash_flow"]
        )
    ]
    
    for account in accounts:
        db_session.add(account)
    db_session.commit()
    
    # Refresh to get IDs
    for account in accounts:
        db_session.refresh(account)
    
    return accounts


@pytest.fixture(scope="function")
def sample_financial_periods(db_session, sample_properties):
    """Create sample financial periods for testing"""
    periods = []
    
    for prop in sample_properties:
        # Create periods for 2023 and 2024
        for year in [2023, 2024]:
            for month in range(1, 13):
                period = FinancialPeriod(
                    property_id=prop.id,
                    period_year=year,
                    period_month=month,
                    period_type="monthly",
                    fiscal_quarter=(month - 1) // 3 + 1,
                    start_date=date(year, month, 1),
                    end_date=date(year, month, 28) if month == 2 else date(year, month, 30),
                    is_closed=True if year == 2023 else False
                )
                periods.append(period)
                db_session.add(period)
    
    db_session.commit()
    
    # Refresh to get IDs
    for period in periods:
        db_session.refresh(period)
    
    return periods


@pytest.fixture(scope="function")
def authenticated_client(db_session, test_user):
    """Create an authenticated test client"""
    from app.main import app
    from app.api.dependencies import get_db
    from app.core.security import create_access_token
    
    # Override the get_db dependency to use test database
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    
    # Create access token
    access_token = create_access_token(data={"sub": test_user.username})
    
    # Set the auth cookie
    client.cookies.set("session_token", access_token)
    
    return client


@pytest.fixture(scope="function")
def admin_authenticated_client(db_session, admin_user):
    """Create an authenticated admin test client"""
    from app.main import app
    from app.api.dependencies import get_db
    from app.core.security import create_access_token
    
    # Override the get_db dependency to use test database
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    
    # Create access token
    access_token = create_access_token(data={"sub": admin_user.username})
    
    # Set the auth cookie
    client.cookies.set("session_token", access_token)
    
    return client


@pytest.fixture(scope="function")
def sample_balance_sheet_data(db_session, sample_properties, sample_financial_periods, sample_chart_of_accounts):
    """Create sample balance sheet data for metrics testing"""
    from app.models.balance_sheet_data import BalanceSheetData
    
    # Get first property and period
    prop = sample_properties[0]  # ESP
    period = sample_financial_periods[0]  # First period
    
    # Create comprehensive balance sheet entries covering all account types
    balance_sheet_entries = [
        # Current Assets
        ("0122-0000", "Cash - Operating", Decimal("250000.00")),
        ("0123-0000", "Cash - Capital Improvements", Decimal("100000.00")),
        ("0210-0000", "Tenant Receivables", Decimal("50000.00")),
        ("0305-0000", "A/R Tenants", Decimal("30000.00")),
        ("0499-9000", "Total Current Assets", Decimal("430000.00")),
        
        # Property & Equipment
        ("0510-0000", "Land", Decimal("3000000.00")),
        ("0610-0000", "Buildings", Decimal("15000000.00")),
        ("1061-0000", "Accumulated Depreciation - Buildings", Decimal("-3000000.00")),
        ("1099-0000", "Total Property & Equipment", Decimal("15000000.00")),
        
        # Total Assets
        ("1999-0000", "TOTAL ASSETS", Decimal("15430000.00")),
        
        # Current Liabilities
        ("1100-0000", "Accounts Payable", Decimal("75000.00")),
        ("2197-0000", "Current Portion Long-Term Debt", Decimal("500000.00")),
        ("2590-0000", "Total Current Liabilities", Decimal("575000.00")),
        
        # Long-term Liabilities
        ("2611-0000", "Senior Debt - KeyBank", Decimal("10000000.00")),
        ("2613-0000", "Mezzanine Debt - KeyBank", Decimal("1500000.00")),
        ("2618-0000", "Mezzanine Debt - Trawler", Decimal("1000000.00")),
        ("2900-0000", "Total Long-term Liabilities", Decimal("12500000.00")),
        ("2999-0000", "TOTAL LIABILITIES", Decimal("13075000.00")),
        
        # Equity
        ("3050-1000", "Partners Contribution", Decimal("1000000.00")),
        ("3910-0000", "Beginning Equity", Decimal("2000000.00")),
        ("3995-0000", "Current Period Earnings", Decimal("355000.00")),
        ("3999-0000", "TOTAL EQUITY", Decimal("2355000.00")),
    ]
    
    entries = []
    for account_code, account_name, amount in balance_sheet_entries:
        # Find account
        account = db_session.query(ChartOfAccounts).filter(
            ChartOfAccounts.account_code == account_code
        ).first()
        
        entry = BalanceSheetData(
            property_id=prop.id,
            period_id=period.id,
            account_id=account.id if account else None,
            account_code=account_code,
            account_name=account_name,
            amount=amount,
            document_type="balance_sheet",
            extraction_confidence=Decimal("0.95")
        )
        entries.append(entry)
        db_session.add(entry)
    
    db_session.commit()
    
    # Refresh all entries
    for entry in entries:
        db_session.refresh(entry)
    
    return entries


@pytest.fixture(scope="function")
def sample_cash_flow_data(db_session, sample_properties, sample_financial_periods, sample_chart_of_accounts):
    """Create sample cash flow data for testing"""
    from app.models.cash_flow_data import CashFlowData
    
    # Get first property and period
    prop = sample_properties[0]  # ESP
    period = sample_financial_periods[0]
    
    # Create realistic cash flow entries
    cash_flow_entries = [
        # INCOME
        ("4010-0000", "Base Rentals", Decimal("450000.00"), "INCOME", "rental_income"),
        ("4020-0000", "Percentage Rent", Decimal("25000.00"), "INCOME", "rental_income"),
        ("4030-0000", "CAM Recoveries", Decimal("85000.00"), "INCOME", "reimbursement_income"),
        
        # OPERATING EXPENSES
        ("6010-0000", "Property Taxes", Decimal("65000.00"), "OPERATING_EXPENSE", "taxes"),
        ("6020-0000", "Insurance", Decimal("18000.00"), "OPERATING_EXPENSE", "insurance"),
        ("6100-0000", "Utilities", Decimal("32000.00"), "OPERATING_EXPENSE", "utilities"),
        ("6200-0000", "Repairs & Maintenance", Decimal("28000.00"), "OPERATING_EXPENSE", "maintenance"),
        ("6300-0000", "Management Fees", Decimal("22500.00"), "OPERATING_EXPENSE", "management"),
    ]
    
    entries = []
    for account_code, account_name, amount, section, category in cash_flow_entries:
        # Find account
        account = db_session.query(ChartOfAccounts).filter(
            ChartOfAccounts.account_code == account_code
        ).first()
        
        entry = CashFlowData(
            property_id=prop.id,
            period_id=period.id,
            account_id=account.id if account else None,
            account_code=account_code,
            account_name=account_name,
            period_amount=amount,
            line_section=section,
            line_category=category,
            extraction_confidence=Decimal("0.95")
        )
        entries.append(entry)
        db_session.add(entry)
    
    db_session.commit()
    
    # Refresh all entries
    for entry in entries:
        db_session.refresh(entry)
    
    return entries


@pytest.fixture(scope="function")
def sample_income_statement_data(db_session, sample_properties, sample_financial_periods, sample_chart_of_accounts):
    """Create sample income statement data for testing"""
    from app.models.income_statement_data import IncomeStatementData
    
    # Get first property and period
    prop = sample_properties[0]  # ESP
    period = sample_financial_periods[0]
    
    # Create realistic income statement entries
    income_statement_entries = [
        # INCOME
        ("4010-0000", "Base Rentals", Decimal("450000.00"), Decimal("5400000.00"), "INCOME", True),
        ("4020-0000", "Percentage Rent", Decimal("25000.00"), Decimal("300000.00"), "INCOME", True),
        ("4030-0000", "CAM Recoveries", Decimal("85000.00"), Decimal("1020000.00"), "INCOME", True),
        
        # OPERATING EXPENSES
        ("6010-0000", "Property Taxes", Decimal("65000.00"), Decimal("780000.00"), "OPERATING_EXPENSE", False),
        ("6020-0000", "Insurance", Decimal("18000.00"), Decimal("216000.00"), "OPERATING_EXPENSE", False),
        ("6100-0000", "Utilities", Decimal("32000.00"), Decimal("384000.00"), "OPERATING_EXPENSE", False),
        ("6200-0000", "Repairs & Maintenance", Decimal("28000.00"), Decimal("336000.00"), "OPERATING_EXPENSE", False),
        ("6300-0000", "Management Fees", Decimal("22500.00"), Decimal("270000.00"), "OPERATING_EXPENSE", False),
    ]
    
    entries = []
    for account_code, account_name, period_amt, ytd_amt, category, is_income in income_statement_entries:
        # Find account
        account = db_session.query(ChartOfAccounts).filter(
            ChartOfAccounts.account_code == account_code
        ).first()
        
        entry = IncomeStatementData(
            property_id=prop.id,
            period_id=period.id,
            account_id=account.id if account else None,
            account_code=account_code,
            account_name=account_name,
            period_amount=period_amt,
            ytd_amount=ytd_amt,
            line_category=category,
            is_income=is_income,
            extraction_confidence=Decimal("0.95")
        )
        entries.append(entry)
        db_session.add(entry)
    
    db_session.commit()
    
    # Refresh all entries
    for entry in entries:
        db_session.refresh(entry)
    
    return entries


@pytest.fixture(scope="function")
def sample_validation_rules(db_session):
    """Create comprehensive validation rules for testing"""
    from app.models.validation_rule import ValidationRule
    
    rules = [
        # Balance Sheet Validations
        ValidationRule(
            rule_name="balance_sheet_equation",
            rule_description="Assets = Liabilities + Equity",
            document_type="balance_sheet",
            rule_type="balance_check",
            rule_formula="total_assets = total_liabilities + total_equity",
            error_message="Balance sheet does not balance: Assets != Liabilities + Equity",
            severity="error",
            tolerance_percentage=Decimal("0.01"),
            is_active=True
        ),
        ValidationRule(
            rule_name="balance_sheet_no_negative_cash",
            rule_description="Cash accounts should not be negative",
            document_type="balance_sheet",
            rule_type="range_check",
            rule_formula="cash_accounts >= 0",
            error_message="Negative cash balance detected",
            severity="warning",
            is_active=True
        ),
        ValidationRule(
            rule_name="balance_sheet_no_negative_equity",
            rule_description="Total equity should not be negative",
            document_type="balance_sheet",
            rule_type="range_check",
            rule_formula="total_equity >= 0",
            error_message="Negative equity detected",
            severity="warning",
            is_active=True
        ),
        # Income Statement Validations
        ValidationRule(
            rule_name="income_statement_net_income",
            rule_description="Net Income = Total Revenue - Total Expenses",
            document_type="income_statement",
            rule_type="balance_check",
            rule_formula="net_income = total_revenue - total_expenses",
            error_message="Net income calculation error",
            severity="error",
            tolerance_percentage=Decimal("0.01"),
            is_active=True
        ),
        ValidationRule(
            rule_name="income_statement_ytd_consistency",
            rule_description="YTD amounts should be >= Period amounts",
            document_type="income_statement",
            rule_type="range_check",
            rule_formula="ytd_amount >= period_amount",
            error_message="YTD is less than period amount",
            severity="warning",
            is_active=True
        ),
        # Cash Flow Validations
        ValidationRule(
            rule_name="cash_flow_noi_calculation",
            rule_description="NOI = Total Income - Operating Expenses",
            document_type="cash_flow",
            rule_type="balance_check",
            rule_formula="noi = total_income - total_operating_expenses",
            error_message="NOI calculation error",
            severity="error",
            tolerance_percentage=Decimal("0.01"),
            is_active=True
        ),
        ValidationRule(
            rule_name="cash_flow_net_income_calculation",
            rule_description="Net Income = NOI - Other Expenses",
            document_type="cash_flow",
            rule_type="balance_check",
            rule_formula="net_income = noi - other_expenses",
            error_message="Net income calculation error",
            severity="error",
            tolerance_percentage=Decimal("0.01"),
            is_active=True
        ),
        ValidationRule(
            rule_name="cash_flow_cash_balance",
            rule_description="Ending Cash = Beginning Cash + Cash Flow",
            document_type="cash_flow",
            rule_type="balance_check",
            rule_formula="ending_cash = beginning_cash + cash_flow",
            error_message="Cash balance reconciliation error",
            severity="error",
            tolerance_percentage=Decimal("0.01"),
            is_active=True
        ),
        # Rent Roll Validations
        ValidationRule(
            rule_name="rent_roll_no_duplicate_units",
            rule_description="Unit numbers must be unique",
            document_type="rent_roll",
            rule_type="uniqueness_check",
            rule_formula="UNIQUE(unit_number)",
            error_message="Duplicate unit numbers found",
            severity="error",
            is_active=True
        ),
        ValidationRule(
            rule_name="rent_roll_valid_lease_dates",
            rule_description="Lease start date must be before end date",
            document_type="rent_roll",
            rule_type="date_check",
            rule_formula="lease_start < lease_end",
            error_message="Invalid lease date range",
            severity="warning",
            is_active=True
        ),
    ]
    
    for rule in rules:
        db_session.add(rule)
    db_session.commit()
    
    # Refresh all rules
    for rule in rules:
        db_session.refresh(rule)
    
    return rules


@pytest.fixture(autouse=True, scope="session")
def create_test_database():
    """Create test database before any tests run"""
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import ProgrammingError
    
    # Connect to default postgres database to create test database
    # Use Docker PostgreSQL credentials
    admin_engine = create_engine("postgresql://reims:reims@localhost:5432/reims")
    
    with admin_engine.connect() as connection:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        
        try:
            # Drop if exists and create
            connection.execute(text("DROP DATABASE IF EXISTS reims_test"))
            connection.execute(text("CREATE DATABASE reims_test OWNER reims"))
        except ProgrammingError as e:
            # Database might not exist yet or we don't have permissions
            print(f"Warning: Could not create test database: {e}")
    
    yield
    
    # Cleanup: drop test database after all tests
    with admin_engine.connect() as connection:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        try:
            connection.execute(text("DROP DATABASE IF EXISTS reims_test"))
        except:
            pass
