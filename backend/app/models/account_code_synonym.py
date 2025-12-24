"""
Account Code Synonym Model

Stores learned synonyms and variations of account codes
for the self-learning forensic reconciliation system.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, DECIMAL, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class AccountCodeSynonym(Base):
    """Learned synonyms and variations of account codes"""
    
    __tablename__ = "account_code_synonyms"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Canonical account information
    canonical_account_code = Column(String(50), nullable=False, index=True)
    canonical_account_name = Column(String(255), nullable=False)
    
    # Synonym/variation information
    synonym_code = Column(String(50), nullable=True, index=True)  # Alternative code
    synonym_name = Column(String(255), nullable=False, index=True)  # Alternative name
    
    # Document type context
    document_type = Column(String(50), nullable=True, index=True)  # balance_sheet, income_statement, etc.
    
    # Similarity metrics
    code_similarity = Column(DECIMAL(5, 2))  # Code similarity score (0-100)
    name_similarity = Column(DECIMAL(5, 2))  # Name similarity score (0-100)
    combined_confidence = Column(DECIMAL(5, 2), default=0.0)  # Combined confidence
    
    # Usage statistics
    usage_count = Column(Integer, default=0)  # How many times this synonym was used
    success_count = Column(Integer, default=0)  # How many times synonym match was successful
    success_rate = Column(DECIMAL(5, 2), default=0.0)  # Success rate percentage
    
    # Learning metadata
    discovered_from = Column(String(100))  # Source of synonym discovery
    is_validated = Column(Boolean, default=False)
    validated_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_synonym_canonical', 'canonical_account_code', 'is_active'),
        Index('idx_synonym_name', 'synonym_name', 'document_type'),
        Index('idx_synonym_confidence', 'combined_confidence', 'is_active'),
    )

