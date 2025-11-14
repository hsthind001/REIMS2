"""
Statistical Anomaly Detection API Endpoints

Z-score and CUSUM anomaly detection for financial metrics (BR-008)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.db.database import get_db
from app.services.statistical_anomaly_service import StatisticalAnomalyService
from app.models.property import Property

router = APIRouter(prefix="/statistical-anomalies", tags=["statistical_anomalies"])
logger = logging.getLogger(__name__)


class ZScoreDetectionRequest(BaseModel):
    property_id: int
    metric_name: str
    lookback_periods: int = 12
    threshold: float = 2.0


class CUSUMDetectionRequest(BaseModel):
    property_id: int
    metric_name: str
    lookback_periods: int = 12
    threshold: float = 3.0
    drift: float = 0.5


class ComprehensiveScanRequest(BaseModel):
    property_id: int
    metrics: Optional[List[str]] = None


@router.post("/zscore/detect")
def detect_zscore_anomalies(
    request: ZScoreDetectionRequest,
    db: Session = Depends(get_db)
):
    """
    Detect anomalies using Z-score method

    Z-score identifies outliers based on standard deviations from mean.

    **Thresholds:**
    - 2.0: Warning (2 standard deviations)
    - 3.0: Critical (3 standard deviations)
    - 3.5+: Urgent (3.5+ standard deviations)

    **Supported Metrics:**
    - total_revenue
    - noi
    - occupancy_rate
    - operating_expenses
    - net_income
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = StatisticalAnomalyService(db)

    try:
        result = service.detect_anomalies_zscore(
            property_id=request.property_id,
            metric_name=request.metric_name,
            lookback_periods=request.lookback_periods,
            threshold=request.threshold
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Z-score anomaly detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cusum/detect")
def detect_cusum_anomalies(
    request: CUSUMDetectionRequest,
    db: Session = Depends(get_db)
):
    """
    Detect anomalies using CUSUM (Cumulative Sum) method

    CUSUM detects sustained shifts in mean values over time.
    More sensitive to gradual changes than Z-score.

    **Thresholds:**
    - 3.0: Warning
    - 5.0: Critical
    - 6.0+: Urgent

    **Drift Parameter:**
    - Allowable drift (default 0.5 standard deviations)
    - Lower drift = more sensitive to small changes
    - Higher drift = only detects larger shifts
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = StatisticalAnomalyService(db)

    try:
        result = service.detect_anomalies_cusum(
            property_id=request.property_id,
            metric_name=request.metric_name,
            lookback_periods=request.lookback_periods,
            threshold=request.threshold,
            drift=request.drift
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"CUSUM anomaly detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/zscore")
def get_zscore_anomalies(
    property_id: int,
    metric_name: str = Query(..., description="Metric to analyze"),
    lookback_periods: int = Query(default=12, ge=3, le=50),
    threshold: float = Query(default=2.0, ge=1.0, le=5.0),
    db: Session = Depends(get_db)
):
    """
    Get Z-score anomalies for a property and metric

    Convenience GET endpoint for Z-score detection
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = StatisticalAnomalyService(db)

    try:
        result = service.detect_anomalies_zscore(
            property_id=property_id,
            metric_name=metric_name,
            lookback_periods=lookback_periods,
            threshold=threshold
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Z-score anomaly detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/cusum")
def get_cusum_anomalies(
    property_id: int,
    metric_name: str = Query(..., description="Metric to analyze"),
    lookback_periods: int = Query(default=12, ge=5, le=50),
    threshold: float = Query(default=3.0, ge=1.0, le=10.0),
    drift: float = Query(default=0.5, ge=0.1, le=2.0),
    db: Session = Depends(get_db)
):
    """
    Get CUSUM anomalies for a property and metric

    Convenience GET endpoint for CUSUM detection
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = StatisticalAnomalyService(db)

    try:
        result = service.detect_anomalies_cusum(
            property_id=property_id,
            metric_name=metric_name,
            lookback_periods=lookback_periods,
            threshold=threshold,
            drift=drift
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"CUSUM anomaly detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/volatility")
def detect_volatility_spikes(
    property_id: int,
    metric_name: str = Query(..., description="Metric to analyze"),
    lookback_periods: int = Query(default=12, ge=6, le=50),
    window_size: int = Query(default=3, ge=2, le=6),
    db: Session = Depends(get_db)
):
    """
    Detect volatility spikes using rolling standard deviation

    Identifies periods where volatility suddenly increases.

    **Parameters:**
    - window_size: Rolling window size for volatility calculation
    - lookback_periods: Historical periods to analyze

    **Detection Logic:**
    - Volatility > 2x average = Warning
    - Volatility > 3x average = Critical
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = StatisticalAnomalyService(db)

    try:
        result = service.detect_volatility_spikes(
            property_id=property_id,
            metric_name=metric_name,
            lookback_periods=lookback_periods,
            window_size=window_size
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Volatility spike detection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comprehensive-scan")
def comprehensive_anomaly_scan(
    request: ComprehensiveScanRequest,
    db: Session = Depends(get_db)
):
    """
    Comprehensive anomaly scan across multiple metrics

    Runs Z-score, CUSUM, and volatility detection on all key metrics.

    **Default Metrics Analyzed:**
    - total_revenue
    - noi
    - occupancy_rate
    - operating_expenses
    - net_income

    **Returns:**
    - Total anomalies detected across all metrics
    - Alerts created for critical anomalies
    - Detailed results by metric
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = StatisticalAnomalyService(db)

    try:
        result = service.comprehensive_anomaly_scan(
            property_id=request.property_id,
            metrics=request.metrics
        )

        return {
            "success": True,
            "property_id": request.property_id,
            "property_name": property.property_name,
            **result
        }

    except Exception as e:
        logger.error(f"Comprehensive anomaly scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/comprehensive-scan")
def get_comprehensive_scan(
    property_id: int,
    metrics: Optional[str] = Query(None, description="Comma-separated list of metrics"),
    db: Session = Depends(get_db)
):
    """
    Comprehensive anomaly scan (GET endpoint)

    Convenience GET endpoint for comprehensive scanning.

    **Example:**
    ```
    GET /statistical-anomalies/properties/1/comprehensive-scan?metrics=total_revenue,noi,occupancy_rate
    ```
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Parse metrics if provided
    metrics_list = None
    if metrics:
        metrics_list = [m.strip() for m in metrics.split(",")]

    service = StatisticalAnomalyService(db)

    try:
        result = service.comprehensive_anomaly_scan(
            property_id=property_id,
            metrics=metrics_list
        )

        return {
            "success": True,
            "property_id": property_id,
            "property_name": property.property_name,
            **result
        }

    except Exception as e:
        logger.error(f"Comprehensive anomaly scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/available")
def get_available_metrics():
    """
    Get list of available metrics for anomaly detection

    Returns all metrics that can be analyzed for anomalies
    """
    return {
        "success": True,
        "metrics": [
            {
                "name": "total_revenue",
                "display_name": "Total Revenue",
                "description": "Total revenue from all sources",
                "category": "Income"
            },
            {
                "name": "noi",
                "display_name": "Net Operating Income (NOI)",
                "description": "Revenue minus operating expenses",
                "category": "Income"
            },
            {
                "name": "operating_expenses",
                "display_name": "Operating Expenses",
                "description": "Total operating expenses",
                "category": "Expenses"
            },
            {
                "name": "net_income",
                "display_name": "Net Income",
                "description": "Bottom-line profit/loss",
                "category": "Income"
            },
            {
                "name": "occupancy_rate",
                "display_name": "Occupancy Rate",
                "description": "Percentage of occupied spaces",
                "category": "Operational"
            }
        ],
        "detection_methods": [
            {
                "name": "Z-score",
                "description": "Identifies outliers based on standard deviations from mean",
                "best_for": "Detecting sudden spikes or drops",
                "recommended_threshold": 2.0
            },
            {
                "name": "CUSUM",
                "description": "Detects sustained shifts in mean values over time",
                "best_for": "Identifying gradual trends and structural changes",
                "recommended_threshold": 3.0
            },
            {
                "name": "Volatility",
                "description": "Detects increases in variability",
                "best_for": "Identifying unstable periods",
                "recommended_window_size": 3
            }
        ]
    }
