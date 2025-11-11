from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class IncomeStatementData(Base):
    """Monthly income statement (P&L) line items - Template v1.0 compliant"""
    
    __tablename__ = "income_statement_data"

    id = Column(Integer, primary_key=True, index=True)
    header_id = Column(Integer, ForeignKey('income_statement_headers.id', ondelete='CASCADE'), nullable=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'))
    header_id = Column(Integer, ForeignKey('income_statement_headers.id', ondelete='CASCADE'))
    account_id = Column(Integer, ForeignKey('chart_of_accounts.id'), nullable=True)  # Nullable for unmatched accounts
    
    # ==================== HEADER METADATA (Template v1.0) ====================
    period_type = Column(String(20))  # "Monthly", "Annual", "Quarterly"
    period_start_date = Column(String(50))  # "Dec 2023" or "01/01/2024"
    period_end_date = Column(String(50))  # "Dec 2023" or "12/31/2024"
    accounting_basis = Column(String(20))  # "Accrual" or "Cash"
    report_generation_date = Column(DateTime(timezone=True))  # Date report was generated
    page_number = Column(Integer)  # Page number for multi-page documents
    
    # ==================== ACCOUNT INFORMATION ====================
    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(255), nullable=False)
    
    # ==================== HIERARCHICAL STRUCTURE (Template v1.0) ====================
    is_subtotal = Column(Boolean, default=False, index=True)  # e.g., "Total Utility Expense"
    is_total = Column(Boolean, default=False, index=True)  # e.g., "TOTAL INCOME", "NOI"
    line_category = Column(String(100))  # "INCOME", "OPERATING_EXPENSE", "ADDITIONAL_EXPENSE", "OTHER_EXPENSE", "SUMMARY"
    line_subcategory = Column(String(100))  # "Utility", "Contracted", "R&M", "Administration", etc.
    line_number = Column(Integer)  # Order in statement for proper display
    account_level = Column(Integer)  # 1-4: hierarchy depth
    
    # ==================== FINANCIAL DATA ====================
    period_amount = Column(DECIMAL(15, 2), nullable=False)  # Period to Date
    ytd_amount = Column(DECIMAL(15, 2))  # Year to Date
    period_percentage = Column(DECIMAL(5, 2))  # % of revenue
    ytd_percentage = Column(DECIMAL(5, 2))
    
    # ==================== CLASSIFICATION (Enhanced) ====================
    is_income = Column(Boolean)  # TRUE for income, FALSE for expense
    is_below_the_line = Column(Boolean, default=False)  # TRUE for depreciation, amortization, mortgage interest
    
    # ==================== CALCULATION ====================
    is_calculated = Column(Boolean, default=False)
    parent_account_code = Column(String(50))
    
    # ==================== EXTRACTION QUALITY (Template v1.0) ====================
    extraction_confidence = Column(DECIMAL(5, 2))  # 0-100 from PDF extraction
    match_confidence = Column(DECIMAL(5, 2))  # 0-100 from account matching
    extraction_method = Column(String(50))  # "table", "text", "template"
    
    # Review workflow
    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    reviewed_at = Column(DateTime(timezone=True))
    review_notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Note: No unique constraint needed since we use DELETE-and-REPLACE strategy
    # Multiple line items can legitimately have the same account code
    __table_args__ = ()
    
    # Relationships
    header = relationship("IncomeStatementHeader", back_populates="line_items")
    property = relationship("Property", back_populates="income_statement_data")
    period = relationship("FinancialPeriod", back_populates="income_statement_data")
    upload = relationship("DocumentUpload", back_populates="income_statement_data")
    header = relationship("IncomeStatementHeader", back_populates="line_items")
    account = relationship("ChartOfAccounts", back_populates="income_statement_entries")

