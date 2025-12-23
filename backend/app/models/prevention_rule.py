"""
Prevention Rule Model

Stores rules for preventing known issues before they occur.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class PreventionRule(Base):
    """
    Rules for preventing known issues.
    
    These rules are applied during pre-flight checks to:
    - Skip problematic validations
    - Apply auto-fixes automatically
    - Override default behaviors
    - Warn about potential issues
    """
    
    __tablename__ = "prevention_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to knowledge base
    issue_kb_id = Column(Integer, ForeignKey('issue_knowledge_base.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Rule type
    rule_type = Column(String(50), nullable=False, index=True)  # 'pre_check', 'auto_fix', 'validation_override', 'warning'
    
    # Rule condition (JSONB: when to apply)
    rule_condition = Column(JSONB, nullable=False)  # {
    #   "document_type": "cash_flow",
    #   "property_code_pattern": "ESP.*",
    #   "file_size_min": 0,
    #   "file_size_max": 10000000,
    #   "extraction_engine": "pymupdf",
    #   "has_keywords": ["income statement", "revenue"],
    #   "confidence_threshold": 0.5
    # }
    
    # Rule action (JSONB: what to do)
    rule_action = Column(JSONB, nullable=False)  # {
    #   "action_type": "skip_validation",
    #   "validation_rule": "document_type_mismatch",
    #   "or": {
    #     "action_type": "auto_fix",
    #     "fix_method": "use_statement_date",
    #     "parameters": {"priority": "statement_date"}
    #   }
    # }
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Statistics
    success_count = Column(Integer, default=0, nullable=False)  # Times rule prevented issue
    failure_count = Column(Integer, default=0, nullable=False)  # Times rule didn't prevent issue
    last_applied_at = Column(DateTime(timezone=True), nullable=True)
    
    # Priority (higher priority rules applied first)
    priority = Column(Integer, default=0, nullable=False, index=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    issue_knowledge = relationship("IssueKnowledgeBase", back_populates="prevention_rules")
    
    def __repr__(self):
        return f"<PreventionRule(id={self.id}, rule_type='{self.rule_type}', is_active={self.is_active})>"

