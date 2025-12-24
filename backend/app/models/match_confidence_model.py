"""
Match Confidence Model

Stores ML model metadata and parameters for match confidence prediction
in the self-learning forensic reconciliation system.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, DECIMAL, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class MatchConfidenceModel(Base):
    """ML models for match confidence prediction"""
    
    __tablename__ = "match_confidence_models"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Model identification
    model_name = Column(String(255), nullable=False, index=True)
    model_type = Column(String(50), nullable=False, index=True)  # xgboost, neural_network, etc.
    model_version = Column(Integer, default=1)  # Version number for model updates
    
    # Model configuration
    model_config = Column(JSON)  # Model hyperparameters and configuration
    feature_list = Column(JSON)  # List of features used by the model
    
    # Model storage
    model_path = Column(String(500))  # Path to serialized model file
    model_binary = Column(Text)  # Base64 encoded model (for small models)
    
    # Performance metrics
    training_accuracy = Column(DECIMAL(5, 2))  # Training accuracy percentage
    validation_accuracy = Column(DECIMAL(5, 2))  # Validation accuracy percentage
    test_accuracy = Column(DECIMAL(5, 2))  # Test accuracy percentage
    
    # Model statistics
    training_samples = Column(Integer, default=0)  # Number of training samples
    prediction_count = Column(Integer, default=0)  # Number of predictions made
    average_prediction_time = Column(DECIMAL(10, 4))  # Average prediction time in seconds
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_production = Column(Boolean, default=False)  # Is this the production model
    
    # Metadata
    trained_at = Column(DateTime(timezone=True), server_default=func.now())
    trained_by = Column(String(100))  # System or user who trained the model
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_model_type_active', 'model_type', 'is_active'),
        Index('idx_model_production', 'is_production', 'is_active'),
    )

