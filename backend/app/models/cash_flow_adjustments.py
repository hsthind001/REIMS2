from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class CashFlowAdjustment(Base):
    """
    Cash Flow Statement adjustments section
    
    Stores non-cash adjustments that reconcile Net Income to Cash Flow:
    - Accounts Receivable changes
    - Property & Equipment changes
    - Accumulated Depreciation changes
    - Escrow account changes
    - Loan & commission cost changes
    - Prepaid & accrued items
    - Accounts Payable changes
    - Inter-property transfers
    - Distributions
    """
    
    __tablename__ = "cash_flow_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    header_id = Column(Integer, ForeignKey('cash_flow_headers.id', ondelete='CASCADE'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'))
    
    # Adjustment Classification
    adjustment_category = Column(String(100), nullable=False, index=True)  
    # Categories: AR_CHANGES, PROPERTY_EQUIPMENT, ACCUMULATED_DEPRECIATION, ESCROW_ACCOUNTS,
    #             LOAN_COSTS, PREPAID_ACCRUED, ACCOUNTS_PAYABLE, INTER_PROPERTY, DISTRIBUTIONS, OTHER
    
    adjustment_name = Column(String(255), nullable=False)  # A/R Tenants, Escrow - Property Tax, Distribution, etc.
    adjustment_description = Column(Text)  # Additional details if needed
    
    # Financial Data
    amount = Column(DECIMAL(15, 2), nullable=False)  # Can be positive or negative
    is_increase = Column(Boolean)  # TRUE if increases cash, FALSE if decreases cash
    
    # Specific Adjustment Details
    account_code = Column(String(50))  # Related account code if applicable
    related_property = Column(String(100))  # For inter-property transfers (e.g., "Hammond Aire LP")
    related_entity = Column(String(255))  # For A/P to specific entities (e.g., "5Rivers CRE, LLC")
    
    # Line positioning
    line_number = Column(Integer)  # Sequential line number in adjustments section
    is_subtotal = Column(Boolean, default=False)  # For category subtotals
    
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
    header = relationship("CashFlowHeader", back_populates="adjustments")
    property = relationship("Property", back_populates="cash_flow_adjustments")
    period = relationship("FinancialPeriod", back_populates="cash_flow_adjustments")
    upload = relationship("DocumentUpload", back_populates="cash_flow_adjustments")

