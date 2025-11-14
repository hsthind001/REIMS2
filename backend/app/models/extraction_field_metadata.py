from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base


class ExtractionFieldMetadata(Base):
    """
    Stores field-level confidence scores and metadata for all extracted data.
    Enables quality tracking, conflict detection, and targeted review workflows.
    """
    
    __tablename__ = "extraction_field_metadata"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Field Identification
    document_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='CASCADE'), nullable=False, index=True)
    table_name = Column(String(100), nullable=False, index=True)
    record_id = Column(Integer, nullable=False)
    field_name = Column(String(100), nullable=False, index=True)
    
    # Confidence and Provenance
    confidence_score = Column(Numeric(5, 4), nullable=False, index=True)  # 0.0000 to 1.0000
    extraction_engine = Column(String(50), nullable=False)  # pymupdf, pdfplumber, camelot, etc.
    
    # Conflict Resolution
    conflicting_values = Column(JSONB, nullable=True)  # Store conflicting values from different engines
    resolution_method = Column(String(50), nullable=True)  # consensus, weighted_vote, ai_override, human_review
    
    # Quality Flags
    needs_review = Column(Boolean, default=False, index=True)
    review_priority = Column(String(20), nullable=True)  # critical, high, medium, low
    flagged_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Reviewer
    reviewed_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    document = relationship("DocumentUpload", back_populates="field_metadata")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    corrections = relationship("ExtractionCorrection", back_populates="field_metadata", cascade="all, delete-orphan")
    
    # Helper Methods
    @property
    def is_high_confidence(self) -> bool:
        """Check if confidence score is above 95%"""
        return float(self.confidence_score) >= 0.95
    
    @property
    def is_low_confidence(self) -> bool:
        """Check if confidence score is below 70%"""
        return float(self.confidence_score) < 0.70
    
    @property
    def has_conflicts(self) -> bool:
        """Check if there are conflicting values from multiple engines"""
        return self.conflicting_values is not None and len(self.conflicting_values) > 0
    
    @classmethod
    def get_low_confidence_fields(cls, db_session, document_id: int, threshold: float = 0.70):
        """
        Retrieve all fields with confidence below threshold for a document.
        
        Args:
            db_session: SQLAlchemy session
            document_id: Document ID to query
            threshold: Confidence threshold (default: 0.70)
            
        Returns:
            Query object with low confidence fields
        """
        return db_session.query(cls).filter(
            cls.document_id == document_id,
            cls.confidence_score < threshold
        ).order_by(cls.confidence_score.asc())
    
    @classmethod
    def get_fields_needing_review(cls, db_session, document_id: int = None):
        """
        Retrieve all fields flagged for review.
        
        Args:
            db_session: SQLAlchemy session
            document_id: Optional document ID to filter by
            
        Returns:
            Query object with fields needing review
        """
        query = db_session.query(cls).filter(cls.needs_review == True)
        
        if document_id:
            query = query.filter(cls.document_id == document_id)
            
        return query.order_by(
            cls.review_priority.desc(),
            cls.confidence_score.asc()
        )
    
    @classmethod
    def get_conflicting_fields(cls, db_session, document_id: int):
        """
        Retrieve all fields with conflicting values from multiple engines.
        
        Args:
            db_session: SQLAlchemy session
            document_id: Document ID to query
            
        Returns:
            Query object with conflicting fields
        """
        return db_session.query(cls).filter(
            cls.document_id == document_id,
            cls.conflicting_values.isnot(None)
        ).order_by(cls.field_name)
    
    def __repr__(self):
        return f"<ExtractionFieldMetadata(id={self.id}, document_id={self.document_id}, field='{self.field_name}', confidence={self.confidence_score})>"

