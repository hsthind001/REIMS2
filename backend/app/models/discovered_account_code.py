"""
Discovered Account Code Model

Stores account codes discovered from financial data tables with metadata
for the self-learning forensic reconciliation system.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, DECIMAL, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class DiscoveredAccountCode(Base):
    """Account codes discovered from financial data tables"""
    
    __tablename__ = "discovered_account_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Account identification
    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(255), nullable=False, index=True)
    
    # Document type where this code was found
    document_type = Column(String(50), nullable=False, index=True)  # balance_sheet, income_statement, etc.
    
    # Source information
    source_table = Column(String(100), nullable=False)  # balance_sheet_data, income_statement_data, etc.
    source_record_id = Column(Integer, nullable=True)  # ID from source table
    
    # Frequency and distribution
    occurrence_count = Column(Integer, default=1)  # How many times this code appears
    property_count = Column(Integer, default=1)  # How many properties use this code
    period_count = Column(Integer, default=1)  # How many periods have this code
    
    # Account classification (inferred)
    account_type = Column(String(50))  # asset, liability, equity, income, expense
    category = Column(String(100))  # current_asset, long_term_liability, etc.
    subcategory = Column(String(100))
    
    # Pattern information
    code_pattern = Column(String(100))  # Regex pattern if applicable
    code_range_start = Column(String(50))  # Start of range if applicable
    code_range_end = Column(String(50))  # End of range if applicable
    
    # Confidence and validation
    confidence_score = Column(DECIMAL(5, 2), default=100.0)  # Confidence in classification
    is_validated = Column(Boolean, default=False)  # Has been manually validated
    validated_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_discovered_code_doc_type', 'account_code', 'document_type'),
        Index('idx_discovered_code_pattern', 'code_pattern'),
    )

