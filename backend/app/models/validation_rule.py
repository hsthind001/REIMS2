from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ValidationRule(Base):
    """Business logic validation rules"""
    
    __tablename__ = "validation_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(100), unique=True, nullable=False)
    rule_description = Column(Text)
    
    # Rule specification
    document_type = Column(String(50), nullable=False)  # Which document this applies to
    rule_type = Column(String(50), nullable=False)  # balance_check, range_check, required_field
    rule_formula = Column(Text)  # e.g., "total_assets = total_liabilities + total_equity"
    
    # Error handling
    error_message = Column(Text)
    severity = Column(String(20), default='error')  # error, warning, info
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    validation_results = relationship("ValidationResult", back_populates="rule")

