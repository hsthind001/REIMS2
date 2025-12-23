"""
Issue Knowledge Base Model

Stores learned issues, patterns, and fixes from the self-learning system.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class IssueKnowledgeBase(Base):
    """
    Knowledge base of learned issues, patterns, and fixes.
    
    Stores information about:
    - Error patterns and their contexts
    - Prevention strategies
    - Applied fixes
    - Issue statistics and confidence scores
    """
    
    __tablename__ = "issue_knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Issue identification
    issue_type = Column(String(100), nullable=False, index=True)  # e.g., 'document_type_mismatch', 'period_detection_error'
    issue_category = Column(String(50), nullable=False, index=True)  # 'extraction', 'validation', 'frontend', 'backend', 'ml_ai'
    
    # Pattern matching
    error_pattern = Column(Text, nullable=True)  # Regex or text pattern to match errors
    error_message_pattern = Column(Text, nullable=True)  # Pattern for error messages
    
    # Context (JSONB for flexible querying)
    context = Column(JSONB, nullable=True)  # {
    #   "document_type": "cash_flow",
    #   "property_pattern": "ESP.*",
    #   "period_pattern": ".*",
    #   "extraction_engine": "pymupdf",
    #   "file_size_range": {"min": 0, "max": 10000000},
    #   "keywords": ["income statement", "revenue"]
    # }
    
    # Prevention strategy (JSONB)
    prevention_strategy = Column(JSONB, nullable=True)  # {
    #   "pre_check": "skip_validation_for_document_type",
    #   "auto_fix": "use_statement_date_for_period",
    #   "validation_override": {"rule": "year_mismatch", "action": "skip"}
    # }
    
    # Fix information
    fix_applied = Column(Text, nullable=True)  # Description of the fix
    fix_code_location = Column(String(500), nullable=True)  # File and function where fix was applied
    fix_implementation = Column(Text, nullable=True)  # Code or configuration changes
    
    # Status
    status = Column(String(20), nullable=False, default='active', index=True)  # 'active', 'resolved', 'suppressed', 'archived'
    
    # Statistics
    occurrence_count = Column(Integer, default=0, nullable=False)
    last_occurred_at = Column(DateTime(timezone=True), nullable=True)
    first_occurred_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey('users.id'), nullable=True)  # User who resolved it
    
    # Confidence and reliability
    confidence_score = Column(DECIMAL(5, 4), default=0.5, nullable=False)  # 0-1, how reliable the pattern is
    auto_fix_success_rate = Column(DECIMAL(5, 4), nullable=True)  # Success rate of auto-fixes
    prevention_success_rate = Column(DECIMAL(5, 4), nullable=True)  # Success rate of prevention
    
    # MCP Integration
    mcp_task_id = Column(String(100), nullable=True, index=True)  # Task ID in task-master-ai
    mcp_task_status = Column(String(20), nullable=True)  # 'pending', 'in-progress', 'done'
    
    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    captures = relationship("IssueCapture", back_populates="issue_knowledge")
    prevention_rules = relationship("PreventionRule", back_populates="issue_knowledge")
    resolver = relationship("User", foreign_keys=[resolved_by])
    
    def __repr__(self):
        return f"<IssueKnowledgeBase(id={self.id}, issue_type='{self.issue_type}', status='{self.status}')>"

