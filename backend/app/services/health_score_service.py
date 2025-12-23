"""
Health Score Service

Calculates configurable health scores with persona-specific weights,
trend components, and blocked close rules.
"""
import logging
from typing import Dict, Optional, List, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.health_score_config import HealthScoreConfig
from app.models.forensic_reconciliation_session import ForensicReconciliationSession
from app.models.forensic_match import ForensicMatch
from app.models.forensic_discrepancy import ForensicDiscrepancy

logger = logging.getLogger(__name__)


class HealthScoreService:
    """Service for calculating configurable health scores"""
    
    # Default weights if no config exists
    DEFAULT_WEIGHTS = {
        'approval_score': 0.4,
        'confidence_score': 0.3,
        'discrepancy_penalty': 0.3
    }
    
    def __init__(self, db: Session):
        """
        Initialize health score service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_config(self, persona: str = 'controller') -> Dict[str, Any]:
        """
        Get health score configuration for a persona
        
        Args:
            persona: Persona type (controller, analyst, investor, auditor)
            
        Returns:
            Configuration dictionary
        """
        config = self.db.query(HealthScoreConfig).filter(
            HealthScoreConfig.persona == persona
        ).first()
        
        if config:
            return {
                'persona': config.persona,
                'weights': config.weights_json or self.DEFAULT_WEIGHTS,
                'trend_weight': float(config.trend_weight) if config.trend_weight else 0.0,
                'volatility_weight': float(config.volatility_weight) if config.volatility_weight else 0.0,
                'blocked_close_rules': config.blocked_close_rules or []
            }
        
        # Return defaults
        return {
            'persona': persona,
            'weights': self.DEFAULT_WEIGHTS,
            'trend_weight': 0.0,
            'volatility_weight': 0.0,
            'blocked_close_rules': []
        }
    
    def calculate_health_score(
        self,
        session_id: int,
        persona: str = 'controller',
        include_trend: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate health score for a reconciliation session
        
        Args:
            session_id: Reconciliation session ID
            persona: Persona type
            include_trend: Whether to include trend component
            
        Returns:
            Dict with health score and breakdown
        """
        session = self.db.query(ForensicReconciliationSession).filter(
            ForensicReconciliationSession.id == session_id
        ).first()
        
        if not session:
            return {
                'error': f'Session {session_id} not found'
            }
        
        # Get configuration
        config = self.get_config(persona)
        weights = config['weights']
        
        # Get matches
        matches = self.db.query(ForensicMatch).filter(
            ForensicMatch.session_id == session_id
        ).all()
        
        # Get discrepancies
        discrepancies = self.db.query(ForensicDiscrepancy).filter(
            ForensicDiscrepancy.session_id == session_id
        ).all()
        
        # Calculate approval score (0-100)
        total_matches = len(matches)
        if total_matches > 0:
            approved = len([m for m in matches if m.status == 'approved'])
            approval_score = (approved / total_matches) * 100
        else:
            approval_score = 0.0
        
        # Calculate average confidence score (0-100)
        if matches:
            avg_confidence = sum([float(m.confidence_score) for m in matches]) / len(matches)
        else:
            avg_confidence = 0.0
        
        # Calculate discrepancy penalty (0-100, higher = worse)
        critical_discrepancies = len([d for d in discrepancies if d.severity == 'critical'])
        high_discrepancies = len([d for d in discrepancies if d.severity == 'high'])
        medium_discrepancies = len([d for d in discrepancies if d.severity == 'medium'])
        
        discrepancy_penalty = (
            critical_discrepancies * 20 +
            high_discrepancies * 10 +
            medium_discrepancies * 5
        )
        discrepancy_penalty = min(100.0, discrepancy_penalty)
        
        # Base health score
        base_score = (
            approval_score * weights.get('approval_score', 0.4) +
            avg_confidence * weights.get('confidence_score', 0.3) +
            (100 - discrepancy_penalty) * weights.get('discrepancy_penalty', 0.3)
        )
        
        # Apply trend component if enabled
        trend_adjustment = 0.0
        if include_trend and config['trend_weight'] > 0:
            trend_adjustment = self._calculate_trend_adjustment(
                session.property_id,
                session.period_id,
                base_score
            ) * config['trend_weight']
        
        # Apply volatility component if enabled
        volatility_adjustment = 0.0
        if config['volatility_weight'] > 0:
            volatility_adjustment = self._calculate_volatility_adjustment(
                session.property_id,
                session.period_id,
                base_score
            ) * config['volatility_weight']
        
        # Final score
        health_score = base_score + trend_adjustment - volatility_adjustment
        
        # Apply blocked close rules
        for rule in config['blocked_close_rules']:
            condition = rule.get('condition')
            max_score = rule.get('max_score', 60)
            
            if condition == 'covenant_violation':
                # Check for critical discrepancies that might indicate covenant violations
                if critical_discrepancies > 0:
                    health_score = min(health_score, max_score)
            elif condition == 'low_confidence':
                if avg_confidence < 70:
                    health_score = min(health_score, max_score)
            elif condition == 'high_discrepancies':
                if critical_discrepancies + high_discrepancies > 5:
                    health_score = min(health_score, max_score)
        
        # Ensure score is between 0 and 100
        health_score = max(0.0, min(100.0, health_score))
        
        return {
            'health_score': health_score,
            'persona': persona,
            'breakdown': {
                'approval_score': approval_score,
                'avg_confidence': avg_confidence,
                'discrepancy_penalty': discrepancy_penalty,
                'base_score': base_score,
                'trend_adjustment': trend_adjustment,
                'volatility_adjustment': volatility_adjustment
            },
            'statistics': {
                'total_matches': total_matches,
                'approved_matches': len([m for m in matches if m.status == 'approved']),
                'critical_discrepancies': critical_discrepancies,
                'high_discrepancies': high_discrepancies,
                'medium_discrepancies': medium_discrepancies
            }
        }
    
    def get_health_score_trend(
        self,
        property_id: int,
        periods: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Get health score trend over multiple periods
        
        Args:
            property_id: Property ID
            periods: Number of periods to include
            
        Returns:
            List of health scores by period
        """
        # Get recent sessions
        sessions = self.db.query(ForensicReconciliationSession).filter(
            ForensicReconciliationSession.property_id == property_id,
            ForensicReconciliationSession.status.in_(['approved', 'completed'])
        ).order_by(
            ForensicReconciliationSession.period_id.desc()
        ).limit(periods).all()
        
        trend = []
        for session in sessions:
            score_data = self.calculate_health_score(session.id, include_trend=False)
            if 'health_score' in score_data:
                trend.append({
                    'period_id': session.period_id,
                    'health_score': score_data['health_score'],
                    'date': session.completed_at.isoformat() if session.completed_at else None
                })
        
        return trend
    
    def _calculate_trend_adjustment(
        self,
        property_id: int,
        period_id: int,
        current_score: float
    ) -> float:
        """
        Calculate trend adjustment based on prior period
        
        Args:
            property_id: Property ID
            period_id: Current period ID
            current_score: Current health score
            
        Returns:
            Trend adjustment (-10 to +10)
        """
        # Get prior period session
        # TODO: Implement period lookup logic
        # For now, return 0
        return 0.0
    
    def _calculate_volatility_adjustment(
        self,
        property_id: int,
        period_id: int,
        current_score: float
    ) -> float:
        """
        Calculate volatility adjustment based on score stability
        
        Args:
            property_id: Property ID
            period_id: Current period ID
            current_score: Current health score
            
        Returns:
            Volatility penalty (0 to 10)
        """
        # Get trend data
        trend = self.get_health_score_trend(property_id, periods=6)
        
        if len(trend) < 3:
            return 0.0
        
        # Calculate standard deviation
        scores = [t['health_score'] for t in trend]
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5
        
        # Higher volatility = higher penalty (max 10 points)
        volatility_penalty = min(10.0, std_dev / 10.0)
        
        return volatility_penalty

