"""
Account Mapping Rule Model

Stores learned mappings from raw_label to account_code with confidence scores.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class AccountMappingRule(Base):
    """Account mapping rule model."""
    
    __tablename__ = "account_mapping_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    raw_label = Column(String(500), nullable=False, index=True)  # Original extracted label
    account_code = Column(String(100), nullable=False, index=True)  # Mapped account code
    
    # Confidence and usage
    confidence_score = Column(Numeric(5, 4), nullable=False, default=0.5)  # 0-1 confidence
    usage_count = Column(Integer, default=0, nullable=False)  # Number of times used
    
    # Context for matching
    context = Column(JSON, nullable=True)  # Document type, property type, etc.
    
    # Metadata
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    last_used_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    last_user = relationship("User", foreign_keys=[last_used_by])
