from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ReconciliationSession(Base):
    """Track each reconciliation event"""
    
    __tablename__ = "reconciliation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)  # balance_sheet, income_statement, cash_flow, rent_roll
    
    # Session tracking
    status = Column(String(50), default='in_progress', index=True)  # in_progress, completed, cancelled
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Summary statistics (stored as JSON)
    summary = Column(JSON)  # {total_records, matches, differences, missing_in_db, missing_in_pdf, resolved}
    
    # Notes
    notes = Column(Text)
    
    # Relationships
    property = relationship("Property")
    period = relationship("FinancialPeriod")
    user = relationship("User")
    differences = relationship("ReconciliationDifference", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ReconciliationSession {self.id}: {self.property_id}-{self.period_id}-{self.document_type}>"

