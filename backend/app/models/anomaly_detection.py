"""
Anomaly Detection Model

Represents detected anomalies in financial data extracted from documents.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
import enum
from app.db.database import Base


class BaselineType(str, enum.Enum):
    """Baseline type for anomaly detection"""
    MEAN = "mean"
    SEASONAL = "seasonal"
    FORECAST = "forecast"
    PEER_GROUP = "peer-group"


class AnomalyDirection(str, enum.Enum):
    """Direction of anomaly change"""
    UP = "up"
    DOWN = "down"


class AnomalyCategory(str, enum.Enum):
    """Anomaly category taxonomy"""
    DATA_QUALITY = "data-quality"
    ACCOUNTING = "accounting"
    PERFORMANCE = "performance"
    COVENANT = "covenant"
    EXTRACTION = "extraction"


class PatternType(str, enum.Enum):
    """Pattern type classification"""
    POINT = "point"
    TREND = "trend"
    SEASONALITY = "seasonality"
    STRUCTURE = "structure"


class ResolutionType(str, enum.Enum):
    """Resolution type enum for anomaly resolution tracking"""
    DATA_ENTRY = "data_entry"
    EXTRACTION = "extraction"
    MAPPING = "mapping"
    BUSINESS_CHANGE = "business_change"
    COVENANT_ISSUE = "covenant_issue"


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
    suppression_reason = Column(Text, nullable=True)  # Reason for suppression (changed to Text for longer reasons)
    
    # World-class enhancement fields (from migration 20251222_0000)
    anomaly_score = Column(Numeric(5, 2), nullable=True, index=True)  # Unified risk score 0-100
    impact_amount = Column(Numeric(15, 2), nullable=True)  # Absolute $ variance/exposure
    direction = Column(
        SQLEnum(AnomalyDirection, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )  # Change direction: up/down
    root_cause_candidates = Column(JSONB, nullable=True)  # Top suspected drivers (JSONB)
    baseline_type = Column(
        SQLEnum(BaselineType, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        index=True
    )  # Baseline method used
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Group related anomalies into incidents
    suppressed_until = Column(DateTime(timezone=True), nullable=True, index=True)  # Suppression expiration
    anomaly_category = Column(
        SQLEnum(AnomalyCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        index=True
    )  # Taxonomy classification
    pattern_type = Column(
        SQLEnum(PatternType, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        index=True
    )  # Pattern classification
    is_one_off = Column(Boolean, default=False, nullable=True)  # One-time anomaly flag
    is_recurrent = Column(Boolean, default=False, nullable=True)  # Recurring pattern flag
    cross_property_pattern = Column(Boolean, default=False, nullable=True)
    
    # Root cause tracking (Task 57)
    resolution_type = Column(
        SQLEnum(ResolutionType, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )  # Resolution type enum
    root_cause = Column(Text, nullable=True)  # Detailed root cause explanation
    
    # Timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Additional metadata
    metadata_json = Column('metadata', JSONB, nullable=True)  # Flexible JSON storage for additional data
    
    # Relationships
    document = relationship("DocumentUpload", backref="anomaly_detections")
    feedback = relationship("AnomalyFeedback", back_populates="anomaly_detection", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AnomalyDetection(id={self.id}, field_name='{self.field_name}', severity='{self.severity}', anomaly_type='{self.anomaly_type}')>"
