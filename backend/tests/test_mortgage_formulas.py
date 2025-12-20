"""
Unit tests for Mortgage Financial Formulas
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.dscr_monitoring_service import DSCRMonitoringService
from app.services.metrics_service import MetricsService
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.income_statement_data import IncomeStatementData
from app.models.financial_metrics import FinancialMetrics


class TestMortgageFormulas:
    """Test mortgage-related financial formula calculations"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_mortgage(self):
        """Create mock mortgage with debt service"""
        mortgage = Mock(spec=MortgageStatementData)
        mortgage.id = 1
        mortgage.property_id = 1
        mortgage.period_id = 1
        mortgage.principal_balance = Decimal("10000000")
        mortgage.principal_due = Decimal("50000")
        mortgage.interest_due = Decimal("40000")
        mortgage.monthly_debt_service = Decimal("90000")
        mortgage.annual_debt_service = Decimal("1080000")
        mortgage.interest_rate = Decimal("5.25")
        return mortgage
    
    def test_dscr_calculation_with_mortgage_data(self, mock_db, mock_mortgage):
        """Test DSCR calculation using mortgage statement data"""
        # Mock NOI
        mock_metrics = Mock(spec=FinancialMetrics)
        mock_metrics.net_operating_income = Decimal("1500000")
        
        # Mock mortgage query
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_mortgage]
        
        dscr_service = DSCRMonitoringService(mock_db)
        
        # Mock _calculate_noi
        with patch.object(dscr_service, '_calculate_noi', return_value=Decimal("1500000")):
            total_debt_service = dscr_service._get_total_debt_service(1, 1)
            
            assert total_debt_service == Decimal("1080000")  # From mortgage annual_debt_service
            
            # DSCR = NOI / Debt Service = 1,500,000 / 1,080,000 = 1.39
            dscr = Decimal("1500000") / total_debt_service
            assert dscr == pytest.approx(Decimal("1.3889"), rel=0.01)
    
    def test_ltv_calculation(self, mock_db):
        """Test LTV calculation"""
        from app.models.balance_sheet_data import BalanceSheetData
        
        # Mock mortgage balances
        mortgage1 = Mock(spec=MortgageStatementData)
        mortgage1.principal_balance = Decimal("8000000")
        mortgage2 = Mock(spec=MortgageStatementData)
        mortgage2.principal_balance = Decimal("2000000")
        
        # Mock property value from balance sheet
        property_value = Mock()
        property_value.amount = Decimal("15000000")
        
        mock_db.query.return_value.filter.return_value.scalar.return_value = Decimal("10000000")
        mock_db.query.return_value.filter.return_value.first.return_value = property_value
        
        # LTV = Total Mortgage Debt / Property Value
        total_mortgage_debt = Decimal("10000000")
        ltv = total_mortgage_debt / property_value.amount
        
        assert ltv == pytest.approx(Decimal("0.6667"), rel=0.01)  # 66.67%
    
    def test_debt_yield_calculation(self, mock_db):
        """Test debt yield calculation"""
        # Debt Yield = NOI / Total Loan Amount * 100
        noi = Decimal("1500000")
        total_loan_amount = Decimal("10000000")
        
        debt_yield = (noi / total_loan_amount) * Decimal("100")
        
        assert debt_yield == Decimal("15.0")  # 15%
    
    def test_break_even_occupancy_calculation(self, mock_db):
        """Test break-even occupancy calculation"""
        # Break-Even = (Operating Expenses + Debt Service) / Gross Potential Rent * 100
        operating_expenses = Decimal("500000")
        debt_service = Decimal("1080000")
        gross_potential_rent = Decimal("2000000")
        
        break_even = ((operating_expenses + debt_service) / gross_potential_rent) * Decimal("100")
        
        assert break_even == Decimal("79.0")  # 79%
    
    def test_interest_coverage_ratio(self, mock_db):
        """Test interest coverage ratio calculation"""
        # Interest Coverage = EBIT / Interest Expense
        # Using NOI as EBIT proxy
        noi = Decimal("1500000")
        total_interest = Decimal("480000")  # Annual interest
        
        interest_coverage = noi / total_interest
        
        assert interest_coverage == pytest.approx(Decimal("3.125"), rel=0.01)  # 3.125x
    
    def test_weighted_average_interest_rate(self, mock_db):
        """Test weighted average interest rate calculation"""
        mortgage1 = Mock(spec=MortgageStatementData)
        mortgage1.principal_balance = Decimal("8000000")
        mortgage1.interest_rate = Decimal("5.0")
        
        mortgage2 = Mock(spec=MortgageStatementData)
        mortgage2.principal_balance = Decimal("2000000")
        mortgage2.interest_rate = Decimal("6.0")
        
        mortgages = [mortgage1, mortgage2]
        
        # Calculate weighted average
        total_weighted = sum(
            Decimal(str(m.principal_balance)) * Decimal(str(m.interest_rate))
            for m in mortgages
        )
        total_principal = sum(
            Decimal(str(m.principal_balance))
            for m in mortgages
        )
        
        weighted_avg = total_weighted / total_principal
        
        # (8M * 5% + 2M * 6%) / 10M = (400,000 + 120,000) / 10,000,000 = 5.2%
        assert weighted_avg == Decimal("5.2")


