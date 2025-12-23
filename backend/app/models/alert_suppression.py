"""
Alert Suppression Models

Models for alert workflow enhancements:
- AlertSuppression: Individual alert suppressions
- AlertSnooze: Alert snoozing
- AlertSuppressionRule: Reusable suppression rules
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base


class AlertSuppression(Base):
    """Individual alert suppression"""
    
    __tablename__ = "alert_suppressions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Alert Reference
    alert_id = Column(Integer, nullable=True, index=True, comment='Specific alert ID (nullable for rule-based)')
    alert_type = Column(String(50), nullable=True, comment='Alert type pattern')
    
    # Suppression Rule
    rule_id = Column(Integer, nullable=True, comment='Suppression rule ID')
    suppression_reason = Column(Text(), nullable=False)
    
    # Expiry
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True, comment='When suppression expires')
    expires_after_periods = Column(Integer, nullable=True, comment='Expire after N periods')
    
    # Scope
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=True, comment='NULL = global suppression')
    account_code = Column(String(50), nullable=True, comment='Account-specific suppression')
    
    # Metadata
    suppressed_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    property = relationship("Property", foreign_keys=[property_id])
    suppressor = relationship("User", foreign_keys=[suppressed_by])
    
    def __repr__(self):
        return f"<AlertSuppression {self.id}: alert_id={self.alert_id}>"


class AlertSnooze(Base):
    """Alert snoozing until next period or date"""
    
    __tablename__ = "alert_snoozes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Alert Reference
    alert_id = Column(Integer, nullable=False, index=True, comment='Alert ID to snooze')
    
    # Snooze Details
    until_period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='SET NULL'), nullable=True, comment='Snooze until this period')
    until_date = Column(DateTime(timezone=True), nullable=True, index=True, comment='Snooze until this date')
    snooze_reason = Column(Text(), nullable=True)
    
    # Metadata
    snoozed_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    period = relationship("FinancialPeriod", foreign_keys=[until_period_id])
    snoozer = relationship("User", foreign_keys=[snoozed_by])
    
    # Composite indexes
    __table_args__ = (
        Index('idx_alert_snoozes_until', 'until_period_id', 'until_date'),
    )
    
    def __repr__(self):
        return f"<AlertSnooze {self.id}: alert_id={self.alert_id}>"


class AlertSuppressionRule(Base):
    """Reusable alert suppression rule"""
    
    __tablename__ = "alert_suppression_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Rule Definition
    rule_name = Column(String(255), nullable=False)
    alert_type_pattern = Column(String(100), nullable=True, comment='Pattern to match alert types')
    condition_json = Column(JSONB(), nullable=True, comment='Conditions for suppression')
    
    # Expiry
    expires_after_periods = Column(Integer, nullable=True, comment='Auto-expire after N periods')
    expires_after_days = Column(Integer, nullable=True, comment='Auto-expire after N days')
    
    # Scope
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=True, comment='NULL = global rule')
    account_code = Column(String(50), nullable=True, comment='Account-specific rule')
    
    # Status
    is_active = Column(Boolean(), nullable=False, server_default='true', index=True)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    property = relationship("Property", foreign_keys=[property_id])
    creator = relationship("User", foreign_keys=[created_by])
    
    # Composite indexes
    __table_args__ = (
        Index('idx_alert_suppression_rules_active', 'is_active', 'property_id'),
    )
    
    def __repr__(self):
        return f"<AlertSuppressionRule {self.id}: {self.rule_name}>"

