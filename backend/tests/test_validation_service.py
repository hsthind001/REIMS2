"""
Comprehensive Validation Service Tests - Sprint 5.1

Tests all business logic validation rules with real data scenarios
"""
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.services.validation_service import ValidationService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.chart_of_accounts import ChartOfAccounts
from app.models.validation_rule import ValidationRule
from app.models.validation_result import ValidationResult


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database for each test"""
    from app.db.database import Base
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Seed validation rules
    _seed_test_rules(session)
    
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _seed_test_rules(db):
    """Seed essential validation rules for testing"""
    rules = [
        ("balance_sheet_equation", "Assets = Liabilities + Equity", "balance_sheet", "balance_check", "error"),
        ("balance_sheet_no_negative_cash", "Cash >= 0", "balance_sheet", "range_check", "warning"),
        ("income_statement_net_income", "Net Income = Revenue - Expenses", "income_statement", "balance_check", "error"),
        ("income_statement_no_negative_revenue", "Revenue >= 0", "income_statement", "range_check", "warning"),
        ("income_statement_ytd_consistency", "YTD >= Period", "income_statement", "range_check", "warning"),
        ("cash_flow_categories_sum", "Operating + Investing + Financing = Net", "cash_flow", "balance_check", "error"),
        ("rent_roll_no_duplicate_units", "Unique units", "rent_roll", "uniqueness_check", "error"),
        ("rent_roll_valid_lease_dates", "Start < End", "rent_roll", "date_check", "warning"),
    ]
    
    for rule_name, desc, doc_type, rule_type, severity in rules:
        rule = ValidationRule(
            rule_name=rule_name,
            rule_description=desc,
            document_type=doc_type,
            rule_type=rule_type,
            rule_formula=desc,
            error_message=desc,
            severity=severity,
            is_active=True
        )
        db.add(rule)
    
    db.commit()


@pytest.fixture
def test_property(db_session):
    """Create test property"""
    prop = Property(property_code='TEST001', property_name='Test Property', status='active')
    db_session.add(prop)
    db_session.commit()
    return prop


@pytest.fixture
def test_period(db_session, test_property):
    """Create test period"""
    period = FinancialPeriod(
        property_id=test_property.id,
        period_year=2024,
        period_month=12,
        period_start_date=date(2024, 12, 1),
        period_end_date=date(2024, 12, 31)
    )
    db_session.add(period)
    db_session.commit()
    return period


@pytest.fixture
def test_upload(db_session, test_property, test_period):
    """Create test upload"""
    upload = DocumentUpload(
        property_id=test_property.id,
        period_id=test_period.id,
        document_type='balance_sheet',
        file_name='test.pdf',
        file_path='test/path.pdf',
        extraction_status='completed'
    )
    db_session.add(upload)
    db_session.commit()
    return upload


class TestBalanceSheetValidation:
    """Test balance sheet validation rules"""
    
    def test_balance_sheet_equation_pass(self, db_session, test_property, test_period, test_upload):
        """Test balance sheet equation when it balances"""
        # Create balanced balance sheet
        # Assets = $1,000,000
        bs_assets = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='1999-0000',
            account_name='TOTAL ASSETS',
            amount=Decimal('1000000.00')
        )
        
        # Liabilities = $600,000
        bs_liabilities = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='2999-0000',
            account_name='TOTAL LIABILITIES',
            amount=Decimal('600000.00')
        )
        
        # Equity = $400,000
        bs_equity = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='3999-0000',
            account_name='TOTAL CAPITAL',
            amount=Decimal('400000.00')
        )
        
        db_session.add_all([bs_assets, bs_liabilities, bs_equity])
        db_session.commit()
        
        # Run validation
        validation_service = ValidationService(db_session)
        result = validation_service.validate_balance_sheet_equation(
            test_upload.id, test_property.id, test_period.id
        )
        
        assert result["passed"] is True
        assert result["difference"] == 0
    
    def test_balance_sheet_equation_fail(self, db_session, test_property, test_period, test_upload):
        """Test balance sheet equation when it doesn't balance"""
        # Create unbalanced balance sheet
        # Assets = $1,000,000
        bs_assets = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='1999-0000',
            account_name='TOTAL ASSETS',
            amount=Decimal('1000000.00')
        )
        
        # Liabilities = $600,000
        bs_liabilities = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='2999-0000',
            account_name='TOTAL LIABILITIES',
            amount=Decimal('600000.00')
        )
        
        # Equity = $350,000 (should be $400,000)
        bs_equity = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='3999-0000',
            account_name='TOTAL CAPITAL',
            amount=Decimal('350000.00')
        )
        
        db_session.add_all([bs_assets, bs_liabilities, bs_equity])
        db_session.commit()
        
        # Run validation
        validation_service = ValidationService(db_session)
        result = validation_service.validate_balance_sheet_equation(
            test_upload.id, test_property.id, test_period.id
        )
        
        assert result["passed"] is False
        assert result["difference"] == 50000  # $50k difference
        assert result["error_message"] is not None
    
    def test_negative_cash_warning(self, db_session, test_property, test_period, test_upload):
        """Test negative cash warning"""
        # Create negative cash
        bs_cash = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='0122-0000',
            account_name='Cash - Operating',
            amount=Decimal('-5000.00')
        )
        
        db_session.add(bs_cash)
        db_session.commit()
        
        # Run validation
        validation_service = ValidationService(db_session)
        result = validation_service.validate_no_negative_cash(
            test_upload.id, test_property.id, test_period.id
        )
        
        assert result["passed"] is False
        assert result["severity"] == "warning"
        assert "negative" in result["error_message"].lower()


