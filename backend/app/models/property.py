from sqlalchemy import Column, Integer, String, Text, DECIMAL, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Property(Base):
    """Master property information"""
    
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String(50), unique=True, nullable=False, index=True)
    property_name = Column(String(255), nullable=False)
    property_type = Column(String(50))  # Retail, Office, Mixed-Use
    
    # Address
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    country = Column(String(50), default='USA')
    
    # Property details
    total_area_sqft = Column(DECIMAL(12, 2))
    acquisition_date = Column(Date)
    ownership_structure = Column(String(100))  # Partnership, LLC, etc.
    
    # Status
    status = Column(String(50), default='active', index=True)  # active, sold, under_contract
    
    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationships (lazy loading to avoid issues with tests and missing tables)
    financial_periods = relationship("FinancialPeriod", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    document_uploads = relationship("DocumentUpload", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    balance_sheet_data = relationship("BalanceSheetData", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    income_statement_data = relationship("IncomeStatementData", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    income_statement_headers = relationship("IncomeStatementHeader", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    cash_flow_headers = relationship("CashFlowHeader", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    cash_flow_data = relationship("CashFlowData", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    cash_flow_adjustments = relationship("CashFlowAdjustment", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    cash_account_reconciliations = relationship("CashAccountReconciliation", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    rent_roll_data = relationship("RentRollData", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    mortgage_statements = relationship("MortgageStatementData", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    financial_metrics = relationship("FinancialMetrics", back_populates="property", cascade="all, delete-orphan", lazy="noload")

    # Next-level AI features relationships
    research_data = relationship("PropertyResearch", back_populates="property_obj", cascade="all, delete-orphan", lazy="noload")
    tenant_recommendations = relationship("TenantRecommendation", back_populates="property_obj", cascade="all, delete-orphan", lazy="noload")
    tenant_history = relationship("TenantPerformanceHistory", back_populates="property_obj", cascade="all, delete-orphan", lazy="noload")

    # Risk management relationships
    committee_alerts = relationship("CommitteeAlert", back_populates="property", cascade="all, delete-orphan", lazy="noload")
    workflow_locks = relationship("WorkflowLock", back_populates="property", cascade="all, delete-orphan", lazy="noload")

    def __repr__(self):
        return f"<Property {self.property_code}: {self.property_name}>"
    
    def validate_status(self):
        """Validate property status"""
        valid_statuses = ['active', 'sold', 'under_contract']
        if self.status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")

