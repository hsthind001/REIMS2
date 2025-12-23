"""
Account Synonym Model

Stores account name synonyms for improved fuzzy matching.
Supports both manual synonyms and learned synonyms from historical approvals.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.db.database import Base


class AccountSynonym(Base):
    """Account name synonyms for matching"""
    
    __tablename__ = "account_synonyms"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Account Information
    account_code = Column(String(50), nullable=True, index=True, comment='Optional account code')
    synonym = Column(String(255), nullable=False, index=True, comment='Synonym text (e.g., "AR", "Receivables")')
    canonical_name = Column(String(255), nullable=False, index=True, comment='Canonical account name')
    
    # Confidence and Source
    confidence = Column(Numeric(5, 2), nullable=False, server_default='100.00', comment='Confidence score 0-100')
    source = Column(String(50), nullable=False, server_default='manual', comment='manual, learned')
    
    # Usage Tracking
    usage_count = Column(Integer, nullable=False, server_default='0', comment='Number of times used')
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, server_default='true')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Composite indexes and constraints
    __table_args__ = (
        UniqueConstraint('account_code', 'synonym', name='uq_account_synonym'),
    )
    
    def __repr__(self):
        return f"<AccountSynonym {self.synonym} -> {self.canonical_name} ({self.source})>"

