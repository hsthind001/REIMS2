"""
Batch Reprocessing Job Model

Tracks batch reprocessing jobs for anomaly detection with progress monitoring.
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.database import Base


class BatchReprocessingJob(Base):
    """
    Track batch reprocessing jobs for anomaly detection.
    
    Allows reprocessing of historical documents with filtering,
    progress tracking, and async execution via Celery.
    """
    
    __tablename__ = "batch_reprocessing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Job Configuration (E2-S3: org-scoped for WebSocket/tenant isolation)
    job_name = Column(String(255), nullable=True)
    initiated_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True)
    
    # Filters
    property_ids = Column(JSONB, nullable=True)  # Array of property IDs to reprocess
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)
    document_types = Column(JSONB, nullable=True)  # Array of document types
    extraction_status_filter = Column(String(50), nullable=True)  # 'all', 'completed', 'failed'
    
    # Job Status
    status = Column(String(50), server_default='queued', nullable=False, index=True)  # queued, running, completed, failed, cancelled
    celery_task_id = Column(String(255), nullable=True)  # Celery task ID for async execution
    
    # Progress Tracking
    total_documents = Column(Integer, server_default='0', nullable=False)
    processed_documents = Column(Integer, server_default='0', nullable=False)
    successful_count = Column(Integer, server_default='0', nullable=False)
    failed_count = Column(Integer, server_default='0', nullable=False)
    skipped_count = Column(Integer, server_default='0', nullable=False)
    
    # Results
    results_summary = Column(JSONB, nullable=True)  # Summary of results (anomalies found, errors, etc.)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_completion_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    user = relationship("User", backref="batch_jobs")
    
    def __repr__(self):
        return f"<BatchReprocessingJob(id={self.id}, job_name='{self.job_name}', status='{self.status}', progress={self.processed_documents}/{self.total_documents})>"

