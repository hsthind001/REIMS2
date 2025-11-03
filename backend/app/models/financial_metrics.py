from sqlalchemy import Column, Integer, DECIMAL, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class FinancialMetrics(Base):
    """Pre-calculated KPIs for fast reporting"""
    
    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Balance Sheet Metrics
    total_assets = Column(DECIMAL(15, 2))
    total_liabilities = Column(DECIMAL(15, 2))
    total_equity = Column(DECIMAL(15, 2))
    current_ratio = Column(DECIMAL(10, 4))  # Current Assets / Current Liabilities
    debt_to_equity_ratio = Column(DECIMAL(10, 4))
    
    # Income Statement Metrics
    total_revenue = Column(DECIMAL(15, 2))
    total_expenses = Column(DECIMAL(15, 2))
    net_operating_income = Column(DECIMAL(15, 2))
    net_income = Column(DECIMAL(15, 2))
    operating_margin = Column(DECIMAL(10, 4))  # NOI / Revenue
    profit_margin = Column(DECIMAL(10, 4))  # Net Income / Revenue
    
    # Cash Flow Metrics
    operating_cash_flow = Column(DECIMAL(15, 2))
    investing_cash_flow = Column(DECIMAL(15, 2))
    financing_cash_flow = Column(DECIMAL(15, 2))
    net_cash_flow = Column(DECIMAL(15, 2))
    beginning_cash_balance = Column(DECIMAL(15, 2))
    ending_cash_balance = Column(DECIMAL(15, 2))
    
    # Rent Roll Metrics
    total_units = Column(Integer)
    occupied_units = Column(Integer)
    vacant_units = Column(Integer)
    occupancy_rate = Column(DECIMAL(5, 2))  # %
    total_leasable_sqft = Column(DECIMAL(12, 2))
    occupied_sqft = Column(DECIMAL(12, 2))
    total_monthly_rent = Column(DECIMAL(12, 2))
    total_annual_rent = Column(DECIMAL(12, 2))
    avg_rent_per_sqft = Column(DECIMAL(10, 4))
    
    # Property Performance
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

