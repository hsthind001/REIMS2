"""
Integration tests for Forensic Reconciliation API endpoints

Tests for:
- Session creation
- Match finding
- Match approval/rejection
- Discrepancy resolution
- Dashboard and health score
"""

import pytest
from decimal import Decimal
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock

from app.main import app
from app.models.forensic_reconciliation_session import ForensicReconciliationSession
from app.models.forensic_match import ForensicMatch
from app.models.forensic_discrepancy import ForensicDiscrepancy
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.user import User


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    return Mock()


@pytest.fixture
def mock_user():
    """Create mock user"""
    user = Mock(spec=User)
    user.id = 1
    user.username = "test_auditor"
    user.email = "auditor@test.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_property():
    """Create mock property"""
    prop = Mock(spec=Property)
    prop.id = 1
    prop.property_code = "TEST-001"
    prop.property_name = "Test Property"
    return prop


@pytest.fixture
def mock_period():
    """Create mock financial period"""
    period = Mock(spec=FinancialPeriod)
    period.id = 1
    period.property_id = 1
    period.period_year = 2024
    period.period_month = 12
    return period


@pytest.fixture
def mock_session():
    """Create mock reconciliation session"""
    session = Mock(spec=ForensicReconciliationSession)
    session.id = 1
    session.property_id = 1
    session.period_id = 1
    session.session_type = "full_reconciliation"
    session.status = "in_progress"
    session.auditor_id = 1
    session.started_at = datetime.now()
    session.completed_at = None
    session.summary = {
        "total_matches": 10,
        "exact_matches": 5,
        "fuzzy_matches": 3,
        "calculated_matches": 2,
        "discrepancies": 1
    }
    session.notes = None
    return session


@pytest.fixture
def mock_match():
    """Create mock match"""
    match = Mock(spec=ForensicMatch)
    match.id = 1
    match.session_id = 1
    match.source_document_type = "balance_sheet"
    match.target_document_type = "income_statement"
    match.match_type = "calculated"
    match.confidence_score = Decimal('95.00')
    match.status = "pending"
    match.amount_difference = Decimal('0.01')
    match.relationship_formula = "BS.CurrentPeriodEarnings = IS.NetIncome"
    return match


@pytest.fixture
def mock_discrepancy():
    """Create mock discrepancy"""
    discrepancy = Mock(spec=ForensicDiscrepancy)
    discrepancy.id = 1
    discrepancy.session_id = 1
    discrepancy.discrepancy_type = "amount_mismatch"
    discrepancy.severity = "high"
    discrepancy.difference = Decimal('1000.00')
    discrepancy.status = "open"
    discrepancy.description = "Test discrepancy"
    return discrepancy


class TestSessionEndpoints:
    """Test session management endpoints"""
    
    @patch('app.api.v1.forensic_reconciliation.get_current_user')
    @patch('app.api.v1.forensic_reconciliation.get_db')
    @patch('app.api.v1.forensic_reconciliation.ForensicReconciliationService')
    def test_create_session(
        self,
        mock_service_class,
        mock_get_db,
        mock_get_user,
        client,
        mock_user,
        mock_property,
        mock_period,
        mock_session
    ):
        """Test creating a new reconciliation session"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session()
        
        mock_service = Mock()
        mock_service.start_reconciliation_session.return_value = mock_session
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/api/v1/forensic-reconciliation/sessions",
            json={
                "property_id": 1,
                "period_id": 1,
                "session_type": "full_reconciliation"
            },
            cookies={"reims_session": "test_session"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["property_id"] == 1
        assert data["period_id"] == 1
        assert data["session_type"] == "full_reconciliation"
    
    @patch('app.api.v1.forensic_reconciliation.get_current_user')
    @patch('app.api.v1.forensic_reconciliation.get_db')
    def test_get_session(
        self,
        mock_get_db,
        mock_get_user,
        client,
        mock_user,
        mock_session
    ):
        """Test retrieving a session"""
        mock_get_user.return_value = mock_user
        mock_db = mock_db_session()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_get_db.return_value = mock_db
        
        response = client.get(
            "/api/v1/forensic-reconciliation/sessions/1",
            cookies={"reims_session": "test_session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
    
    @patch('app.api.v1.forensic_reconciliation.get_current_user')
    @patch('app.api.v1.forensic_reconciliation.get_db')
    @patch('app.api.v1.forensic_reconciliation.ForensicReconciliationService')
    def test_run_reconciliation(
        self,
        mock_service_class,
        mock_get_db,
        mock_get_user,
        client,
        mock_user
    ):
        """Test running reconciliation"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session()
        
        mock_service = Mock()
        mock_service.find_all_matches.return_value = {
            "total_matches": 10,
            "matches_created": 10
        }
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/api/v1/forensic-reconciliation/sessions/1/run",
            json={
                "use_exact": True,
                "use_fuzzy": True,
                "use_calculated": True,
                "use_inferred": False,
                "use_rules": True
            },
            cookies={"reims_session": "test_session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_matches"] == 10


