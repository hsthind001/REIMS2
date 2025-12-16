"""
Hallucination Review Queue Model

Stores flagged answers with unverified claims for manual review.
"""
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Boolean, JSON, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class HallucinationReview(Base):
    """
    Review queue for answers with unverified claims (potential hallucinations)
    
    Stores flagged answers for manual review by human reviewers.
    """
    __tablename__ = "hallucination_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    nlq_query_id = Column(Integer, ForeignKey("nlq_queries.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Answer information
    original_answer = Column(Text, nullable=False, comment="Original LLM-generated answer")
    original_confidence = Column(Numeric(5, 4), nullable=True, comment="Original confidence score")
    adjusted_confidence = Column(Numeric(5, 4), nullable=True, comment="Adjusted confidence after detection")
    
    # Detection results
    total_claims = Column(Integer, nullable=False, default=0, comment="Total numeric claims extracted")
    verified_claims = Column(Integer, nullable=False, default=0, comment="Number of verified claims")
    unverified_claims = Column(Integer, nullable=False, default=0, comment="Number of unverified claims")
    flagged_claims = Column(JSON, nullable=True, comment="List of flagged claims with details")
    
    # Review status
    status = Column(
        Text,
        nullable=False,
        default='pending',
        index=True,
        comment="Review status: pending, reviewed, approved, rejected"
    )
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="User who reviewed")
    reviewed_at = Column(DateTime(timezone=True), nullable=True, comment="Review timestamp")
    review_notes = Column(Text, nullable=True, comment="Reviewer notes")
    
    # Metadata
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True, index=True)
    period_id = Column(Integer, ForeignKey("financial_periods.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    nlq_query = relationship("NLQQuery", foreign_keys=[nlq_query_id])
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    property_obj = relationship("Property", foreign_keys=[property_id])
    
    def __repr__(self):
        return f"<HallucinationReview(id={self.id}, status={self.status}, unverified_claims={self.unverified_claims})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'nlq_query_id': self.nlq_query_id,
            'user_id': self.user_id,
            'original_answer': self.original_answer,
            'original_confidence': float(self.original_confidence) if self.original_confidence else None,
            'adjusted_confidence': float(self.adjusted_confidence) if self.adjusted_confidence else None,
            'total_claims': self.total_claims,
            'verified_claims': self.verified_claims,
            'unverified_claims': self.unverified_claims,
            'flagged_claims': self.flagged_claims,
            'status': self.status,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'review_notes': self.review_notes,
            'property_id': self.property_id,
            'period_id': self.period_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

