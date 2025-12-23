"""
Notification Model

Represents in-app notifications for users.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class Notification(Base):
    """
    Notification Model
    
    Stores in-app notifications for users including alerts, system messages, and info.
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    
    # User reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Notification details
    type = Column(String(50), nullable=False)  # alert, anomaly, system, info
    severity = Column(String(20), nullable=False)  # critical, urgent, warning, info
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    
    # Metadata (for links, additional data, etc.)
    metadata_json = Column(JSONB, nullable=True)
    
    # Status tracking
    read_at = Column(DateTime(timezone=True), nullable=True, index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", backref="notifications")
    
    @property
    def read(self) -> bool:
        """Check if notification is read"""
        return self.read_at is not None
    
    @property
    def link(self) -> str | None:
        """Get link from metadata if available"""
        if self.metadata_json and isinstance(self.metadata_json, dict):
            return self.metadata_json.get("link")
        return None
    
    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.type}', severity='{self.severity}', title='{self.title}')>"

