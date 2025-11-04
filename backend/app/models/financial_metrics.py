from sqlalchemy import Column, Integer, DECIMAL, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class FinancialMetrics(Base):
    """Pre-calculated KPIs for fast reporting - Template v1.0 Enhanced"""
    
    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # ==================== BALANCE SHEET TOTALS ====================
    total_assets = Column(DECIMAL(15, 2))
    total_current_assets = Column(DECIMAL(15, 2))
    total_property_equipment = Column(DECIMAL(15, 2))
    total_other_assets = Column(DECIMAL(15, 2))
    total_liabilities = Column(DECIMAL(15, 2))
    total_current_liabilities = Column(DECIMAL(15, 2))
    total_long_term_liabilities = Column(DECIMAL(15, 2))
    total_equity = Column(DECIMAL(15, 2))
    
    # ==================== LIQUIDITY METRICS (Template v1.0) ====================
    current_ratio = Column(DECIMAL(10, 4))  # Current Assets / Current Liabilities
    quick_ratio = Column(DECIMAL(10, 4))  # (Current Assets - Receivables) / Current Liabilities
    cash_ratio = Column(DECIMAL(10, 4))  # Total Cash / Current Liabilities
    working_capital = Column(DECIMAL(15, 2))  # Current Assets - Current Liabilities
    
    # ==================== LEVERAGE METRICS (Template v1.0) ====================
    debt_to_assets_ratio = Column(DECIMAL(10, 4))  # Total Liabilities / Total Assets
    debt_to_equity_ratio = Column(DECIMAL(10, 4))  # Total Liabilities / Total Equity
    equity_ratio = Column(DECIMAL(10, 4))  # Total Equity / Total Assets
    ltv_ratio = Column(DECIMAL(10, 4))  # Total Long-Term Debt / Net Property Value
    
    # ==================== PROPERTY METRICS (Template v1.0) ====================
    gross_property_value = Column(DECIMAL(15, 2))  # Total property before depreciation
    accumulated_depreciation = Column(DECIMAL(15, 2))  # Total accumulated depreciation
    net_property_value = Column(DECIMAL(15, 2))  # Gross - Accumulated
    depreciation_rate = Column(DECIMAL(10, 4))  # Accum Depr / Gross Property
    land_value = Column(DECIMAL(15, 2))  # Land (never depreciates)
    building_value_net = Column(DECIMAL(15, 2))  # Buildings net of depreciation
    improvements_value_net = Column(DECIMAL(15, 2))  # Improvements net of depreciation
    
    # ==================== CASH POSITION ANALYSIS (Template v1.0) ====================
    operating_cash = Column(DECIMAL(15, 2))  # Sum of operating cash accounts (0122-0125)
    restricted_cash = Column(DECIMAL(15, 2))  # Sum of escrow accounts (1310-1340)
    total_cash_position = Column(DECIMAL(15, 2))  # Operating + Restricted cash
    
    # ==================== RECEIVABLES ANALYSIS (Template v1.0) ====================
    tenant_receivables = Column(DECIMAL(15, 2))  # A/R Tenants (0305-0000)
    intercompany_receivables = Column(DECIMAL(15, 2))  # Sum of inter-company A/R
    other_receivables = Column(DECIMAL(15, 2))  # Other A/R accounts
    total_receivables = Column(DECIMAL(15, 2))  # Sum of all receivables
    ar_percentage_of_assets = Column(DECIMAL(10, 4))  # Total Receivables / Current Assets
    
    # ==================== DEBT ANALYSIS (Template v1.0) ====================
    short_term_debt = Column(DECIMAL(15, 2))  # Current portion of LTD + short-term loans
    institutional_debt = Column(DECIMAL(15, 2))  # Primary lenders (Wells Fargo, NorthMarq, etc.)
    mezzanine_debt = Column(DECIMAL(15, 2))  # Mezz financing (Trawler, etc.)
    shareholder_loans = Column(DECIMAL(15, 2))  # Loans from shareholders
    long_term_debt = Column(DECIMAL(15, 2))  # Total long-term debt
    total_debt = Column(DECIMAL(15, 2))  # Short-term + Long-term
    
    # ==================== EQUITY ANALYSIS (Template v1.0) ====================
    partners_contribution = Column(DECIMAL(15, 2))  # Capital contributions (3050-0000)
    beginning_equity = Column(DECIMAL(15, 2))  # Retained earnings from prior periods (3910-0000)
    partners_draw = Column(DECIMAL(15, 2))  # Partner withdrawals (3920-0000)
    distributions = Column(DECIMAL(15, 2))  # Cash distributions (3990-0000)
    current_period_earnings = Column(DECIMAL(15, 2))  # Net income for period (3995-0000)
    ending_equity = Column(DECIMAL(15, 2))  # Total capital (3999-0000)
    equity_change = Column(DECIMAL(15, 2))  # Period-over-period equity change
    
    # ==================== INCOME STATEMENT METRICS ====================
    total_revenue = Column(DECIMAL(15, 2))
    total_expenses = Column(DECIMAL(15, 2))
    net_operating_income = Column(DECIMAL(15, 2))
    net_income = Column(DECIMAL(15, 2))
    operating_margin = Column(DECIMAL(10, 4))  # NOI / Revenue
    profit_margin = Column(DECIMAL(10, 4))  # Net Income / Revenue
    
    # ==================== CASH FLOW METRICS ====================
    operating_cash_flow = Column(DECIMAL(15, 2))
    investing_cash_flow = Column(DECIMAL(15, 2))
    financing_cash_flow = Column(DECIMAL(15, 2))
    net_cash_flow = Column(DECIMAL(15, 2))
    beginning_cash_balance = Column(DECIMAL(15, 2))
    ending_cash_balance = Column(DECIMAL(15, 2))
    
    # ==================== RENT ROLL METRICS ====================
    total_units = Column(Integer)
    occupied_units = Column(Integer)
    vacant_units = Column(Integer)
    occupancy_rate = Column(DECIMAL(5, 2))  # %
    total_leasable_sqft = Column(DECIMAL(12, 2))
    occupied_sqft = Column(DECIMAL(12, 2))
    total_monthly_rent = Column(DECIMAL(12, 2))
    total_annual_rent = Column(DECIMAL(12, 2))
    avg_rent_per_sqft = Column(DECIMAL(10, 4))
    
    # ==================== PROPERTY PERFORMANCE ====================
    noi_per_sqft = Column(DECIMAL(10, 4))
    revenue_per_sqft = Column(DECIMAL(10, 4))
    expense_ratio = Column(DECIMAL(5, 2))  # Expenses / Revenue
    
    # Metadata
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', name='uq_metrics_property_period'),
    )
    
    # Relationships
    property = relationship("Property", back_populates="financial_metrics")
    period = relationship("FinancialPeriod", back_populates="financial_metrics")

