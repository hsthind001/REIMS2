from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class AnomalyThreshold(Base):
    """Store absolute value thresholds for anomaly detection per account code"""
    
    __tablename__ = "anomaly_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    account_code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "5400-0002"
    account_name = Column(String(255), nullable=False)  # e.g., "Salaries Expense"
    threshold_value = Column(DECIMAL(15, 2), nullable=False)  # Absolute value threshold
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Optional relationship to chart_of_accounts
    # account = relationship("ChartOfAccounts", foreign_keys=[account_code], primaryjoin="AnomalyThreshold.account_code == ChartOfAccounts.account_code")

    def __repr__(self):
        return f"<AnomalyThreshold(account_code='{self.account_code}', threshold_value={self.threshold_value})>"


class SystemConfig(Base):
    """Store system-wide configuration values"""
    
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "anomaly_threshold_default"
    config_value = Column(String(500), nullable=False)  # Stored as string, parsed as needed
    description = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<SystemConfig(config_key='{self.config_key}', config_value='{self.config_value}')>"

