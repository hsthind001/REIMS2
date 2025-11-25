from sqlalchemy import Column, Integer, String, BigInteger, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class DocumentUpload(Base):
    """Tracks all uploaded financial PDFs"""
    
    __tablename__ = "document_uploads"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Document type
    document_type = Column(String(50), nullable=False, index=True)  # balance_sheet, income_statement, cash_flow, rent_roll
    
    # File information
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500))  # S3/MinIO path
    file_hash = Column(String(64))  # MD5/SHA256 for deduplication
    file_size_bytes = Column(BigInteger)
    
    # Upload tracking
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_by = Column(Integer, ForeignKey('users.id'))
    
    # Extraction status
    extraction_status = Column(String(50), default='pending', index=True)  # pending, processing, completed, failed
    extraction_started_at = Column(DateTime(timezone=True))
    extraction_completed_at = Column(DateTime(timezone=True))
    extraction_id = Column(Integer, ForeignKey('extraction_logs.id'))  # Link to extraction quality tracking
    
    # Versioning
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)  # Latest version
    
    # Notes
    notes = Column(Text)
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', 'document_type', 'version', name='uq_property_period_doctype_version'),
    )
    
    # Relationships
    property = relationship("Property", back_populates="document_uploads")
    period = relationship("FinancialPeriod", back_populates="document_uploads")
    extraction_log = relationship("ExtractionLog", foreign_keys=[extraction_id])
    field_metadata = relationship("ExtractionFieldMetadata", back_populates="document", cascade="all, delete-orphan")
    balance_sheet_data = relationship("BalanceSheetData", back_populates="upload", cascade="all, delete-orphan")
    income_statement_data = relationship("IncomeStatementData", back_populates="upload", cascade="all, delete-orphan")
    income_statement_header = relationship("IncomeStatementHeader", back_populates="upload", uselist=False, cascade="all, delete-orphan")
    cash_flow_header = relationship("CashFlowHeader", back_populates="upload", uselist=False, cascade="all, delete-orphan")
    income_statement_header = relationship("IncomeStatementHeader", back_populates="upload", uselist=False, cascade="all, delete-orphan")
    cash_flow_data = relationship("CashFlowData", back_populates="upload", cascade="all, delete-orphan")
    cash_flow_adjustments = relationship("CashFlowAdjustment", back_populates="upload", cascade="all, delete-orphan")
    cash_account_reconciliations = relationship("CashAccountReconciliation", back_populates="upload", cascade="all, delete-orphan")
    rent_roll_data = relationship("RentRollData", back_populates="upload", cascade="all, delete-orphan")
    validation_results = relationship("ValidationResult", back_populates="upload", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    concordance_records = relationship("ConcordanceTable", back_populates="upload", cascade="all, delete-orphan")

