from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ChartOfAccounts(Base):
    """Master chart of accounts - template for all financial line items"""
    
    __tablename__ = "chart_of_accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_code = Column(String(50), unique=True, nullable=False, index=True)  # "0122-0000", "4010-0000"
    account_name = Column(String(255), nullable=False)  # "Cash - Operating", "Base Rentals"
    
    # Classification
    account_type = Column(String(50), nullable=False, index=True)  # asset, liability, equity, income, expense
    category = Column(String(100), index=True)  # current_asset, long_term_liability, operating_expense
    subcategory = Column(String(100))  # cash, accounts_receivable, utilities
    
    # Hierarchy
    parent_account_code = Column(String(50))  # For nested structure
    
    # Document mapping
    document_types = Column(ARRAY(Text))  # ["balance_sheet", "cash_flow"]
    
    # Calculated fields
    is_calculated = Column(Boolean, default=False)  # Is this a total/subtotal?
    calculation_formula = Column(Text)  # e.g., "0122-0000 + 0123-0000 + 0125-0000"
    
    # Display
    display_order = Column(Integer)  # Order in reports
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships (lazy loading to avoid issues with tests)
    balance_sheet_entries = relationship("BalanceSheetData", back_populates="account", lazy="noload")
    income_statement_entries = relationship("IncomeStatementData", back_populates="account", lazy="noload")
    cash_flow_entries = relationship("CashFlowData", back_populates="account", lazy="noload")

