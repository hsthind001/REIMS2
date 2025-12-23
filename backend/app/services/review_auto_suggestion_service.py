"""
Review Auto-Suggestion Service

Learns from user corrections and auto-suggests account mappings with confidence scores.
"""

from typing import Dict, Optional, Any, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import logging

from app.models.chart_of_accounts import ChartOfAccounts

logger = logging.getLogger(__name__)


class ReviewAutoSuggestionService:
    """
    Auto-suggests account mappings based on historical corrections.
    
    Features:
    - Learns from user corrections
    - Calculates confidence scores
    - Auto-applies high-confidence suggestions
    - Flags low-confidence for review
    """
    
    def __init__(self, db: Session):
        """Initialize auto-suggestion service."""
        self.db = db
        self.confidence_threshold_auto_apply = 0.90  # Auto-apply if confidence >= 90%
        self.confidence_threshold_review = 0.70  # Flag for review if confidence < 70%
    
    def learn_from_correction(
        self,
        raw_label: str,
        account_code: str,
        user_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Learn from a user correction.
        
        Args:
            raw_label: Original extracted label
            account_code: Corrected account code
            user_id: User who made the correction
            context: Optional context (document type, property, etc.)
            
        Returns:
            True if mapping rule was created/updated
        """
        # Check if mapping rule exists
        from app.models.account_mapping_rule import AccountMappingRule
        
        rule = self.db.query(AccountMappingRule).filter(
            AccountMappingRule.raw_label == raw_label
        ).first()
        
        if rule:
            # Update existing rule
            rule.account_code = account_code
            rule.usage_count += 1
            rule.last_used_at = datetime.utcnow()
            rule.last_used_by = user_id
            
            # Recalculate confidence
            rule.confidence_score = self._calculate_confidence(rule)
        else:
            # Create new rule
            rule = AccountMappingRule(
                raw_label=raw_label,
                account_code=account_code,
                usage_count=1,
                confidence_score=Decimal('0.5'),  # Initial low confidence
                created_by=user_id,
                last_used_by=user_id,
                last_used_at=datetime.utcnow(),
                context=context or {}
            )
            self.db.add(rule)
        
        self.db.commit()
        self.db.refresh(rule)
        
        logger.info(f"Learned mapping: {raw_label} -> {account_code} (confidence: {rule.confidence_score})")
        
        return True
    
    def suggest_mapping(
        self,
        raw_label: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Suggest account mapping for a raw label.
        
        Args:
            raw_label: Raw extracted label
            context: Optional context for matching
            
        Returns:
            Dict with suggestion and confidence, or None
        """
        from app.models.account_mapping_rule import AccountMappingRule
        
        # Find matching rules
        rules = self.db.query(AccountMappingRule).filter(
            AccountMappingRule.raw_label.ilike(f'%{raw_label}%')
        ).order_by(
            AccountMappingRule.confidence_score.desc(),
            AccountMappingRule.usage_count.desc()
        ).limit(5).all()
        
        if not rules:
            return None
        
        # Get best match
        best_rule = rules[0]
        
        # Apply context matching if provided
        if context:
            # Filter by context similarity
            context_matches = [
                r for r in rules
                if self._context_match(r.context, context)
            ]
            if context_matches:
                best_rule = context_matches[0]
        
        return {
            'raw_label': raw_label,
            'suggested_account_code': best_rule.account_code,
            'confidence_score': float(best_rule.confidence_score),
            'usage_count': best_rule.usage_count,
            'auto_apply': float(best_rule.confidence_score) >= self.confidence_threshold_auto_apply,
            'needs_review': float(best_rule.confidence_score) < self.confidence_threshold_review,
            'alternatives': [
                {
                    'account_code': r.account_code,
                    'confidence': float(r.confidence_score),
                    'usage_count': r.usage_count
                }
                for r in rules[1:5]
            ]
        }
    
    def _calculate_confidence(self, rule) -> Decimal:
        """
        Calculate confidence score for a mapping rule.
        
        Factors:
        - Usage count (more uses = higher confidence)
        - Consistency (same mapping = higher confidence)
        - Recency (recent uses = higher confidence)
        """
        # Base confidence from usage count
        usage_factor = min(1.0, rule.usage_count / 10.0)  # Max at 10 uses
        
        # Consistency factor - check for conflicting mappings
        consistency_factor = self._calculate_consistency_factor(rule)
        
        # Recency factor
        if rule.last_used_at:
            days_since = (datetime.utcnow() - rule.last_used_at).days
            recency_factor = max(0.5, 1.0 - (days_since / 365.0))  # Decay over 1 year
        else:
            recency_factor = 0.5
        
        # Combined confidence
        confidence = Decimal(str(usage_factor * 0.4 + consistency_factor * 0.4 + recency_factor * 0.2))
        
        return min(Decimal('1.0'), max(Decimal('0.0'), confidence))
    
    def _calculate_consistency_factor(self, rule) -> float:
        """
        Calculate consistency factor based on historical mapping accuracy.
        
        Checks if the same raw_label has been mapped to different account_codes.
        Higher consistency = same mapping used consistently.
        Lower consistency = conflicting mappings exist.
        
        Returns:
            Float between 0.0 and 1.0
        """
        try:
            from app.models.account_mapping_rule import AccountMappingRule
            
            # Find all rules with the same raw_label (case-insensitive)
            all_rules = self.db.query(AccountMappingRule).filter(
                func.lower(AccountMappingRule.raw_label) == func.lower(rule.raw_label)
            ).all()
            
            if not all_rules or len(all_rules) == 1:
                # No conflicts - perfect consistency
                return 1.0
            
            # Count how many times each account_code is used
            account_code_counts = {}
            total_uses = 0
            
            for r in all_rules:
                account_code = r.account_code
                usage = r.usage_count or 1
                account_code_counts[account_code] = account_code_counts.get(account_code, 0) + usage
                total_uses += usage
            
            if total_uses == 0:
                return 0.5  # Default if no usage data
            
            # Calculate consistency: percentage of uses that match the current rule's account_code
            current_account_uses = account_code_counts.get(rule.account_code, 0)
            consistency_ratio = current_account_uses / total_uses
            
            # Penalize for multiple conflicting mappings
            num_conflicts = len([code for code, count in account_code_counts.items() if code != rule.account_code and count > 0])
            conflict_penalty = min(0.3, num_conflicts * 0.1)  # Max 30% penalty
            
            # Calculate final consistency factor
            consistency_factor = consistency_ratio * (1.0 - conflict_penalty)
            
            # Ensure minimum consistency for rules with some usage
            if rule.usage_count > 0:
                consistency_factor = max(0.3, consistency_factor)  # Minimum 30% if used
            
            return max(0.0, min(1.0, consistency_factor))
        
        except Exception as e:
            logger.error(f"Error calculating consistency factor: {e}", exc_info=True)
            # Default to moderate consistency on error
            return 0.7
    
    def _context_match(
        self,
        rule_context: Dict[str, Any],
        query_context: Dict[str, Any]
    ) -> bool:
        """Check if rule context matches query context."""
        if not rule_context or not query_context:
            return True  # No context = match
        
        # Match on document type
        if 'document_type' in query_context and 'document_type' in rule_context:
            if query_context['document_type'] != rule_context['document_type']:
                return False
        
        # Match on property type (if available)
        if 'property_type' in query_context and 'property_type' in rule_context:
            if query_context['property_type'] != rule_context['property_type']:
                return False
        
        return True
    
    def auto_apply_suggestions(
        self,
        raw_labels: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Auto-apply high-confidence suggestions.
        
        Args:
            raw_labels: List of raw labels to map
            context: Optional context
            
        Returns:
            Dict with applied mappings and flagged items
        """
        applied = []
        flagged = []
        
        for raw_label in raw_labels:
            suggestion = self.suggest_mapping(raw_label, context)
            
            if not suggestion:
                flagged.append({
                    'raw_label': raw_label,
                    'reason': 'no_suggestion_available'
                })
            elif suggestion['auto_apply']:
                applied.append({
                    'raw_label': raw_label,
                    'account_code': suggestion['suggested_account_code'],
                    'confidence': suggestion['confidence_score']
                })
            else:
                flagged.append({
                    'raw_label': raw_label,
                    'suggestion': suggestion,
                    'reason': 'low_confidence' if suggestion['needs_review'] else 'below_auto_apply_threshold'
                })
        
        return {
            'applied': applied,
            'flagged': flagged,
            'total': len(raw_labels),
            'applied_count': len(applied),
            'flagged_count': len(flagged)
        }
