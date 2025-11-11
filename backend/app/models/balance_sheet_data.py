from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class BalanceSheetData(Base):
    """Monthly balance sheet line items - Template v1.0 compliant"""
    
    __tablename__ = "balance_sheet_data"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'))
    account_id = Column(Integer, ForeignKey('chart_of_accounts.id'), nullable=True)  # Nullable for unmatched accounts
    
    # ==================== HEADER METADATA (Template v1.0) ====================
    report_title = Column(String(100), default='Balance Sheet')  # Document title
    period_ending = Column(String(50))  # e.g., "Dec 2023", "Dec 2024"
    accounting_basis = Column(String(20))  # "Accrual" or "Cash"
    report_date = Column(DateTime(timezone=True))  # Date report was generated
    page_number = Column(Integer)  # Page number for multi-page documents
    
    # ==================== ACCOUNT INFORMATION ====================
    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(255), nullable=False)
    
    # ==================== HIERARCHICAL STRUCTURE (Template v1.0) ====================
    is_subtotal = Column(Boolean, default=False, index=True)  # e.g., "Total Current Assets"
    is_total = Column(Boolean, default=False, index=True)  # e.g., "TOTAL ASSETS"
    account_level = Column(Integer)  # 1-4: hierarchy depth
    account_category = Column(String(100))  # e.g., "ASSETS", "LIABILITIES", "CAPITAL"
    account_subcategory = Column(String(100))  # e.g., "Current Assets", "Long Term Liabilities"
    
    # ==================== FINANCIAL DATA ====================
    amount = Column(DECIMAL(15, 2), nullable=False)  # Current balance
    is_debit = Column(Boolean)  # TRUE for debit accounts (assets, expenses)
    is_contra_account = Column(Boolean, default=False)  # Accumulated depreciation, distributions
    expected_sign = Column(String(10))  # "positive", "negative", "either"
    
    # ==================== CALCULATION & RELATIONSHIPS ====================
    is_calculated = Column(Boolean, default=False)  # Is this a calculated/total line
    parent_account_code = Column(String(50))  # Parent in hierarchy
    
    # ==================== EXTRACTION QUALITY (Template v1.0) ====================
    extraction_confidence = Column(DECIMAL(5, 2))  # 0-100 from PDF extraction
    match_confidence = Column(DECIMAL(5, 2))  # 0-100 from account matching
    extraction_method = Column(String(50))  # "table", "text", "template"
    
    # ==================== REVIEW WORKFLOW ====================
    needs_review = Column(Boolean, default=False, index=True)
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
    property = relationship("Property", back_populates="balance_sheet_data")
    period = relationship("FinancialPeriod", back_populates="balance_sheet_data")
    upload = relationship("DocumentUpload", back_populates="balance_sheet_data")
    account = relationship("ChartOfAccounts", back_populates="balance_sheet_entries")

