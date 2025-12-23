"""
Auto Resolution Rule Model

Defines rules for automatically resolving tier 0 exceptions (auto-close)
and suggesting fixes for tier 1 exceptions.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base


class AutoResolutionRule(Base):
    """Rule for auto-resolving exceptions based on patterns"""
    
    __tablename__ = "auto_resolution_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Rule Definition
    rule_name = Column(String(255), nullable=False)
    pattern_type = Column(String(50), nullable=False, index=True, comment='rounding, timing, synonym, mapping')
    
    # Condition (JSONB for flexible pattern matching)
    condition_json = Column(JSONB(), nullable=False, comment='Pattern matching conditions')
    
    # Action
    action_type = Column(String(50), nullable=False, comment='auto_close, suggest_fix, route_to_queue')
    suggested_mapping = Column(JSONB(), nullable=True, comment='Suggested account mapping or adjustment')
    
    # Confidence Threshold
    confidence_threshold = Column(Numeric(5, 2), nullable=False, comment='Minimum confidence to apply rule (0-100)')
    
    # Scope
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=True, comment='NULL = global rule')
    statement_type = Column(String(50), nullable=True, comment='NULL = all statement types')
    
    # Status
    is_active = Column(Boolean(), nullable=False, server_default='true')
    priority = Column(Integer, nullable=False, server_default='0', index=True, comment='Higher priority rules evaluated first')
    
    # Metadata
    description = Column(Text(), nullable=True)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Relationships
    property = relationship("Property", foreign_keys=[property_id])
    creator = relationship("User", foreign_keys=[created_by])
    
    # Composite indexes
    __table_args__ = (
        Index('idx_auto_resolution_rules_pattern', 'pattern_type', 'is_active'),
        Index('idx_auto_resolution_rules_priority', 'priority', 'is_active'),
    )
    
    def __repr__(self):
        return f"<AutoResolutionRule {self.rule_name}: {self.pattern_type} ({self.action_type})>"

