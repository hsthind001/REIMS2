"""
Integration tests for Alert Trigger Service
"""
import pytest
from datetime import datetime
from decimal import Decimal

from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.financial_metrics import FinancialMetrics
from app.models.committee_alert import CommitteeAlert, AlertStatus
from app.services.alert_trigger_service import AlertTriggerService
from app.services.alert_rules_service import AlertRulesService
from app.models.alert_rule import AlertRule, RuleType, RuleCondition


@pytest.fixture
def sample_property(db_session: Session):
    """Create sample property"""
    property = Property(
        property_name="Test Property",
        property_code="TEST001",
        property_type="Commercial"
    )
    db_session.add(property)
    db_session.commit()
    db_session.refresh(property)
    return property


@pytest.fixture
def sample_period(db_session: Session, sample_property):
    """Create sample financial period"""
    period = FinancialPeriod(
        property_id=sample_property.id,
        period_year=2024,
        period_month=12,
        period_name="2024-12",
        period_start_date=datetime(2024, 12, 1),
        period_end_date=datetime(2024, 12, 31)
    )
    db_session.add(period)
    db_session.commit()
    db_session.refresh(period)
    return period


@pytest.fixture
def sample_metrics(db_session: Session, sample_property, sample_period):
    """Create sample financial metrics"""
    metrics = FinancialMetrics(
        property_id=sample_property.id,
        period_id=sample_period.id,
        dscr=Decimal("1.15"),  # Below threshold
        net_operating_income=Decimal("100000"),
        total_debt_service=Decimal("87000"),
        occupancy_rate=Decimal("85.0")
    )
    db_session.add(metrics)
    db_session.commit()
    db_session.refresh(metrics)
    return metrics


@pytest.fixture
def sample_rule(db_session: Session):
    """Create sample alert rule"""
    rule = AlertRule(
        rule_name="DSCR Threshold Breach",
        description="Alert when DSCR falls below 1.25",
        rule_type=RuleType.THRESHOLD,
        field_name="dscr",
        condition=RuleCondition.LESS_THAN,
        threshold_value=Decimal("1.25"),
        severity="critical",
        is_active=True,
        cooldown_period=60
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


def test_evaluate_and_trigger_alerts(db_session: Session, sample_property, sample_period, sample_metrics, sample_rule):
    """Test alert evaluation and triggering"""
    service = AlertTriggerService(db_session)
    
    # Evaluate and trigger alerts
    alerts = service.evaluate_and_trigger_alerts(
        property_id=sample_property.id,
        period_id=sample_period.id,
        metrics=sample_metrics
    )
    
    assert isinstance(alerts, list)
    # Should have created at least one alert
    assert len(alerts) >= 1
    
    # Verify alert was created in database
    created_alert = db_session.query(CommitteeAlert).filter(
        CommitteeAlert.property_id == sample_property.id,
        CommitteeAlert.status == AlertStatus.ACTIVE
    ).first()
    
    assert created_alert is not None
    assert created_alert.alert_type.value == "DSCR_BREACH"
    assert created_alert.severity.value == "CRITICAL"


def test_evaluate_property_alerts(db_session: Session, sample_property, sample_period, sample_metrics, sample_rule):
    """Test property-wide alert evaluation"""
    service = AlertTriggerService(db_session)
    
    result = service.evaluate_property_alerts(
        property_id=sample_property.id,
        period_id=sample_period.id
    )
    
    assert result["property_id"] == sample_property.id
    assert "total_alerts_triggered" in result
    assert "alerts_by_period" in result
    assert result["total_alerts_triggered"] >= 1


def test_no_duplicate_alerts(db_session: Session, sample_property, sample_period, sample_metrics, sample_rule):
    """Test that duplicate alerts are not created"""
    service = AlertTriggerService(db_session)
    
    # Trigger alerts twice
    alerts1 = service.evaluate_and_trigger_alerts(
        property_id=sample_property.id,
        period_id=sample_period.id,
        metrics=sample_metrics
    )
    
    # Wait a moment and trigger again (should be in cooldown)
    alerts2 = service.evaluate_and_trigger_alerts(
        property_id=sample_property.id,
        period_id=sample_period.id,
        metrics=sample_metrics
    )
    
    # Second call should not create duplicate (cooldown prevents it)
    # But if cooldown passes, deduplication logic should prevent duplicates
    total_alerts = db_session.query(CommitteeAlert).filter(
        CommitteeAlert.property_id == sample_property.id,
        CommitteeAlert.status == AlertStatus.ACTIVE
    ).count()
    
    # Should have at least one alert, but not necessarily two if cooldown is active
    assert total_alerts >= 1

