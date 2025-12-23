from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ForensicDiscrepancy(Base):
    """Track discrepancies found during forensic reconciliation"""
    
    __tablename__ = "forensic_discrepancies"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('forensic_reconciliation_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    match_id = Column(Integer, ForeignKey('forensic_matches.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Discrepancy Details
    discrepancy_type = Column(String(100), nullable=False, comment='amount_mismatch, missing_source, missing_target, date_mismatch')
    severity = Column(String(50), nullable=False, index=True, comment='critical, high, medium, low')
    exception_tier = Column(String(50), nullable=True, index=True, comment='tier_0_auto_close, tier_1_auto_suggest, tier_2_route, tier_3_escalate')
    auto_resolution_rule_id = Column(Integer, ForeignKey('auto_resolution_rules.id', ondelete='SET NULL'), nullable=True, comment='Rule that auto-resolved this discrepancy')
    
    # Values
    source_value = Column(Numeric(15, 2), nullable=True)
    target_value = Column(Numeric(15, 2), nullable=True)
    expected_value = Column(Numeric(15, 2), nullable=True)
    actual_value = Column(Numeric(15, 2), nullable=True)
    difference = Column(Numeric(15, 2), nullable=True)
    difference_percent = Column(Numeric(10, 4), nullable=True)
    
    # Description and Resolution
    description = Column(Text, nullable=False)
    suggested_resolution = Column(Text, nullable=True)
    
    # Resolution Status
    status = Column(String(50), nullable=False, server_default='open', index=True, comment='open, investigating, resolved, accepted')
    resolved_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    session = relationship("ForensicReconciliationSession", back_populates="discrepancies")
    match = relationship("ForensicMatch", back_populates="discrepancies")
    resolver = relationship("User", foreign_keys=[resolved_by])
    auto_resolution_rule = relationship("AutoResolutionRule", foreign_keys=[auto_resolution_rule_id])
    
    # Composite indexes
    __table_args__ = (
        Index('idx_forensic_discrepancies_severity', 'severity', 'status'),
        Index('idx_forensic_discrepancies_status', 'status', 'created_at'),
        Index('idx_forensic_discrepancies_tier', 'exception_tier', 'severity'),
    )
    
    def __repr__(self):
        return f"<ForensicDiscrepancy {self.id}: {self.discrepancy_type} ({self.severity})>"

