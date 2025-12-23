"""
Feedback Calibration Celery Tasks

Weekly task to analyze anomaly feedback and adjust detection thresholds.
Updates model weights in ensemble based on feedback results.
"""

from celery import shared_task
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.database import SessionLocal
from app.services.adaptive_threshold_service import AdaptiveThresholdService
from app.services.anomaly_risk_scorer import AnomalyRiskScorer
from app.services.enhanced_anomaly_ensemble import EnhancedAnomalyEnsemble
import logging

logger = logging.getLogger(__name__)


@shared_task(name='feedback_calibration.weekly_recalibration')
def weekly_feedback_calibration():
    """
    Weekly Celery task to recalibrate thresholds and model weights.
    
    Analyzes anomaly_feedback table to:
    1. Calculate false positive rate per detector
    2. Adjust detection thresholds
    3. Update ensemble model weights
    """
    db: Session = SessionLocal()
    
    try:
        logger.info("Starting weekly feedback calibration")
        
        # 1. Recalibrate adaptive thresholds
        threshold_service = AdaptiveThresholdService(db)
        threshold_results = threshold_service.recalibrate_all_thresholds()
        logger.info(f"Recalibrated {threshold_results['recalibrated']} thresholds")
        
        # 2. Recalibrate ensemble weights
        ensemble = EnhancedAnomalyEnsemble(db)
        ensemble.calibrate_thresholds_from_feedback()
        logger.info("Recalibrated ensemble thresholds")
        
        # 3. Recalibrate risk scorer weights
        risk_scorer = AnomalyRiskScorer(db)
        updated_weights = risk_scorer.calibrate_weights_from_feedback()
        logger.info(f"Recalibrated risk scorer weights: {len(updated_weights)} detectors")
        
        # 4. Log calibration results
        calibration_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'thresholds_recalibrated': threshold_results['recalibrated'],
            'ensemble_thresholds_updated': True,
            'risk_scorer_weights_updated': True,
            'weights': updated_weights
        }
        
        logger.info(f"Weekly calibration complete: {calibration_log}")
        
        return calibration_log
        
    except Exception as e:
        logger.error(f"Error in weekly feedback calibration: {e}", exc_info=True)
        raise
    finally:
        db.close()
