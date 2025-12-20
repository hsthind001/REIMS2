from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base


class MortgageStatementData(Base):
    """Mortgage statement data - stores extracted mortgage statement information"""
    
    __tablename__ = "mortgage_statement_data"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'), nullable=True)
    lender_id = Column(Integer, ForeignKey('lenders.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Loan Identification
    loan_number = Column(String(50), nullable=False)
    loan_type = Column(String(50), nullable=True)  # 'first_mortgage', 'mezzanine', 'line_of_credit'
    property_address = Column(Text, nullable=True)
    borrower_name = Column(String(255), nullable=True)
    
    # Statement Metadata
    statement_date = Column(Date, nullable=False, index=True)
    payment_due_date = Column(Date, nullable=True)
    statement_period_start = Column(Date, nullable=True)
    statement_period_end = Column(Date, nullable=True)
    
    # Current Balances (as of statement date)
    principal_balance = Column(DECIMAL(15, 2), nullable=False)
    tax_escrow_balance = Column(DECIMAL(15, 2), server_default='0')
    insurance_escrow_balance = Column(DECIMAL(15, 2), server_default='0')
    reserve_balance = Column(DECIMAL(15, 2), server_default='0')
    other_escrow_balance = Column(DECIMAL(15, 2), server_default='0')
    suspense_balance = Column(DECIMAL(15, 2), server_default='0')
    total_loan_balance = Column(DECIMAL(15, 2), nullable=True)  # Calculated: principal + all escrows
    
    # Current Period Payment Breakdown
    principal_due = Column(DECIMAL(12, 2), nullable=True)
    interest_due = Column(DECIMAL(12, 2), nullable=True)
    tax_escrow_due = Column(DECIMAL(12, 2), nullable=True)
    insurance_escrow_due = Column(DECIMAL(12, 2), nullable=True)
    reserve_due = Column(DECIMAL(12, 2), nullable=True)
    late_fees = Column(DECIMAL(10, 2), server_default='0')
    other_fees = Column(DECIMAL(10, 2), server_default='0')
    total_payment_due = Column(DECIMAL(12, 2), nullable=True)
    
    # Year-to-Date Totals
    ytd_principal_paid = Column(DECIMAL(15, 2), server_default='0')
    ytd_interest_paid = Column(DECIMAL(15, 2), server_default='0')
    ytd_taxes_disbursed = Column(DECIMAL(15, 2), server_default='0')
    ytd_insurance_disbursed = Column(DECIMAL(15, 2), server_default='0')
    ytd_reserve_disbursed = Column(DECIMAL(15, 2), server_default='0')
    ytd_total_paid = Column(DECIMAL(15, 2), nullable=True)  # Calculated: ytd_principal_paid + ytd_interest_paid
    
    # Loan Terms (from loan documents or statements)
    original_loan_amount = Column(DECIMAL(15, 2), nullable=True)
    interest_rate = Column(DECIMAL(6, 4), nullable=True)  # e.g., 5.25% stored as 5.2500
    loan_term_months = Column(Integer, nullable=True)
    maturity_date = Column(Date, nullable=True, index=True)
    origination_date = Column(Date, nullable=True)
    payment_frequency = Column(String(20), nullable=True)  # 'monthly', 'quarterly', 'annual'
    amortization_type = Column(String(50), nullable=True)  # 'fully_amortizing', 'interest_only', 'balloon'
    
    # Calculated Fields
    remaining_term_months = Column(Integer, nullable=True)  # Calculated from maturity_date and statement_date
    ltv_ratio = Column(DECIMAL(10, 4), nullable=True)  # To be calculated from property value
    annual_debt_service = Column(DECIMAL(15, 2), nullable=True)  # Annual P+I payments
    monthly_debt_service = Column(DECIMAL(12, 2), nullable=True)  # Monthly P+I payments
    
    # Extraction Quality
    extraction_confidence = Column(DECIMAL(5, 2), nullable=True)
    extraction_method = Column(String(50), nullable=True)
    extraction_coordinates = Column(JSONB, nullable=True)  # Store bounding boxes for all extracted fields
    
    # Review Workflow
    needs_review = Column(Boolean, default=False, index=True)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Validation
    validation_score = Column(DECIMAL(5, 2), nullable=True)
    has_errors = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', 'loan_number', name='uq_mortgage_property_period_loan'),
        Index('idx_mortgage_property_period', 'property_id', 'period_id'),
        Index('idx_mortgage_review', 'needs_review', 'property_id'),
    )
    
    # Relationships
    property = relationship("Property", back_populates="mortgage_statements")
    period = relationship("FinancialPeriod", back_populates="mortgage_statements")
    upload = relationship("DocumentUpload", back_populates="mortgage_statement_data")
    lender = relationship("Lender", back_populates="mortgage_statements")
    payment_history = relationship("MortgagePaymentHistory", back_populates="mortgage", cascade="all, delete-orphan")


