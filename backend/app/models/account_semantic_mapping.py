"""
Account Semantic Mapping Model

Maps account names to codes using NLP and semantic similarity
for the self-learning forensic reconciliation system.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, DECIMAL, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class AccountSemanticMapping(Base):
    """Semantic mappings between account names and codes using NLP"""
    
    __tablename__ = "account_semantic_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Account identification
    account_name = Column(String(255), nullable=False, index=True)
    account_code = Column(String(50), nullable=False, index=True)
    
    # Document type context
    document_type = Column(String(50), nullable=True, index=True)  # balance_sheet, income_statement, etc.
    
    # Semantic information
    semantic_embedding = Column(JSON)  # Vector embedding of account name
    embedding_model = Column(String(100))  # Model used for embedding (e.g., 'sentence-transformers/all-MiniLM-L6-v2')
    
    # Similarity scores
    semantic_similarity = Column(DECIMAL(5, 2))  # Semantic similarity score (0-100)
    fuzzy_match_score = Column(DECIMAL(5, 2))  # Fuzzy string matching score (0-100)
    combined_confidence = Column(DECIMAL(5, 2), default=0.0)  # Combined confidence score
    
    # Alternative mappings
    alternative_codes = Column(JSON)  # List of alternative account codes with confidence scores
    alternative_names = Column(JSON)  # List of alternative account names
    
    # Learning metadata
    match_count = Column(Integer, default=0)  # How many times this mapping was used successfully
    success_rate = Column(DECIMAL(5, 2), default=0.0)  # Success rate of this mapping
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Validation
    is_validated = Column(Boolean, default=False)
    validated_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_semantic_name_code', 'account_name', 'account_code'),
        Index('idx_semantic_doc_type', 'document_type', 'is_active'),
        Index('idx_semantic_confidence', 'combined_confidence', 'is_active'),
    )

