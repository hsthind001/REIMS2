from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ForensicReconciliationSession(Base):
    """Track forensic reconciliation sessions across all document types"""
    
    __tablename__ = "forensic_reconciliation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    auditor_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Session Metadata
    session_type = Column(String(50), nullable=False, comment='full_reconciliation, cross_document, specific_match')
    status = Column(String(50), nullable=False, server_default='in_progress', index=True, comment='in_progress, pending_review, approved, rejected')
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Summary Statistics (JSONB)
    summary = Column(JSONB, nullable=True, comment='{total_matches, exact_matches, fuzzy_matches, inferred_matches, discrepancies}')
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    property = relationship("Property")
    period = relationship("FinancialPeriod")
    auditor = relationship("User")
    matches = relationship("ForensicMatch", back_populates="session", cascade="all, delete-orphan")
    discrepancies = relationship("ForensicDiscrepancy", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ForensicReconciliationSession {self.id}: {self.property_id}-{self.period_id}-{self.session_type}>"

