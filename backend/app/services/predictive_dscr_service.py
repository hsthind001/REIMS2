"""
Predictive DSCR Service

Forecasts DSCR 3-6 months ahead using trend analysis and alerts on covenant breaches.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import numpy as np
import pandas as pd
import logging

from app.models.financial_metrics import FinancialMetrics
from app.models.committee_alert import CommitteeAlert, AlertType, AlertSeverity
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("statsmodels not available - predictive DSCR disabled")


class PredictiveDSCRService:
    """
    Forecasts DSCR and alerts on covenant breaches.
    
    Uses ARIMA or exponential smoothing to forecast 3-6 months ahead.
    """
    
    def __init__(self, db: Session):
        """Initialize predictive DSCR service."""
        self.db = db
        self.dscr_threshold = 1.25  # Default covenant threshold
        self.forecast_horizon_months = 6
    
    def forecast_dscr(
        self,
        property_id: int,
        forecast_months: int = 6
    ) -> Dict[str, Any]:
        """
        Forecast DSCR for next N months.
        
        Args:
            property_id: Property ID
            forecast_months: Number of months to forecast (3-6)
            
        Returns:
            Dict with forecast results and breach alerts
        """
        if not STATSMODELS_AVAILABLE:
            return {'error': 'statsmodels not available'}
        
        # Get historical DSCR data
        dscr_history = self._get_dscr_history(property_id)
        
        if len(dscr_history) < 12:
            return {'error': 'Insufficient historical data (need 12+ months)'}
        
        # Forecast using ARIMA
        forecast = self._forecast_with_arima(dscr_history, forecast_months)
        
        # Check for covenant breaches
        breach_alerts = []
        for month, dscr_value in enumerate(forecast['forecast_values'], 1):
            if dscr_value < self.dscr_threshold:
                breach_alerts.append({
                    'month': month,
                    'forecasted_dscr': dscr_value,
                    'threshold': self.dscr_threshold,
                    'breach_magnitude': self.dscr_threshold - dscr_value
                })
        
        # Store forecast (in production, would store in dscr_forecasts table)
        forecast_result = {
            'property_id': property_id,
            'forecast_months': forecast_months,
            'forecast_values': forecast['forecast_values'],
            'confidence_intervals': forecast.get('confidence_intervals', []),
            'breach_alerts': breach_alerts,
            'forecast_date': datetime.utcnow().isoformat()
        }
        
        # Create alerts for breaches
        if breach_alerts:
            self._create_breach_alerts(property_id, breach_alerts)
        
        return forecast_result
    
    def _get_dscr_history(self, property_id: int) -> List[float]:
        """Get historical DSCR values."""
        metrics = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id
        ).order_by(FinancialMetrics.period_id).all()
        
        dscr_values = []
        for metric in metrics:
            if metric.net_operating_income and metric.total_debt:
                noi = float(metric.net_operating_income)
                debt = float(metric.total_debt)
                # Estimate annual debt service (5% interest)
                annual_debt_service = (debt * 0.05)
                dscr = noi / annual_debt_service if annual_debt_service > 0 else 0.0
                dscr_values.append(dscr)
        
        return dscr_values
    
    def _forecast_with_arima(
        self,
        history: List[float],
        forecast_months: int
    ) -> Dict[str, Any]:
        """Forecast using ARIMA model."""
        try:
            series = pd.Series(history)
            
            # Fit ARIMA model
            model = ARIMA(series, order=(1, 1, 1)).fit()
            
            # Forecast
            forecast = model.forecast(steps=forecast_months)
            
            return {
                'forecast_values': forecast.tolist(),
                'model_aic': model.aic
            }
        except Exception as e:
            logger.error(f"ARIMA forecasting error: {e}")
            # Fallback to simple trend
            return {
                'forecast_values': [history[-1]] * forecast_months,
                'model_aic': None
            }
    
    def _create_breach_alerts(
        self,
        property_id: int,
        breach_alerts: List[Dict[str, Any]]
    ) -> None:
        """Create alerts for DSCR covenant breaches."""
        from app.models.committee_alert import CommitteeType, AlertStatus
        
        for breach in breach_alerts:
            alert = CommitteeAlert(
                property_id=property_id,
                alert_type=AlertType.COVENANT_BREACH,
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.ACTIVE,
                title=f"Forecasted DSCR Breach in {breach['month']} months",
                description=(
                    f"DSCR forecast indicates breach in {breach['month']} months. "
                    f"Forecasted DSCR: {breach['forecasted_dscr']:.2f}, "
                    f"Threshold: {breach['threshold']:.2f}"
                ),
                assigned_committee=CommitteeType.RISK_COMMITTEE,
                requires_approval=True,
                metadata={
                    'forecast_month': breach['month'],
                    'forecasted_dscr': breach['forecasted_dscr'],
                    'breach_magnitude': breach['breach_magnitude']
                }
            )
            
            self.db.add(alert)
        
        self.db.commit()
