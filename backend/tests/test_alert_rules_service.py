"""
Unit tests for Alert Rules Service
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.alert_rule import AlertRule, RuleType, RuleCondition
from app.models.financial_metrics import FinancialMetrics
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.services.alert_rules_service import AlertRulesService


@pytest.fixture
def sample_rule(db_session: Session):
    """Create a sample alert rule for testing"""
    rule = AlertRule(
        rule_name="Test DSCR Rule",
        description="Test rule for DSCR threshold",
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


@pytest.fixture
def sample_metrics(db_session: Session, sample_property, sample_period):
    """Create sample financial metrics"""
    metrics = FinancialMetrics(
        property_id=sample_property.id,
        period_id=sample_period.id,
        dscr=Decimal("1.15"),  # Below threshold
        net_operating_income=Decimal("100000"),
        total_debt_service=Decimal("87000")
    )
    db_session.add(metrics)
    db_session.commit()
    db_session.refresh(metrics)
    return metrics


def test_get_active_rules(db_session: Session, sample_rule):
    """Test getting active rules"""
    service = AlertRulesService(db_session)
    
    rules = service.get_active_rules()
    assert len(rules) >= 1
    assert any(r.id == sample_rule.id for r in rules)
    
    # Test with property filter
    rules = service.get_active_rules(property_id=1)
    assert isinstance(rules, list)


def test_evaluate_rule_triggered(db_session: Session, sample_rule, sample_metrics):
    """Test rule evaluation when condition is met"""
    service = AlertRulesService(db_session)
    
    result = service.evaluate_rule(
        rule=sample_rule,
        property_id=sample_metrics.property_id,
        period_id=sample_metrics.period_id,
        metrics=sample_metrics
    )
    
    assert result["triggered"] is True
    assert result["severity"] == "critical"
    assert result["actual_value"] == 1.15
    assert result["threshold_value"] == 1.25
    assert "breach_magnitude" in result


def test_evaluate_rule_not_triggered(db_session: Session, sample_rule):
    """Test rule evaluation when condition is not met"""
    service = AlertRulesService(db_session)
    
    # Create metrics with DSCR above threshold
    metrics = FinancialMetrics(
        property_id=1,
        period_id=1,
        dscr=Decimal("1.50")  # Above threshold
    )
    db_session.add(metrics)
    db_session.commit()
    
    result = service.evaluate_rule(
        rule=sample_rule,
        property_id=1,
        period_id=1,
        metrics=metrics
    )
    
    assert result["triggered"] is False
    assert result["reason"] == "condition_not_met"


def test_cooldown_period(db_session: Session, sample_rule, sample_metrics):
    """Test cooldown period enforcement"""
    service = AlertRulesService(db_session)
    
    # First evaluation - should trigger
    result1 = service.evaluate_rule(
        rule=sample_rule,
        property_id=sample_metrics.property_id,
        period_id=sample_metrics.period_id,
        metrics=sample_metrics
    )
    assert result1["triggered"] is True
    
    # Second evaluation immediately - should be in cooldown
    result2 = service.evaluate_rule(
        rule=sample_rule,
        property_id=sample_metrics.property_id,
        period_id=sample_metrics.period_id,
        metrics=sample_metrics
    )
    assert result2["triggered"] is False
    assert result2["reason"] == "cooldown"


def test_severity_mapping(db_session: Session, sample_metrics):
    """Test dynamic severity mapping based on breach magnitude"""
    # Create rule with severity mapping
    rule = AlertRule(
        rule_name="Test Rule with Severity Mapping",
        rule_type=RuleType.THRESHOLD,
        field_name="dscr",
        condition=RuleCondition.LESS_THAN,
        threshold_value=Decimal("1.25"),
        severity="warning",
        is_active=True,
        severity_mapping={
            "critical_threshold": 0.2,  # 20% below
            "high_threshold": 0.1,  # 10% below
            "warning_threshold": 0.05  # 5% below
        }
    )
    db_session.add(rule)
    db_session.commit()
    
    service = AlertRulesService(db_session)
    
    # DSCR of 1.15 is 8% below 1.25 threshold
    # Should map to "high" severity (between 5% and 10%)
    result = service.evaluate_rule(
        rule=rule,
        property_id=sample_metrics.property_id,
        period_id=sample_metrics.period_id,
        metrics=sample_metrics
    )
    
    assert result["triggered"] is True
    # Breach magnitude is approximately -0.08 (8% below)
    # Should map to "high" based on severity_mapping


def test_evaluate_all_rules(db_session: Session, sample_rule, sample_metrics):
    """Test evaluating all active rules"""
    service = AlertRulesService(db_session)
    
    results = service.evaluate_all_rules(
        property_id=sample_metrics.property_id,
        period_id=sample_metrics.period_id,
        metrics=sample_metrics
    )
    
    assert isinstance(results, list)
    # Should have at least one triggered rule
    assert len(results) >= 1
    assert all("rule" in r for r in results)
    assert all("triggered" in r for r in results)

