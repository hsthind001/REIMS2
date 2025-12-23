"""
Issue Capture Model

Captures individual occurrences of issues with full context for learning.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class IssueCapture(Base):
    """
    Individual issue capture with full context.
    
    Each time an issue occurs, it's captured here with:
    - Full error details
    - Context (document, property, period, etc.)
    - Stack trace (if available)
    - Severity and category
    """
    
    __tablename__ = "issue_captures"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to knowledge base
    issue_kb_id = Column(Integer, ForeignKey('issue_knowledge_base.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Document context
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'), nullable=True, index=True)
    document_type = Column(String(50), nullable=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='SET NULL'), nullable=True, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Error details
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)  # Full stack trace if available
    error_type = Column(String(100), nullable=True)  # Exception class name
    
    # Context (JSONB for flexible storage)
    context = Column(JSONB, nullable=True)  # {
    #   "filename": "document.pdf",
    #   "file_size": 1234567,
    #   "page_count": 5,
    #   "extraction_engine": "pymupdf",
    #   "detected_type": "cash_flow",
    #   "expected_type": "income_statement",
    #   "detected_year": 2023,
    #   "expected_year": 2024,
    #   "detected_month": 1,
    #   "expected_month": 2,
    #   "api_endpoint": "/api/v1/documents/upload",
    #   "user_id": 1,
    #   "request_id": "abc123"
    # }
    
    # Severity and category
    severity = Column(String(20), nullable=False, default='error', index=True)  # 'critical', 'error', 'warning', 'info'
    issue_category = Column(String(50), nullable=False, index=True)  # 'extraction', 'validation', 'frontend', 'backend', 'ml_ai'
    
    # Resolution
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Auto-fix attempt
    auto_fix_attempted = Column(Boolean, default=False, nullable=False)
    auto_fix_successful = Column(Boolean, nullable=True)
    auto_fix_method = Column(String(100), nullable=True)  # Which auto-fix was attempted
    
    # Timestamps
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    issue_knowledge = relationship("IssueKnowledgeBase", back_populates="captures")
    upload = relationship("DocumentUpload")
    property_obj = relationship("Property")
    period = relationship("FinancialPeriod")
    resolver_user = relationship("User", foreign_keys=[resolved_by])
    
    def __repr__(self):
        return f"<IssueCapture(id={self.id}, severity='{self.severity}', resolved={self.resolved})>"

