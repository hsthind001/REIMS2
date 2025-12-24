"""
Account Code Pattern Model

Stores learned patterns and rules for account codes discovered
by the self-learning forensic reconciliation system.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, DECIMAL, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class AccountCodePattern(Base):
    """Learned patterns for account codes"""
    
    __tablename__ = "account_code_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Pattern identification
    pattern_name = Column(String(255), nullable=False, index=True)
    pattern_type = Column(String(50), nullable=False, index=True)  # regex, range, category, semantic
    
    # Pattern definition
    pattern_definition = Column(Text, nullable=False)  # Regex pattern, range definition, etc.
    pattern_json = Column(JSON)  # Structured pattern data
    
    # Matching rules
    match_rule = Column(Text)  # SQL-like or regex matching rule
    match_confidence = Column(DECIMAL(5, 2), default=100.0)  # Confidence in pattern matching
    
    # Scope
    document_type = Column(String(50), nullable=True, index=True)  # Specific document type or null for all
    account_type = Column(String(50), nullable=True, index=True)  # asset, liability, etc.
    category = Column(String(100), nullable=True)  # current_asset, etc.
    
    # Pattern metadata
    description = Column(Text)  # Human-readable description
    examples = Column(JSON)  # Example account codes that match this pattern
    match_count = Column(Integer, default=0)  # How many accounts matched this pattern
    
    # Learning metadata
    discovered_from = Column(String(100))  # Source of pattern discovery
    learning_confidence = Column(DECIMAL(5, 2), default=50.0)  # Confidence in pattern validity
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
        Index('idx_pattern_type_doc', 'pattern_type', 'document_type'),
        Index('idx_pattern_active_priority', 'is_active', 'priority'),
    )

