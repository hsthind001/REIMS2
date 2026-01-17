
"""
Financial Forecasting Service using Facebook Prophet.

Provides time-series forecasting for key financial metrics (NOI, Revenue, Expenses).
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.financial_metrics import FinancialMetrics
from app.core.config import settings

logger = logging.getLogger(__name__)

# Optional Prophet import
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("Prophet not found. Forecasting disabled.")

class FinancialForecastingService:
    def __init__(self, db: Session):
        self.db = db

    def forecast_noi(self, property_id: int, periods: int = 12) -> Dict[str, Any]:
        """
        Forecast Net Operating Income (NOI) for the next `periods` months.
        """
        if not PROPHET_AVAILABLE:
            return {"error": "Prophet library not installed"}

        # 1. Fetch historical data
        try:
            metrics = self._fetch_historical_metrics(property_id)
            if len(metrics) < 12: # Need enough data points
                return {"error": "Insufficient historical data (need at least 12 months)"}

            # 2. Prepare DataFrame for Prophet (ds, y)
            df = pd.DataFrame([
                {
                    "ds": m.period_end_date, # Date
                    "y": float(m.net_operating_income) # Value
                } for m in metrics
            ])
            
            # Ensure dates are datetime
            df["ds"] = pd.to_datetime(df["ds"])
            
            # 3. Train Model
            model = Prophet(yearly_seasonality=True, daily_seasonality=False, weekly_seasonality=False)
            model.fit(df)
            
            # 4. Make Future DataFrame
            future = model.make_future_dataframe(periods=periods, freq='M')
            
            # 5. Predict
            forecast = model.predict(future)
            
            # 6. Format Result
            # Extract last `periods` rows (the forecast)
            future_forecast = forecast.tail(periods)
            
            result = {
                "property_id": property_id,
                "forecast_periods": periods,
                "data": [
                    {
                        "date": row["ds"].strftime("%Y-%m-%d"),
                        "predicted_noi": round(row["yhat"], 2),
                        "lower_bound": round(row["yhat_lower"], 2),
                        "upper_bound": round(row["yhat_upper"], 2)
                    }
                    for _, row in future_forecast.iterrows()
                ]
            }
            return result

        except Exception as e:
            logger.error(f"Forecasting failed: {e}")
            return {"error": str(e)}

    def _fetch_historical_metrics(self, property_id: int) -> List[FinancialMetrics]:
        stmt = select(FinancialMetrics).where(
            FinancialMetrics.property_id == property_id
        ).order_by(FinancialMetrics.period_end_date)
        return self.db.execute(stmt).scalars().all()
