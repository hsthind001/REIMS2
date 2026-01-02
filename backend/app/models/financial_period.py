from sqlalchemy import Column, Integer, Date, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class FinancialPeriod(Base):
    """Monthly reporting periods for properties"""
    
    __tablename__ = "financial_periods"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Period definition
    period_year = Column(Integer, nullable=False, index=True)  # 2024, 2025
    period_month = Column(Integer, nullable=False)  # 1-12
    period_start_date = Column(Date, nullable=False)  # 2024-01-01
    period_end_date = Column(Date, nullable=False)  # 2024-01-31
    
    # Fiscal year tracking
    fiscal_year = Column(Integer)
    fiscal_quarter = Column(Integer)  # 1-4
    
    # Status
    is_closed = Column(Boolean, default=False)  # Locked for editing
    closed_date = Column(DateTime(timezone=True))
    closed_by = Column(Integer, ForeignKey('users.id'))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('property_id', 'period_year', 'period_month', name='uq_property_period'),
    )
    
    # Relationships
    property = relationship("Property", back_populates="financial_periods")
    document_uploads = relationship("DocumentUpload", back_populates="period", cascade="all, delete-orphan")
    balance_sheet_data = relationship("BalanceSheetData", back_populates="period", cascade="all, delete-orphan")
    income_statement_data = relationship("IncomeStatementData", back_populates="period", cascade="all, delete-orphan")
    income_statement_headers = relationship("IncomeStatementHeader", back_populates="period", cascade="all, delete-orphan")
    cash_flow_headers = relationship("CashFlowHeader", back_populates="period", cascade="all, delete-orphan")
    income_statement_headers = relationship("IncomeStatementHeader", back_populates="period", cascade="all, delete-orphan")
    cash_flow_data = relationship("CashFlowData", back_populates="period", cascade="all, delete-orphan")
    cash_flow_adjustments = relationship("CashFlowAdjustment", back_populates="period", cascade="all, delete-orphan")
    cash_account_reconciliations = relationship("CashAccountReconciliation", back_populates="period", cascade="all, delete-orphan")
    rent_roll_data = relationship("RentRollData", back_populates="period", cascade="all, delete-orphan")
    mortgage_statements = relationship("MortgageStatementData", back_populates="period", cascade="all, delete-orphan")
    financial_metrics = relationship("FinancialMetrics", back_populates="period", cascade="all, delete-orphan")
    document_completeness = relationship("PeriodDocumentCompleteness", back_populates="period", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FinancialPeriod {self.property_id}: {self.period_year}-{self.period_month:02d}>"
    
    def get_period_range(self):
        """Get period date range as tuple"""
        return (self.period_start_date, self.period_end_date)
    
    def is_current_period(self):
        """Check if this period includes today's date"""
        from datetime import date
        today = date.today()
        return self.period_start_date <= today <= self.period_end_date

