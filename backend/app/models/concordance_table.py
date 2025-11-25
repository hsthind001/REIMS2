"""
Concordance Table Model

Stores field-by-field comparison of extraction results across all models
for each document upload. Automatically updated on document extraction.
"""
from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ConcordanceTable(Base):
    """
    Concordance table for comparing extraction results across models
    
    Stores field-by-field values from each model and calculates agreement
    """
    __tablename__ = "concordance_tables"
    
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='CASCADE'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)  # balance_sheet, income_statement, etc.
    
    # Field identification
    field_name = Column(String(255), nullable=False)  # e.g., "account_4010", "total_revenue"
    field_display_name = Column(String(255))  # e.g., "Base Rentals", "Total Revenue"
    account_code = Column(String(50), index=True)  # If applicable
    
    # Values from each model (stored as JSON for flexibility)
    model_values = Column(JSON, nullable=False)  # {"pymupdf": "$215,671.29", "pdfplumber": "$215,671.29", ...}
    
    # Normalized value for comparison
    normalized_value = Column(String(255))  # "215671.29"
    
    # Agreement metrics
    agreement_count = Column(Integer, default=0)  # Number of models that agree
    total_models = Column(Integer, default=0)  # Total models that extracted this field
    agreement_percentage = Column(DECIMAL(5, 2), default=0.0)  # 0-100
    
    # Consensus flags
    has_consensus = Column(Boolean, default=False)  # True if agreement >= 75%
    is_perfect_agreement = Column(Boolean, default=False)  # True if 100% agreement
    conflicting_models = Column(JSON)  # List of model names that disagree
    
    # Best value (from ensemble voting)
    final_value = Column(String(255))  # Final agreed-upon value
    final_model = Column(String(50))  # Model that provided final value (or "ensemble")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_concordance_upload_field', 'upload_id', 'field_name'),
        Index('ix_concordance_agreement', 'has_consensus', 'agreement_percentage'),
    )
    
    # Relationships
    upload = relationship("DocumentUpload", back_populates="concordance_records")
    property = relationship("Property")
    period = relationship("FinancialPeriod")

