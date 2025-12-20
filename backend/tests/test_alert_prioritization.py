"""
Unit tests for Alert Prioritization Service
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from app.models.committee_alert import CommitteeAlert, AlertSeverity, AlertStatus, AlertType, CommitteeType
from app.services.alert_prioritization_service import AlertPrioritizationService


@pytest.fixture
def sample_alert(db_session: Session):
    """Create a sample alert for testing"""
    alert = CommitteeAlert(
        property_id=1,
        alert_type=AlertType.DSCR_BREACH,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
        title="Test DSCR Alert",
        description="Test alert description",
        threshold_value=Decimal("1.25"),
        actual_value=Decimal("1.15"),
        assigned_committee=CommitteeType.FINANCE_SUBCOMMITTEE,
        triggered_at=datetime.utcnow()
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert


def test_calculate_priority_score(db_session: Session, sample_alert):
    """Test priority score calculation"""
    service = AlertPrioritizationService(db_session)
    
    priority = service.calculate_priority_score(sample_alert)
    
    assert priority is not None
    assert 0 <= float(priority) <= 100
    # Critical alert should have high priority
    assert float(priority) >= 50


def test_update_alert_priority(db_session: Session, sample_alert):
    """Test updating alert priority"""
    service = AlertPrioritizationService(db_session)
    
    updated_alert = service.update_alert_priority(sample_alert)
    
    assert updated_alert.priority_score is not None
    assert 0 <= float(updated_alert.priority_score) <= 100
    
    # Verify it's saved
    db_session.refresh(sample_alert)
    assert sample_alert.priority_score is not None


def test_severity_score_mapping(db_session: Session):
    """Test severity to score mapping"""
    service = AlertPrioritizationService(db_session)
    
    urgent_score = service._get_severity_score(AlertSeverity.URGENT)
    critical_score = service._get_severity_score(AlertSeverity.CRITICAL)
    warning_score = service._get_severity_score(AlertSeverity.WARNING)
    info_score = service._get_severity_score(AlertSeverity.INFO)
    
    assert urgent_score == 100.0
    assert critical_score == 90.0
    assert warning_score == 60.0
    assert info_score == 30.0
    assert urgent_score > critical_score > warning_score > info_score


def test_breach_magnitude_score(db_session: Session):
    """Test breach magnitude scoring"""
    service = AlertPrioritizationService(db_session)
    
    # Create alert with large breach
    alert = CommitteeAlert(
        property_id=1,
        alert_type=AlertType.DSCR_BREACH,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
        title="Test Alert",
        description="Test",
        threshold_value=Decimal("1.25"),
        actual_value=Decimal("0.75"),  # 40% below threshold
        assigned_committee=CommitteeType.FINANCE_SUBCOMMITTEE,
        triggered_at=datetime.utcnow()
    )
    
    score = service._get_breach_magnitude_score(alert)
    assert score >= 80.0  # Large breach should score high
    
    # Small breach
    alert.actual_value = Decimal("1.20")  # 4% below threshold
    score = service._get_breach_magnitude_score(alert)
    assert score < 50  # Small breach should score lower

