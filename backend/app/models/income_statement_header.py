from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class IncomeStatementHeader(Base):
    """
    Income Statement header metadata
    
    Stores summary-level information for each income statement including:
    - Property and period identification
    - Report metadata (dates, accounting basis)
    - Key financial totals (Income, Expenses, NOI, Net Income)
    - Extraction quality metrics
    """
    
    __tablename__ = "income_statement_headers"

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
    period_type = Column(String(20))  # Monthly, Annual, Quarterly
    accounting_basis = Column(String(50), nullable=False)  # Accrual, Cash
    report_generation_date = Column(Date)
    
    # Income Section Totals
    total_income = Column(DECIMAL(15, 2), nullable=False)
    base_rentals = Column(DECIMAL(15, 2))
    total_recovery_income = Column(DECIMAL(15, 2))
    total_other_income = Column(DECIMAL(15, 2))
    total_revenue = Column(DECIMAL(15, 2))
    gross_potential_income = Column(DECIMAL(15, 2))
    effective_gross_income = Column(DECIMAL(15, 2))
    
    # Operating Expense Section Totals
    total_expenses = Column(DECIMAL(15, 2), nullable=False)
    total_operating_expenses = Column(DECIMAL(15, 2))
    total_property_expenses = Column(DECIMAL(15, 2))
    total_utility_expenses = Column(DECIMAL(15, 2))
    total_contracted_expenses = Column(DECIMAL(15, 2))
    total_rm_expenses = Column(DECIMAL(15, 2))
    total_admin_expenses = Column(DECIMAL(15, 2))
    
    # Additional Expense Totals
    total_additional_operating_expenses = Column(DECIMAL(15, 2))
    total_management_fees = Column(DECIMAL(15, 2))
    total_leasing_costs = Column(DECIMAL(15, 2))
    total_ll_expenses = Column(DECIMAL(15, 2))
    
    # Performance Metrics
    net_operating_income = Column(DECIMAL(15, 2), nullable=False)  # NOI
    noi_percentage = Column(DECIMAL(5, 2))  # NOI / Total Income * 100
    
    # Other Income/Expenses (below the line)
    mortgage_interest = Column(DECIMAL(15, 2))
    depreciation = Column(DECIMAL(15, 2))
    amortization = Column(DECIMAL(15, 2))
    total_other_income_expense = Column(DECIMAL(15, 2))
    
    # Net Income
    net_income = Column(DECIMAL(15, 2), nullable=False)
    net_income_percentage = Column(DECIMAL(5, 2))  # Net Income / Total Income * 100
    
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
    property = relationship("Property", back_populates="income_statement_headers")
    period = relationship("FinancialPeriod", back_populates="income_statement_headers")
    upload = relationship("DocumentUpload", back_populates="income_statement_header")
    line_items = relationship("IncomeStatementData", back_populates="header", cascade="all, delete-orphan")

