from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base


class ExtractionTemplate(Base):
    """PDF parsing templates for document types"""
    
    __tablename__ = "extraction_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(100), unique=True, nullable=False)
    document_type = Column(String(50), nullable=False)
    
    # Template definition
    template_structure = Column(JSONB)  # JSON defining expected structure
    keywords = Column(ARRAY(Text))  # Keywords for document classification
    extraction_rules = Column(JSONB)  # Rules for extracting specific fields
    
    # Status
    is_default = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

