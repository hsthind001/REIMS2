from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.sql import func
from app.db.database import Base


class AuditTrail(Base):
    """Complete audit trail for all financial data changes"""
    
    __tablename__ = "audit_trail"

    id = Column(Integer, primary_key=True, index=True)
    
    # What was changed
    table_name = Column(String(100), nullable=False, index=True)
    record_id = Column(Integer, nullable=False, index=True)
    action = Column(String(50), nullable=False)  # insert, update, delete
    
    # Change details
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    changed_fields = Column(ARRAY(Text))
    
    # Who and when
    changed_by = Column(Integer, ForeignKey('users.id'), index=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Additional context
    reason = Column(Text)
    ip_address = Column(INET)

