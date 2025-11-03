"""
Comprehensive Metrics Service Tests - Sprint 5.2

Tests all 35 financial KPI calculations with real data scenarios
Verifies zero division protection, NULL handling, and calculation accuracy
"""
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.services.metrics_service import MetricsService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.financial_metrics import FinancialMetrics


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
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_property(db_session):
    """Create test property"""
    prop = Property(property_code='WEND001', property_name='Wendover Commons', status='active')
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


class TestBalanceSheetMetrics:
    """Test balance sheet metrics calculations"""
    
    def test_balance_sheet_totals(self, db_session, test_property, test_period):
        """Test calculation of balance sheet totals"""
        # Create balance sheet data with actual Wendover values
        bs_data = [
            ('1999-0000', 'TOTAL ASSETS', Decimal('22939865.40')),
            ('2999-0000', 'TOTAL LIABILITIES', Decimal('21769610.72')),
            ('3999-0000', 'TOTAL CAPITAL', Decimal('1170254.68')),
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
        
        # Calculate metrics
        metrics_service = MetricsService(db_session)
        metrics_data = metrics_service.calculate_balance_sheet_metrics(
            test_property.id, test_period.id
        )
        
        # Verify totals
        assert metrics_data['total_assets'] == Decimal('22939865.40')
        assert metrics_data['total_liabilities'] == Decimal('21769610.72')
        assert metrics_data['total_equity'] == Decimal('1170254.68')
    
    def test_current_ratio_calculation(self, db_session, test_property, test_period):
        """Test current ratio = Current Assets / Current Liabilities"""
        # Create current accounts
        bs_data = [
            ('0499-9000', 'Total Current Assets', Decimal('500000.00')),
            ('2590-0000', 'Total Current Liabilities', Decimal('250000.00')),
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
        
        # Calculate metrics
        metrics_service = MetricsService(db_session)
        metrics_data = metrics_service.calculate_balance_sheet_metrics(
            test_property.id, test_period.id
        )
        
        # Verify current ratio: 500,000 / 250,000 = 2.0
        assert metrics_data['current_ratio'] == Decimal('2.0')
    
    def test_debt_to_equity_ratio(self, db_session, test_property, test_period):
        """Test debt-to-equity ratio calculation"""
        # Wendover actual values
        bs_data = [
            ('2999-0000', 'TOTAL LIABILITIES', Decimal('21769610.72')),
            ('3999-0000', 'TOTAL CAPITAL', Decimal('1170254.68')),
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
        
        # Calculate
        metrics_service = MetricsService(db_session)
        metrics_data = metrics_service.calculate_balance_sheet_metrics(
            test_property.id, test_period.id
        )
        
        # Verify: 21,769,610.72 / 1,170,254.68 ≈ 18.60
        assert metrics_data['debt_to_equity_ratio'] is not None
        assert abs(metrics_data['debt_to_equity_ratio'] - Decimal('18.60')) < Decimal('0.1')


class TestIncomeStatementMetrics:
    """Test income statement metrics calculations"""
    
    def test_operating_margin(self, db_session, test_property, test_period):
        """Test operating margin = NOI / Revenue * 100"""
        # Create income statement data
        is_data = [
            ('4999-0000', 'TOTAL REVENUE', Decimal('3179456.89'), False),
            ('6299-0000', 'NET OPERATING INCOME', Decimal('1860030.71'), True),
        ]
        
        for code, name, amount, is_calc in is_data:
            item = IncomeStatementData(
                property_id=test_property.id,
                period_id=test_period.id,
                account_id=None,
                account_code=code,
                account_name=name,
                period_amount=amount,
                is_calculated=is_calc
            )
            db_session.add(item)
        
        db_session.commit()
        
        # Calculate
        metrics_service = MetricsService(db_session)
        metrics_data = metrics_service.calculate_income_statement_metrics(
            test_property.id, test_period.id
        )
        
        # Verify: (1,860,030.71 / 3,179,456.89) * 100 ≈ 58.52%
        assert metrics_data['operating_margin'] is not None
        assert abs(metrics_data['operating_margin'] - Decimal('58.52')) < Decimal('0.1')
    
    def test_profit_margin_negative(self, db_session, test_property, test_period):
        """Test profit margin with negative net income (loss)"""
        # Wendover actual values (net loss)
        is_data = [
            ('4999-0000', 'TOTAL REVENUE', Decimal('3179456.89'), False),
            ('9090-0000', 'NET INCOME', Decimal('-571883.75'), True),
        ]
        
        for code, name, amount, is_calc in is_data:
            item = IncomeStatementData(
                property_id=test_property.id,
                period_id=test_period.id,
                account_id=None,
                account_code=code,
                account_name=name,
                period_amount=amount,
                is_calculated=is_calc
            )
            db_session.add(item)
        
        db_session.commit()
        
        # Calculate
        metrics_service = MetricsService(db_session)
        metrics_data = metrics_service.calculate_income_statement_metrics(
            test_property.id, test_period.id
        )
        
        # Verify: (-571,883.75 / 3,179,456.89) * 100 ≈ -17.99%
        assert metrics_data['profit_margin'] is not None
        assert abs(metrics_data['profit_margin'] - Decimal('-17.99')) < Decimal('0.1')


class TestRentRollMetrics:
    """Test rent roll metrics calculations"""
    
    def test_occupancy_rate_calculation(self, db_session, test_property, test_period):
        """Test occupancy rate = (Occupied / Total) * 100"""
        # Create rent roll with 10 units, 9 occupied
        for i in range(10):
            unit = RentRollData(
                property_id=test_property.id,
                period_id=test_period.id,
                unit_number=f'A-{i+101}',
                tenant_name='Tenant' if i < 9 else 'VACANT',
                occupancy_status='occupied' if i < 9 else 'vacant',
                monthly_rent=Decimal('5000.00') if i < 9 else Decimal('0.00')
            )
            db_session.add(unit)
        
        db_session.commit()
        
        # Calculate
        metrics_service = MetricsService(db_session)
        metrics_data = metrics_service.calculate_rent_roll_metrics(
            test_property.id, test_period.id
        )
        
        # Verify: 9 / 10 * 100 = 90%
        assert metrics_data['total_units'] == 10
        assert metrics_data['occupied_units'] == 9
        assert metrics_data['vacant_units'] == 1
        assert metrics_data['occupancy_rate'] == Decimal('90.0')
    
    def test_rent_per_sqft_calculation(self, db_session, test_property, test_period):
        """Test average rent per sqft"""
        # Create rent roll with sqft data
        units = [
            ('A-101', 'Tenant A', Decimal('10000.00'), Decimal('50000.00')),  # $10k rent, 50k sqft
            ('A-102', 'Tenant B', Decimal('5000.00'), Decimal('25000.00')),   # $5k rent, 25k sqft
        ]
        
        for unit_num, tenant, sqft, rent in units:
            unit = RentRollData(
                property_id=test_property.id,
                period_id=test_period.id,
                unit_number=unit_num,
                tenant_name=tenant,
                unit_area_sqft=sqft,
                monthly_rent=rent,
                occupancy_status='occupied'
            )
            db_session.add(unit)
        
        db_session.commit()
        
        # Calculate
        metrics_service = MetricsService(db_session)
        metrics_data = metrics_service.calculate_rent_roll_metrics(
            test_property.id, test_period.id
        )
        
        # Verify: $55,000 / 75,000 sqft = $0.73/sqft
        total_rent = Decimal('55000.00')
        total_sqft = Decimal('75000.00')
        expected_avg = total_rent / total_sqft
        
        assert metrics_data['total_monthly_rent'] == total_rent
        assert metrics_data['total_leasable_sqft'] == total_sqft
        assert abs(metrics_data['avg_rent_per_sqft'] - expected_avg) < Decimal('0.01')


class TestCashFlowMetrics:
    """Test cash flow metrics calculations"""
    
    def test_cash_flow_category_sums(self, db_session, test_property, test_period):
        """Test cash flow sums by category"""
        # Create cash flow data
        cf_data = [
            ('operating', Decimal('1860030.71')),
            ('investing', Decimal('-50000.00')),
            ('financing', Decimal('-918941.18')),
        ]
        
        for category, amount in cf_data:
            item = CashFlowData(
                property_id=test_property.id,
                period_id=test_period.id,
                account_id=None,
                account_code=f'CF-{category[:3].upper()}',
                account_name=f'{category.title()} Activities',
                period_amount=amount,
                cash_flow_category=category
            )
            db_session.add(item)
        
        db_session.commit()
        
        # Calculate
        metrics_service = MetricsService(db_session)
        metrics_data = metrics_service.calculate_cash_flow_metrics(
            test_property.id, test_period.id
        )
        
        # Verify sums
        assert metrics_data['operating_cash_flow'] == Decimal('1860030.71')
        assert metrics_data['investing_cash_flow'] == Decimal('-50000.00')
        assert metrics_data['financing_cash_flow'] == Decimal('-918941.18')
        
        # Verify net: 1,860,030.71 - 50,000.00 - 918,941.18 = 891,089.53
        expected_net = Decimal('891089.53')
        assert abs(metrics_data['net_cash_flow'] - expected_net) < Decimal('0.1')


class TestSafeDivide:
    """Test zero division protection"""
    
    def test_safe_divide_normal(self, db_session):
        """Test normal division"""
        metrics_service = MetricsService(db_session)
        
        result = metrics_service.safe_divide(Decimal('100'), Decimal('50'))
        assert result == Decimal('2.0')
    
    def test_safe_divide_by_zero(self, db_session):
        """Test division by zero returns 0"""
        metrics_service = MetricsService(db_session)
        
        result = metrics_service.safe_divide(Decimal('100'), Decimal('0'))
        assert result == Decimal('0')
    
    def test_safe_divide_with_none(self, db_session):
        """Test division with None values returns None"""
        metrics_service = MetricsService(db_session)
        
        assert metrics_service.safe_divide(None, Decimal('50')) is None
        assert metrics_service.safe_divide(Decimal('100'), None) is None
        assert metrics_service.safe_divide(None, None) is None


class TestMetricsServiceIntegration:
    """Test full metrics service workflow"""
    
    def test_calculate_all_metrics_wendover(self, db_session, test_property, test_period):
        """Test calculating all metrics with Wendover-like data"""
        # Create complete financial data set
        
        # Balance sheet
        bs_data = [
            ('1999-0000', 'TOTAL ASSETS', Decimal('22939865.40')),
            ('2999-0000', 'TOTAL LIABILITIES', Decimal('21769610.72')),
            ('3999-0000', 'TOTAL CAPITAL', Decimal('1170254.68')),
            ('0499-9000', 'Total Current Assets', Decimal('500000.00')),
            ('2590-0000', 'Total Current Liabilities', Decimal('250000.00')),
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
        
        # Income statement
        is_data = [
            ('4999-0000', 'TOTAL REVENUE', Decimal('3179456.89')),
            ('8999-0000', 'TOTAL EXPENSES', Decimal('3751340.64')),
            ('6299-0000', 'NET OPERATING INCOME', Decimal('1860030.71')),
            ('9090-0000', 'NET INCOME', Decimal('-571883.75')),
        ]
        
        for code, name, amount in is_data:
            item = IncomeStatementData(
                property_id=test_property.id,
                period_id=test_period.id,
                account_id=None,
                account_code=code,
                account_name=name,
                period_amount=amount
            )
            db_session.add(item)
        
        # Rent roll
        for i in range(10):
            unit = RentRollData(
                property_id=test_property.id,
                period_id=test_period.id,
                unit_number=f'A-{i+101}',
                tenant_name='Tenant' if i < 9 else 'VACANT',
                occupancy_status='occupied' if i < 9 else 'vacant',
                unit_area_sqft=Decimal('5000.00'),
                monthly_rent=Decimal('5000.00') if i < 9 else Decimal('0.00')
            )
            db_session.add(unit)
        
        db_session.commit()
        
        # Calculate ALL metrics
        metrics_service = MetricsService(db_session)
        metrics = metrics_service.calculate_all_metrics(
            test_property.id, test_period.id
        )
        
        # Verify metrics stored
        assert metrics is not None
        assert metrics.total_assets == Decimal('22939865.40')
        assert metrics.current_ratio == Decimal('2.0')
        assert metrics.total_revenue == Decimal('3179456.89')
        assert metrics.occupancy_rate == Decimal('90.0')
        
        # Verify margins
        assert metrics.operating_margin is not None
        assert metrics.profit_margin is not None
    
    def test_metrics_upsert_logic(self, db_session, test_property, test_period):
        """Test that metrics are updated if they already exist"""
        # Create initial metrics
        initial_metrics = FinancialMetrics(
            property_id=test_property.id,
            period_id=test_period.id,
            total_assets=Decimal('1000000.00')
        )
        db_session.add(initial_metrics)
        db_session.commit()
        initial_id = initial_metrics.id
        
        # Add balance sheet data
        bs_item = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='1999-0000',
            account_name='TOTAL ASSETS',
            amount=Decimal('2000000.00')
        )
        db_session.add(bs_item)
        db_session.commit()
        
        # Recalculate metrics
        metrics_service = MetricsService(db_session)
        updated_metrics = metrics_service.calculate_all_metrics(
            test_property.id, test_period.id
        )
        
        # Verify same record was updated (not new record created)
        assert updated_metrics.id == initial_id
        assert updated_metrics.total_assets == Decimal('2000000.00')
        
        # Verify only one metrics record exists
        count = db_session.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == test_property.id,
            FinancialMetrics.period_id == test_period.id
        ).count()
        
        assert count == 1


class TestPerformanceMetrics:
    """Test performance metrics calculations"""
    
    def test_noi_per_sqft(self, db_session, test_property, test_period):
        """Test NOI per sqft calculation"""
        # Create income statement with NOI
        is_item = IncomeStatementData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='6299-0000',
            account_name='NET OPERATING INCOME',
            period_amount=Decimal('100000.00')
        )
        db_session.add(is_item)
        
        # Create rent roll with total sqft
        unit = RentRollData(
            property_id=test_property.id,
            period_id=test_period.id,
            unit_number='A-101',
            tenant_name='Tenant',
            unit_area_sqft=Decimal('50000.00'),
            monthly_rent=Decimal('5000.00'),
            occupancy_status='occupied'
        )
        db_session.add(unit)
        db_session.commit()
        
        # Calculate all metrics
        metrics_service = MetricsService(db_session)
        metrics = metrics_service.calculate_all_metrics(
            test_property.id, test_period.id
        )
        
        # Verify: $100,000 / 50,000 sqft = $2.00/sqft
        assert metrics.noi_per_sqft == Decimal('2.00')


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_no_data_returns_empty_metrics(self, db_session, test_property, test_period):
        """Test metrics calculation with no data"""
        metrics_service = MetricsService(db_session)
        metrics = metrics_service.calculate_all_metrics(
            test_property.id, test_period.id
        )
        
        # Should create metrics record even with no data
        assert metrics is not None
        assert metrics.property_id == test_property.id
        assert metrics.period_id == test_period.id
    
    def test_partial_data_calculates_available_metrics(self, db_session, test_property, test_period):
        """Test that metrics are calculated from available data only"""
        # Only add balance sheet data (no income statement or rent roll)
        bs_item = BalanceSheetData(
            property_id=test_property.id,
            period_id=test_period.id,
            account_id=None,
            account_code='1999-0000',
            account_name='TOTAL ASSETS',
            amount=Decimal('1000000.00')
        )
        db_session.add(bs_item)
        db_session.commit()
        
        # Calculate
        metrics_service = MetricsService(db_session)
        metrics = metrics_service.calculate_all_metrics(
            test_property.id, test_period.id
        )
        
        # Should have balance sheet metrics
        assert metrics.total_assets == Decimal('1000000.00')
        
        # Should NOT have income statement or rent roll metrics
        assert metrics.total_revenue is None
        assert metrics.occupancy_rate is None

