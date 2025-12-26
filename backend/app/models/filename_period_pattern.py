"""
Filename Period Pattern Model

Self-learning pattern recognition for filename → period detection.
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime


class FilenamePeriodPattern(Base):
    """
    Learned patterns for filename → period detection.

    This table stores patterns learned from successful uploads and their
    filename → period mappings. The system uses these patterns to auto-detect
    periods for future uploads with similar filename patterns.

    Example:
    - Pattern: "Income_Statement_*_Accrual-{M}.{YY}-{M}.{YY}.pdf"
    - Example: "Income_Statement_esp_Accrual-5.25-6.25.pdf"
    - Detected: Month 6, Year 2025 (ending period)
    - Times seen: 12, Times correct: 11 → 91.7% success rate
    """

    __tablename__ = "filename_period_patterns"

    id = Column(Integer, primary_key=True, index=True)

    # Pattern information
    pattern_type = Column(String(50), nullable=False, comment="period_range, single_month, fiscal_year")
    filename_pattern = Column(String(200), nullable=False, comment="Regex pattern extracted from filename")
    example_filename = Column(String(255), nullable=True, comment="Example filename that matches this pattern")

    # Detection results
    detected_month = Column(Integer, nullable=True, comment="Month detected (1-12)")
    detected_year = Column(Integer, nullable=True, comment="Year detected")
    confidence = Column(Numeric(5, 2), nullable=False, server_default="100.0")

    # Success tracking
    times_seen = Column(Integer, nullable=False, server_default="1", comment="Number of times this pattern was encountered")
    times_correct = Column(Integer, nullable=False, server_default="0", comment="Number of times detection was correct")
    times_incorrect = Column(Integer, nullable=False, server_default="0", comment="Number of times detection was incorrect")

    # Context
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=True)
    document_type = Column(String(50), nullable=True)

    # Timestamps
    learned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Additional metadata
    extra_data = Column(JSONB, nullable=True, comment="Additional metadata like detection_method, first_seen_filename")

    # Relationships
    property_obj = relationship("Property", back_populates="filename_patterns")

    # Calculated property for success rate
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.times_seen == 0:
            return 0.0
        return (self.times_correct / self.times_seen) * 100.0

    def __repr__(self):
        return f"<FilenamePeriodPattern(id={self.id}, pattern='{self.filename_pattern}', success_rate={self.success_rate:.1f}%)>"

    # Indexes
    __table_args__ = (
        Index('idx_filename_patterns_property', 'property_id', 'document_type'),
        {'comment': 'Self-learning filename pattern recognition for period detection'}
    )
