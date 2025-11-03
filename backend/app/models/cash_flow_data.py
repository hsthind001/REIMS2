from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class CashFlowData(Base):
    """Monthly cash flow statement line items"""
    
    __tablename__ = "cash_flow_data"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'))
    account_id = Column(Integer, ForeignKey('chart_of_accounts.id'), nullable=False)
    
    # Account information
    account_code = Column(String(50), nullable=False)
    account_name = Column(String(255), nullable=False)
    
    # Financial data
    period_amount = Column(DECIMAL(15, 2), nullable=False)
    ytd_amount = Column(DECIMAL(15, 2))
    period_percentage = Column(DECIMAL(5, 2))
    ytd_percentage = Column(DECIMAL(5, 2))
    
    # Cash flow classification
    cash_flow_category = Column(String(50), index=True)  # operating, investing, financing
    is_inflow = Column(Boolean)  # TRUE for cash in, FALSE for cash out
    
    # Calculation
    is_calculated = Column(Boolean, default=False)
    parent_account_code = Column(String(50))
    
    # Extraction quality
    extraction_confidence = Column(DECIMAL(5, 2))
    
    # Review workflow
    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    reviewed_at = Column(DateTime(timezone=True))
    review_notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', 'account_code', name='uq_cf_property_period_account'),
    )
    
    # Relationships
    property = relationship("Property", back_populates="cash_flow_data")
    period = relationship("FinancialPeriod", back_populates="cash_flow_data")
    upload = relationship("DocumentUpload", back_populates="cash_flow_data")
    account = relationship("ChartOfAccounts", back_populates="cash_flow_entries")

