"""
Anomaly Feedback Model

Tracks user feedback on anomaly detections to enable learning and improvement.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class AnomalyFeedback(Base):
    """
    Store user feedback on anomaly detections.
    
    Used for:
    - Learning which anomalies are false positives
    - Improving detection accuracy over time
    - Auto-suppressing learned false positives
    """
    
    __tablename__ = "anomaly_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    anomaly_detection_id = Column(Integer, ForeignKey('anomaly_detections.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # Optional - can be anonymous
    
    # Feedback type
    feedback_type = Column(String(20), nullable=False)  # 'confirmed', 'dismissed', 'false_positive', 'false_negative'
    is_anomaly = Column(Boolean, nullable=False)  # User's assessment: True = real anomaly, False = false positive
    
    # Optional notes
    notes = Column(Text, nullable=True)
    
    # Learning metadata
    account_code = Column(String(50), nullable=True, index=True)  # For pattern learning
    anomaly_type = Column(String(50), nullable=True)  # Type of anomaly (z_score, percentage_change, etc.)
    severity = Column(String(20), nullable=True)  # Severity level
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    anomaly_detection = relationship("AnomalyDetection", backref="feedback")
    user = relationship("User", backref="anomaly_feedback")
    
    def __repr__(self):
        return f"<AnomalyFeedback(id={self.id}, feedback_type='{self.feedback_type}', is_anomaly={self.is_anomaly})>"


class AnomalyLearningPattern(Base):
    """
    Learned patterns from user feedback.
    
    Tracks patterns like "User always dismisses X type of anomaly for account Y"
    to enable auto-suppression.
    """
    
    __tablename__ = "anomaly_learning_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Pattern identification
    account_code = Column(String(50), nullable=True, index=True)
    anomaly_type = Column(String(50), nullable=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # Pattern details
    pattern_type = Column(String(50), nullable=False)  # 'always_dismiss', 'always_confirm', 'conditional'
    condition = Column(Text, nullable=True)  # JSON condition for when pattern applies
    
    # Statistics
    occurrence_count = Column(Integer, default=0)  # How many times this pattern occurred
    suppression_rate = Column(DECIMAL(5, 4), nullable=True)  # Rate of suppression (0-1)
    
    # Auto-suppression settings
    auto_suppress = Column(Boolean, default=False)  # Whether to auto-suppress based on this pattern
    confidence = Column(DECIMAL(5, 4), default=0.5)  # Confidence in pattern (0-1)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_applied_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<AnomalyLearningPattern(id={self.id}, pattern_type='{self.pattern_type}', auto_suppress={self.auto_suppress})>"