class TestIncomeStatementValidation:
    """Test income statement validation rules"""
    
    def test_net_income_validation_pass(self, db_session, test_property, test_period):
        """Test net income calculation validation"""
        # Create upload for income statement
        upload = DocumentUpload(
            property_id=test_property.id,
            period_id=test_period.id,
            document_type='income_statement',
            file_name='test.pdf',
            file_path='test/path.pdf',
            extraction_status='completed'
        )
        db_session.add(upload)
        db_session.commit()
        
        # Revenue = $500,000
        is_revenue = IncomeStatementData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='4010-0000',
            account_name='Base Rentals',
            period_amount=Decimal('500000.00'),
            is_calculated=False
        )
        
        # Expenses = $300,000
        is_expense = IncomeStatementData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='5100-0000',
            account_name='Repairs & Maintenance',
            period_amount=Decimal('300000.00'),
            is_calculated=False
        )
        
        # Net Income = $200,000
        is_net = IncomeStatementData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='9090-0000',
            account_name='NET INCOME',
            period_amount=Decimal('200000.00'),
            is_calculated=True
        )
        
        db_session.add_all([is_revenue, is_expense, is_net])
        db_session.commit()
        
        # Run validation
        validation_service = ValidationService(db_session)
        result = validation_service.validate_net_income(
            upload.id, test_property.id, test_period.id
        )
        
        assert result["passed"] is True
    
    def test_ytd_consistency(self, db_session, test_property, test_period):
        """Test YTD >= Period validation"""
        upload = DocumentUpload(
            property_id=test_property.id,
            period_id=test_period.id,
            document_type='income_statement',
            file_name='test.pdf',
            file_path='test/path.pdf',
            extraction_status='completed'
        )
        db_session.add(upload)
        db_session.commit()
        
        # Create item where YTD < Period (invalid)
        is_item = IncomeStatementData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='4010-0000',
            account_name='Base Rentals',
            period_amount=Decimal('100000.00'),
            ytd_amount=Decimal('50000.00')  # YTD less than Period - invalid
        )
        
        db_session.add(is_item)
        db_session.commit()
        
        # Run validation
        validation_service = ValidationService(db_session)
        result = validation_service.validate_ytd_consistency(
            upload.id, test_property.id, test_period.id
        )
        
        assert result["passed"] is False
        assert result["severity"] == "warning"


