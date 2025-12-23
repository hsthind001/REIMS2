"""
Risk Engine Health API Endpoint

Provides KPIs: coverage, runtime, latency, volumes, false-positive rates.
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.model_monitoring_service import ModelMonitoringService

router = APIRouter(prefix="/api/v1/risk-engine-health", tags=["risk-engine-health"])


@router.get("/metrics")
async def get_risk_engine_metrics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get risk engine health metrics.
    
    Returns KPIs: coverage, runtime, latency, volumes, false-positive rates.
    """
    monitoring_service = ModelMonitoringService(db)
    
    # Calculate lookback days
    if end_date:
        lookback_days = (end_date - (start_date or datetime.utcnow() - timedelta(days=30))).days
    else:
        lookback_days = 30
    
    metrics = monitoring_service.calculate_performance_metrics(lookback_days=lookback_days)
    
    # Filter by severity if provided
    if severity:
        metrics['alert_volumes'] = {
            k: v for k, v in metrics['alert_volumes'].items()
            if k.lower() == severity.lower() or k == 'total'
        }
    
    return metrics


@router.get("/degradation-alerts")
async def get_degradation_alerts(
    db: Session = Depends(get_db)
):
    """Get alerts for model performance degradation."""
    monitoring_service = ModelMonitoringService(db)
    metrics = monitoring_service.calculate_performance_metrics()
    
    alerts = []
    
    # Check for degradation
    if metrics['false_positive_ratio']['false_positive_rate'] > 0.25:
        alerts.append({
            'type': 'high_fpr',
            'severity': 'warning',
            'message': f"False positive rate ({metrics['false_positive_ratio']['false_positive_rate']:.1%}) exceeds threshold (25%)"
        })
    
    if metrics['detection_coverage']['account_coverage_percentage'] < 80:
        alerts.append({
            'type': 'low_coverage',
            'severity': 'warning',
            'message': f"Detection coverage ({metrics['detection_coverage']['account_coverage_percentage']:.1f}%) below target (80%)"
        })
    
    return {'alerts': alerts, 'timestamp': datetime.utcnow().isoformat()}
