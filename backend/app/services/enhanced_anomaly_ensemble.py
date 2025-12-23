"""
Enhanced Anomaly Ensemble Service

Combines multiple anomaly detection methods with calibrated thresholds and weighted ensemble.
Replaces fixed contamination=0.1 with dynamic calibration based on historical data.
Outputs continuous anomaly scores from each detector for granular analysis.
"""

from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import numpy as np
import logging

from app.models.anomaly_detection import AnomalyDetection
from app.models.anomaly_feedback import AnomalyFeedback
from app.services.anomaly_risk_scorer import AnomalyRiskScorer

logger = logging.getLogger(__name__)


class EnhancedAnomalyEnsemble:
    """
    Enhanced ensemble that combines multiple detectors with calibrated thresholds.
    
    Features:
    - Dynamic threshold calibration (replaces fixed contamination=0.1)
    - Continuous anomaly scores from each detector
    - Weighted ensemble strategy based on account volume and data characteristics
    - Consensus detection mechanism
    """
    
    def __init__(self, db: Session):
        """Initialize enhanced ensemble detector."""
        self.db = db
        self.risk_scorer = AnomalyRiskScorer(db)
        
        # Strategy-based weights (will be calibrated)
        self.strategy_weights = {
            'low_volume': {
                'z_score': 0.40,
                'percentage_change': 0.35,
                'robust_mad': 0.25
            },
            'high_volume': {
                'isolation_forest': 0.30,
                'autoencoder': 0.30,
                'lof': 0.20,
                'ocsvm': 0.20
            },
            'time_series': {
                'cusum': 0.35,
                'lstm': 0.30,
                'seasonal': 0.20,
                'forecast_residual': 0.15
            }
        }
        
        # Calibrated thresholds (will be updated from feedback)
        self.calibrated_thresholds = {}
    
    def detect_with_ensemble(
        self,
        property_id: int,
        account_code: str,
        document_type: str = 'income_statement',
        lookback_periods: int = 24
    ) -> Dict[str, Any]:
        """
        Run ensemble detection with calibrated thresholds.
        
        Args:
            property_id: Property to analyze
            account_code: Account code to analyze
            document_type: Type of document
            lookback_periods: Historical periods to use
            
        Returns:
            Ensemble detection results with continuous scores
        """
        # Determine strategy based on account characteristics
        strategy = self._determine_strategy(property_id, account_code, document_type)
        
        # Get calibrated threshold for this account
        threshold = self._get_calibrated_threshold(property_id, account_code, strategy)
        
        # Run detectors based on strategy
        detector_results = self._run_strategy_detectors(
            property_id, account_code, document_type, lookback_periods, strategy
        )
        
        # Combine results with weighted ensemble
        ensemble_result = self._combine_with_weights(
            detector_results, strategy, threshold
        )
        
        # Calculate unified risk score
        if ensemble_result['anomalies']:
            risk_score_result = self.risk_scorer.calculate_unified_risk_score(
                ensemble_result['anomalies'],
                property_id,
                account_code
            )
            ensemble_result['risk_score'] = risk_score_result['risk_score']
            ensemble_result['risk_confidence'] = risk_score_result['confidence']
        else:
            ensemble_result['risk_score'] = 0.0
            ensemble_result['risk_confidence'] = 0.0
        
        return ensemble_result
    
    def _determine_strategy(
        self,
        property_id: int,
        account_code: str,
        document_type: str
    ) -> str:
        """
        Determine ensemble strategy based on account characteristics.
        
        Returns: 'low_volume', 'high_volume', or 'time_series'
        """
        # Check historical data volume
        from app.models.income_statement_data import IncomeStatementData
        from app.models.balance_sheet_data import BalanceSheetData
        
        if document_type == 'income_statement':
            count = self.db.query(func.count(IncomeStatementData.id)).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.account_code == account_code
            ).scalar()
        else:
            count = self.db.query(func.count(BalanceSheetData.id)).filter(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.account_code == account_code
            ).scalar()
        
        # Determine strategy
        if count < 12:
            return 'low_volume'
        elif count >= 24:
            return 'time_series'
        else:
            return 'high_volume'
    
    def _get_calibrated_threshold(
        self,
        property_id: int,
        account_code: str,
        strategy: str
    ) -> float:
        """
        Get calibrated threshold for this account (replaces fixed contamination=0.1).
        
        Calibrates based on historical feedback data.
        """
        # Check if we have a cached threshold
        cache_key = f"{property_id}_{account_code}_{strategy}"
        if cache_key in self.calibrated_thresholds:
            return self.calibrated_thresholds[cache_key]
        
        # Calculate threshold from feedback
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        feedback = self.db.query(AnomalyFeedback).join(
            AnomalyDetection
        ).filter(
            and_(
                AnomalyDetection.property_id == property_id,
                AnomalyDetection.field_name == account_code,
                AnomalyFeedback.created_at >= cutoff_date
            )
        ).all()
        
        if len(feedback) < 10:
            # Not enough feedback - use default
            default_thresholds = {
                'low_volume': 0.15,  # Higher threshold for low volume
                'high_volume': 0.08,  # Lower threshold for high volume
                'time_series': 0.10
            }
            threshold = default_thresholds.get(strategy, 0.10)
        else:
            # Calculate optimal threshold from feedback
            false_positive_rate = sum(
                1 for fb in feedback
                if fb.feedback_type == 'dismissed' or (not fb.is_anomaly and fb.feedback_type != 'confirmed')
            ) / len(feedback)
            
            # Adjust threshold based on false positive rate
            # Higher FPR -> increase threshold (less sensitive)
            # Lower FPR -> decrease threshold (more sensitive)
            base_threshold = 0.10
            if false_positive_rate > 0.3:
                threshold = min(0.20, base_threshold * 1.5)
            elif false_positive_rate < 0.1:
                threshold = max(0.05, base_threshold * 0.7)
            else:
                threshold = base_threshold
        
        # Cache threshold
        self.calibrated_thresholds[cache_key] = threshold
        
        return threshold
    
    def _run_strategy_detectors(
        self,
        property_id: int,
        account_code: str,
        document_type: str,
        lookback_periods: int,
        strategy: str
    ) -> List[Dict[str, Any]]:
        """
        Run detectors based on strategy.
        
        Returns list of detector results with continuous scores.
        """
        results = []
        
        if strategy == 'low_volume':
            # Use statistical methods
            from app.services.statistical_anomaly_service import StatisticalAnomalyService
            from app.services.robust_anomaly_detector import RobustAnomalyDetector
            
            stat_service = StatisticalAnomalyService(self.db)
            robust_detector = RobustAnomalyDetector(self.db)
            
            # Z-score detection
            zscore_result = stat_service.detect_anomalies_zscore(
                property_id, account_code, lookback_periods
            )
            if zscore_result and zscore_result.get('anomalies'):
                results.append({
                    'method': 'z_score',
                    'anomalies': zscore_result['anomalies'],
                    'scores': [a.get('z_score', 0) for a in zscore_result['anomalies']],
                    'confidence': 0.75
                })
            
            # Robust MAD
            robust_anomalies = robust_detector.detect_robust_anomalies(
                property_id, account_code, document_type, lookback_periods
            )
            if robust_anomalies:
                results.append({
                    'method': 'robust_mad',
                    'anomalies': robust_anomalies,
                    'scores': [a.get('robust_z_score', 0) for a in robust_anomalies],
                    'confidence': 0.80
                })
        
        elif strategy == 'high_volume':
            # Use ML methods
            from app.services.anomaly_detection_service import AnomalyDetectionService
            
            ml_service = AnomalyDetectionService(self.db)
            
            # Isolation Forest
            iforest_anomalies = ml_service.detect_ml_anomalies(
                property_id, document_type, method='iforest'
            )
            if iforest_anomalies:
                results.append({
                    'method': 'isolation_forest',
                    'anomalies': iforest_anomalies,
                    'scores': [a.get('anomaly_score', 0) for a in iforest_anomalies],
                    'confidence': 0.70
                })
            
            # LOF
            lof_anomalies = ml_service.detect_ml_anomalies(
                property_id, document_type, method='lof'
            )
            if lof_anomalies:
                results.append({
                    'method': 'lof',
                    'anomalies': lof_anomalies,
                    'scores': [a.get('anomaly_score', 0) for a in lof_anomalies],
                    'confidence': 0.65
                })
        
        elif strategy == 'time_series':
            # Use time-series methods
            from app.services.seasonal_anomaly_detector import SeasonalAnomalyDetector
            from app.services.forecast_anomaly_detector import ForecastAnomalyDetector
            
            seasonal_detector = SeasonalAnomalyDetector(self.db)
            forecast_detector = ForecastAnomalyDetector(self.db)
            
            # Seasonal detection
            seasonal_anomalies = seasonal_detector.detect_seasonal_anomalies(
                property_id, account_code, document_type
            )
            if seasonal_anomalies:
                results.append({
                    'method': 'seasonal',
                    'anomalies': seasonal_anomalies,
                    'scores': [a.get('z_score', 0) for a in seasonal_anomalies],
                    'confidence': 0.75
                })
            
            # Forecast-residual detection
            forecast_anomalies = forecast_detector.detect_forecast_residual_anomalies(
                property_id, account_code, document_type, lookback_periods
            )
            if forecast_anomalies:
                results.append({
                    'method': 'forecast_residual',
                    'anomalies': forecast_anomalies,
                    'scores': [a.get('z_score', 0) for a in forecast_anomalies],
                    'confidence': 0.70
                })
        
        return results
    
    def _combine_with_weights(
        self,
        detector_results: List[Dict[str, Any]],
        strategy: str,
        threshold: float
    ) -> Dict[str, Any]:
        """
        Combine detector results using weighted ensemble.
        
        Returns consensus anomalies with continuous scores.
        """
        if not detector_results:
            return {
                'anomalies': [],
                'consensus_count': 0,
                'strategy': strategy,
                'threshold': threshold
            }
        
        # Get weights for this strategy
        weights = self.strategy_weights.get(strategy, {})
        
        # Collect all anomalies with weighted scores
        anomaly_scores = {}  # (field_name, period_id) -> weighted score
        
        for result in detector_results:
            method = result['method']
            weight = weights.get(method, 0.1)
            confidence = result.get('confidence', 0.7)
            anomalies = result.get('anomalies', [])
            scores = result.get('scores', [])
            
            for anomaly, score in zip(anomalies, scores):
                key = (
                    anomaly.get('account_code') or anomaly.get('field_name'),
                    anomaly.get('period_id')
                )
                
                if key not in anomaly_scores:
                    anomaly_scores[key] = {
                        'anomaly': anomaly,
                        'weighted_score': 0.0,
                        'total_weight': 0.0,
                        'methods': []
                    }
                
                # Weighted score contribution
                contribution = abs(float(score)) * weight * confidence
                anomaly_scores[key]['weighted_score'] += contribution
                anomaly_scores[key]['total_weight'] += weight * confidence
                anomaly_scores[key]['methods'].append(method)
        
        # Filter by threshold and normalize
        consensus_anomalies = []
        for key, data in anomaly_scores.items():
            if data['total_weight'] > 0:
                normalized_score = data['weighted_score'] / data['total_weight']
                
                # Apply threshold
                if normalized_score >= threshold:
                    consensus_anomaly = data['anomaly'].copy()
                    consensus_anomaly['ensemble_score'] = normalized_score
                    consensus_anomaly['detection_methods'] = data['methods']
                    consensus_anomaly['is_consensus'] = True
                    consensus_anomalies.append(consensus_anomaly)
        
        # Sort by ensemble score
        consensus_anomalies.sort(key=lambda a: a.get('ensemble_score', 0), reverse=True)
        
        return {
            'anomalies': consensus_anomalies,
            'consensus_count': len(consensus_anomalies),
            'strategy': strategy,
            'threshold': threshold,
            'detector_count': len(detector_results)
        }
    
    def calibrate_thresholds_from_feedback(
        self,
        lookback_days: int = 90
    ) -> Dict[str, float]:
        """
        Recalibrate thresholds from feedback data.
        
        Updates calibrated_thresholds cache.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Group feedback by property/account/strategy
        feedback_groups = {}
        
        feedback = self.db.query(AnomalyFeedback).join(
            AnomalyDetection
        ).filter(
            AnomalyFeedback.created_at >= cutoff_date
        ).all()
        
        for fb in feedback:
            detection = fb.anomaly_detection
            strategy = self._determine_strategy(
                detection.property_id if hasattr(detection, 'property_id') else None,
                detection.field_name,
                'income_statement'  # Default
            )
            
            key = f"{detection.property_id}_{detection.field_name}_{strategy}"
            if key not in feedback_groups:
                feedback_groups[key] = []
            feedback_groups[key].append(fb)
        
        # Calculate thresholds for each group
        for key, group_feedback in feedback_groups.items():
            if len(group_feedback) >= 10:
                false_positive_rate = sum(
                    1 for fb in group_feedback
                    if fb.feedback_type == 'dismissed' or (not fb.is_anomaly and fb.feedback_type != 'confirmed')
                ) / len(group_feedback)
                
                # Adjust threshold
                base_threshold = 0.10
                if false_positive_rate > 0.3:
                    threshold = min(0.20, base_threshold * 1.5)
                elif false_positive_rate < 0.1:
                    threshold = max(0.05, base_threshold * 0.7)
                else:
                    threshold = base_threshold
                
                self.calibrated_thresholds[key] = threshold
        
        logger.info(f"Calibrated {len(self.calibrated_thresholds)} thresholds from {len(feedback)} feedback records")
        return self.calibrated_thresholds