class TestRentRollValidation:
    """Test rent roll validation rules"""
    
    def test_no_duplicate_units_pass(self, db_session, test_property, test_period):
        """Test duplicate units detection - passing case"""
        upload = DocumentUpload(
            property_id=test_property.id,
            period_id=test_period.id,
            document_type='rent_roll',
            file_name='test.pdf',
            file_path='test/path.pdf',
            extraction_status='completed'
        )
        db_session.add(upload)
        db_session.commit()
        
        # Create two different units (no duplicates)
        unit1 = RentRollData(
            property_id=test_property.id,
            period_id=test_period.id,
            unit_number='A-101',
            tenant_name='Tenant 1',
            monthly_rent=Decimal('5000.00'),
            occupancy_status='occupied'
        )
        
        unit2 = RentRollData(
            property_id=test_property.id,
            period_id=test_period.id,
            unit_number='A-102',
            tenant_name='Tenant 2',
            monthly_rent=Decimal('5000.00'),
            occupancy_status='occupied'
        )
        
        db_session.add_all([unit1, unit2])
        db_session.commit()
        
        # Run validation
        validation_service = ValidationService(db_session)
        result = validation_service.validate_no_duplicate_units(
            upload.id, test_property.id, test_period.id
        )
        
        assert result["passed"] is True
    
    def test_lease_dates_validation(self, db_session, test_property, test_period):
        """Test lease date validation"""
        upload = DocumentUpload(
            property_id=test_property.id,
            period_id=test_period.id,
            document_type='rent_roll',
            file_name='test.pdf',
            file_path='test/path.pdf',
            extraction_status='completed'
        )
        db_session.add(upload)
        db_session.commit()
        
        # Create unit with invalid dates (start >= end)
        unit = RentRollData(
            property_id=test_property.id,
            period_id=test_period.id,
            unit_number='A-101',
            tenant_name='Bad Dates Tenant',
            lease_start_date=date(2025, 1, 1),
            lease_end_date=date(2024, 1, 1),  # End before start - invalid!
            monthly_rent=Decimal('5000.00'),
            occupancy_status='occupied'
        )
        
        db_session.add(unit)
        db_session.commit()
        
        # Run validation
        validation_service = ValidationService(db_session)
        result = validation_service.validate_lease_dates(
            upload.id, test_property.id, test_period.id
        )
        
        assert result["passed"] is False
        assert result["severity"] == "warning"


class TestCashFlowValidation:
    """Test cash flow validation rules"""
    
    def test_cash_flow_categories_sum(self, db_session, test_property, test_period):
        """Test cash flow categories sum validation"""
        upload = DocumentUpload(
            property_id=test_property.id,
            period_id=test_period.id,
            document_type='cash_flow',
            file_name='test.pdf',
            file_path='test/path.pdf',
            extraction_status='completed'
        )
        db_session.add(upload)
        db_session.commit()
        
        # Create cash flow data
        operating = CashFlowData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='CF-OP',
            account_name='Operating Activities',
            period_amount=Decimal('100000.00'),
            cash_flow_category='operating'
        )
        
        investing = CashFlowData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='CF-IN',
            account_name='Investing Activities',
            period_amount=Decimal('-20000.00'),
            cash_flow_category='investing'
        )
        
        financing = CashFlowData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='CF-FIN',
            account_name='Financing Activities',
            period_amount=Decimal('-30000.00'),
            cash_flow_category='financing'
        )
        
        db_session.add_all([operating, investing, financing])
        db_session.commit()
        
        # Run validation
        validation_service = ValidationService(db_session)
        result = validation_service.validate_cash_flow_categories(
            upload.id, test_property.id, test_period.id
        )
        
        # Net = 100000 - 20000 - 30000 = 50000
        assert result["passed"] is True
        assert result["expected_value"] == 50000.00


