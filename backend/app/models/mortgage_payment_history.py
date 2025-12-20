from sqlalchemy import Column, Integer, String, DECIMAL, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class MortgagePaymentHistory(Base):
    """Mortgage payment history - tracks individual payment records"""
    
    __tablename__ = "mortgage_payment_history"

    id = Column(Integer, primary_key=True, index=True)
    mortgage_id = Column(Integer, ForeignKey('mortgage_statement_data.id', ondelete='CASCADE'), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    
    # Payment Details
    payment_date = Column(Date, nullable=False, index=True)
    payment_number = Column(Integer, nullable=True)  # Payment sequence (e.g., payment 60 of 360)
    
    # Payment Breakdown
    principal_paid = Column(DECIMAL(12, 2), nullable=False)
    interest_paid = Column(DECIMAL(12, 2), nullable=False)
    escrow_paid = Column(DECIMAL(12, 2), server_default='0')
    fees_paid = Column(DECIMAL(10, 2), server_default='0')
    total_payment = Column(DECIMAL(12, 2), nullable=False)
    
    # Balance After Payment
    principal_balance_after = Column(DECIMAL(15, 2), nullable=True)
    escrow_balance_after = Column(DECIMAL(12, 2), nullable=True)
    
    # Status
    payment_status = Column(String(50), nullable=True)  # 'on_time', 'late', 'missed', 'prepayment'
    days_late = Column(Integer, server_default='0')
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('mortgage_id', 'payment_date', name='uq_mortgage_payment'),
        Index('idx_payment_mortgage', 'mortgage_id'),
    )
    
    # Relationships
    mortgage = relationship("MortgageStatementData", back_populates="payment_history")
    property = relationship("Property")


