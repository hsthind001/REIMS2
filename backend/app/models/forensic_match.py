from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ForensicMatch(Base):
    """Store matches between financial documents across all 5 document types"""
    
    __tablename__ = "forensic_matches"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('forensic_reconciliation_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Source Document Information
    source_document_type = Column(String(50), nullable=False, index=True, comment='balance_sheet, income_statement, cash_flow, rent_roll, mortgage_statement')
    source_table_name = Column(String(100), nullable=False, comment='balance_sheet_data, income_statement_data, etc.')
    source_record_id = Column(Integer, nullable=False)
    source_account_code = Column(String(50), nullable=True)
    source_account_name = Column(String(255), nullable=True)
    source_amount = Column(Numeric(15, 2), nullable=True)
    source_field_name = Column(String(100), nullable=True, comment='amount, period_amount, etc.')
    
    # Target Document Information
    target_document_type = Column(String(50), nullable=False, index=True)
    target_table_name = Column(String(100), nullable=False)
    target_record_id = Column(Integer, nullable=False)
    target_account_code = Column(String(50), nullable=True)
    target_account_name = Column(String(255), nullable=True)
    target_amount = Column(Numeric(15, 2), nullable=True)
    target_field_name = Column(String(100), nullable=True)
    
    # Matching Metadata
    match_type = Column(String(50), nullable=False, index=True, comment='exact, fuzzy, inferred, calculated')
    confidence_score = Column(Numeric(5, 2), nullable=False, comment='0-100')
    amount_difference = Column(Numeric(15, 2), nullable=True)
    amount_difference_percent = Column(Numeric(10, 4), nullable=True)
    match_algorithm = Column(String(100), nullable=True, comment='exact_match, fuzzy_string, account_code_range, calculated_relationship')
    
    # Relationship Type
    relationship_type = Column(String(100), nullable=True, comment='equality, sum, difference, calculation')
    relationship_formula = Column(Text, nullable=True, comment='e.g., BS.current_period_earnings = IS.net_income')
    
    # Review Status
    status = Column(String(50), nullable=False, server_default='pending', index=True, comment='pending, approved, rejected, modified')
    reviewed_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    auditor_override = Column(Boolean, nullable=False, server_default='false')
    auditor_override_reason = Column(Text, nullable=True)
    
    # Audit Trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Relationships
    session = relationship("ForensicReconciliationSession", back_populates="matches")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    discrepancies = relationship("ForensicDiscrepancy", back_populates="match", cascade="all, delete-orphan")
    
    # Composite indexes
    __table_args__ = (
        Index('idx_forensic_matches_source', 'source_document_type', 'source_record_id'),
        Index('idx_forensic_matches_target', 'target_document_type', 'target_record_id'),
        Index('idx_forensic_matches_status', 'status', 'confidence_score'),
        Index('idx_forensic_matches_match_type', 'match_type', 'confidence_score'),
    )
    
    def __repr__(self):
        return f"<ForensicMatch {self.id}: {self.source_document_type}->{self.target_document_type} (confidence: {self.confidence_score})>"

