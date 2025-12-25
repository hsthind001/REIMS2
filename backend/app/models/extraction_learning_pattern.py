"""
Extraction Learning Pattern Model - Tracks user corrections and approval patterns
for intelligent self-learning and auto-correction
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class ExtractionLearningPattern(Base):
    """
    Stores learned patterns from user reviews to enable intelligent auto-correction.

    When users consistently approve certain extractions (e.g., "A/R Other" at 82% confidence),
    the system learns to trust similar patterns in the future.
    """
    __tablename__ = "extraction_learning_patterns"

    id = Column(Integer, primary_key=True, index=True)

    # Pattern identification
    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(255), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)  # balance_sheet, income_statement, etc.
    property_id = Column(Integer, index=True)  # Optional: property-specific patterns

    # Pattern statistics
    total_occurrences = Column(Integer, default=1, nullable=False)
    approved_count = Column(Integer, default=0, nullable=False)
    rejected_count = Column(Integer, default=0, nullable=False)
    auto_approved_count = Column(Integer, default=0, nullable=False)

    # Confidence metrics
    min_confidence_seen = Column(Float, nullable=True)
    max_confidence_seen = Column(Float, nullable=True)
    avg_confidence = Column(Float, nullable=True)

    # Learning thresholds
    learned_confidence_threshold = Column(Float, default=85.0, nullable=False)
    auto_approve_threshold = Column(Float, default=80.0, nullable=True)  # Learned from patterns

    # Pattern strength and reliability
    pattern_strength = Column(Float, default=0.0, nullable=False)  # 0-100 score
    reliability_score = Column(Float, default=0.0, nullable=False)  # approved / total
    is_trustworthy = Column(Boolean, default=False, nullable=False, index=True)  # Auto-approve ready

    # Learning metadata
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_approved_at = Column(DateTime(timezone=True), nullable=True)
    last_rejected_at = Column(DateTime(timezone=True), nullable=True)

    # Additional pattern data
    common_variations = Column(JSON, nullable=True)  # Store name variations
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ExtractionLearningPattern(account={self.account_code}, trustworthy={self.is_trustworthy}, reliability={self.reliability_score:.2f})>"

    def calculate_reliability(self):
        """Calculate reliability score (approved / total)"""
        if self.total_occurrences == 0:
            return 0.0
        return (self.approved_count + self.auto_approved_count) / self.total_occurrences

    def calculate_pattern_strength(self):
        """
        Calculate pattern strength based on:
        - Number of occurrences (more = stronger)
        - Reliability score (higher = stronger)
        - Consistency (lower confidence variance = stronger)
        """
        if self.total_occurrences < 3:
            return 0.0

        # Base strength from occurrences (capped at 40 points)
        occurrence_score = min(40, self.total_occurrences * 4)

        # Reliability contributes up to 40 points
        reliability_score = self.calculate_reliability() * 40

        # Consistency score (up to 20 points)
        consistency_score = 0
        if self.min_confidence_seen and self.max_confidence_seen:
            confidence_variance = self.max_confidence_seen - self.min_confidence_seen
            consistency_score = max(0, 20 - confidence_variance)

        return min(100, occurrence_score + reliability_score + consistency_score)

    def should_auto_approve(self, confidence: float) -> bool:
        """
        Determine if a record should be auto-approved based on learned patterns.

        Criteria:
        - Pattern is marked as trustworthy
        - Confidence is above learned threshold
        - Pattern has sufficient occurrences (5+)
        - Reliability score > 0.8 (80% approval rate)
        """
        if not self.is_trustworthy:
            return False

        if self.total_occurrences < 5:
            return False

        if self.calculate_reliability() < 0.8:
            return False

        if self.auto_approve_threshold and confidence >= self.auto_approve_threshold:
            return True

        return False

    def update_from_review(self, approved: bool, confidence: float):
        """Update pattern statistics after a review"""
        self.total_occurrences += 1

        if approved:
            self.approved_count += 1
            self.last_approved_at = func.now()
        else:
            self.rejected_count += 1
            self.last_rejected_at = func.now()

        # Update confidence ranges
        if self.min_confidence_seen is None or confidence < self.min_confidence_seen:
            self.min_confidence_seen = confidence

        if self.max_confidence_seen is None or confidence > self.max_confidence_seen:
            self.max_confidence_seen = confidence

        # Update average confidence
        if self.avg_confidence is None:
            self.avg_confidence = confidence
        else:
            self.avg_confidence = (self.avg_confidence * (self.total_occurrences - 1) + confidence) / self.total_occurrences

        # Recalculate scores
        self.reliability_score = self.calculate_reliability()
        self.pattern_strength = self.calculate_pattern_strength()

        # Update trustworthy status
        # Criteria: 5+ occurrences, 80%+ reliability, 60+ pattern strength
        if (self.total_occurrences >= 5 and
            self.reliability_score >= 0.8 and
            self.pattern_strength >= 60):
            self.is_trustworthy = True
            # Set auto-approve threshold to min_confidence - 2%
            if self.min_confidence_seen:
                self.auto_approve_threshold = max(75.0, self.min_confidence_seen - 2.0)

        self.last_updated_at = func.now()
