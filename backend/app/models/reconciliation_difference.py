from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ReconciliationDifference(Base):
    """Store detected differences between PDF and database"""
    
    __tablename__ = "reconciliation_differences"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('reconciliation_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Account information
    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(255))
    
    # Field that differs
    field_name = Column(String(100))  # amount, account_name, etc.
    
    # Values
    pdf_value = Column(DECIMAL(15, 2))
    db_value = Column(DECIMAL(15, 2))
    difference = Column(DECIMAL(15, 2))  # Absolute difference
    difference_percent = Column(DECIMAL(5, 2))  # Percentage difference
    
    # Difference categorization
    difference_type = Column(String(50), index=True)  # exact, tolerance, mismatch, missing_pdf, missing_db
    
    # Status and resolution
    status = Column(String(50), default='pending', index=True)  # pending, resolved, ignored
    resolved_by = Column(Integer, ForeignKey('users.id'))
    resolved_at = Column(DateTime(timezone=True))
    
    # Confidence and flags
    confidence_score = Column(DECIMAL(5, 2))
    needs_review = Column(Boolean, default=False)
    flags = Column(Text)  # Comma-separated flags
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ReconciliationSession", back_populates="differences")
    resolver = relationship("User", foreign_keys=[resolved_by])
    resolutions = relationship("ReconciliationResolution", back_populates="difference", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ReconciliationDifference {self.id}: {self.account_code} - {self.difference_type}>"

