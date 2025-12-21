"""
Anomaly Detection Model

Represents detected anomalies in financial data extracted from documents.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from app.db.database import Base


class AnomalyDetection(Base):
    """
    Store detected anomalies in financial data.
    
    Anomalies can be detected through:
    - Statistical methods (Z-score, percentage change)
    - ML methods (Isolation Forest, LOF, Autoencoder, etc.)
    - Missing data detection
    """
    
    __tablename__ = "anomaly_detections"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Anomaly details
    field_name = Column(String(100), nullable=False)  # Account code or field name
    field_value = Column(String(500), nullable=True)  # Current value
    expected_value = Column(String(500), nullable=True)  # Expected value
    
    # Statistical metrics
    z_score = Column(Numeric(10, 4), nullable=True)
    percentage_change = Column(Numeric(10, 4), nullable=True)
    
    # Detection metadata
    anomaly_type = Column(String(50), nullable=False)  # statistical, ml, missing_data
    severity = Column(String(20), nullable=False, index=True)  # critical, high, medium, low
    confidence = Column(Numeric(5, 4), nullable=False)  # 0-1 confidence score
    
    # Enhanced detection fields (from migration 20251220_0300)
    forecast_method = Column(String(50), nullable=True, index=True)  # prophet, arima, ets, ensemble
    confidence_calibrated = Column(Numeric(5, 4), nullable=True)  # Calibrated confidence score
    detection_window = Column(String(20), nullable=True, index=True)  # short_term, medium_term, long_term
    windows_detected = Column(Integer, nullable=True)  # Number of windows that detected this
    ensemble_confidence = Column(Numeric(5, 4), nullable=True)  # Confidence from ensemble methods
    detection_methods = Column(ARRAY(String(50)), nullable=True)  # Array of methods used
    is_consensus = Column(Boolean, default=False, nullable=True, index=True)  # Multiple methods agree
    change_point_detected = Column(Boolean, default=False, nullable=True)  # Structural break detected
    context_suppressed = Column(Boolean, default=False, nullable=True)  # Suppressed by context rules
    suppression_reason = Column(String(255), nullable=True)  # Reason for suppression
    
    # Timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Additional metadata
    metadata_json = Column('metadata', JSONB, nullable=True)  # Flexible JSON storage for additional data
    
    # Relationships
    document = relationship("DocumentUpload", backref="anomaly_detections")
    feedback = relationship("AnomalyFeedback", back_populates="anomaly_detection", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AnomalyDetection(id={self.id}, field_name='{self.field_name}', severity='{self.severity}', anomaly_type='{self.anomaly_type}')>"

