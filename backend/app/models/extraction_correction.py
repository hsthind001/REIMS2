"""
Extraction Correction Model - Active Learning feedback
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class ExtractionCorrection(Base):
    """
    Extraction Corrections - Active learning feedback loop

    Captures human corrections to improve future extractions
    """
    __tablename__ = "extraction_corrections"

    id = Column(Integer, primary_key=True, index=True)
    field_metadata_id = Column(
        Integer,
        ForeignKey("extraction_field_metadata.id", ondelete="SET NULL"),
        nullable=True
    )
    original_value = Column(Text, nullable=True, comment="Original extracted value")
    corrected_value = Column(Text, nullable=True, comment="Human-corrected value")
    correction_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of correction: account_code, amount, account_name, etc."
    )
    corrected_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    corrected_at = Column(DateTime, server_default=func.now())
    confidence_before = Column(Numeric(5, 4), nullable=True, comment="Confidence before correction")
    pattern_detected = Column(JSONB, nullable=True, comment="Detected pattern for future learning")
    applied_to_future = Column(Boolean, default=False, comment="Whether pattern has been applied to future extractions")

    # Relationships
    field_metadata = relationship("ExtractionFieldMetadata", back_populates="corrections")
    user = relationship("User")

    def __repr__(self):
        return f"<ExtractionCorrection(id={self.id}, type={self.correction_type}, applied={self.applied_to_future})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'field_metadata_id': self.field_metadata_id,
            'original_value': self.original_value,
            'corrected_value': self.corrected_value,
            'correction_type': self.correction_type,
            'corrected_by': self.corrected_by,
            'corrected_at': self.corrected_at.isoformat() if self.corrected_at else None,
            'confidence_before': float(self.confidence_before) if self.confidence_before else None,
            'pattern_detected': self.pattern_detected,
            'applied_to_future': self.applied_to_future
        }

    @classmethod
    def detect_pattern(cls, corrections: list) -> dict:
        """
        Detect patterns from multiple corrections

        For example:
        - Common OCR errors (0 vs O, 1 vs I)
        - Consistent account code mappings
        - Formatting patterns
        """
        if len(corrections) < 3:
            return None

        # Simple pattern detection
        patterns = {
            'correction_type': corrections[0].correction_type,
            'frequency': len(corrections),
            'examples': [
                {
                    'original': c.original_value,
                    'corrected': c.corrected_value
                }
                for c in corrections[:5]
            ]
        }

        return patterns
