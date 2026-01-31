from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class CashFlowData(Base):
    """
    Cash flow statement line items
    
    Stores detailed line-by-line data from cash flow statements including:
    - Income items (Base Rentals, Recoveries, Other Income)
    - Operating Expenses (Property, Utility, Contracted, R&M, Admin)
    - Additional Expenses (Management, Taxes, Leasing, Landlord)
    - Performance Metrics (NOI, Net Income)
    - Hierarchical structure with subtotals and totals
    """
    
    __tablename__ = "cash_flow_data"

    id = Column(Integer, primary_key=True, index=True)
    header_id = Column(Integer, ForeignKey('cash_flow_headers.id', ondelete='CASCADE'), nullable=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='SET NULL'))
    account_id = Column(Integer, ForeignKey('chart_of_accounts.id'), nullable=True)  # Nullable for unmatched accounts
    
    # Account information
    account_code = Column(String(50), nullable=False)
    account_name = Column(String(255), nullable=False)
    
    # Financial data - Multi-column support (Period to Date / Year to Date)
    period_amount = Column(DECIMAL(15, 2), nullable=False)
    ytd_amount = Column(DECIMAL(15, 2))
    period_percentage = Column(DECIMAL(5, 2))  # (Amount / Total Income) * 100
    ytd_percentage = Column(DECIMAL(5, 2))
    
    # Template v1.0: Section Classification
    line_section = Column(String(50), index=True)  # INCOME, OPERATING_EXPENSE, ADDITIONAL_EXPENSE, PERFORMANCE_METRICS
    line_category = Column(String(100), index=True)  # Base Rental Income, Recovery Income, Property Expenses, Utility Expenses, etc.
    line_subcategory = Column(String(100))  # Tax Recovery, Insurance Recovery, Electricity, Gas, etc.
    
    # Hierarchical Structure
    line_number = Column(Integer)  # Sequential line number in statement
    is_subtotal = Column(Boolean, default=False)  # Total Utility Expense, Total R&M, etc.
    is_total = Column(Boolean, default=False)  # Total Income, Total Expenses, NOI, Net Income
    parent_line_id = Column(Integer, ForeignKey('cash_flow_data.id'), nullable=True)  # Link to parent subtotal/total
    
    # Cash flow classification (legacy - kept for backwards compatibility)
    cash_flow_category = Column(String(50), index=True)  # operating, investing, financing
    is_inflow = Column(Boolean)  # TRUE for cash in, FALSE for cash out
    
    # Calculation flags
    is_calculated = Column(Boolean, default=False)  # TRUE for NOI, Net Income (derived values)
    parent_account_code = Column(String(50))  # Legacy field
    
    # Extraction quality
    extraction_confidence = Column(DECIMAL(5, 2))
    
    # Review workflow
    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    reviewed_at = Column(DateTime(timezone=True))
    review_notes = Column(Text)
    
    # Metadata
    page_number = Column(Integer)  # Page number in source PDF
    
    # ==================== EXTRACTION COORDINATES (PDF Source Navigation) ====================
    extraction_x0 = Column(DECIMAL(10, 2), nullable=True)  # Left coordinate in PDF
    extraction_y0 = Column(DECIMAL(10, 2), nullable=True)  # Top coordinate in PDF
    extraction_x1 = Column(DECIMAL(10, 2), nullable=True)  # Right coordinate in PDF
    extraction_y1 = Column(DECIMAL(10, 2), nullable=True)  # Bottom coordinate in PDF
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Unique constraint - modified to include line_number for uniqueness
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', 'account_code', 'line_number', name='uq_cf_property_period_account_line'),
    )
    
    # Relationships
    header = relationship("CashFlowHeader", back_populates="line_items")
    property = relationship("Property", back_populates="cash_flow_data")
    period = relationship("FinancialPeriod", back_populates="cash_flow_data")
    upload = relationship("DocumentUpload", back_populates="cash_flow_data")
    account = relationship("ChartOfAccounts", back_populates="cash_flow_entries")
    parent_line = relationship("CashFlowData", remote_side=[id], backref="child_lines")