class TestValidationServiceIntegration:
    """Test validation service integration"""
    
    def test_validate_upload_balance_sheet(self, db_session, test_property, test_period, test_upload):
        """Test full validation workflow for balance sheet"""
        # Create balanced balance sheet data
        bs_data = [
            ('1999-0000', 'TOTAL ASSETS', Decimal('1000000.00')),
            ('2999-0000', 'TOTAL LIABILITIES', Decimal('600000.00')),
            ('3999-0000', 'TOTAL CAPITAL', Decimal('400000.00')),
            ('0122-0000', 'Cash - Operating', Decimal('50000.00')),
        ]
        
        for code, name, amount in bs_data:
            item = BalanceSheetData(
                property_id=test_property.id,
                period_id=test_period.id,
                account_id=None,
                account_code=code,
                account_name=name,
                amount=amount
            )
            db_session.add(item)
        
        db_session.commit()
        
        # Run full validation
        validation_service = ValidationService(db_session)
        results = validation_service.validate_upload(test_upload.id)
        
        assert results["success"] is True
        assert results["total_checks"] >= 2  # At least equation + cash check
        assert results["overall_passed"] is True
    
    def test_validation_results_stored(self, db_session, test_property, test_period, test_upload):
        """Test that validation results are stored in database"""
        # Create simple balance sheet
        bs_assets = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='1999-0000',
            account_name='TOTAL ASSETS',
            amount=Decimal('1000000.00')
        )
        db_session.add(bs_assets)
        db_session.commit()
        
        # Run validation
        validation_service = ValidationService(db_session)
        validation_service.validate_upload(test_upload.id)
        
        # Check that results were stored
        stored_results = db_session.query(ValidationResult).filter(
            ValidationResult.upload_id == test_upload.id
        ).all()
        
        assert len(stored_results) > 0
        assert all(r.upload_id == test_upload.id for r in stored_results)


class TestToleranceHandling:
    """Test tolerance handling for rounding errors"""
    
    def test_tolerance_within_limit(self, db_session, test_property, test_period, test_upload):
        """Test that small differences within tolerance pass"""
        # Create balance sheet with tiny rounding difference
        # Assets = $1,000,000.00
        bs_assets = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='1999-0000',
            account_name='TOTAL ASSETS',
            amount=Decimal('1000000.00')
        )
        
        # Liabilities + Equity = $1,000,000.50 (0.00005% difference)
        bs_liabilities = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='2999-0000',
            account_name='TOTAL LIABILITIES',
            amount=Decimal('600000.30')
        )
        
        bs_equity = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='3999-0000',
            account_name='TOTAL CAPITAL',
            amount=Decimal('400000.20')
        )
        
        db_session.add_all([bs_assets, bs_liabilities, bs_equity])
        db_session.commit()
        
        # Run validation with 1% tolerance
        validation_service = ValidationService(db_session, tolerance_percentage=1.0)
        result = validation_service.validate_balance_sheet_equation(
            test_upload.id, test_property.id, test_period.id
        )
        
        # Should pass - difference is only $0.50 which is < 1% of $1M
        assert result["passed"] is True


class TestRealDataScenarios:
    """Test with real Wendover data scenarios"""
    
    def test_wendover_balance_sheet_equation(self, db_session, test_property, test_period, test_upload):
        """Test with actual Wendover balance sheet values"""
        # Actual Wendover 2024-12 values
        bs_data = [
            ('1999-0000', 'TOTAL ASSETS', Decimal('22939865.40')),
            ('2999-0000', 'TOTAL LIABILITIES', Decimal('21769610.72')),
            ('3999-0000', 'TOTAL CAPITAL', Decimal('1170254.68')),  # Calculated: 22939865.40 - 21769610.72
        ]
        
        for code, name, amount in bs_data:
            item = BalanceSheetData(
                property_id=test_property.id,
                period_id=test_period.id,
                account_id=None,
                account_code=code,
                account_name=name,
                amount=amount
            )
            db_session.add(item)
        
        db_session.commit()
        
        # Run validation
        validation_service = ValidationService(db_session)
        result = validation_service.validate_balance_sheet_equation(
            test_upload.id, test_property.id, test_period.id
        )
        
        # Should pass (Wendover data is accurate)
        assert result["passed"] is True, f"Validation failed: {result.get('error_message')}"

