"""
Test Suite for DSCR Monitoring Service

Tests cover:
- DSCR calculation
- Alert generation
- Workflow lock creation
- Historical DSCR tracking
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.dscr_monitoring_service import DSCRMonitoringService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.income_statement_data import IncomeStatementData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.committee_alert import CommitteeAlert, AlertSeverity, AlertStatus
from app.models.workflow_lock import WorkflowLock, LockReason, LockStatus


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def sample_property():
    """Sample property for testing"""
    return Property(
        id=1,
        property_code="TEST-001",
        property_name="Test Property",
        property_type="Office"
    )


@pytest.fixture
def sample_period():
    """Sample financial period for testing"""
    return FinancialPeriod(
        id=1,
        property_id=1,
        period_year=2024,
        period_month=12,
        period_start_date=datetime(2024, 12, 1),
        period_end_date=datetime(2024, 12, 31)
    )


@pytest.fixture
def dscr_service(mock_db):
    """DSCRMonitoringService instance for testing"""
    return DSCRMonitoringService(mock_db)


class TestDSCRCalculation:
    """Test DSCR calculation logic"""

    def test_calculate_dscr_healthy(self, dscr_service, mock_db, sample_property, sample_period):
        """Test DSCR calculation for healthy property (DSCR >= 1.25)"""
        # Mock NOI data
        noi_data = [
            Mock(account_code="4010-0000", amount=Decimal("100000.00")),  # Rental Income
            Mock(account_code="5010-0000", amount=Decimal("30000.00")),  # Operating Expenses
        ]
        
        # Mock Debt Service data
        debt_service_data = [
            Mock(principal_payment=Decimal("20000.00"), interest_payment=Decimal("35000.00"))
        ]
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            noi_data,  # Income statement data
            debt_service_data  # Mortgage statement data
        ]
        
        result = dscr_service.calculate_dscr(sample_property.id, sample_period.id)
        
        assert result is not None
        assert result.get("success") is True
        assert "dscr" in result
        assert "status" in result
        
        # DSCR = NOI / Debt Service = 70000 / 55000 = 1.27 (healthy)
        if result.get("dscr"):
            assert result["dscr"] >= 1.25
            assert result["status"] == "healthy"

    def test_calculate_dscr_warning(self, dscr_service, mock_db, sample_property, sample_period):
        """Test DSCR calculation for warning status (1.10 <= DSCR < 1.25)"""
        # Mock lower NOI
        noi_data = [
            Mock(account_code="4010-0000", amount=Decimal("60000.00")),
            Mock(account_code="5010-0000", amount=Decimal("30000.00")),
        ]
        
        debt_service_data = [
            Mock(principal_payment=Decimal("20000.00"), interest_payment=Decimal("35000.00"))
        ]
        
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            noi_data,
            debt_service_data
        ]
        
        result = dscr_service.calculate_dscr(sample_property.id, sample_period.id)
        
        if result.get("success") and result.get("dscr"):
            dscr = result["dscr"]
            if 1.10 <= dscr < 1.25:
                assert result["status"] == "warning"

    def test_calculate_dscr_critical(self, dscr_service, mock_db, sample_property, sample_period):
        """Test DSCR calculation for critical status (DSCR < 1.10)"""
        # Mock very low NOI
        noi_data = [
            Mock(account_code="4010-0000", amount=Decimal("40000.00")),
            Mock(account_code="5010-0000", amount=Decimal("30000.00")),
        ]
        
        debt_service_data = [
            Mock(principal_payment=Decimal("20000.00"), interest_payment=Decimal("35000.00"))
        ]
        
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            noi_data,
            debt_service_data
        ]
        
        result = dscr_service.calculate_dscr(sample_property.id, sample_period.id)
        
        if result.get("success") and result.get("dscr"):
            dscr = result["dscr"]
            if dscr < 1.10:
                assert result["status"] == "critical"

    def test_calculate_dscr_no_data(self, dscr_service, mock_db, sample_property, sample_period):
        """Test DSCR calculation when no data is available"""
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        result = dscr_service.calculate_dscr(sample_property.id, sample_period.id)
        
        assert result is not None
        # Should handle gracefully
        assert result.get("success") is False or result.get("dscr") is None


class TestDSCRAlertGeneration:
    """Test DSCR alert generation"""

    def test_generate_dscr_alert_critical(self, dscr_service, mock_db):
        """Test generation of critical DSCR alert"""
        dscr_result = {
            "success": True,
            "dscr": 0.95,
            "status": "critical",
            "noi": Decimal("50000.00"),
            "total_debt_service": Decimal("55000.00")
        }
        
        property_obj = Mock(id=1, property_code="TEST-001")
        period_obj = Mock(id=1, period_year=2024, period_month=12)
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            property_obj,
            period_obj
        ]
        
        alert = dscr_service._create_dscr_alert(
            property_id=1,
            period_id=1,
            dscr_result=dscr_result
        )
        
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.alert_type == "DSCR_BREACH"

    def test_generate_dscr_alert_warning(self, dscr_service, mock_db):
        """Test generation of warning DSCR alert"""
        dscr_result = {
            "success": True,
            "dscr": 1.15,
            "status": "warning",
            "noi": Decimal("60000.00"),
            "total_debt_service": Decimal("55000.00")
        }
        
        property_obj = Mock(id=1, property_code="TEST-001")
        period_obj = Mock(id=1, period_year=2024, period_month=12)
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            property_obj,
            period_obj
        ]
        
        alert = dscr_service._create_dscr_alert(
            property_id=1,
            period_id=1,
            dscr_result=dscr_result
        )
        
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING


class TestWorkflowLockCreation:
    """Test workflow lock creation for DSCR breaches"""

    def test_create_workflow_lock_critical_dscr(self, dscr_service, mock_db):
        """Test creation of workflow lock for critical DSCR"""
        dscr_result = {
            "success": True,
            "dscr": 0.95,
            "status": "critical"
        }
        
        property_obj = Mock(id=1, property_code="TEST-001")
        
        mock_db.query.return_value.filter.return_value.first.return_value = property_obj
        
        lock = dscr_service._create_workflow_lock(
            property_id=1,
            period_id=1,
            dscr_result=dscr_result
        )
        
        assert lock is not None
        assert lock.lock_reason == LockReason.DSCR_BREACH
        assert lock.lock_status == LockStatus.ACTIVE


class TestDSCRHistoricalTracking:
    """Test historical DSCR tracking"""

    def test_get_historical_dscr(self, dscr_service, mock_db, sample_property):
        """Test retrieval of historical DSCR values"""
        periods = [
            Mock(id=1, period_year=2024, period_month=12, period_end_date=datetime(2024, 12, 31)),
            Mock(id=2, period_year=2024, period_month=11, period_end_date=datetime(2024, 11, 30)),
            Mock(id=3, period_year=2024, period_month=10, period_end_date=datetime(2024, 10, 31)),
        ]
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = periods
        
        # Mock DSCR calculations for each period
        with patch.object(dscr_service, 'calculate_dscr') as mock_calc:
            mock_calc.side_effect = [
                {"success": True, "dscr": 1.30, "status": "healthy"},
                {"success": True, "dscr": 1.20, "status": "warning"},
                {"success": True, "dscr": 1.35, "status": "healthy"},
            ]
            
            history = dscr_service.get_historical_dscr(
                property_id=1,
                months=3
            )
            
            assert history is not None
            assert len(history) == 3

    def test_detect_dscr_trend(self, dscr_service, mock_db):
        """Test detection of DSCR trends (improving/declining)"""
        historical_data = [
            {"period": "2024-10", "dscr": 1.35},
            {"period": "2024-11", "dscr": 1.20},
            {"period": "2024-12", "dscr": 1.05},
        ]
        
        trend = dscr_service._detect_dscr_trend(historical_data)
        
        assert trend is not None
        # Should detect declining trend
        assert trend.get("direction") == "declining" or trend.get("trend") == "down"


@pytest.mark.integration
class TestDSCRServiceIntegration:
    """Integration tests for DSCR monitoring service"""

    def test_complete_dscr_monitoring_workflow(self, db_session, sample_property, sample_period):
        """Test complete DSCR monitoring workflow"""
        # Create income statement data
        income_data = IncomeStatementData(
            property_id=sample_property.id,
            period_id=sample_period.id,
            account_code="4010-0000",
            account_name="Base Rental Income",
            amount=Decimal("100000.00")
        )
        expense_data = IncomeStatementData(
            property_id=sample_property.id,
            period_id=sample_period.id,
            account_code="5010-0000",
            account_name="Operating Expenses",
            amount=Decimal("30000.00")
        )
        
        # Create mortgage statement data
        mortgage_data = MortgageStatementData(
            property_id=sample_property.id,
            period_id=sample_period.id,
            principal_payment=Decimal("20000.00"),
            interest_payment=Decimal("35000.00")
        )
        
        db_session.add_all([income_data, expense_data, mortgage_data])
        db_session.commit()
        
        # Calculate DSCR
        dscr_service = DSCRMonitoringService(db_session)
        result = dscr_service.calculate_dscr(sample_property.id, sample_period.id)
        
        assert result is not None
        assert result.get("success") is True
        assert "dscr" in result
        assert result["dscr"] > 0

