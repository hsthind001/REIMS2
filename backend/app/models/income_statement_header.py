"""
Income Statement Header Model - Template v1.0 Compliant

Stores summary-level information for each income statement including:
- Property and period identification
- Report metadata (dates, accounting basis, period type)
- Key financial totals (Income, Expenses, NOI, Net Income)
- Extraction quality metrics
"""
from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class IncomeStatementHeader(Base):
    """
    Income Statement header metadata with comprehensive summary metrics
    
    Template v1.0 compliant with all summary totals and categorized subtotals
    """
    
    __tablename__ = "income_statement_headers"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'))
    
    # ==================== PROPERTY IDENTIFICATION ====================
    property_name = Column(String(255), nullable=False)
    property_code = Column(String(50), nullable=False)
    
    # ==================== PERIOD INFORMATION ====================
    report_period_start = Column(Date, nullable=False)
    report_period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)  # "Monthly", "Annual", "Quarterly"
    accounting_basis = Column(String(50), nullable=False)  # "Accrual", "Cash"
    report_generation_date = Column(Date)
    
    # ==================== INCOME SECTION TOTALS ====================
    total_income = Column(DECIMAL(15, 2), nullable=False)
    base_rentals = Column(DECIMAL(15, 2))  # 4010-0000
    total_recovery_income = Column(DECIMAL(15, 2))  # Tax + Insurance + CAM reimbursements
    total_other_income = Column(DECIMAL(15, 2))  # Interest, fees, misc
    
    # ==================== OPERATING EXPENSES TOTALS ====================
    total_operating_expenses = Column(DECIMAL(15, 2), nullable=False)  # 5990-0000
    
    # Operating Expense Subtotals
    total_property_expenses = Column(DECIMAL(15, 2))  # Property Tax + Insurance
    total_utility_expenses = Column(DECIMAL(15, 2))  # 5199-0000 subtotal
    total_contracted_expenses = Column(DECIMAL(15, 2))  # 5299-0000 subtotal
    total_rm_expenses = Column(DECIMAL(15, 2))  # 5399-0000 R&M subtotal
    total_admin_expenses = Column(DECIMAL(15, 2))  # 5499-0000 Admin subtotal
    
    # ==================== ADDITIONAL OPERATING EXPENSES ====================
    total_additional_operating_expenses = Column(DECIMAL(15, 2))  # 6190-0000
    total_management_fees = Column(DECIMAL(15, 2))  # Off-site + On-site + Professional
    total_leasing_costs = Column(DECIMAL(15, 2))  # Commissions + TI
    total_ll_expenses = Column(DECIMAL(15, 2))  # 6069-0000 Landlord expenses subtotal
    
    # ==================== TOTAL EXPENSES ====================
    total_expenses = Column(DECIMAL(15, 2), nullable=False)  # 6199-0000
    
    # ==================== NET OPERATING INCOME (NOI) ====================
    net_operating_income = Column(DECIMAL(15, 2), nullable=False)  # 6299-0000
    noi_percentage = Column(DECIMAL(5, 2))  # (NOI / Total Income) * 100
    
    # ==================== OTHER INCOME/EXPENSES (BELOW THE LINE) ====================
    mortgage_interest = Column(DECIMAL(15, 2))  # 7010-0000
    depreciation = Column(DECIMAL(15, 2))  # 7020-0000
    amortization = Column(DECIMAL(15, 2))  # 7030-0000
    total_other_income_expense = Column(DECIMAL(15, 2))  # 7090-0000
    
    # ==================== NET INCOME (BOTTOM LINE) ====================
    net_income = Column(DECIMAL(15, 2), nullable=False)  # 9090-0000
    net_income_percentage = Column(DECIMAL(5, 2))  # (Net Income / Total Income) * 100
    
    # ==================== EXTRACTION QUALITY ====================
    extraction_confidence = Column(DECIMAL(5, 2))  # 0-100 overall confidence
    validation_passed = Column(Boolean, default=False)  # All critical validations passed
    
    # ==================== REVIEW WORKFLOW ====================
    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    reviewed_at = Column(DateTime(timezone=True))
    
    # ==================== METADATA ====================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # ==================== RELATIONSHIPS ====================
    property = relationship("Property", back_populates="income_statement_headers")
    period = relationship("FinancialPeriod", back_populates="income_statement_headers")
    upload = relationship("DocumentUpload", back_populates="income_statement_header")
    line_items = relationship("IncomeStatementData", back_populates="header", cascade="all, delete-orphan")
