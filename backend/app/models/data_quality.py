"""
Data Quality Model

Tracks data quality scores for documents and periods, aggregating
extraction confidence, validation rates, unmatched accounts, and manual corrections.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class DataQualityScore(Base):
    """
    Store data quality scores for documents and periods.
    
    Aggregates:
    - Extraction confidence
    - Validation pass rates
    - Unmatched accounts
    - Manual corrections
    """
    
    __tablename__ = "data_quality_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # References
    document_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Quality Index (0-100)
    quality_index = Column(Numeric(5, 2), nullable=False, index=True)  # Overall quality score 0-100
    
    # Component Scores (0-100 each)
    completeness = Column(Numeric(5, 2), nullable=True)  # Completeness score
    consistency = Column(Numeric(5, 2), nullable=True)  # Consistency score
    timeliness = Column(Numeric(5, 2), nullable=True)  # Timeliness score
    validity = Column(Numeric(5, 2), nullable=True)  # Validity score
    
    # Extraction Metrics
    extraction_confidence_avg = Column(Numeric(5, 4), nullable=True)  # Average extraction confidence (0-1)
    match_confidence_avg = Column(Numeric(5, 4), nullable=True)  # Average match confidence (0-1)
    
    # Quality Indicators
    unmatched_accounts_count = Column(Integer, nullable=False, default=0)  # Count of unmatched accounts
    manual_corrections_count = Column(Integer, nullable=False, default=0)  # Count of manual corrections
    
    # Metadata
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    document = relationship("DocumentUpload", backref="data_quality_scores")
    period = relationship("FinancialPeriod", backref="data_quality_scores")
    property = relationship("Property", backref="data_quality_scores")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quality_index >= 0 AND quality_index <= 100', name='check_quality_index_range'),
        CheckConstraint('completeness >= 0 AND completeness <= 100', name='check_completeness_range'),
        CheckConstraint('consistency >= 0 AND consistency <= 100', name='check_consistency_range'),
        CheckConstraint('timeliness >= 0 AND timeliness <= 100', name='check_timeliness_range'),
        CheckConstraint('validity >= 0 AND validity <= 100', name='check_validity_range'),
        CheckConstraint('extraction_confidence_avg >= 0 AND extraction_confidence_avg <= 1', name='check_extraction_confidence_range'),
        CheckConstraint('match_confidence_avg >= 0 AND match_confidence_avg <= 1', name='check_match_confidence_range'),
    )
    
    def __repr__(self):
        return f"<DataQualityScore(id={self.id}, document_id={self.document_id}, quality_index={self.quality_index})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "period_id": self.period_id,
            "property_id": self.property_id,
            "quality_index": float(self.quality_index) if self.quality_index else None,
            "completeness": float(self.completeness) if self.completeness else None,
            "consistency": float(self.consistency) if self.consistency else None,
            "timeliness": float(self.timeliness) if self.timeliness else None,
            "validity": float(self.validity) if self.validity else None,
            "extraction_confidence_avg": float(self.extraction_confidence_avg) if self.extraction_confidence_avg else None,
            "match_confidence_avg": float(self.match_confidence_avg) if self.match_confidence_avg else None,
            "unmatched_accounts_count": self.unmatched_accounts_count,
            "manual_corrections_count": self.manual_corrections_count,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
