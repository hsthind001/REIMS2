from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ReconciliationResolution(Base):
    """Audit trail of corrections made during reconciliation"""
    
    __tablename__ = "reconciliation_resolutions"

    id = Column(Integer, primary_key=True, index=True)
    difference_id = Column(Integer, ForeignKey('reconciliation_differences.id', ondelete='CASCADE'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Action taken
    action_taken = Column(String(50), nullable=False)  # accept_pdf, accept_db, manual_entry, ignore
    
    # Values before and after
    old_value = Column(DECIMAL(15, 2))
    new_value = Column(DECIMAL(15, 2))
    
    # Justification
    reason = Column(Text)
    
    # Audit
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    difference = relationship("ReconciliationDifference", back_populates="resolutions")
    user = relationship("User")
    
    def __repr__(self):
        return f"<ReconciliationResolution {self.id}: {self.action_taken}>"

