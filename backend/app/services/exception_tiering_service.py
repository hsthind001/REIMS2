"""
Exception Tiering Service

Classifies matches and discrepancies into exception tiers and handles
auto-resolution for tier 0 exceptions.
"""
import logging
from typing import Dict, Optional, List, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.forensic_match import ForensicMatch
from app.models.forensic_discrepancy import ForensicDiscrepancy
from app.models.auto_resolution_rule import AutoResolutionRule
from app.services.materiality_service import MaterialityService

logger = logging.getLogger(__name__)


class ExceptionTieringService:
    """Service for classifying exceptions into tiers and auto-resolving"""
    
    # Tier thresholds
    TIER_0_CONFIDENCE_THRESHOLD = 98.0  # Auto-close
    TIER_1_CONFIDENCE_THRESHOLD = 90.0  # Auto-suggest
    TIER_2_CONFIDENCE_THRESHOLD = 70.0  # Route to committee
    # Below 70.0 = Tier 3 (escalate)
    
    def __init__(self, db: Session):
        """
        Initialize exception tiering service
        
        Args:
            db: Database session
        """
        self.db = db
        self.materiality_service = MaterialityService(db)
    
    def classify_exception(
        self,
        match: ForensicMatch,
        discrepancy: Optional[ForensicDiscrepancy] = None
    ) -> str:
        """
        Classify a match/discrepancy into an exception tier
        
        Args:
            match: ForensicMatch object
            discrepancy: Optional ForensicDiscrepancy object
            
        Returns:
            Exception tier: 'tier_0_auto_close', 'tier_1_auto_suggest', 'tier_2_route', 'tier_3_escalate'
        """
        confidence = float(match.confidence_score)
        
        # Get materiality information
        is_material, materiality_details = self.materiality_service.is_material(
            property_id=match.session.property_id,
            amount=match.amount_difference or Decimal('0'),
            account_code=match.source_account_code,
            statement_type=match.source_document_type
        )
        
        risk_class = materiality_details.get('risk_class', 'medium')
        
        # Tier 0: Auto-close
        # - High confidence (≥98%)
        # - Immaterial (< threshold)
        # - Not a critical account
        if (confidence >= self.TIER_0_CONFIDENCE_THRESHOLD and
            not is_material and
            risk_class not in ['critical', 'high']):
            return 'tier_0_auto_close'
        
        # Tier 1: Auto-suggest
        # - Good confidence (90-97%)
        # - Material but fixable
        # - Not critical account
        if (confidence >= self.TIER_1_CONFIDENCE_THRESHOLD and
            confidence < self.TIER_0_CONFIDENCE_THRESHOLD and
            risk_class != 'critical'):
            return 'tier_1_auto_suggest'
        
        # Tier 3: Escalate
        # - Low confidence (<70%)
        # - OR critical account
        # - OR covenant risk (if discrepancy indicates)
        if (confidence < self.TIER_2_CONFIDENCE_THRESHOLD or
            risk_class == 'critical' or
            (discrepancy and discrepancy.severity == 'critical')):
            return 'tier_3_escalate'
        
        # Tier 2: Route to committee (default)
        # - Medium confidence (70-89%)
        # - Material
        # - Needs review
        return 'tier_2_route'
    
    def auto_resolve_tier_0(
        self,
        match: ForensicMatch,
        rule_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Auto-resolve a tier 0 exception
        
        Args:
            match: ForensicMatch to auto-resolve
            rule_id: Optional rule ID that triggered auto-resolution
            
        Returns:
            Dict with resolution details
        """
        # Check if match meets tier 0 criteria
        tier = self.classify_exception(match)
        if tier != 'tier_0_auto_close':
            return {
                'success': False,
                'reason': f'Match does not meet tier 0 criteria (current tier: {tier})'
            }
        
        # Apply auto-resolution
        match.status = 'approved'
        match.exception_tier = 'tier_0_auto_close'
        match.review_notes = 'Auto-resolved: High confidence, immaterial, non-critical account'
        
        if rule_id:
            match.review_notes += f' (Rule ID: {rule_id})'
        
        self.db.commit()
        
        logger.info(f"Auto-resolved match {match.id} (tier 0)")
        
        return {
            'success': True,
            'match_id': match.id,
            'tier': 'tier_0_auto_close',
            'action': 'approved'
        }
    
    def suggest_tier_1_fix(
        self,
        match: ForensicMatch
    ) -> Dict[str, Any]:
        """
        Suggest a fix for a tier 1 exception
        
        Args:
            match: ForensicMatch to suggest fix for
            
        Returns:
            Dict with suggested fix details
        """
        tier = self.classify_exception(match)
        if tier != 'tier_1_auto_suggest':
            return {
                'success': False,
                'reason': f'Match does not meet tier 1 criteria (current tier: {tier})'
            }
        
        suggestions = []
        
        # Check for rounding differences
        if match.amount_difference:
            abs_diff = abs(match.amount_difference)
            if abs_diff <= Decimal('0.10'):
                suggestions.append({
                    'type': 'rounding_adjustment',
                    'description': f'Minor rounding difference of ${abs_diff}',
                    'suggested_action': 'Accept as rounding difference',
                    'confidence': 95.0
                })
        
        # Check for account mapping suggestions
        if match.source_account_code != match.target_account_code:
            suggestions.append({
                'type': 'account_mapping',
                'description': f'Account code mismatch: {match.source_account_code} vs {match.target_account_code}',
                'suggested_action': f'Map {match.source_account_code} to {match.target_account_code}',
                'confidence': float(match.confidence_score)
            })
        
        # Check auto-resolution rules
        rules = self.db.query(AutoResolutionRule).filter(
            and_(
                AutoResolutionRule.is_active == True,
                AutoResolutionRule.action_type == 'suggest_fix',
                or_(
                    AutoResolutionRule.property_id == match.session.property_id,
                    AutoResolutionRule.property_id.is_(None)
                ),
                or_(
                    AutoResolutionRule.statement_type == match.source_document_type,
                    AutoResolutionRule.statement_type.is_(None)
                ),
                AutoResolutionRule.confidence_threshold <= match.confidence_score
            )
        ).order_by(
            AutoResolutionRule.priority.desc()
        ).all()
        
        for rule in rules:
            # Check if rule condition matches
            if self._check_rule_condition(rule, match):
                suggestions.append({
                    'type': 'rule_based',
                    'rule_id': rule.id,
                    'rule_name': rule.rule_name,
                    'description': rule.description or rule.rule_name,
                    'suggested_action': rule.suggested_mapping,
                    'confidence': float(rule.confidence_threshold)
                })
        
        return {
            'success': True,
            'match_id': match.id,
            'tier': 'tier_1_auto_suggest',
            'suggestions': suggestions
        }
    
    def route_tier_2(
        self,
        match: ForensicMatch,
        committee_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Route a tier 2 exception to a committee queue
        
        Args:
            match: ForensicMatch to route
            committee_id: Optional committee ID
            
        Returns:
            Dict with routing details
        """
        tier = self.classify_exception(match)
        if tier != 'tier_2_route':
            return {
                'success': False,
                'reason': f'Match does not meet tier 2 criteria (current tier: {tier})'
            }
        
        match.exception_tier = 'tier_2_route'
        match.status = 'pending'
        
        if committee_id:
            # TODO: Link to committee when committee system is available
            match.review_notes = f'Routed to committee {committee_id}'
        
        self.db.commit()
        
        return {
            'success': True,
            'match_id': match.id,
            'tier': 'tier_2_route',
            'status': 'pending',
            'committee_id': committee_id
        }
    
    def escalate_tier_3(
        self,
        match: ForensicMatch,
        reason: str
    ) -> Dict[str, Any]:
        """
        Escalate a tier 3 exception
        
        Args:
            match: ForensicMatch to escalate
            reason: Escalation reason
            
        Returns:
            Dict with escalation details
        """
        tier = self.classify_exception(match)
        if tier != 'tier_3_escalate':
            return {
                'success': False,
                'reason': f'Match does not meet tier 3 criteria (current tier: {tier})'
            }
        
        match.exception_tier = 'tier_3_escalate'
        match.status = 'pending'
        match.review_notes = f'ESCALATED: {reason}'
        
        # TODO: Create critical alert
        # alert_service.create_critical_alert(
        #     property_id=match.session.property_id,
        #     match_id=match.id,
        #     reason=reason
        # )
        
        self.db.commit()
        
        logger.warning(f"Escalated match {match.id} to tier 3: {reason}")
        
        return {
            'success': True,
            'match_id': match.id,
            'tier': 'tier_3_escalate',
            'status': 'pending',
            'reason': reason
        }
    
    def _check_rule_condition(
        self,
        rule: AutoResolutionRule,
        match: ForensicMatch
    ) -> bool:
        """
        Check if a rule condition matches a match
        
        Args:
            rule: AutoResolutionRule
            match: ForensicMatch
            
        Returns:
            True if condition matches
        """
        condition = rule.condition_json
        
        if not condition:
            return False
        
        # Check pattern type
        pattern_type = rule.pattern_type
        
        if pattern_type == 'rounding':
            # Check if amount difference is within rounding threshold
            threshold = condition.get('max_difference', 0.10)
            if match.amount_difference:
                return abs(match.amount_difference) <= Decimal(str(threshold))
        
        elif pattern_type == 'timing':
            # Check if difference is expected timing difference
            expected_periods = condition.get('expected_periods', 1)
            # TODO: Implement period-based timing check
            return False
        
        elif pattern_type == 'synonym':
            # Check if account names match synonym pattern
            source_name = match.source_account_name or ''
            target_name = match.target_account_name or ''
            synonyms = condition.get('synonyms', [])
            return (source_name.lower() in [s.lower() for s in synonyms] or
                   target_name.lower() in [s.lower() for s in synonyms])
        
        elif pattern_type == 'mapping':
            # Check if account codes match mapping pattern
            source_code = match.source_account_code or ''
            target_code = match.target_account_code or ''
            mappings = condition.get('mappings', {})
            return mappings.get(source_code) == target_code
        
        return False
    
    def classify_and_apply_tiering(
        self,
        match: ForensicMatch,
        auto_resolve: bool = True
    ) -> Dict[str, Any]:
        """
        Classify a match and apply appropriate tiering action
        
        Args:
            match: ForensicMatch to classify
            auto_resolve: Whether to auto-resolve tier 0 matches
            
        Returns:
            Dict with classification and action results
        """
        # Get associated discrepancy if exists
        discrepancy = self.db.query(ForensicDiscrepancy).filter(
            ForensicDiscrepancy.match_id == match.id
        ).first()
        
        # Classify tier
        tier = self.classify_exception(match, discrepancy)
        match.exception_tier = tier
        
        result = {
            'match_id': match.id,
            'tier': tier,
            'confidence': float(match.confidence_score)
        }
        
        # Apply tier-specific action
        if tier == 'tier_0_auto_close' and auto_resolve:
            auto_result = self.auto_resolve_tier_0(match)
            result.update(auto_result)
        elif tier == 'tier_1_auto_suggest':
            suggest_result = self.suggest_tier_1_fix(match)
            result.update(suggest_result)
        elif tier == 'tier_2_route':
            route_result = self.route_tier_2(match)
            result.update(route_result)
        elif tier == 'tier_3_escalate':
            escalate_result = self.escalate_tier_3(
                match,
                reason=f'Low confidence ({match.confidence_score}%) or critical account'
            )
            result.update(escalate_result)
        
        # Update discrepancy tier if exists
        if discrepancy:
            discrepancy.exception_tier = tier
            self.db.commit()
        
        self.db.commit()
        
        return result

