"""
Learned Match Pattern Model

Stores successful match patterns for learning in the self-learning
forensic reconciliation system.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, DECIMAL, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class LearnedMatchPattern(Base):
    """Successful match patterns for learning"""
    
    __tablename__ = "learned_match_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Pattern identification
    pattern_name = Column(String(255), nullable=False, index=True)
    pattern_type = Column(String(50), nullable=False, index=True)  # exact, fuzzy, calculated, inferred
    
    # Source and target information
    source_document_type = Column(String(50), nullable=False, index=True)
    source_account_code = Column(String(50), nullable=True, index=True)
    source_account_name = Column(String(255), nullable=True)
    
    target_document_type = Column(String(50), nullable=False, index=True)
    target_account_code = Column(String(50), nullable=True, index=True)
    target_account_name = Column(String(255), nullable=True)
    
    # Relationship information
    relationship_type = Column(String(50))  # equality, sum, calculation, etc.
    relationship_formula = Column(Text)  # Formula describing the relationship
    
    # Match statistics
    match_count = Column(Integer, default=0)  # How many times this pattern matched
    success_count = Column(Integer, default=0)  # How many times match was approved
    success_rate = Column(DECIMAL(5, 2), default=0.0)  # Success rate percentage
    
    # Confidence metrics
    average_confidence = Column(DECIMAL(5, 2), default=0.0)  # Average confidence score
    min_confidence = Column(DECIMAL(5, 2), default=0.0)
    max_confidence = Column(DECIMAL(5, 2), default=0.0)
    
    # Pattern details
    pattern_json = Column(JSON)  # Detailed pattern information
    conditions = Column(JSON)  # Conditions for pattern to apply
    
    # Learning metadata
    first_discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_validated = Column(Boolean, default=False)
    validated_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    priority = Column(Integer, default=0)  # Higher priority patterns checked first
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_learned_pattern_source_target', 'source_document_type', 'target_document_type'),
        Index('idx_learned_pattern_active_priority', 'is_active', 'priority'),
        Index('idx_learned_pattern_success_rate', 'success_rate', 'is_active'),
    )

