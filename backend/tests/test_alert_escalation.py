"""
Unit tests for Alert Escalation Service
"""
import pytest
from datetime import datetime, timedelta

from app.models.committee_alert import CommitteeAlert, AlertSeverity, AlertStatus, AlertType, CommitteeType
from app.services.alert_escalation_service import AlertEscalationService


@pytest.fixture
def overdue_alert(db_session: Session):
    """Create an alert that should be escalated"""
    alert = CommitteeAlert(
        property_id=1,
        alert_type=AlertType.DSCR_BREACH,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
        title="Overdue Alert",
        description="Test",
        assigned_committee=CommitteeType.FINANCE_SUBCOMMITTEE,
        triggered_at=datetime.utcnow() - timedelta(hours=5)  # 5 hours ago (past 4-hour threshold)
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert


def test_time_based_escalation(db_session: Session, overdue_alert):
    """Test time-based escalation"""
    service = AlertEscalationService(db_session)
    
    result = service.check_and_escalate_alerts()
    
    assert result["total_checked"] >= 1
    # Should have escalated the overdue alert
    assert result["escalated"] >= 1
    
    # Verify alert was escalated
    db_session.refresh(overdue_alert)
    assert overdue_alert.escalation_level is not None
    assert overdue_alert.escalation_level >= 1
    assert overdue_alert.escalated_at is not None


def test_severity_based_escalation(db_session: Session):
    """Test severity-based escalation"""
    service = AlertEscalationService(db_session)
    
    # Create critical alert not assigned to executive committee
    alert = CommitteeAlert(
        property_id=1,
        alert_type=AlertType.DSCR_BREACH,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
        title="Critical Alert",
        description="Test",
        assigned_committee=CommitteeType.FINANCE_SUBCOMMITTEE,  # Not executive
        triggered_at=datetime.utcnow()
    )
    db_session.add(alert)
    db_session.commit()
    
    escalation_result = service._check_escalation(alert)
    
    assert escalation_result["should_escalate"] is True
    assert "severity_based" in escalation_result["reason"]


def test_manual_escalation(db_session: Session):
    """Test manual escalation"""
    service = AlertEscalationService(db_session)
    
    alert = CommitteeAlert(
        property_id=1,
        alert_type=AlertType.DSCR_BREACH,
        severity=AlertSeverity.WARNING,
        status=AlertStatus.ACTIVE,
        title="Test Alert",
        description="Test",
        assigned_committee=CommitteeType.FINANCE_SUBCOMMITTEE,
        triggered_at=datetime.utcnow()
    )
    db_session.add(alert)
    db_session.commit()
    
    escalated = service.escalate_alert_manually(
        alert_id=alert.id,
        reason="Manual escalation for testing",
        target_committee=CommitteeType.EXECUTIVE_COMMITTEE
    )
    
    assert escalated.escalation_level == 1
    assert escalated.assigned_committee == CommitteeType.EXECUTIVE_COMMITTEE
    assert escalated.escalated_at is not None
    assert escalated.alert_metadata is not None
    assert "escalation_history" in escalated.alert_metadata

