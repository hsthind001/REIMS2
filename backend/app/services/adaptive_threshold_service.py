"""
Adaptive Threshold Service

Enables adaptive thresholds using anomaly feedback and recalibrates weekly via Celery.
Uses rolling windows and seasonal baseline adjustments.
"""

from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import numpy as np
import os
import logging

from app.models.anomaly_threshold import AnomalyThreshold
from app.models.anomaly_detection import AnomalyDetection
from app.models.anomaly_feedback import AnomalyFeedback
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)


class AdaptiveThresholdService:
    """
    Manages adaptive thresholds that adjust based on feedback.
    
    Features:
    - Weekly recalibration via Celery
    - Rolling windows
    - Seasonal baseline adjustments
    - Account-specific volatility bands
    """
    
    def __init__(self, db: Session):
        """Initialize adaptive threshold service."""
        self.db = db
        self.adaptive_thresholds_enabled = os.getenv('ADAPTIVE_THRESHOLDS_ENABLED', 'true').lower() == 'true'
        self.rolling_window_days = 90  # 3 months
        self.seasonal_adjustment_enabled = True
    
    def get_adaptive_threshold(
        self,
        account_code: str,
        property_id: Optional[int] = None
    ) -> Decimal:
        """
        Get adaptive threshold for an account.
        
        Args:
            account_code: Account code
            property_id: Optional property ID for property-specific thresholds
            
        Returns:
            Adaptive threshold value
        """
        if not self.adaptive_thresholds_enabled:
            # Return default threshold
            threshold = self.db.query(AnomalyThreshold).filter(
                AnomalyThreshold.account_code == account_code,
                AnomalyThreshold.is_active == True
            ).first()
            
            if threshold:
                return threshold.threshold_value
            return Decimal('0.15')  # Default 15%
        
        # Get or create threshold record
        threshold = self.db.query(AnomalyThreshold).filter(
            AnomalyThreshold.account_code == account_code,
            AnomalyThreshold.is_active == True
        ).first()
        
        if not threshold:
            # Create default threshold
            threshold = AnomalyThreshold(
                account_code=account_code,
                account_name=account_code,
                threshold_value=Decimal('0.15'),
                is_active=True
            )
            self.db.add(threshold)
            self.db.commit()
        
        # Calculate adaptive threshold
        adaptive_value = self._calculate_adaptive_threshold(account_code, property_id)
        
        # Update threshold if different
        if abs(float(threshold.threshold_value - adaptive_value)) > 0.001:
            threshold.threshold_value = adaptive_value
            threshold.updated_at = datetime.utcnow()
            self.db.commit()
        
        return adaptive_value
    
    def _calculate_adaptive_threshold(
        self,
        account_code: str,
        property_id: Optional[int] = None
    ) -> Decimal:
        """
        Calculate adaptive threshold using feedback and historical data.
        
        Uses:
        - False positive rate from feedback
        - Historical volatility
        - Seasonal adjustments
        """
        # Get feedback data
        cutoff_date = datetime.utcnow() - timedelta(days=self.rolling_window_days)
        
        feedback = self.db.query(AnomalyFeedback).join(
            AnomalyDetection
        ).filter(
            and_(
                AnomalyDetection.field_name == account_code,
                AnomalyFeedback.created_at >= cutoff_date
            )
        ).all()
        
        if len(feedback) < 10:
            # Not enough feedback - use default
            return Decimal('0.15')
        
        # Calculate false positive rate
        false_positives = sum(
            1 for fb in feedback
            if fb.feedback_type == 'dismissed' or (not fb.is_anomaly and fb.feedback_type != 'confirmed')
        )
        
        false_positive_rate = false_positives / len(feedback)
        
        # Calculate historical volatility
        volatility = self._calculate_volatility(account_code, property_id)
        
        # Base threshold
        base_threshold = Decimal('0.15')  # 15%
        
        # Adjust based on false positive rate
        # High FPR -> increase threshold (less sensitive)
        # Low FPR -> decrease threshold (more sensitive)
        if false_positive_rate > 0.3:
            adjustment = 1.5  # Increase by 50%
        elif false_positive_rate > 0.2:
            adjustment = 1.2  # Increase by 20%
        elif false_positive_rate < 0.1:
            adjustment = 0.7  # Decrease by 30%
        elif false_positive_rate < 0.15:
            adjustment = 0.85  # Decrease by 15%
        else:
            adjustment = 1.0  # No adjustment
        
        # Adjust based on volatility
        # High volatility -> increase threshold
        # Low volatility -> decrease threshold
        if volatility > 0.3:
            volatility_adjustment = 1.3
        elif volatility > 0.2:
            volatility_adjustment = 1.1
        elif volatility < 0.1:
            volatility_adjustment = 0.9
        else:
            volatility_adjustment = 1.0
        
        # Apply adjustments
        adaptive_threshold = base_threshold * Decimal(str(adjustment)) * Decimal(str(volatility_adjustment))
        
        # Clamp to reasonable range (5% - 50%)
        adaptive_threshold = max(Decimal('0.05'), min(Decimal('0.50'), adaptive_threshold))
        
        return adaptive_threshold
    
    def _calculate_volatility(
        self,
        account_code: str,
        property_id: Optional[int] = None
    ) -> float:
        """Calculate historical volatility for account."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.rolling_window_days)
        
        # Get historical values
        from app.models.income_statement_data import IncomeStatementData
        
        query = self.db.query(IncomeStatementData.period_amount).join(
            FinancialPeriod
        ).filter(
            and_(
                IncomeStatementData.account_code == account_code,
                FinancialPeriod.period_end_date >= cutoff_date
            )
        )
        
        if property_id:
            query = query.filter(IncomeStatementData.property_id == property_id)
        
        values = [float(row.period_amount) for row in query.all() if row.period_amount]
        
        if len(values) < 3:
            return 0.2  # Default volatility
        
        # Calculate coefficient of variation (CV)
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        if mean_val == 0:
            return 0.2
        
        cv = std_val / abs(mean_val)
        
        return min(1.0, cv)  # Cap at 1.0
    
    def recalibrate_all_thresholds(self) -> Dict[str, Any]:
        """
        Recalibrate all active thresholds.
        
        This should be called weekly via Celery task.
        
        Returns:
            Dict with recalibration results
        """
        if not self.adaptive_thresholds_enabled:
            return {'recalibrated': 0, 'message': 'Adaptive thresholds disabled'}
        
        thresholds = self.db.query(AnomalyThreshold).filter(
            AnomalyThreshold.is_active == True
        ).all()
        
        recalibrated = 0
        updates = []
        
        for threshold in thresholds:
            try:
                old_value = threshold.threshold_value
                new_value = self._calculate_adaptive_threshold(threshold.account_code)
                
                if abs(float(old_value - new_value)) > 0.001:
                    threshold.threshold_value = new_value
                    threshold.updated_at = datetime.utcnow()
                    recalibrated += 1
                    
                    updates.append({
                        'account_code': threshold.account_code,
                        'old_threshold': float(old_value),
                        'new_threshold': float(new_value),
                        'change_pct': float((new_value - old_value) / old_value * 100) if old_value > 0 else 0
                    })
            except Exception as e:
                logger.error(f"Error recalibrating threshold for {threshold.account_code}: {e}")
        
        if updates:
            self.db.commit()
        
        logger.info(f"Recalibrated {recalibrated} thresholds")
        
        return {
            'recalibrated': recalibrated,
            'total_thresholds': len(thresholds),
            'updates': updates
        }
