"""
Forensic Discrepancy Validator

Handles the validation of matches and identification of discrepancies.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.forensic_reconciliation_session import ForensicReconciliationSession
from app.models.forensic_match import ForensicMatch
from app.models.forensic_discrepancy import ForensicDiscrepancy
from app.services.calculated_rules_engine import CalculatedRulesEngine

logger = logging.getLogger(__name__)

class ForensicDiscrepancyValidator:
    """
    Validator for identifying discrepancies and calculating health scores.
    """

    def __init__(self, db: Session, rules_engine: Optional[CalculatedRulesEngine] = None):
        self.db = db
        self.rules_engine = rules_engine or CalculatedRulesEngine(db)

    def validate_session(self, session_id: int) -> Dict[str, Any]:
        """
        Validate matches and calculate session health.
        Updates session status but does NOT handle transaction commit.
        """
        session = self.db.query(ForensicReconciliationSession).filter(
            ForensicReconciliationSession.id == session_id
        ).first()
        
        if not session:
            return {'error': 'Session not found'}
            
        matches = self.db.query(ForensicMatch).filter(
            ForensicMatch.session_id == session_id
        ).all()
        
        discrepancies = []
        
        # 1. Match-based discrepancies
        for match in matches:
            if match.confidence_score < 70.0:
                 self._create_discrepancy(discrepancies, session_id, match, 'Low confidence match')
            
            if match.amount_difference and match.amount_difference > Decimal('1000'):
                 self._create_discrepancy(discrepancies, session_id, match, 'Large amount difference')

        # 2. Rule-based validation
        rule_results = self.rules_engine.evaluate_rules(
            property_id=session.property_id,
            period_id=session.period_id
        )
        
        failed_rule_count = 0
        for result in rule_results:
            if result.get('status') == 'FAIL':
                failed_rule_count += 1
                self._create_rule_discrepancy(discrepancies, session_id, result)

        # 3. Add all discrepancies to DB
        self.db.add_all(discrepancies)
        self.db.flush() # Flush to get IDs, but don't commit

        # 4. Update session stats
        health_score = self._calculate_health_score(matches, discrepancies)
        
        session.status = 'completed' # Or 'validated'
        session.health_score = health_score
        session.discrepancy_count = len(discrepancies)
        session.summary = {
            **(session.summary or {}),
            'discrepancies': len(discrepancies),
            'rule_failures': failed_rule_count,
            'health_score': health_score
        }
        
        return {
            'discrepancies': discrepancies,
            'health_score': health_score,
            'rule_results': rule_results
        }

    def _create_discrepancy(self, list_ref, session_id, match, reason):
        d = ForensicDiscrepancy(
            session_id=session_id,
            match_id=match.id,
            discrepancy_type='amount_mismatch',
            severity='high' if (match.amount_difference and match.amount_difference > 10000) else 'medium',
            description=f"{reason}: {match.amount_difference}",
            status='open'
        )
        list_ref.append(d)

    def _create_rule_discrepancy(self, list_ref, session_id, result):
        d = ForensicDiscrepancy(
            session_id=session_id,
            discrepancy_type='rule_failure',
            severity=result.get('severity', 'medium'),
            description=result.get('message'),
            status='open'
        )
        list_ref.append(d)

    def _calculate_health_score(self, matches, discrepancies):
        if not matches:
             return 0.0
        
        score = 100.0
        score -= len(discrepancies) * 5 # Simplified logic
        return max(0.0, score)
