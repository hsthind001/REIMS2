from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class CashFlowHeader(Base):
    """
    Cash Flow Statement header metadata
    
    Stores summary-level information for each cash flow statement including:
    - Property and period identification
    - Report metadata (dates, accounting basis)
    - Key financial totals (Income, Expenses, NOI, Net Income, Cash Flow)
    - Extraction quality metrics
    """
    
    __tablename__ = "cash_flow_headers"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'))
    
    # Property Identification
    property_name = Column(String(255), nullable=False)
    property_code = Column(String(50), nullable=False)
    
    # Period Information
    report_period_start = Column(Date, nullable=False)
    report_period_end = Column(Date, nullable=False)
    accounting_basis = Column(String(50), nullable=False)  # Accrual, Cash
    report_generation_date = Column(Date)
    
    # Income Section Totals
    total_income = Column(DECIMAL(15, 2), nullable=False)
    base_rentals = Column(DECIMAL(15, 2))
    total_recovery_income = Column(DECIMAL(15, 2))
    total_other_income = Column(DECIMAL(15, 2))
    
    # Expense Section Totals
    total_operating_expenses = Column(DECIMAL(15, 2), nullable=False)
    total_property_expenses = Column(DECIMAL(15, 2))
    total_utility_expenses = Column(DECIMAL(15, 2))
    total_contracted_expenses = Column(DECIMAL(15, 2))
    total_rm_expenses = Column(DECIMAL(15, 2))
    total_admin_expenses = Column(DECIMAL(15, 2))
    
    # Additional Expenses
    total_additional_operating_expenses = Column(DECIMAL(15, 2))
    total_management_fees = Column(DECIMAL(15, 2))
    total_ll_expenses = Column(DECIMAL(15, 2))
    
    # Total Expenses
    total_expenses = Column(DECIMAL(15, 2), nullable=False)
    
    # Performance Metrics
    net_operating_income = Column(DECIMAL(15, 2), nullable=False)  # NOI
    noi_percentage = Column(DECIMAL(5, 2))  # NOI / Total Income * 100
    
    # Other Income/Expenses
    mortgage_interest = Column(DECIMAL(15, 2))
    depreciation = Column(DECIMAL(15, 2))
    amortization = Column(DECIMAL(15, 2))
    total_other_income_expense = Column(DECIMAL(15, 2))
    
    # Net Income
    net_income = Column(DECIMAL(15, 2), nullable=False)
    net_income_percentage = Column(DECIMAL(5, 2))  # Net Income / Total Income * 100
    
    # Adjustments
    total_adjustments = Column(DECIMAL(15, 2))
    
    # Cash Flow
    cash_flow = Column(DECIMAL(15, 2), nullable=False)
    cash_flow_percentage = Column(DECIMAL(5, 2))  # Cash Flow / Total Income * 100
    
    # Cash Account Summary
    beginning_cash_balance = Column(DECIMAL(15, 2))
    ending_cash_balance = Column(DECIMAL(15, 2))
    cash_difference = Column(DECIMAL(15, 2))
    
    # Extraction quality
    extraction_confidence = Column(DECIMAL(5, 2))
    validation_passed = Column(Boolean, default=False)
    
    # Review workflow
    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    reviewed_at = Column(DateTime(timezone=True))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    property = relationship("Property", back_populates="cash_flow_headers")
    period = relationship("FinancialPeriod", back_populates="cash_flow_headers")
    upload = relationship("DocumentUpload", back_populates="cash_flow_header")
    line_items = relationship("CashFlowData", back_populates="header", cascade="all, delete-orphan")
    adjustments = relationship("CashFlowAdjustment", back_populates="header", cascade="all, delete-orphan")
    cash_accounts = relationship("CashAccountReconciliation", back_populates="header", cascade="all, delete-orphan")

