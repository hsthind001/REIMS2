"""
Account Mapping Model

Stores historical mapping decisions learned from user approvals.
Used to suggest account mappings and improve matching accuracy.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class AccountMapping(Base):
    """Historical account mappings learned from approvals"""
    
    __tablename__ = "account_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Mapping Definition
    source_account_code = Column(String(50), nullable=False, index=True)
    source_account_name = Column(String(255), nullable=True)
    target_account_code = Column(String(50), nullable=False, index=True)
    target_account_name = Column(String(255), nullable=True)
    
    # Mapping Type
    mapping_type = Column(String(50), nullable=False, comment='exact, fuzzy, calculated, inferred')
    source_document_type = Column(String(50), nullable=True, index=True)
    target_document_type = Column(String(50), nullable=True, index=True)
    
    # Learning from Approvals
    approved_count = Column(Integer, nullable=False, server_default='0', comment='Number of times this mapping was approved')
    rejected_count = Column(Integer, nullable=False, server_default='0', comment='Number of times this mapping was rejected')
    last_approved_at = Column(DateTime(timezone=True), nullable=True)
    last_approved_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Confidence
    confidence_score = Column(Numeric(5, 2), nullable=False, server_default='50.00', index=True, comment='Calculated confidence based on approvals')
    
    # Status
    is_active = Column(Boolean, nullable=False, server_default='true')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Relationships
    approver = relationship("User", foreign_keys=[last_approved_by])
    
    # Composite indexes and constraints
    __table_args__ = (
        Index('idx_account_mappings_source', 'source_account_code', 'source_document_type'),
        Index('idx_account_mappings_target', 'target_account_code', 'target_document_type'),
        Index('idx_account_mappings_confidence', 'confidence_score', 'is_active'),
        UniqueConstraint('source_account_code', 'target_account_code', 'source_document_type', 'target_document_type', name='uq_account_mapping'),
    )
    
    def __repr__(self):
        return f"<AccountMapping {self.source_account_code} -> {self.target_account_code} ({self.confidence_score}%)>"

