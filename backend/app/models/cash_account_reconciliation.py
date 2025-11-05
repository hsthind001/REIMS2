from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class CashAccountReconciliation(Base):
    """
    Cash Account Reconciliation
    
    Tracks cash account movements and validates that cash flow equals
    the change in cash balances. Each cash account (Operating, Escrow, etc.)
    has beginning and ending balances with the difference.
    
    Business Rule: Sum of all differences must equal Cash Flow
    """
    
    __tablename__ = "cash_account_reconciliations"

    id = Column(Integer, primary_key=True, index=True)
    header_id = Column(Integer, ForeignKey('cash_flow_headers.id', ondelete='CASCADE'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'))
    
    # Account Information
    account_name = Column(String(255), nullable=False)  # "Cash - Operating", "Cash - Operating IV-PNC", etc.
    account_type = Column(String(50), nullable=False, index=True)  # operating, escrow, other
    account_code = Column(String(50))  # Account code if available
    
    # Cash Balances
    beginning_balance = Column(DECIMAL(15, 2), nullable=False)
    ending_balance = Column(DECIMAL(15, 2), nullable=False)
    difference = Column(DECIMAL(15, 2), nullable=False)  # ending_balance - beginning_balance
    
    # Validation
    difference_calculated = Column(DECIMAL(15, 2))  # System-calculated difference for validation
    difference_matches = Column(Boolean, default=True)  # TRUE if difference = ending - beginning
    
    # Special Flags
    is_negative_balance = Column(Boolean, default=False)  # Flag overdraft situations
    is_escrow_account = Column(Boolean, default=False)  # TRUE for escrow accounts
    is_total_row = Column(Boolean, default=False)  # TRUE for "Total Cash" summary row
    
    # Line positioning
    line_number = Column(Integer)  # Sequential line number in reconciliation section
    
    # Extraction quality
    extraction_confidence = Column(DECIMAL(5, 2))
    
    # Review workflow
    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    reviewed_at = Column(DateTime(timezone=True))
    review_notes = Column(Text)
    
    # Metadata
    page_number = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    header = relationship("CashFlowHeader", back_populates="cash_accounts")
    property = relationship("Property", back_populates="cash_account_reconciliations")
    period = relationship("FinancialPeriod", back_populates="cash_account_reconciliations")
    upload = relationship("DocumentUpload", back_populates="cash_account_reconciliations")

