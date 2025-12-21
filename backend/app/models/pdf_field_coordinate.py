"""
PDF Field Coordinate Model

Stores coordinate information for PDF fields to enable highlighting in PDF viewer.
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class PDFFieldCoordinate(Base):
    """
    Store coordinate information for PDF fields.
    
    Enables accurate highlighting of anomaly fields in PDF viewer
    even when auto-extraction fails.
    """
    
    __tablename__ = "pdf_field_coordinates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Document & Field Reference
    document_upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='CASCADE'), nullable=False, index=True)
    table_name = Column(String(50), nullable=False, index=True)  # balance_sheet, income_statement, etc.
    record_id = Column(Integer, nullable=False, index=True)  # Record ID within the table
    field_name = Column(String(100), nullable=False, index=True)  # Field name (account code, etc.)
    column_type = Column(String(20), nullable=True)  # period_amount, ytd_amount, etc.
    
    # Coordinate Information
    page_number = Column(Integer, nullable=False, index=True)
    x0 = Column(Numeric(10, 4), nullable=False)  # Left coordinate
    y0 = Column(Numeric(10, 4), nullable=False)  # Top coordinate
    x1 = Column(Numeric(10, 4), nullable=False)  # Right coordinate
    y1 = Column(Numeric(10, 4), nullable=False)  # Bottom coordinate
    
    # Extraction Method
    extraction_method = Column(String(50), nullable=False)  # 'pdfplumber', 'layoutlm', 'manual', etc.
    confidence = Column(Numeric(5, 4), nullable=True)  # Confidence in coordinate accuracy (0-1)
    
    # Matched Text
    matched_text = Column(String(500), nullable=True)  # Text that was matched to this coordinate
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    document = relationship("DocumentUpload", backref="field_coordinates")
    
    def __repr__(self):
        return f"<PDFFieldCoordinate(id={self.id}, field_name='{self.field_name}', page={self.page_number}, method='{self.extraction_method}')>"

