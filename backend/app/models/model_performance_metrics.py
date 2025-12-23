"""
Model Performance Metrics Model

Tracks performance metrics for ML models used in anomaly detection and other services.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class ModelPerformanceMetrics(Base):
    """
    Model Performance Metrics Model
    
    Stores performance metrics for ML models including detection coverage,
    runtime, latency, alert volumes, and false-positive ratios.
    """
    __tablename__ = "model_performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    
    # Model identification
    model_name = Column(String(100), nullable=False, index=True)  # e.g., "isolation_forest", "autoencoder"
    model_type = Column(String(50), nullable=False, index=True)  # e.g., "anomaly_detection", "extraction"
    detector_method = Column(String(100), nullable=True)  # e.g., "z_score", "isolation_forest"
    
    # Performance metrics
    detection_coverage = Column(Float, nullable=True, comment="Percentage of accounts/periods scanned (0-100)")
    runtime_per_batch_ms = Column(Float, nullable=True, comment="Average runtime per batch in milliseconds")
    queue_latency_ms = Column(Float, nullable=True, comment="Queue latency in milliseconds")
    
    # Alert metrics
    alert_volume_total = Column(Integer, nullable=True, default=0)
    alert_volume_critical = Column(Integer, nullable=True, default=0)
    alert_volume_high = Column(Integer, nullable=True, default=0)
    alert_volume_medium = Column(Integer, nullable=True, default=0)
    alert_volume_low = Column(Integer, nullable=True, default=0)
    
    # Quality metrics
    false_positive_rate = Column(Float, nullable=True, comment="False positive ratio (0-1)")
    true_positive_rate = Column(Float, nullable=True, comment="True positive rate / recall (0-1)")
    precision = Column(Float, nullable=True, comment="Precision score (0-1)")
    f1_score = Column(Float, nullable=True, comment="F1 score (0-1)")
    
    # Additional metrics (stored as JSON for flexibility)
    additional_metrics = Column(JSONB, nullable=True)
    
    # Context
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=True, index=True)
    period_id = Column(Integer, ForeignKey("financial_periods.id", ondelete="CASCADE"), nullable=True, index=True)
    batch_id = Column(String(100), nullable=True, index=True)  # Identifier for the batch run
    
    # Timestamps
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    property = relationship("Property", backref="model_performance_metrics")
    period = relationship("FinancialPeriod", backref="model_performance_metrics")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_model_performance_model_type', 'model_type', 'recorded_at'),
        Index('idx_model_performance_property_period', 'property_id', 'period_id', 'recorded_at'),
    )
    
    def __repr__(self):
        return f"<ModelPerformanceMetrics(id={self.id}, model='{self.model_name}', type='{self.model_type}', recorded_at='{self.recorded_at}')>"

