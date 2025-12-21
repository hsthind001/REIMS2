"""
PyOD Model Selection Log Model

Logs LLM-powered model selection decisions for PyOD anomaly detection algorithms.
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base


class PyODModelSelectionLog(Base):
    """
    Log LLM-powered model selection decisions.
    
    Tracks which PyOD algorithm was selected and why,
    enabling learning and improvement of model selection.
    """
    
    __tablename__ = "pyod_model_selection_log"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Selection Context
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=True, index=True)
    account_code = Column(String(50), nullable=True, index=True)
    data_characteristics = Column(JSONB, nullable=True)  # Sample size, feature count, seasonality, etc.
    
    # LLM Selection
    llm_recommended_models = Column(JSONB, nullable=True)  # Array of recommended models from LLM
    selected_model = Column(String(50), nullable=True, index=True)  # Actually selected model
    selection_reasoning = Column(Text, nullable=True)  # LLM reasoning for selection
    
    # Model Performance
    cross_validation_score = Column(Numeric(5, 4), nullable=True)  # Cross-validation score
    actual_precision = Column(Numeric(5, 4), nullable=True)  # Actual precision on test data
    actual_recall = Column(Numeric(5, 4), nullable=True)  # Actual recall on test data
    
    # Metadata
    selected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    property = relationship("Property", backref="model_selections")
    
    def __repr__(self):
        return f"<PyODModelSelectionLog(id={self.id}, selected_model='{self.selected_model}', property_id={self.property_id})>"

