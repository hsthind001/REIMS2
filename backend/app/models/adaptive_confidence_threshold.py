"""
Adaptive Confidence Threshold Model - Account-specific confidence thresholds
that learn from historical accuracy
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.db.database import Base


class AdaptiveConfidenceThreshold(Base):
    """
    Stores adaptive confidence thresholds per account type.

    Instead of a fixed 85% threshold for all accounts, this learns optimal thresholds
    based on account complexity and historical accuracy.
    """
    __tablename__ = "adaptive_confidence_thresholds"

    id = Column(Integer, primary_key=True, index=True)

    # Account identification
    account_code = Column(String(50), nullable=False, unique=True, index=True)
    account_name = Column(String(255), nullable=False)
    account_category = Column(String(100), nullable=True, index=True)  # Assets, Liabilities, Revenue, etc.

    # Current threshold
    current_threshold = Column(Float, default=85.0, nullable=False)
    original_threshold = Column(Float, default=85.0, nullable=False)

    # Learning statistics
    total_extractions = Column(Integer, default=0, nullable=False)
    successful_extractions = Column(Integer, default=0, nullable=False)  # Approved + auto-approved
    failed_extractions = Column(Integer, default=0, nullable=False)  # Rejected

    # Accuracy tracking
    historical_accuracy = Column(Float, default=1.0, nullable=False)  # success / total
    avg_extraction_confidence = Column(Float, nullable=True)
    min_successful_confidence = Column(Float, nullable=True)  # Lowest confidence that was still correct

    # Complexity assessment
    complexity_score = Column(Float, default=50.0, nullable=False)  # 0-100, higher = more complex
    is_simple_account = Column(Boolean, default=False, nullable=False)  # Cash, basic revenue
    is_complex_account = Column(Boolean, default=False, nullable=False)  # AR Other, Construction Mgmt

    # Adaptive learning
    adjustment_count = Column(Integer, default=0, nullable=False)
    last_adjustment_date = Column(DateTime(timezone=True), nullable=True)
    last_adjustment_amount = Column(Float, nullable=True)  # How much threshold changed

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AdaptiveThreshold(account={self.account_code}, threshold={self.current_threshold:.1f}%, accuracy={self.historical_accuracy:.2%})>"

    def calculate_accuracy(self) -> float:
        """Calculate current accuracy rate"""
        if self.total_extractions == 0:
            return 1.0
        return self.successful_extractions / self.total_extractions

    def assess_complexity(self):
        """
        Assess account complexity based on:
        - Historical accuracy (lower = more complex)
        - Confidence variance (higher variance = more complex)
        - Frequency of rejections
        """
        base_complexity = 50.0

        # Factor 1: Low accuracy suggests complexity
        accuracy = self.calculate_accuracy()
        if accuracy < 0.7:
            base_complexity += 30
        elif accuracy < 0.85:
            base_complexity += 15

        # Factor 2: Frequent rejections
        if self.total_extractions > 5:
            rejection_rate = self.failed_extractions / self.total_extractions
            if rejection_rate > 0.3:
                base_complexity += 20
            elif rejection_rate > 0.15:
                base_complexity += 10

        # Factor 3: Low successful confidence suggests difficult extraction
        if self.min_successful_confidence and self.min_successful_confidence < 80:
            base_complexity += 15

        self.complexity_score = min(100, base_complexity)

        # Classify account
        if self.complexity_score < 30:
            self.is_simple_account = True
            self.is_complex_account = False
        elif self.complexity_score > 70:
            self.is_simple_account = False
            self.is_complex_account = True
        else:
            self.is_simple_account = False
            self.is_complex_account = False

    def adjust_threshold(self):
        """
        Intelligently adjust confidence threshold based on performance.

        Logic:
        - High accuracy (>95%) + low min_confidence → LOWER threshold (be less strict)
        - Low accuracy (<80%) → RAISE threshold (be more strict)
        - Complex accounts → LOWER threshold (don't over-penalize difficult accounts)
        - Simple accounts → Keep HIGH threshold (should extract perfectly)
        """
        if self.total_extractions < 5:
            return  # Need more data

        accuracy = self.calculate_accuracy()
        old_threshold = self.current_threshold

        # Case 1: High accuracy - we can be more lenient
        if accuracy >= 0.95 and self.min_successful_confidence:
            # Lower threshold to min_successful_confidence - 2%
            suggested_threshold = max(75.0, self.min_successful_confidence - 2.0)
            self.current_threshold = min(self.current_threshold, suggested_threshold)

        # Case 2: Low accuracy - be more strict
        elif accuracy < 0.80:
            # Raise threshold by 2%
            self.current_threshold = min(95.0, self.current_threshold + 2.0)

        # Case 3: Complex account with moderate accuracy - be lenient
        elif self.is_complex_account and accuracy >= 0.85:
            self.current_threshold = max(75.0, self.current_threshold - 3.0)

        # Case 4: Simple account - maintain high standards
        elif self.is_simple_account:
            self.current_threshold = max(85.0, self.current_threshold)

        # Record adjustment
        if abs(self.current_threshold - old_threshold) > 0.1:
            self.adjustment_count += 1
            self.last_adjustment_amount = self.current_threshold - old_threshold
            self.last_adjustment_date = func.now()

    def record_extraction(self, confidence: float, success: bool):
        """Record an extraction attempt and learn from it"""
        self.total_extractions += 1

        if success:
            self.successful_extractions += 1
            # Track minimum successful confidence
            if self.min_successful_confidence is None or confidence < self.min_successful_confidence:
                self.min_successful_confidence = confidence
        else:
            self.failed_extractions += 1

        # Update average confidence
        if self.avg_extraction_confidence is None:
            self.avg_extraction_confidence = confidence
        else:
            self.avg_extraction_confidence = (
                (self.avg_extraction_confidence * (self.total_extractions - 1) + confidence) /
                self.total_extractions
            )

        # Update historical accuracy
        self.historical_accuracy = self.calculate_accuracy()

        # Reassess complexity and adjust threshold every 10 extractions
        if self.total_extractions % 10 == 0:
            self.assess_complexity()
            self.adjust_threshold()

        self.updated_at = func.now()

    def should_flag_for_review(self, confidence: float) -> bool:
        """Determine if extraction should be flagged based on adaptive threshold"""
        return confidence < self.current_threshold

    def get_recommendation(self) -> str:
        """Get human-readable recommendation for this account"""
        if self.is_simple_account:
            return f"Simple account - maintaining high threshold ({self.current_threshold:.1f}%)"
        elif self.is_complex_account:
            return f"Complex account - adjusted threshold to {self.current_threshold:.1f}% (was {self.original_threshold:.1f}%)"
        else:
            accuracy_pct = self.historical_accuracy * 100
            return f"Accuracy: {accuracy_pct:.1f}% - Current threshold: {self.current_threshold:.1f}%"
