"""
E5-S3: Validation run tracking for deterministic, versioned rule execution.

Each validation run records inputs (upload_id), rule version snapshot, and timestamps.
Enables reproducible reruns and audit trail.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.db.database import Base


class ValidationRun(Base):
    """Tracks each validation run for reproducibility (E5-S3)."""

    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("document_uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    # Snapshot of rule versions at run time (JSON or hash) for reproducibility
    rules_version_hash = Column(String(64), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # Optional: store rule IDs/versions as JSON for audit
    rules_snapshot = Column(Text, nullable=True)
    total_rules = Column(Integer, nullable=True)
    passed_count = Column(Integer, nullable=True)
    failed_count = Column(Integer, nullable=True)
