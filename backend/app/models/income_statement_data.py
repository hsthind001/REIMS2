from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class IncomeStatementData(Base):
    """Monthly income statement (P&L) line items"""
    
    __tablename__ = "income_statement_data"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'))
    account_id = Column(Integer, ForeignKey('chart_of_accounts.id'), nullable=True)  # Nullable for unmatched accounts
    
    # Account information
    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(255), nullable=False)
    
    # Financial data
    period_amount = Column(DECIMAL(15, 2), nullable=False)  # Period to Date
    ytd_amount = Column(DECIMAL(15, 2))  # Year to Date
    period_percentage = Column(DECIMAL(5, 2))  # % of revenue
    ytd_percentage = Column(DECIMAL(5, 2))
    
    # Classification
    is_income = Column(Boolean)  # TRUE for income, FALSE for expense
    
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
        UniqueConstraint('property_id', 'period_id', 'account_code', name='uq_is_property_period_account'),
    )
    
    # Relationships
    property = relationship("Property", back_populates="income_statement_data")
    period = relationship("FinancialPeriod", back_populates="income_statement_data")
    upload = relationship("DocumentUpload", back_populates="income_statement_data")
    account = relationship("ChartOfAccounts", back_populates="income_statement_entries")

