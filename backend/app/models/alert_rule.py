"""
Alert Rule Model
Defines rules for automatic alert generation based on financial metrics
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

from app.db.database import Base


class RuleType(str, enum.Enum):
    """Rule types"""
    THRESHOLD = "threshold"  # Simple threshold comparison
    STATISTICAL = "statistical"  # Z-score, percentage change
    TREND = "trend"  # Trend analysis over time
    COMPOSITE = "composite"  # Multiple conditions combined


class RuleCondition(str, enum.Enum):
    """Rule conditions"""
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    PERCENTAGE_CHANGE = "percentage_change"
    Z_SCORE = "z_score"
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    ABSOLUTE_CHANGE = "absolute_change"


class AlertRule(Base):
    """
    Alert Rule Model
    
    Defines rules that automatically generate alerts when conditions are met.
    Rules can be property-specific or global, and support various evaluation types.
    """
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    
    # Basic information
    rule_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Rule configuration
    rule_type = Column(String(50), nullable=False, default="threshold")  # threshold, statistical, trend, composite
    field_name = Column(String(100), nullable=False)  # Metric or account code to monitor
    condition = Column(String(50), nullable=False)  # greater_than, less_than, equals, etc.
    threshold_value = Column(Numeric(15, 4), nullable=True)
    
    # Severity and status
    severity = Column(String(20), nullable=False, default="warning")  # critical, high, medium, low, warning, info
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Enhanced fields (from Phase 9 migration)
    rule_expression = Column(JSONB, nullable=True)  # Flexible JSON rule definition
    severity_mapping = Column(JSONB, nullable=True)  # Dynamic severity based on breach magnitude
    cooldown_period = Column(Integer, nullable=True, default=60)  # Minutes between alerts
    rule_dependencies = Column(JSONB, nullable=True)  # Related rules that must trigger first
    property_specific = Column(Boolean, nullable=True, default=False)  # Property-level vs global
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True, index=True)
    rule_template_id = Column(Integer, nullable=True)  # Link to template if created from template
    execution_count = Column(Integer, nullable=True, default=0)  # Performance tracking
    last_triggered_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=datetime.utcnow)
    
    # Relationships
    property = relationship("Property", backref="alert_rules")
    
    def __repr__(self):
        return f"<AlertRule(id={self.id}, name={self.rule_name}, type={self.rule_type}, active={self.is_active})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "rule_name": self.rule_name,
            "description": self.description,
            "rule_type": self.rule_type if self.rule_type else None,
            "field_name": self.field_name,
            "condition": self.condition if self.condition else None,
            "threshold_value": float(self.threshold_value) if self.threshold_value else None,
            "severity": self.severity,
            "is_active": self.is_active,
            "rule_expression": self.rule_expression,
            "severity_mapping": self.severity_mapping,
            "cooldown_period": self.cooldown_period,
            "rule_dependencies": self.rule_dependencies,
            "property_specific": self.property_specific,
            "property_id": self.property_id,
            "rule_template_id": self.rule_template_id,
            "execution_count": self.execution_count,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def is_in_cooldown(self) -> bool:
        """Check if rule is in cooldown period"""
        if not self.last_triggered_at or not self.cooldown_period:
            return False
        
        from datetime import timedelta
        cooldown_end = self.last_triggered_at + timedelta(minutes=self.cooldown_period)
        return datetime.utcnow() < cooldown_end

