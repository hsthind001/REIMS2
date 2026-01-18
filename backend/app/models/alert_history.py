"""
Alert History Model
Tracks all state changes and actions on alerts
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.db.database import Base


class AlertHistory(Base):
    """
    Alert History Model
    
    Tracks all alert state changes:
    - Created, acknowledged, resolved, dismissed
    - Escalation events
    - Notification deliveries
    - Resolution steps
    """
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    
    # Reference to alert
    alert_id = Column(Integer, ForeignKey("committee_alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Action details
    action_type = Column(String(50), nullable=False, index=True)  # created, acknowledged, resolved, dismissed, escalated, notified
    action_by = Column(Integer, nullable=True, index=True)  # User ID
    action_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # State changes
    previous_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=True)
    previous_severity = Column(String(20), nullable=True)
    new_severity = Column(String(20), nullable=True)
    
    # Additional information
    notes = Column(Text, nullable=True)
    action_metadata = Column(JSONB, nullable=True)  # Action-specific data (renamed from metadata to avoid SQLAlchemy reserved word)
    
    # Relationships
    alert = relationship("CommitteeAlert", backref=backref("history", cascade="all, delete-orphan"))
    
    def __repr__(self):
        return f"<AlertHistory(id={self.id}, alert_id={self.alert_id}, action={self.action_type})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "action_type": self.action_type,
            "action_by": self.action_by,
            "action_at": self.action_at.isoformat() if self.action_at else None,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "previous_severity": self.previous_severity,
            "new_severity": self.new_severity,
            "notes": self.notes,
            "action_metadata": self.action_metadata
        }

