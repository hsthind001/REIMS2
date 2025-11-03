from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ValidationResult(Base):
    """Stores validation results for each upload"""
    
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='CASCADE'), nullable=False, index=True)
    rule_id = Column(Integer, ForeignKey('validation_rules.id'), nullable=False)
    
    # Result
    passed = Column(Boolean, nullable=False, index=True)
    
    # Values
    expected_value = Column(DECIMAL(15, 2))
    actual_value = Column(DECIMAL(15, 2))
    difference = Column(DECIMAL(15, 2))
    difference_percentage = Column(DECIMAL(10, 4))
    
    # Details
    error_message = Column(Text)
    severity = Column(String(20))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    upload = relationship("DocumentUpload", back_populates="validation_results")
    rule = relationship("ValidationRule", back_populates="validation_results")

