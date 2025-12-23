"""
Materiality Configuration Model

Defines materiality thresholds and risk classifications for reconciliation.
Supports property-specific, statement-specific, and account-specific configurations.
"""
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base


class AccountRiskClass(Base):
    """Risk classification for account code patterns"""
    
    __tablename__ = "account_risk_classes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Account Pattern
    account_code_pattern = Column(String(50), nullable=False, index=True, comment='e.g., "1*" for assets, "2*" for liabilities')
    account_name_pattern = Column(String(255), nullable=True, comment='Optional name pattern for matching')
    
    # Risk Classification
    risk_class = Column(String(50), nullable=False, index=True, comment='critical, high, medium, low')
    default_tolerance_absolute = Column(Numeric(15, 2), nullable=True, comment='Default absolute tolerance')
    default_tolerance_percent = Column(Numeric(10, 4), nullable=True, comment='Default percentage tolerance')
    reconciliation_frequency = Column(String(50), nullable=False, server_default='monthly', comment='daily, weekly, monthly, quarterly')
    
    # Property Type Override (JSONB)
    property_type_override = Column(JSONB(), nullable=True, comment='Property-specific overrides')
    
    # Metadata
    description = Column(Text(), nullable=True)
    is_active = Column(Boolean(), nullable=False, server_default='true')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    def __repr__(self):
        return f"<AccountRiskClass {self.account_code_pattern}: {self.risk_class}>"


class MaterialityConfig(Base):
    """Materiality configuration for reconciliation thresholds"""
    
    __tablename__ = "materiality_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Scope (NULL values indicate defaults)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=True, index=True, comment='NULL = global default')
    statement_type = Column(String(50), nullable=True, comment='balance_sheet, income_statement, cash_flow, rent_roll, mortgage_statement, NULL = all')
    account_code = Column(String(50), nullable=True, comment='NULL = statement-level default')
    
    # Thresholds
    absolute_threshold = Column(Numeric(15, 2), nullable=False, comment='Absolute materiality threshold')
    relative_threshold_percent = Column(Numeric(10, 4), nullable=True, comment='Relative threshold as % of revenue/assets')
    risk_class = Column(String(50), nullable=False, comment='critical, high, medium, low')
    
    # Tolerance Configuration
    tolerance_type = Column(String(50), nullable=False, server_default='standard', comment='strict, standard, loose')
    tolerance_absolute = Column(Numeric(15, 2), nullable=True)
    tolerance_percent = Column(Numeric(10, 4), nullable=True)
    
    # Effective Dates
    effective_date = Column(Date(), nullable=False, server_default=func.current_date())
    expires_at = Column(Date(), nullable=True)
    
    # Metadata
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    
    # Relationships
    property = relationship("Property", foreign_keys=[property_id])
    creator = relationship("User", foreign_keys=[created_by])
    
    # Composite indexes
    __table_args__ = (
        Index('idx_materiality_configs_scope', 'property_id', 'statement_type', 'account_code'),
        Index('idx_materiality_configs_effective', 'effective_date', 'expires_at'),
    )
    
    def __repr__(self):
        scope = f"Property {self.property_id}" if self.property_id else "Global"
        stmt = f"/{self.statement_type}" if self.statement_type else ""
        acct = f"/{self.account_code}" if self.account_code else ""
        return f"<MaterialityConfig {scope}{stmt}{acct}: {self.risk_class}>"

