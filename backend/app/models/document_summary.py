"""
Document Summary Model

Stores AI-generated summaries of lease documents, OMs, and other property documents
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

from app.db.database import Base


class DocumentType(str, enum.Enum):
    """Document type"""
    LEASE = "LEASE"
    OFFERING_MEMORANDUM = "OFFERING_MEMORANDUM"
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    APPRAISAL = "APPRAISAL"
    INSPECTION_REPORT = "INSPECTION_REPORT"
    LEGAL_DOCUMENT = "LEGAL_DOCUMENT"
    OTHER = "OTHER"


class SummaryStatus(str, enum.Enum):
    """Summary processing status"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentSummary(Base):
    """
    Document Summary Model

    Stores AI-generated summaries of property documents
    """
    __tablename__ = "document_summaries"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("document_uploads.id"), nullable=True, index=True)

    # Document details
    document_type = Column(SQLEnum(DocumentType), nullable=False, index=True)
    document_name = Column(String(300), nullable=False)
    document_path = Column(String(500), nullable=True)

    # Summary details
    summary_type = Column(String(50), nullable=False)  # "lease", "om", "financial", etc.
    status = Column(SQLEnum(SummaryStatus), nullable=False, default=SummaryStatus.PENDING, index=True)

    # AI-generated content
    executive_summary = Column(Text, nullable=True)  # Brief overview
    detailed_summary = Column(Text, nullable=True)  # Full summary
    key_points = Column(JSONB, nullable=True)  # Structured key points as JSON array
    extracted_data = Column(JSONB, nullable=True)  # Structured data extracted from document

    # For lease documents
    lease_data = Column(JSONB, nullable=True)  # Tenant, term, rent, options, etc.

    # For offering memoranda
    om_data = Column(JSONB, nullable=True)  # Property details, financials, market analysis

    # Confidence and quality metrics
    confidence_score = Column(Integer, nullable=True)  # 0-100
    has_hallucination_flag = Column(Boolean, default=False)  # True if M3 auditor flagged issues
    hallucination_details = Column(JSONB, nullable=True)  # Details of flagged issues

    # Processing metadata
    llm_provider = Column(String(50), nullable=True)  # "openai", "anthropic"
    llm_model = Column(String(100), nullable=True)  # "gpt-4", "claude-3-opus-20240229"
    processing_time_seconds = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Additional metadata
    summary_metadata = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    property = relationship("Property", backref="document_summaries")
    created_by_user = relationship("User", foreign_keys=[created_by], backref="document_summaries_created")

    def __repr__(self):
        return f"<DocumentSummary(id={self.id}, type={self.document_type}, status={self.status})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "property_id": self.property_id,
            "document_id": self.document_id,
            "document_type": self.document_type.value if self.document_type else None,
            "document_name": self.document_name,
            "document_path": self.document_path,
            "summary_type": self.summary_type,
            "status": self.status.value if self.status else None,
            "executive_summary": self.executive_summary,
            "detailed_summary": self.detailed_summary,
            "key_points": self.key_points,
            "extracted_data": self.extracted_data,
            "lease_data": self.lease_data,
            "om_data": self.om_data,
            "confidence_score": self.confidence_score,
            "has_hallucination_flag": self.has_hallucination_flag,
            "hallucination_details": self.hallucination_details,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "processing_time_seconds": self.processing_time_seconds,
            "token_count": self.token_count,
            "error_message": self.error_message,
            "metadata": self.summary_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_by": self.created_by,
        }

    def is_completed(self) -> bool:
        """Check if summary is completed"""
        return self.status == SummaryStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if summary failed"""
        return self.status == SummaryStatus.FAILED

    def has_quality_issues(self) -> bool:
        """Check if summary has quality issues"""
        return self.has_hallucination_flag or (self.confidence_score and self.confidence_score < 70)
