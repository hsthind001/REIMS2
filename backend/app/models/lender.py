from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Lender(Base):
    """Lender reference data for long-term debt tracking"""
    
    __tablename__ = "lenders"

    id = Column(Integer, primary_key=True, index=True)
    
    # Lender Information
    lender_name = Column(String(255), nullable=False, unique=True, index=True)
    lender_short_name = Column(String(100))  # e.g., "CIBC", "Wells Fargo"
    lender_type = Column(String(50))  # "mortgage", "mezzanine", "shareholder_loan"
    
    # Account Mapping
    account_code = Column(String(50), index=True)  # Associated chart of accounts code
    
    # Lender Details
    lender_category = Column(String(50))  # "institutional", "family_trust", "shareholder"
    is_active = Column(Boolean, default=True, index=True)
    
    # Additional Info
    notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    mortgage_statements = relationship("MortgageStatementData", back_populates="lender", cascade="all, delete-orphan")

