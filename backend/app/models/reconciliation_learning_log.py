"""
Reconciliation Learning Log Model

Tracks learning activities and improvements in the self-learning
forensic reconciliation system.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, DECIMAL, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ReconciliationLearningLog(Base):
    """Tracks learning activities and improvements"""
    
    __tablename__ = "reconciliation_learning_log"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Activity identification
    activity_type = Column(String(50), nullable=False, index=True)  # pattern_discovery, rule_creation, model_training, etc.
    activity_name = Column(String(255), nullable=False)
    
    # Context
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='SET NULL'), nullable=True, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='SET NULL'), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey('forensic_reconciliation_sessions.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Activity details
    description = Column(Text)  # Human-readable description
    activity_data = Column(JSON)  # Structured activity data
    
    # Results
    result_type = Column(String(50))  # success, failure, partial
    result_summary = Column(Text)  # Summary of results
    result_data = Column(JSON)  # Structured result data
    
    # Impact metrics
    matches_improved = Column(Integer, default=0)  # Number of matches improved
    rules_created = Column(Integer, default=0)  # Number of rules created
    patterns_discovered = Column(Integer, default=0)  # Number of patterns discovered
    confidence_improvement = Column(DECIMAL(5, 2), default=0.0)  # Confidence improvement percentage
    
    # Execution metadata
    execution_time_ms = Column(Integer)  # Execution time in milliseconds
    triggered_by = Column(String(50))  # manual, scheduled, automatic
    
    # Status
    is_successful = Column(Boolean, default=True, index=True)
    error_message = Column(Text, nullable=True)  # Error message if failed
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    __table_args__ = (
        Index('idx_learning_log_type_date', 'activity_type', 'created_at'),
        Index('idx_learning_log_property_period', 'property_id', 'period_id'),
        Index('idx_learning_log_success', 'is_successful', 'created_at'),
    )

