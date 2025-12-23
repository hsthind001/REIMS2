"""
Scheduled Task Model

Stores user-scheduled tasks for future execution or recurring schedules.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.db.database import Base


class ScheduleType(str, enum.Enum):
    """Schedule type enum"""
    ONCE = "once"
    RECURRING = "recurring"


class TaskStatus(str, enum.Enum):
    """Task status enum"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledTask(Base):
    """
    Scheduled Task Model
    
    Stores user-scheduled tasks for future execution or recurring schedules.
    """
    __tablename__ = "scheduled_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Task details
    task_type = Column(String(100), nullable=False, index=True)  # e.g., 'extract_document', 'anomaly_detection'
    schedule_type = Column(SQLEnum(ScheduleType), nullable=False)
    task_name = Column(String(200), nullable=True)  # User-friendly name
    
    # Scheduling
    scheduled_time = Column(DateTime(timezone=True), nullable=True)  # For 'once' type
    cron_expression = Column(String(100), nullable=True)  # For 'recurring' type (e.g., "0 2 * * *")
    celery_beat_schedule_id = Column(String(200), nullable=True, unique=True)  # Celery Beat schedule ID
    
    # Task parameters (stored as JSON string, can be parsed)
    parameters = Column(Text, nullable=True)  # JSON string of task parameters
    
    # Status tracking
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING, index=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    run_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    # User tracking
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    creator = relationship("User", backref="scheduled_tasks")
    
    def __repr__(self):
        return f"<ScheduledTask(id={self.id}, task_type='{self.task_type}', schedule_type='{self.schedule_type}')>"

