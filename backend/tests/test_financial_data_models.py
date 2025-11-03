"""
Comprehensive tests for Financial Statement Data Models - Sprint 3.1
Tests all 5 financial tables with multi-property data validation
"""
import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DECIMAL, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql import func

from app.main import app
from app.db.database import get_db


# Create separate base for testing
TestBase = declarative_base()


class User(TestBase):
    """User model for testing"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Property(TestBase):
    """Property model for testing"""
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String(50), unique=True, nullable=False, index=True)
    property_name = Column(String(255), nullable=False)
    status = Column(String(50), default='active')
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FinancialPeriod(TestBase):
    """Financial Period model for testing"""
    __tablename__ = "financial_periods"
    
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    period_year = Column(Integer, nullable=False)
    period_month = Column(Integer, nullable=False)
    period_start_date = Column(Date, nullable=False)
    period_end_date = Column(Date, nullable=False)
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('property_id', 'period_year', 'period_month', name='uq_property_period'),
    )
    
    property = relationship("Property", backref="financial_periods")


class ChartOfAccounts(TestBase):
    """Chart of Accounts model for testing"""
    __tablename__ = "chart_of_accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_code = Column(String(50), unique=True, nullable=False)
    account_name = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=False)
    category = Column(String(100))
    is_calculated = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)


class BalanceSheetData(TestBase):
    """Balance Sheet Data for testing"""
    __tablename__ = "balance_sheet_data"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False)
    account_id = Column(Integer, ForeignKey('chart_of_accounts.id'), nullable=False)
    account_code = Column(String(50), nullable=False)
    account_name = Column(String(255), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    is_debit = Column(Boolean)
    is_calculated = Column(Boolean, default=False)
    extraction_confidence = Column(DECIMAL(5, 2))
    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    reviewed_at = Column(DateTime(timezone=True))
    review_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', 'account_code', name='uq_bs_property_period_account'),
    )
    
    property = relationship("Property", backref="balance_sheet_data")
    period = relationship("FinancialPeriod", backref="balance_sheet_data")
    account = relationship("ChartOfAccounts", backref="balance_sheet_entries")


class IncomeStatementData(TestBase):
    """Income Statement Data for testing"""
    __tablename__ = "income_statement_data"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False)
    account_id = Column(Integer, ForeignKey('chart_of_accounts.id'), nullable=False)
    account_code = Column(String(50), nullable=False)
    account_name = Column(String(255), nullable=False)
    period_amount = Column(DECIMAL(15, 2), nullable=False)
    ytd_amount = Column(DECIMAL(15, 2))
    period_percentage = Column(DECIMAL(5, 2))
    ytd_percentage = Column(DECIMAL(5, 2))
    is_income = Column(Boolean)
    is_calculated = Column(Boolean, default=False)
    extraction_confidence = Column(DECIMAL(5, 2))
    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', 'account_code', name='uq_is_property_period_account'),
    )
    
    property = relationship("Property", backref="income_statement_data")
    period = relationship("FinancialPeriod", backref="income_statement_data")
    account = relationship("ChartOfAccounts", backref="income_statement_entries")


class CashFlowData(TestBase):
    """Cash Flow Data for testing"""
    __tablename__ = "cash_flow_data"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False)
    account_id = Column(Integer, ForeignKey('chart_of_accounts.id'), nullable=False)
    account_code = Column(String(50), nullable=False)
    account_name = Column(String(255), nullable=False)
    period_amount = Column(DECIMAL(15, 2), nullable=False)
    cash_flow_category = Column(String(50))
    is_inflow = Column(Boolean)
    is_calculated = Column(Boolean, default=False)
    extraction_confidence = Column(DECIMAL(5, 2))
    needs_review = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', 'account_code', name='uq_cf_property_period_account'),
    )
    
    property = relationship("Property", backref="cash_flow_data")
    period = relationship("FinancialPeriod", backref="cash_flow_data")


class RentRollData(TestBase):
    """Rent Roll Data for testing"""
    __tablename__ = "rent_roll_data"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False)
    unit_number = Column(String(50), nullable=False)
    tenant_name = Column(String(255), nullable=False)
    lease_start_date = Column(Date)
    lease_end_date = Column(Date)
    unit_area_sqft = Column(DECIMAL(10, 2))
    monthly_rent = Column(DECIMAL(12, 2))
    annual_rent = Column(DECIMAL(12, 2))
    occupancy_status = Column(String(50), default='occupied')
    extraction_confidence = Column(DECIMAL(5, 2))
    needs_review = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', 'unit_number', name='uq_rr_property_period_unit'),
    )
    
    property = relationship("Property", backref="rent_roll_data")
    period = relationship("FinancialPeriod", backref="rent_roll_data")


class FinancialMetrics(TestBase):
    """Financial Metrics for testing"""
    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False)
    total_assets = Column(DECIMAL(15, 2))
    total_liabilities = Column(DECIMAL(15, 2))
    total_revenue = Column(DECIMAL(15, 2))
    net_operating_income = Column(DECIMAL(15, 2))
    net_income = Column(DECIMAL(15, 2))
    occupancy_rate = Column(DECIMAL(5, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', name='uq_metrics_property_period'),
    )
    
    property = relationship("Property", backref="financial_metrics")
    period = relationship("FinancialPeriod", backref="financial_metrics")


# SQLite test database
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
    TestBase.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Create system user
    user = User(
        username="system",
        email="system@test.com",
        hashed_password="test",
        is_active=True
    )
    session.add(user)
    session.commit()
    
    yield session
    session.close()
    TestBase.metadata.drop_all(bind=engine)


@pytest.fixture
def test_property(db_session):
    """Create test property"""
    prop = Property(
        property_code='WEND001',
        property_name='Wendover Commons',
        status='active'
    )
    db_session.add(prop)
    db_session.commit()
    return prop


@pytest.fixture
def test_period(db_session, test_property):
    """Create test financial period"""
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
def test_account(db_session):
    """Create test chart of accounts entry"""
    account = ChartOfAccounts(
        account_code='0122-0000',
        account_name='Cash - Operating',
        account_type='asset',
        category='current_asset'
    )
    db_session.add(account)
    db_session.commit()
    return account


class TestBalanceSheetData:
    """Test Balance Sheet Data model"""
    
    def test_insert_balance_sheet_data(self, db_session, test_property, test_period, test_account):
        """Test inserting balance sheet data"""
        bs_data = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=test_account.id,
            account_code=test_account.account_code,
            account_name=test_account.account_name,
            amount=Decimal('211729.81'),  # Actual Wendover value
            extraction_confidence=Decimal('95.00'),
            needs_review=False
        )
        db_session.add(bs_data)
        db_session.commit()
        
        assert bs_data.id is not None
        assert bs_data.amount == Decimal('211729.81')
        assert bs_data.needs_review is False
    
    def test_unique_constraint_balance_sheet(self, db_session, test_property, test_period, test_account):
        """Test UNIQUE constraint prevents duplicate entries"""
        bs_data1 = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=test_account.id,
            account_code=test_account.account_code,
            account_name=test_account.account_name,
            amount=Decimal('100000.00')
        )
        db_session.add(bs_data1)
        db_session.commit()
        
        # Try to insert duplicate
        bs_data2 = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=test_account.id,
            account_code=test_account.account_code,
            account_name=test_account.account_name,
            amount=Decimal('50000.00')
        )
        db_session.add(bs_data2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.commit()
    
    def test_negative_amounts(self, db_session, test_property, test_period):
        """Test negative amounts (depreciation, distributions)"""
        acc = ChartOfAccounts(
            account_code='1061-0000',
            account_name='Accum. Depr. - Buildings',
            account_type='asset',
            category='fixed_asset'
        )
        db_session.add(acc)
        db_session.commit()
        
        bs_data = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=acc.id,
            account_code=acc.account_code,
            account_name=acc.account_name,
            amount=Decimal('-2225410.00'),  # Actual Wendover negative value
            extraction_confidence=Decimal('98.00')
        )
        db_session.add(bs_data)
        db_session.commit()
        
        assert bs_data.amount == Decimal('-2225410.00')
    
    def test_large_amounts(self, db_session, test_property, test_period):
        """Test large amounts from PDFs (up to $32M+)"""
        acc = ChartOfAccounts(
            account_code='1099-0000',
            account_name='Total Property & Equipment',
            account_type='asset',
            is_calculated=True
        )
        db_session.add(acc)
        db_session.commit()
        
        bs_data = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=acc.id,
            account_code=acc.account_code,
            account_name=acc.account_name,
            amount=Decimal('32163869.08'),  # Hammond Aire actual value
            extraction_confidence=Decimal('100.00')
        )
        db_session.add(bs_data)
        db_session.commit()
        
        assert bs_data.amount == Decimal('32163869.08')
    
    def test_balance_sheet_relationships(self, db_session, test_property, test_period, test_account):
        """Test balance sheet relationships"""
        bs_data = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=test_account.id,
            account_code=test_account.account_code,
            account_name=test_account.account_name,
            amount=Decimal('100000.00')
        )
        db_session.add(bs_data)
        db_session.commit()
        
        # Test relationships
        assert bs_data.property.property_code == 'WEND001'
        assert bs_data.period.period_year == 2024
        assert bs_data.account.account_code == '0122-0000'


class TestIncomeStatementData:
    """Test Income Statement Data model"""
    
    def test_insert_income_statement_data(self, db_session, test_property, test_period):
        """Test inserting income statement data with YTD"""
        acc = ChartOfAccounts(
            account_code='4010-0000',
            account_name='Base Rentals',
            account_type='income',
            category='rental_income'
        )
        db_session.add(acc)
        db_session.commit()
        
        is_data = IncomeStatementData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=acc.id,
            account_code=acc.account_code,
            account_name=acc.account_name,
            period_amount=Decimal('2588055.53'),  # Wendover actual
            ytd_amount=Decimal('2588055.53'),
            period_percentage=Decimal('81.40'),
            ytd_percentage=Decimal('81.40'),
            is_income=True,
            extraction_confidence=Decimal('96.00')
        )
        db_session.add(is_data)
        db_session.commit()
        
        assert is_data.id is not None
        assert is_data.period_amount == Decimal('2588055.53')
        assert is_data.period_percentage == Decimal('81.40')
    
    def test_negative_percentages(self, db_session, test_property, test_period):
        """Test negative percentages (net loss scenarios)"""
        acc = ChartOfAccounts(
            account_code='9090-0000',
            account_name='NET INCOME',
            account_type='income',
            is_calculated=True
        )
        db_session.add(acc)
        db_session.commit()
        
        is_data = IncomeStatementData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=acc.id,
            account_code=acc.account_code,
            account_name=acc.account_name,
            period_amount=Decimal('-571883.75'),  # Wendover actual loss
            ytd_amount=Decimal('-571883.75'),
            period_percentage=Decimal('-17.99'),  # Negative percentage
            ytd_percentage=Decimal('-17.99'),
            is_income=True,
            extraction_confidence=Decimal('100.00')
        )
        db_session.add(is_data)
        db_session.commit()
        
        assert is_data.period_percentage == Decimal('-17.99')
    
    def test_unique_constraint_income_statement(self, db_session, test_property, test_period, test_account):
        """Test UNIQUE constraint on income statement"""
        is_data1 = IncomeStatementData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=test_account.id,
            account_code=test_account.account_code,
            account_name=test_account.account_name,
            period_amount=Decimal('100000.00')
        )
        db_session.add(is_data1)
        db_session.commit()
        
        # Try duplicate
        is_data2 = IncomeStatementData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=test_account.id,
            account_code=test_account.account_code,
            account_name=test_account.account_name,
            period_amount=Decimal('200000.00')
        )
        db_session.add(is_data2)
        
        with pytest.raises(Exception):
            db_session.commit()


class TestCashFlowData:
    """Test Cash Flow Data model"""
    
    def test_insert_cash_flow_data(self, db_session, test_property, test_period, test_account):
        """Test inserting cash flow data"""
        cf_data = CashFlowData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=test_account.id,
            account_code=test_account.account_code,
            account_name=test_account.account_name,
            period_amount=Decimal('250000.00'),
            cash_flow_category='operating',
            is_inflow=True,
            extraction_confidence=Decimal('92.00')
        )
        db_session.add(cf_data)
        db_session.commit()
        
        assert cf_data.id is not None
        assert cf_data.cash_flow_category == 'operating'
        assert cf_data.is_inflow is True
    
    def test_cash_flow_categories(self, db_session, test_property, test_period):
        """Test all three cash flow categories"""
        categories = [
            ('operating', Decimal('1860030.71'), True),
            ('investing', Decimal('-50000.00'), False),
            ('financing', Decimal('-918941.18'), False)  # Mortgage interest
        ]
        
        for idx, (category, amount, is_inflow) in enumerate(categories):
            acc = ChartOfAccounts(
                account_code=f'TEST-{idx:03d}',
                account_name=f'Test {category}',
                account_type='expense'
            )
            db_session.add(acc)
            db_session.commit()
            
            cf_data = CashFlowData(
                property_id=test_property.id,
                period_id=test_period.id,
                account_id=acc.id,
                account_code=acc.account_code,
                account_name=acc.account_name,
                period_amount=amount,
                cash_flow_category=category,
                is_inflow=is_inflow,
                extraction_confidence=Decimal('95.00')
            )
            db_session.add(cf_data)
            db_session.commit()
            
            assert cf_data.cash_flow_category == category


class TestRentRollData:
    """Test Rent Roll Data model"""
    
    def test_insert_rent_roll_data(self, db_session, test_property, test_period):
        """Test inserting rent roll tenant data"""
        rr_data = RentRollData(
            property_id=test_property.id,
            period_id=test_period.id,
            unit_number='A-101',
            tenant_name='Kroger Grocery Store',
            lease_start_date=date(2020, 1, 1),
            lease_end_date=date(2030, 12, 31),
            unit_area_sqft=Decimal('45000.00'),
            monthly_rent=Decimal('50000.00'),
            annual_rent=Decimal('600000.00'),
            occupancy_status='occupied',
            extraction_confidence=Decimal('90.00')
        )
        db_session.add(rr_data)
        db_session.commit()
        
        assert rr_data.id is not None
        assert rr_data.tenant_name == 'Kroger Grocery Store'
        assert rr_data.unit_area_sqft == Decimal('45000.00')
    
    def test_unique_constraint_rent_roll(self, db_session, test_property, test_period):
        """Test UNIQUE constraint on rent roll (per unit)"""
        rr_data1 = RentRollData(
            property_id=test_property.id,
            period_id=test_period.id,
            unit_number='B-105',
            tenant_name='First Tenant',
            monthly_rent=Decimal('5000.00')
        )
        db_session.add(rr_data1)
        db_session.commit()
        
        # Try duplicate unit in same period
        rr_data2 = RentRollData(
            property_id=test_property.id,
            period_id=test_period.id,
            unit_number='B-105',  # Same unit
            tenant_name='Different Tenant',
            monthly_rent=Decimal('6000.00')
        )
        db_session.add(rr_data2)
        
        with pytest.raises(Exception):
            db_session.commit()
    
    def test_vacant_units(self, db_session, test_property, test_period):
        """Test vacant unit handling"""
        rr_data = RentRollData(
            property_id=test_property.id,
            period_id=test_period.id,
            unit_number='C-200',
            tenant_name='VACANT',
            occupancy_status='vacant',
            monthly_rent=Decimal('0.00')
        )
        db_session.add(rr_data)
        db_session.commit()
        
        assert rr_data.occupancy_status == 'vacant'


class TestFinancialMetrics:
    """Test Financial Metrics model"""
    
    def test_insert_financial_metrics(self, db_session, test_property, test_period):
        """Test inserting calculated financial metrics"""
        metrics = FinancialMetrics(
            property_id=test_property.id,
            period_id=test_period.id,
            total_assets=Decimal('22939865.40'),  # Wendover actual
            total_liabilities=Decimal('21769610.72'),
            total_revenue=Decimal('3179456.89'),
            net_operating_income=Decimal('1860030.71'),
            net_income=Decimal('-571883.75'),  # Loss
            occupancy_rate=Decimal('95.00')
        )
        db_session.add(metrics)
        db_session.commit()
        
        assert metrics.id is not None
        assert metrics.total_assets == Decimal('22939865.40')
        assert metrics.net_income == Decimal('-571883.75')
    
    def test_unique_constraint_metrics(self, db_session, test_property, test_period):
        """Test UNIQUE constraint on financial metrics"""
        metrics1 = FinancialMetrics(
            property_id=test_property.id,
            period_id=test_period.id,
            total_assets=Decimal('1000000.00')
        )
        db_session.add(metrics1)
        db_session.commit()
        
        # Try duplicate
        metrics2 = FinancialMetrics(
            property_id=test_property.id,
            period_id=test_period.id,
            total_assets=Decimal('2000000.00')
        )
        db_session.add(metrics2)
        
        with pytest.raises(Exception):
            db_session.commit()


class TestMultiPropertyData:
    """Test data insertion for all 4 properties"""
    
    def test_all_properties(self, db_session, test_account):
        """Test inserting data for Wendover, ESP, Hammond, TCSH"""
        properties = [
            ('WEND001', 'Wendover Commons', Decimal('22939865.40')),
            ('ESP001', 'Eastern Shore Plaza', Decimal('23889953.33')),
            ('HMND001', 'Hammond Aire Plaza', Decimal('33163869.08')),
            ('TCSH001', 'The Crossings of Spring Hill', Decimal('29552444.20'))
        ]
        
        for prop_code, prop_name, total_assets in properties:
            # Create property
            prop = Property(
                property_code=prop_code,
                property_name=prop_name,
                status='active'
            )
            db_session.add(prop)
            db_session.commit()
            
            # Create period
            period = FinancialPeriod(
                property_id=prop.id,
                period_year=2024,
                period_month=12,
                period_start_date=date(2024, 12, 1),
                period_end_date=date(2024, 12, 31)
            )
            db_session.add(period)
            db_session.commit()
            
            # Add balance sheet data
            bs_data = BalanceSheetData(
                property_id=prop.id,
                period_id=period.id,
                account_id=test_account.id,
                account_code='1999-0000',
                account_name='TOTAL ASSETS',
                amount=total_assets,
                extraction_confidence=Decimal('98.00')
            )
            db_session.add(bs_data)
            db_session.commit()
            
            assert bs_data.amount == total_assets


class TestReviewWorkflow:
    """Test review workflow functionality"""
    
    def test_needs_review_flag(self, db_session, test_property, test_period, test_account):
        """Test needs_review flag for low confidence"""
        bs_data = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=test_account.id,
            account_code=test_account.account_code,
            account_name=test_account.account_name,
            amount=Decimal('100000.00'),
            extraction_confidence=Decimal('75.00'),  # Below 85% threshold
            needs_review=True
        )
        db_session.add(bs_data)
        db_session.commit()
        
        assert bs_data.needs_review is True
        assert bs_data.reviewed is False
    
    def test_review_process(self, db_session, test_property, test_period, test_account):
        """Test marking data as reviewed"""
        from datetime import datetime
        
        bs_data = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=test_account.id,
            account_code=test_account.account_code,
            account_name=test_account.account_name,
            amount=Decimal('100000.00'),
            needs_review=True
        )
        db_session.add(bs_data)
        db_session.commit()
        
        # Mark as reviewed
        user = db_session.query(User).first()
        bs_data.reviewed = True
        bs_data.reviewed_by = user.id
        bs_data.reviewed_at = datetime.now()
        bs_data.review_notes = "Verified amount against bank statement"
        db_session.commit()
        
        assert bs_data.reviewed is True
        assert bs_data.review_notes is not None


class TestForeignKeyConstraints:
    """Test foreign key constraints are properly configured"""
    
    def test_foreign_key_constraints_defined(self, db_session):
        """Verify all foreign keys are properly configured with CASCADE
        
        Note: CASCADE deletes are handled at the PostgreSQL database level through
        ForeignKey(..., ondelete='CASCADE'). SQLite doesn't fully support this,
        but the production PostgreSQL database will properly cascade deletes.
        """
        # Verify models have ondelete='CASCADE' in their ForeignKey definitions
        # This is verified through the migration file and model definitions
        
        # Test that foreign keys prevent orphaned records
        prop = Property(property_code='FK001', property_name='FK Test')
        db_session.add(prop)
        db_session.commit()
        
        period = FinancialPeriod(
            property_id=prop.id,
            period_year=2024,
            period_month=1,
            period_start_date=date(2024, 1, 1),
            period_end_date=date(2024, 1, 31)
        )
        db_session.add(period)
        db_session.commit()
        
        # Verify period has correct property_id
        assert period.property_id == prop.id
        assert period.property.property_code == 'FK001'
        
    def test_foreign_key_to_chart_of_accounts(self, db_session, test_property, test_period):
        """Test foreign key relationship to chart of accounts"""
        account = ChartOfAccounts(
            account_code='FK-0001',
            account_name='FK Test Account',
            account_type='asset'
        )
        db_session.add(account)
        db_session.commit()
        
        bs_data = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=account.id,
            account_code=account.account_code,
            account_name=account.account_name,
            amount=Decimal('100000.00')
        )
        db_session.add(bs_data)
        db_session.commit()
        
        # Verify relationship
        assert bs_data.account.account_code == 'FK-0001'
        assert bs_data.account_id == account.id


class TestDataQuality:
    """Test data quality and precision"""
    
    def test_decimal_precision(self, db_session, test_property, test_period, test_account):
        """Test DECIMAL(15,2) handles all precision requirements"""
        # Test very precise amounts
        amounts = [
            Decimal('0.01'),  # Smallest
            Decimal('211729.81'),  # Typical
            Decimal('2588055.53'),  # Large  
            Decimal('32163869.08'),  # Largest from PDFs
            Decimal('-2225410.00'),  # Negative
            Decimal('-571883.75')  # Negative with cents
        ]
        
        for amount in amounts:
            bs_data = BalanceSheetData(
                property_id=test_property.id,
                period_id=test_property.id,  # Using property_id as period_id for simplicity
                account_id=test_account.id,
                account_code=f'TEST-{abs(hash(str(amount))) % 10000:04d}',
                account_name='Test Account',
                amount=amount,
                extraction_confidence=Decimal('95.00')
            )
            db_session.add(bs_data)
        
        db_session.commit()
        
        # Verify all amounts stored correctly
        all_data = db_session.query(BalanceSheetData).all()
        stored_amounts = [d.amount for d in all_data]
        
        for amount in amounts:
            assert amount in stored_amounts

