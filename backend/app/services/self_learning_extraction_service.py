"""
Self-Learning Extraction Service

Implements intelligent, adaptive extraction validation with 4 layers:
1. Adaptive Confidence Thresholds
2. Pattern Learning & Auto-Correction
3. Fuzzy Account Matching
4. Ensemble Confidence Boosting

This service reduces false positives and automatically improves over time.
"""
import logging
from typing import Optional, Dict, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from difflib import SequenceMatcher
from datetime import datetime, timedelta

from app.models.extraction_learning_pattern import ExtractionLearningPattern
from app.models.adaptive_confidence_threshold import AdaptiveConfidenceThreshold
from app.models.chart_of_accounts import ChartOfAccounts

logger = logging.getLogger(__name__)


class SelfLearningExtractionService:
    """
    Intelligent service that learns from user corrections and automatically improves
    extraction validation over time.
    """

    def __init__(self, db: Session):
        self.db = db
        self.fuzzy_match_threshold = 0.85  # 85% similarity for fuzzy matching
        self.pattern_learning_enabled = True
        self.adaptive_thresholds_enabled = True
        self.fuzzy_matching_enabled = True
        self.ensemble_boosting_enabled = True

    # ==================== LAYER 1: ADAPTIVE CONFIDENCE THRESHOLDS ====================

    def get_adaptive_threshold(self, account_code: str, account_name: str,
                                account_category: Optional[str] = None) -> float:
        """
        Get adaptive confidence threshold for a specific account.

        Returns account-specific threshold instead of fixed 85%.
        Creates new threshold entry if account hasn't been seen before.
        """
        if not self.adaptive_thresholds_enabled:
            return 85.0

        threshold = self.db.query(AdaptiveConfidenceThreshold).filter(
            AdaptiveConfidenceThreshold.account_code == account_code
        ).first()

        if not threshold:
            # Create new threshold entry for this account
            threshold = AdaptiveConfidenceThreshold(
                account_code=account_code,
                account_name=account_name,
                account_category=account_category,
                current_threshold=85.0,
                original_threshold=85.0
            )
            self.db.add(threshold)
            self.db.commit()
            logger.info(f"Created new adaptive threshold for account {account_code}")

        return threshold.current_threshold

    def record_extraction_result(self, account_code: str, account_name: str,
                                 confidence: float, success: bool):
        """
        Record extraction result and let adaptive threshold learn from it.

        Args:
            account_code: Account code extracted
            confidence: Extraction confidence (0-100)
            success: Whether user approved (True) or rejected (False) the extraction
        """
        threshold = self.db.query(AdaptiveConfidenceThreshold).filter(
            AdaptiveConfidenceThreshold.account_code == account_code
        ).first()

        if not threshold:
            threshold = AdaptiveConfidenceThreshold(
                account_code=account_code,
                account_name=account_name
            )
            self.db.add(threshold)

        threshold.record_extraction(confidence, success)
        self.db.commit()

        logger.info(
            f"Recorded extraction for {account_code}: "
            f"confidence={confidence:.1f}%, success={success}, "
            f"new_threshold={threshold.current_threshold:.1f}%"
        )

    def should_flag_for_review(self, account_code: str, account_name: str,
                               confidence: float, account_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Intelligent decision on whether to flag record for review.

        Uses adaptive thresholds instead of fixed 85%.

        Returns:
            (needs_review, reason)
        """
        # Condition 1: No account match
        if account_id is None or account_code == "UNMATCHED":
            return True, "Account not matched in Chart of Accounts"

        # Condition 2: Below adaptive threshold
        adaptive_threshold = self.get_adaptive_threshold(account_code, account_name)
        if confidence < adaptive_threshold:
            return True, f"Below adaptive threshold ({confidence:.1f}% < {adaptive_threshold:.1f}%)"

        return False, "Passed adaptive threshold validation"

    # ==================== LAYER 2: PATTERN LEARNING & AUTO-CORRECTION ====================

    def get_learning_pattern(self, account_code: str, account_name: str,
                            document_type: str, property_id: Optional[int] = None) -> Optional[ExtractionLearningPattern]:
        """Get existing learning pattern for this account"""
        query = self.db.query(ExtractionLearningPattern).filter(
            and_(
                ExtractionLearningPattern.account_code == account_code,
                ExtractionLearningPattern.document_type == document_type
            )
        )

        # Property-specific pattern takes precedence
        if property_id:
            pattern = query.filter(ExtractionLearningPattern.property_id == property_id).first()
            if pattern:
                return pattern

        # Fall back to global pattern
        return query.filter(ExtractionLearningPattern.property_id.is_(None)).first()

    def check_auto_approve_pattern(self, account_code: str, account_name: str,
                                   document_type: str, confidence: float,
                                   property_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Check if this extraction matches a learned pattern for auto-approval.

        Returns:
            (should_auto_approve, reason)
        """
        if not self.pattern_learning_enabled:
            return False, None

        pattern = self.get_learning_pattern(account_code, account_name, document_type, property_id)

        if pattern and pattern.should_auto_approve(confidence):
            reason = (
                f"Auto-approved by learned pattern: "
                f"{pattern.approved_count + pattern.auto_approved_count}/{pattern.total_occurrences} approvals, "
                f"reliability={pattern.reliability_score:.1%}, "
                f"min_confidence={pattern.auto_approve_threshold:.1f}%"
            )
            logger.info(f"Auto-approving {account_code}: {reason}")
            return True, reason

        return False, None

    def record_review_feedback(self, account_code: str, account_name: str,
                              document_type: str, confidence: float, approved: bool,
                              property_id: Optional[int] = None):
        """
        Record user review feedback to learn patterns.

        When users consistently approve certain extractions, system learns to auto-approve.
        """
        pattern = self.get_learning_pattern(account_code, account_name, document_type, property_id)

        if not pattern:
            # Create new pattern
            pattern = ExtractionLearningPattern(
                account_code=account_code,
                account_name=account_name,
                document_type=document_type,
                property_id=property_id,
                total_occurrences=0
            )
            self.db.add(pattern)

        pattern.update_from_review(approved, confidence)
        self.db.commit()

        logger.info(
            f"Updated pattern for {account_code}: "
            f"approved={approved}, reliability={pattern.reliability_score:.2%}, "
            f"trustworthy={pattern.is_trustworthy}"
        )

    # ==================== LAYER 3: FUZZY ACCOUNT MATCHING ====================

    def fuzzy_match_account(self, account_code: str, account_name: str) -> Optional[Tuple[int, str, float]]:
        """
        Attempt fuzzy matching when exact match fails.

        Uses Levenshtein-style similarity to handle:
        - Typos in account codes
        - Truncated account names
        - Minor variations

        Returns:
            (account_id, matched_code, similarity_score) or None
        """
        if not self.fuzzy_matching_enabled:
            return None

        # Try code-based fuzzy match first
        all_accounts = self.db.query(ChartOfAccounts).all()

        best_match = None
        best_score = 0.0

        for account in all_accounts:
            # Calculate similarity for both code and name
            code_similarity = self._calculate_similarity(account_code, account.account_code)
            name_similarity = self._calculate_similarity(account_name.lower(), account.account_name.lower())

            # Weighted average (code 60%, name 40%)
            combined_score = code_similarity * 0.6 + name_similarity * 0.4

            if combined_score > best_score and combined_score >= self.fuzzy_match_threshold:
                best_score = combined_score
                best_match = (account.id, account.account_code, combined_score)

        if best_match:
            logger.info(
                f"Fuzzy match found for '{account_code}'/'{account_name}': "
                f"matched to '{best_match[1]}' with {best_match[2]:.1%} similarity"
            )

        return best_match

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings (0-1)"""
        return SequenceMatcher(None, str1, str2).ratio()

    # ==================== LAYER 4: ENSEMBLE CONFIDENCE BOOSTING ====================

    def boost_confidence_with_ensemble(self, account_code: str, confidence: float,
                                      extraction_results: Optional[Dict] = None) -> float:
        """
        Boost confidence using ensemble validation.

        Criteria for boosting:
        1. Multiple extraction engines agree (consensus)
        2. Historical temporal consistency (same account last period)
        3. Cross-validation with similar records

        Args:
            account_code: Extracted account code
            confidence: Base confidence from extraction
            extraction_results: Optional dict with multi-engine results

        Returns:
            Boosted confidence (capped at 100)
        """
        if not self.ensemble_boosting_enabled:
            return confidence

        boosted_confidence = confidence
        boost_reasons = []

        # Boost 1: Multi-engine consensus
        if extraction_results and 'engine_results' in extraction_results:
            agreeing_engines = sum(
                1 for result in extraction_results['engine_results']
                if result.get('account_code') == account_code
            )
            if agreeing_engines >= 3:
                boost = min(5.0, agreeing_engines * 1.5)
                boosted_confidence += boost
                boost_reasons.append(f"{agreeing_engines} engines agreed (+{boost:.1f}%)")

        # Boost 2: Temporal consistency (same account appeared recently)
        recent_count = self._count_recent_occurrences(account_code, days=90)
        if recent_count >= 3:
            boost = min(3.0, recent_count * 0.5)
            boosted_confidence += boost
            boost_reasons.append(f"Seen {recent_count}x recently (+{boost:.1f}%)")

        # Boost 3: Historical accuracy for this account
        pattern = self.db.query(ExtractionLearningPattern).filter(
            ExtractionLearningPattern.account_code == account_code,
            ExtractionLearningPattern.reliability_score >= 0.9
        ).first()
        if pattern:
            boost = 4.0
            boosted_confidence += boost
            boost_reasons.append(f"High reliability pattern (+{boost:.1f}%)")

        # Cap at 100
        boosted_confidence = min(100.0, boosted_confidence)

        if boost_reasons:
            logger.info(
                f"Confidence boosted for {account_code}: "
                f"{confidence:.1f}% → {boosted_confidence:.1f}% "
                f"({', '.join(boost_reasons)})"
            )

        return boosted_confidence

    def _count_recent_occurrences(self, account_code: str, days: int = 90) -> int:
        """Count how many times this account appeared in recent extractions"""
        cutoff_date = datetime.now() - timedelta(days=days)

        pattern = self.db.query(ExtractionLearningPattern).filter(
            and_(
                ExtractionLearningPattern.account_code == account_code,
                ExtractionLearningPattern.last_updated_at >= cutoff_date
            )
        ).first()

        return pattern.total_occurrences if pattern else 0

    # ==================== COMPREHENSIVE VALIDATION ====================

    def validate_extraction(self, account_code: str, account_name: str,
                           confidence: float, document_type: str,
                           account_id: Optional[int] = None,
                           property_id: Optional[int] = None,
                           extraction_results: Optional[Dict] = None) -> Dict:
        """
        Comprehensive intelligent validation combining all 4 layers.

        Returns a decision dict with:
        - needs_review: bool
        - auto_approved: bool  (NEW!)
        - confidence: float (possibly boosted)
        - matched_account_id: int (possibly fuzzy matched)
        - validation_path: str (explanation of decision)
        - boost_applied: float
        """
        validation_path = []
        original_confidence = confidence
        matched_account_id = account_id
        auto_approved = False

        # LAYER 4: Ensemble Confidence Boosting (do this first)
        boosted_confidence = self.boost_confidence_with_ensemble(
            account_code, confidence, extraction_results
        )
        if boosted_confidence > confidence:
            validation_path.append(
                f"Confidence boosted: {confidence:.1f}% → {boosted_confidence:.1f}%"
            )
        confidence = boosted_confidence

        # LAYER 3: Fuzzy Account Matching (if no exact match)
        if matched_account_id is None and account_code != "UNMATCHED":
            fuzzy_result = self.fuzzy_match_account(account_code, account_name)
            if fuzzy_result:
                matched_account_id, matched_code, similarity = fuzzy_result
                validation_path.append(
                    f"Fuzzy matched to '{matched_code}' ({similarity:.1%} similarity)"
                )

        # LAYER 2: Pattern Learning & Auto-Correction
        should_auto_approve, auto_reason = self.check_auto_approve_pattern(
            account_code, account_name, document_type, confidence, property_id
        )
        if should_auto_approve:
            auto_approved = True
            validation_path.append(f"Auto-approved: {auto_reason}")
            return {
                'needs_review': False,
                'auto_approved': True,
                'confidence': confidence,
                'matched_account_id': matched_account_id,
                'validation_path': ' → '.join(validation_path),
                'boost_applied': confidence - original_confidence
            }

        # LAYER 1: Adaptive Confidence Thresholds
        needs_review, reason = self.should_flag_for_review(
            account_code, account_name, confidence, matched_account_id
        )
        validation_path.append(reason)

        return {
            'needs_review': needs_review,
            'auto_approved': False,
            'confidence': confidence,
            'matched_account_id': matched_account_id,
            'validation_path': ' → '.join(validation_path),
            'boost_applied': confidence - original_confidence
        }

    # ==================== MONITORING & REPORTING ====================

    def get_learning_statistics(self) -> Dict:
        """Get statistics about the self-learning system"""
        total_patterns = self.db.query(func.count(ExtractionLearningPattern.id)).scalar()
        trustworthy_patterns = self.db.query(func.count(ExtractionLearningPattern.id)).filter(
            ExtractionLearningPattern.is_trustworthy == True
        ).scalar()

        total_thresholds = self.db.query(func.count(AdaptiveConfidenceThreshold.id)).scalar()
        adjusted_thresholds = self.db.query(func.count(AdaptiveConfidenceThreshold.id)).filter(
            AdaptiveConfidenceThreshold.adjustment_count > 0
        ).scalar()

        total_auto_approvals = self.db.query(
            func.sum(ExtractionLearningPattern.auto_approved_count)
        ).scalar() or 0

        return {
            'total_patterns_learned': total_patterns,
            'trustworthy_patterns': trustworthy_patterns,
            'auto_approve_ready': trustworthy_patterns,
            'total_adaptive_thresholds': total_thresholds,
            'adjusted_thresholds': adjusted_thresholds,
            'total_auto_approvals': total_auto_approvals,
            'system_maturity': self._calculate_system_maturity(),
            'estimated_review_reduction': self._estimate_review_reduction()
        }

    def _calculate_system_maturity(self) -> float:
        """Calculate overall system maturity (0-100%)"""
        total_patterns = self.db.query(func.count(ExtractionLearningPattern.id)).scalar()
        if total_patterns == 0:
            return 0.0

        trustworthy = self.db.query(func.count(ExtractionLearningPattern.id)).filter(
            ExtractionLearningPattern.is_trustworthy == True
        ).scalar()

        return min(100.0, (trustworthy / total_patterns) * 100)

    def _estimate_review_reduction(self) -> float:
        """Estimate percentage reduction in manual reviews"""
        total_patterns = self.db.query(ExtractionLearningPattern).all()
        if not total_patterns:
            return 0.0

        total_future_items = sum(p.total_occurrences for p in total_patterns)
        auto_approvable = sum(
            p.total_occurrences for p in total_patterns
            if p.is_trustworthy
        )

        if total_future_items == 0:
            return 0.0

        return (auto_approvable / total_future_items) * 100
