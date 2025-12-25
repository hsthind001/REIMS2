"""
Filename Pattern Learning Service

Self-learning system for filename → period detection.
Learns patterns from successful uploads and applies them to future uploads.
"""

from sqlalchemy.orm import Session
from app.models.filename_period_pattern import FilenamePeriodPattern
import re
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FilenamePatternLearningService:
    """
    Learn and apply filename → period detection patterns.

    This service:
    1. Captures successful uploads and their filename → period mappings
    2. Identifies recurring patterns
    3. Applies learned patterns to future uploads
    4. Adjusts confidence based on success rate
    """

    def __init__(self, db: Session):
        self.db = db

    def learn_from_upload(
        self,
        filename: str,
        detected_month: int,
        detected_year: int,
        property_id: int,
        document_type: str,
        detection_method: str,  # 'filename_range', 'pdf_content', 'manual', 'user_correction'
        was_correct: Optional[bool] = None
    ):
        """
        Learn a pattern from an upload.

        Args:
            filename: Original filename
            detected_month: Month that was used
            detected_year: Year that was used
            property_id: Property ID
            document_type: Document type
            detection_method: How month was detected
            was_correct: If known, whether this detection was correct (None = assumed correct)
        """
        try:
            # Extract pattern from filename
            pattern = self._extract_pattern(filename)
            if not pattern:
                logger.warning(f"Could not extract pattern from filename: {filename}")
                return

            # Check if pattern exists
            existing = self.db.query(FilenamePeriodPattern).filter(
                FilenamePeriodPattern.filename_pattern == pattern,
                FilenamePeriodPattern.property_id == property_id,
                FilenamePeriodPattern.document_type == document_type
            ).first()

            if existing:
                # Update existing pattern
                existing.times_seen += 1
                existing.last_seen_at = datetime.now()

                if was_correct is not None:
                    if was_correct:
                        existing.times_correct += 1
                    else:
                        existing.times_incorrect += 1
                elif was_correct is None:
                    # Assume correct if not specified
                    existing.times_correct += 1

                logger.info(f"Updated pattern: {pattern} (seen {existing.times_seen} times, {existing.success_rate:.1f}% success)")
            else:
                # Create new pattern
                new_pattern = FilenamePeriodPattern(
                    pattern_type=self._classify_pattern(pattern),
                    filename_pattern=pattern,
                    example_filename=filename,
                    detected_month=detected_month,
                    detected_year=detected_year,
                    property_id=property_id,
                    document_type=document_type,
                    times_seen=1,
                    times_correct=1 if (was_correct is None or was_correct) else 0,
                    times_incorrect=0 if (was_correct is None or was_correct) else 1,
                    metadata={
                        "detection_method": detection_method,
                        "first_seen_filename": filename,
                        "learned_at": datetime.now().isoformat()
                    }
                )
                self.db.add(new_pattern)
                logger.info(f"Learned new pattern: {pattern} from {filename}")

            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to learn pattern from {filename}: {e}")
            self.db.rollback()

    def apply_learned_pattern(
        self,
        filename: str,
        property_id: int,
        document_type: str
    ) -> Optional[Dict]:
        """
        Try to apply a learned pattern to this filename.

        Returns:
            {
                "month": int,
                "year": int,
                "confidence": float,
                "pattern": str,
                "success_rate": float,
                "times_seen": int,
                "source": "learned_pattern"
            }
            or None if no pattern matches
        """
        try:
            pattern = self._extract_pattern(filename)
            if not pattern:
                return None

            # Find matching pattern
            learned = self.db.query(FilenamePeriodPattern).filter(
                FilenamePeriodPattern.filename_pattern == pattern,
                FilenamePeriodPattern.property_id == property_id,
                FilenamePeriodPattern.document_type == document_type
            ).order_by(
                FilenamePeriodPattern.times_seen.desc()
            ).first()

            if learned and learned.times_seen >= 2:  # Must be seen at least twice
                # Calculate confidence based on success rate and times seen
                success_rate = learned.success_rate
                confidence = min(success_rate, 95)

                # Boost confidence if seen many times
                if learned.times_seen >= 10:
                    confidence = min(confidence + 5, 99)

                # Only use if success rate is decent (>= 70%)
                if success_rate >= 70:
                    logger.info(f"Applied learned pattern: {pattern} ({success_rate:.1f}% success, seen {learned.times_seen} times)")
                    return {
                        "month": learned.detected_month,
                        "year": learned.detected_year,
                        "confidence": float(confidence),
                        "pattern": learned.filename_pattern,
                        "success_rate": float(success_rate),
                        "times_seen": learned.times_seen,
                        "source": "learned_pattern"
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to apply learned pattern: {e}")
            return None

    def _extract_pattern(self, filename: str) -> Optional[str]:
        """
        Extract a reusable pattern from filename.

        Examples:
        - "Income_Statement_esp_Accrual-5.25-6.25.pdf" → "Income_Statement_*_Accrual-{M}.{YY}-{M}.{YY}.pdf"
        - "Cash_Flow_esp_Accrual-12.24-1.25.pdf" → "Cash_Flow_*_Accrual-{M}.{YY}-{M}.{YY}.pdf"
        - "RentRoll-1.25.pdf" → "RentRoll-{M}.{YY}.pdf"
        - "2024.01.06 esp wells fargo loan 1008.pdf" → "{YYYY}.{MM}.{DD} * wells fargo loan *.pdf"
        """
        # Replace property code (3-10 uppercase letters followed by 3+ digits)
        pattern = re.sub(r'\b[A-Z]{3,10}\d{3,}\b', '*', filename, flags=re.IGNORECASE)

        # Replace period range with tokens (MM.YY-MM.YY or MM-YY-MM-YY)
        pattern = re.sub(r'\d{1,2}\.\d{2}-\d{1,2}\.\d{2}', '{M}.{YY}-{M}.{YY}', pattern)
        pattern = re.sub(r'\d{1,2}-\d{2}-\d{1,2}-\d{2}(?!\.)', '{M}-{YY}-{M}-{YY}', pattern)

        # Replace full date formats (YYYY.MM.DD or YYYY-MM-DD or MM.DD.YYYY)
        pattern = re.sub(r'\d{4}[\.\-]\d{1,2}[\.\-]\d{1,2}', '{YYYY}.{MM}.{DD}', pattern)
        pattern = re.sub(r'\d{1,2}[\.\-]\d{1,2}[\.\-]\d{4}', '{MM}.{DD}.{YYYY}', pattern)

        # Replace single month-year (MM.YY or MM.YYYY or MM/YY)
        pattern = re.sub(r'\d{1,2}\.\d{2,4}', '{M}.{YY}', pattern)
        pattern = re.sub(r'\d{1,2}/\d{2,4}', '{M}/{YY}', pattern)

        # Replace standalone numbers (like "1008" in loan number)
        pattern = re.sub(r'\b\d{3,}\b', '*', pattern)

        return pattern if pattern != filename else None

    def _classify_pattern(self, pattern: str) -> str:
        """Classify pattern type."""
        if '{M}.{YY}-{M}.{YY}' in pattern or '{M}-{YY}-{M}-{YY}' in pattern or '{M}/{YY}-{M}/{YY}' in pattern:
            return 'period_range'
        elif '{YYYY}.{MM}.{DD}' in pattern or '{MM}.{DD}.{YYYY}' in pattern:
            return 'full_date'
        elif '{M}.{YY}' in pattern or '{M}/{YY}' in pattern:
            return 'single_month'
        else:
            return 'unknown'

    def get_pattern_statistics(self, property_id: Optional[int] = None, document_type: Optional[str] = None) -> Dict:
        """
        Get statistics about learned patterns.

        Returns:
            {
                "total_patterns": int,
                "average_success_rate": float,
                "total_uploads_learned": int,
                "patterns": [...]
            }
        """
        try:
            query = self.db.query(FilenamePeriodPattern)

            if property_id:
                query = query.filter(FilenamePeriodPattern.property_id == property_id)
            if document_type:
                query = query.filter(FilenamePeriodPattern.document_type == document_type)

            patterns = query.all()

            if not patterns:
                return {
                    "total_patterns": 0,
                    "average_success_rate": 0.0,
                    "total_uploads_learned": 0,
                    "patterns": []
                }

            total_uploads = sum(p.times_seen for p in patterns)
            avg_success_rate = sum(p.success_rate * p.times_seen for p in patterns) / total_uploads if total_uploads > 0 else 0

            return {
                "total_patterns": len(patterns),
                "average_success_rate": round(avg_success_rate, 2),
                "total_uploads_learned": total_uploads,
                "patterns": [
                    {
                        "pattern": p.filename_pattern,
                        "pattern_type": p.pattern_type,
                        "example": p.example_filename,
                        "success_rate": round(p.success_rate, 2),
                        "times_seen": p.times_seen,
                        "document_type": p.document_type
                    }
                    for p in sorted(patterns, key=lambda x: x.times_seen, reverse=True)
                ]
            }

        except Exception as e:
            logger.error(f"Failed to get pattern statistics: {e}")
            return {
                "total_patterns": 0,
                "average_success_rate": 0.0,
                "total_uploads_learned": 0,
                "patterns": [],
                "error": str(e)
            }