class TestMatchEndpoints:
    """Test match management endpoints"""
    
    @patch('app.api.v1.forensic_reconciliation.get_current_user')
    @patch('app.api.v1.forensic_reconciliation.get_db')
    @patch('app.api.v1.forensic_reconciliation.ForensicReconciliationService')
    def test_get_matches(
        self,
        mock_service_class,
        mock_get_db,
        mock_get_user,
        client,
        mock_user,
        mock_match
    ):
        """Test retrieving matches for a session"""
        mock_get_user.return_value = mock_user
        mock_db = mock_db_session()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_match]
        mock_get_db.return_value = mock_db
        
        mock_service = Mock()
        mock_service._match_to_dict.return_value = {
            "id": 1,
            "match_type": "calculated",
            "confidence_score": 95.0
        }
        mock_service_class.return_value = mock_service
        
        response = client.get(
            "/api/v1/forensic-reconciliation/sessions/1/matches",
            cookies={"reims_session": "test_session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
    
    @patch('app.api.v1.forensic_reconciliation.get_current_user')
    @patch('app.api.v1.forensic_reconciliation.get_db')
    @patch('app.api.v1.forensic_reconciliation.ForensicReconciliationService')
    def test_approve_match(
        self,
        mock_service_class,
        mock_get_db,
        mock_get_user,
        client,
        mock_user
    ):
        """Test approving a match"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session()
        
        mock_service = Mock()
        mock_service.approve_match.return_value = True
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/api/v1/forensic-reconciliation/matches/1/approve",
            json={"notes": "Looks good"},
            cookies={"reims_session": "test_session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Match approved successfully"
    
    @patch('app.api.v1.forensic_reconciliation.get_current_user')
    @patch('app.api.v1.forensic_reconciliation.get_db')
    @patch('app.api.v1.forensic_reconciliation.ForensicReconciliationService')
    def test_reject_match(
        self,
        mock_service_class,
        mock_get_db,
        mock_get_user,
        client,
        mock_user
    ):
        """Test rejecting a match"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session()
        
        mock_service = Mock()
        mock_service.reject_match.return_value = True
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/api/v1/forensic-reconciliation/matches/1/reject",
            json={"reason": "Amount mismatch too large"},
            cookies={"reims_session": "test_session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Match rejected successfully"


class TestDiscrepancyEndpoints:
    """Test discrepancy management endpoints"""
    
    @patch('app.api.v1.forensic_reconciliation.get_current_user')
    @patch('app.api.v1.forensic_reconciliation.get_db')
    @patch('app.api.v1.forensic_reconciliation.ForensicReconciliationService')
    def test_get_discrepancies(
        self,
        mock_service_class,
        mock_get_db,
        mock_get_user,
        client,
        mock_user,
        mock_discrepancy
    ):
        """Test retrieving discrepancies"""
        mock_get_user.return_value = mock_user
        mock_db = mock_db_session()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_discrepancy]
        mock_get_db.return_value = mock_db
        
        mock_service = Mock()
        mock_service._discrepancy_to_dict.return_value = {
            "id": 1,
            "severity": "high",
            "status": "open"
        }
        mock_service_class.return_value = mock_service
        
        response = client.get(
            "/api/v1/forensic-reconciliation/sessions/1/discrepancies",
            cookies={"reims_session": "test_session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
    
    @patch('app.api.v1.forensic_reconciliation.get_current_user')
    @patch('app.api.v1.forensic_reconciliation.get_db')
    @patch('app.api.v1.forensic_reconciliation.ForensicReconciliationService')
    def test_resolve_discrepancy(
        self,
        mock_service_class,
        mock_get_db,
        mock_get_user,
        client,
        mock_user
    ):
        """Test resolving a discrepancy"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session()
        
        mock_service = Mock()
        mock_service.resolve_discrepancy.return_value = True
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/api/v1/forensic-reconciliation/discrepancies/1/resolve",
            json={
                "resolution_notes": "Corrected data entry error",
                "new_value": 100000.00
            },
            cookies={"reims_session": "test_session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Discrepancy resolved successfully"


class TestDashboardEndpoints:
    """Test dashboard and health score endpoints"""
    
    @patch('app.api.v1.forensic_reconciliation.get_current_user')
    @patch('app.api.v1.forensic_reconciliation.get_db')
    @patch('app.api.v1.forensic_reconciliation.ForensicReconciliationService')
    def test_get_dashboard(
        self,
        mock_service_class,
        mock_get_db,
        mock_get_user,
        client,
        mock_user
    ):
        """Test retrieving dashboard data"""
        mock_get_user.return_value = mock_user
        mock_get_db.return_value = mock_db_session()
        
        mock_service = Mock()
        mock_service.get_reconciliation_dashboard.return_value = {
            "session_id": 1,
            "summary": {
                "total_matches": 10,
                "discrepancies": 1
            }
        }
        mock_service_class.return_value = mock_service
        
        response = client.get(
            "/api/v1/forensic-reconciliation/dashboard/1/1",
            cookies={"reims_session": "test_session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
    
    @patch('app.api.v1.forensic_reconciliation.get_current_user')
    @patch('app.api.v1.forensic_reconciliation.get_db')
    @patch('app.api.v1.forensic_reconciliation.ForensicReconciliationService')
    def test_get_health_score(
        self,
        mock_service_class,
        mock_get_db,
        mock_get_user,
        client,
        mock_user,
        mock_session
    ):
        """Test retrieving health score"""
        mock_get_user.return_value = mock_user
        mock_db = mock_db_session()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_session
        mock_get_db.return_value = mock_db
        
        mock_service = Mock()
        mock_service.validate_matches.return_value = {
            "health_score": 85.5,
            "total_matches": 10,
            "discrepancies": 1
        }
        mock_service_class.return_value = mock_service
        
        response = client.get(
            "/api/v1/forensic-reconciliation/health-score/1/1",
            cookies={"reims_session": "test_session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "health_score" in data

