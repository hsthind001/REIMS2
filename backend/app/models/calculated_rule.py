"""
Calculated Rule Model

Versioned calculated matching rules for forensic reconciliation.
Stores formulas, tolerances, and failure explanations.
"""
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Text, Boolean, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base


class CalculatedRule(Base):
    """Versioned calculated matching rules"""
    
    __tablename__ = "calculated_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Rule Identification
    rule_id = Column(String(100), nullable=False, index=True, comment='Unique rule identifier (e.g., "BS_IS_NET_INCOME")')
    version = Column(Integer, nullable=False, server_default='1', comment='Rule version number')
    
    # Scope
    property_scope = Column(JSONB(), nullable=True, comment='Property IDs or "all"')
    doc_scope = Column(JSONB(), nullable=False, comment='Document types this rule applies to')
    
    # Rule Definition
    rule_name = Column(String(255), nullable=False)
    formula = Column(Text(), nullable=False, comment='Formula text (e.g., "BS.current_period_earnings = IS.net_income")')
    description = Column(Text(), nullable=True)
    
    # Tolerances
    tolerance_absolute = Column(Numeric(15, 2), nullable=True)
    tolerance_percent = Column(Numeric(10, 4), nullable=True)
    
    # Materiality and Severity
    materiality_threshold = Column(Numeric(15, 2), nullable=True)
    severity = Column(String(50), nullable=False, server_default='medium', comment='critical, high, medium, low')
    
    # Failure Explanation Template
    failure_explanation_template = Column(Text(), nullable=True, comment='Template with placeholders for failure explanation')
    
    # Effective Dates
    effective_date = Column(Date(), nullable=False, server_default=func.current_date())
    expires_at = Column(Date(), nullable=True)
    
    # Status
    is_active = Column(Boolean(), nullable=False, server_default='true', index=True)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    # Composite indexes and constraints
    __table_args__ = (
        Index('idx_calculated_rules_rule_id', 'rule_id', 'version'),
        Index('idx_calculated_rules_active', 'is_active', 'effective_date', 'expires_at'),
        UniqueConstraint('rule_id', 'version', name='uq_calculated_rule_version'),
    )
    
    def __repr__(self):
        return f"<CalculatedRule {self.rule_id} v{self.version}: {self.rule_name}>"

