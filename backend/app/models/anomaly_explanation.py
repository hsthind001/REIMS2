"""
Anomaly Explanation Model

Stores XAI explanations (SHAP, LIME, root causes, actions) for anomaly detections.
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base


class AnomalyExplanation(Base):
    """
    Store explainable AI (XAI) explanations for anomaly detections.
    
    Includes:
    - SHAP values (global feature importance)
    - LIME explanations (local interpretable)
    - Root cause analysis
    - Suggested actions
    """
    
    __tablename__ = "anomaly_explanations"
    
    id = Column(Integer, primary_key=True, index=True)
    anomaly_detection_id = Column(Integer, ForeignKey('anomaly_detections.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Root Cause Analysis
    root_cause_type = Column(String(50), nullable=False, index=True)  # trend_break, seasonal_deviation, outlier, etc.
    root_cause_description = Column(Text, nullable=False)
    contributing_factors = Column(JSONB, nullable=True)  # JSON array of contributing factors
    
    # SHAP Values (Global Feature Importance)
    shap_values = Column(JSONB, nullable=True)  # SHAP values for each feature
    shap_base_value = Column(Numeric(10, 4), nullable=True)  # Base value from SHAP
    shap_feature_importance = Column(JSONB, nullable=True)  # Feature importance rankings
    
    # LIME Explanation (Local Interpretable)
    lime_explanation = Column(JSONB, nullable=True)  # LIME explanation data
    lime_intercept = Column(Numeric(10, 4), nullable=True)  # LIME intercept
    lime_score = Column(Numeric(5, 4), nullable=True)  # LIME score
    
    # Suggested Actions
    suggested_actions = Column(JSONB, nullable=True)  # Array of suggested actions
    action_category = Column(String(50), nullable=True)  # Category of actions (investigate, review, etc.)
    
    # Metadata
    explanation_generated_at = Column(DateTime(timezone=True), nullable=True)
    explanation_method = Column(String(20), nullable=True)  # 'shap', 'lime', 'both'
    computation_time_ms = Column(Integer, nullable=True)  # Time taken to generate explanation
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    anomaly_detection = relationship("AnomalyDetection", backref="explanations")
    
    def __repr__(self):
        return f"<AnomalyExplanation(id={self.id}, root_cause_type='{self.root_cause_type}', method='{self.explanation_method}')>"

