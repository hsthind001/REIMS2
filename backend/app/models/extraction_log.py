from sqlalchemy import Column, Integer, String, Float, JSON, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class ExtractionLog(Base):
    """Track PDF extraction quality and results (E2-S3: org-scoped)"""
    
    __tablename__ = "extraction_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # File information
    filename = Column(String, nullable=False)
    file_size = Column(Integer)
    file_hash = Column(String, index=True)  # MD5 or SHA256 hash
    
    # Document classification
    document_type = Column(String)  # digital, scanned, mixed, etc.
    total_pages = Column(Integer)
    
    # Extraction details
    strategy_used = Column(String)  # auto, fast, accurate, multi_engine
    engines_used = Column(JSON)  # List of engines used
    primary_engine = Column(String)
    
    # Quality metrics
    confidence_score = Column(Float)  # 0-100
    quality_level = Column(String)  # excellent, good, acceptable, poor, failed
    passed_checks = Column(Integer)
    total_checks = Column(Integer)
    
    # Processing details
    processing_time_seconds = Column(Float)
    extraction_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Validation results
    validation_issues = Column(JSON)  # List of issues found
    validation_warnings = Column(JSON)  # List of warnings
    recommendations = Column(JSON)  # List of recommendations
    
    # Extracted content (optional - can be large)
    extracted_text = Column(Text, nullable=True)  # Store if needed
    text_preview = Column(String(500))  # First 500 chars
    total_words = Column(Integer)
    total_chars = Column(Integer)
    
    # Table extraction
    tables_found = Column(Integer, default=0)
    images_found = Column(Integer, default=0)
    
    # Review status
    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Additional metadata
    custom_metadata = Column(JSON)  # Additional custom metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

