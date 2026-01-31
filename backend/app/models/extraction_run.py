"""
ExtractionRun - Master JSON chain-of-custody for multi-LLM extraction (AbeAI-style).
Stores run_id, document_upload_id, extraction_log_id, and full master_json per run.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class ExtractionRun(Base):
    """
    Tracks each extraction run with full Master JSON for audit and reproducibility.
    Master JSON sections: header, extraction, candidates, evidence, validation, decision, telemetry.
    """
    __tablename__ = "extraction_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(36), nullable=False, unique=True, index=True)  # UUID as string
    document_upload_id = Column(Integer, ForeignKey("document_uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    extraction_log_id = Column(Integer, ForeignKey("extraction_logs.id", ondelete="SET NULL"), nullable=True, index=True)

    # Full Master JSON (header, extraction, candidates, evidence, validation, decision, telemetry)
    master_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    document_upload = relationship("DocumentUpload", back_populates="extraction_run")
    extraction_log = relationship("ExtractionLog", backref="extraction_run")
