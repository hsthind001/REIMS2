"""
Data Quality Rule Model

Defines field-level quality requirements as metadata.
"""

from sqlalchemy import Column, Integer, String, Boolean, Numeric, JSON, DateTime, Text
from sqlalchemy.sql import func
from app.db.database import Base


class DataQualityRule(Base):
    """Data quality rule model."""
    
    __tablename__ = "data_quality_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    field_name = Column(String(200), nullable=False, index=True)
    mandatory = Column(Boolean, default=False)
    numeric_validation = Column(Boolean, default=False)
    tolerance = Column(Numeric(10, 4), nullable=True)
    reconciliation_rules = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
