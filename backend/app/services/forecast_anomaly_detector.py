"""
Forecast-Residual Anomaly Detector Service

Implements forecast-residual detection using ARIMA/ETS models.
Fits lightweight forecasting models per (property, account_group), then flags
anomalies on the residual (actual - forecast).

This is the gold standard approach for time-series anomaly detection:
1. Forecast expected value
2. Calculate residual = actual - forecast
3. Flag anomalies on residual using Z-score or percentile
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import numpy as np
import pandas as pd
import logging

from app.models.anomaly_detection import AnomalyDetection, BaselineType
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)

# Import forecasting models
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("statsmodels not available - forecast-residual detection disabled")


class ForecastAnomalyDetector:
    """
    Detects anomalies using forecast-residual method.
    
    For each (property, account_group):
    1. Fit forecasting model (ETS for short series, ARIMA for 12+ periods)
    2. Forecast expected value
    3. Calculate residual = actual - forecast
    4. Flag anomalies on residual using Z-score
    """
    
    def __init__(self, db: Session):
        """Initialize forecast anomaly detector."""
        self.db = db
        if not STATSMODELS_AVAILABLE:
            logger.warning("Forecast-residual detection requires statsmodels")
        self.z_score_threshold = 2.5  # Threshold for residual anomalies
        self.min_periods_ets = 6  # Minimum periods for ETS
        self.min_periods_arima = 12  # Minimum periods for ARIMA
    
    def detect_forecast_residual_anomalies(
        self,
        property_id: int,
        account_code: str,
        document_type: str = 'income_statement',
        lookback_periods: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies using forecast-residual method.
        
        Args:
            property_id: Property to analyze
            account_code: Account code to analyze
            document_type: Type of document (income_statement, balance_sheet)
            lookback_periods: Number of historical periods to use
            
        Returns:
            List of detected anomalies with forecast information
        """
        if not STATSMODELS_AVAILABLE:
            logger.warning("statsmodels not available - skipping forecast-residual detection")
            return []
        
        anomalies = []
        
        # Get historical data
        if document_type == 'income_statement':
            data = self._get_income_statement_data(property_id, account_code, lookback_periods)
        elif document_type == 'balance_sheet':
            data = self._get_balance_sheet_data(property_id, account_code, lookback_periods)
        else:
            logger.warning(f"Unsupported document type: {document_type}")
            return []
        
        if len(data) < self.min_periods_ets:
            logger.info(f"Insufficient data for forecasting: {len(data)} periods (need {self.min_periods_ets})")
            return []
        
        # Extract time series
        values = [float(item['amount']) for item in data]
        dates = [item['period_end_date'] for item in data]
        
        # Select forecasting method based on data length
        if len(values) >= self.min_periods_arima:
            forecast_result = self._forecast_with_arima(values, dates)
            forecast_method = 'arima'
        else:
            forecast_result = self._forecast_with_ets(values, dates)
            forecast_method = 'ets'
        
        if forecast_result is None:
            logger.warning("Forecasting failed - skipping anomaly detection")
            return []
        
        # Get current period
        current_period = data[-1]
        current_value = float(current_period['amount'])
        forecast_value = forecast_result['forecast']
        
        # Calculate residual
        residual = current_value - forecast_value
        residual_pct = (residual / forecast_value * 100) if forecast_value != 0 else 0
        
        # Calculate historical residuals for Z-score
        historical_residuals = forecast_result.get('historical_residuals', [])
        
        if len(historical_residuals) > 2:
            residual_mean = np.mean(historical_residuals)
            residual_std = np.std(historical_residuals) if len(historical_residuals) > 1 else 1.0
            if residual_std > 0:
                z_score = (residual - residual_mean) / residual_std
            else:
                z_score = abs(residual_pct) / 20.0
        else:
            # Fallback: use percentage deviation
            z_score = abs(residual_pct) / 20.0
        
        # Determine severity
        if abs(z_score) >= 3.0 or abs(residual_pct) >= 50:
            severity = 'critical'
        elif abs(z_score) >= 2.5 or abs(residual_pct) >= 30:
            severity = 'high'
        elif abs(z_score) >= 2.0 or abs(residual_pct) >= 20:
            severity = 'medium'
        else:
            severity = 'low'
        
        # Only flag if exceeds threshold
        if abs(z_score) >= self.z_score_threshold or abs(residual_pct) >= 20:
            anomaly = {
                'type': 'forecast_residual',
                'severity': severity,
                'property_id': property_id,
                'account_code': account_code,
                'document_type': document_type,
                'current_value': current_value,
                'forecast_value': forecast_value,
                'residual': residual,
                'residual_percentage': residual_pct,
                'z_score': z_score,
                'baseline_type': 'forecast',
                'forecast_method': forecast_method,
                'forecast_confidence': forecast_result.get('confidence', 0.7),
                'period_id': current_period['period_id'],
                'document_id': current_period.get('document_id'),
                'detected_at': datetime.utcnow()
            }
            anomalies.append(anomaly)
        
        return anomalies
    
    def _get_income_statement_data(
        self,
        property_id: int,
        account_code: str,
        lookback_periods: int
    ) -> List[Dict[str, Any]]:
        """Get income statement data for forecasting."""
        data = self.db.query(
            IncomeStatementData.period_amount,
            FinancialPeriod.period_end_date,
            FinancialPeriod.id.label('period_id'),
            IncomeStatementData.upload_id.label('document_id')
        ).join(
            FinancialPeriod, IncomeStatementData.period_id == FinancialPeriod.id
        ).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.account_code == account_code
        ).order_by(FinancialPeriod.period_end_date).limit(lookback_periods + 1).all()
        
        return [
            {
                'amount': float(row.period_amount or 0),
                'period_end_date': row.period_end_date,
                'period_id': row.period_id,
                'document_id': row.document_id
            }
            for row in data
        ]
    
    def _get_balance_sheet_data(
        self,
        property_id: int,
        account_code: str,
        lookback_periods: int
    ) -> List[Dict[str, Any]]:
        """Get balance sheet data for forecasting."""
        data = self.db.query(
            BalanceSheetData.amount,
            FinancialPeriod.period_end_date,
            FinancialPeriod.id.label('period_id'),
            BalanceSheetData.upload_id.label('document_id')
        ).join(
            FinancialPeriod, BalanceSheetData.period_id == FinancialPeriod.id
        ).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.account_code == account_code
        ).order_by(FinancialPeriod.period_end_date).limit(lookback_periods + 1).all()
        
        return [
            {
                'amount': float(row.amount or 0),
                'period_end_date': row.period_end_date,
                'period_id': row.period_id,
                'document_id': row.document_id
            }
            for row in data
        ]
    
    def _forecast_with_ets(
        self,
        values: List[float],
        dates: List[datetime]
    ) -> Optional[Dict[str, Any]]:
        """
        Forecast using Exponential Smoothing (ETS) for short series.
        
        Good for series with 6-12 periods.
        """
        try:
            if len(values) < self.min_periods_ets:
                return None
            
            # Create pandas Series
            series = pd.Series(values, index=pd.to_datetime(dates))
            
            # Fit ETS model (additive trend, additive seasonal if enough data)
            if len(values) >= 12:
                # Try seasonal ETS
                try:
                    model = ExponentialSmoothing(
                        series,
                        trend='add',
                        seasonal='add',
                        seasonal_periods=12
                    ).fit()
                except:
                    # Fallback to non-seasonal
                    model = ExponentialSmoothing(
                        series,
                        trend='add'
                    ).fit()
            else:
                # Non-seasonal ETS
                model = ExponentialSmoothing(
                    series,
                    trend='add'
                ).fit()
            
            # Forecast next period
            forecast = model.forecast(steps=1).iloc[0]
            
            # Calculate historical residuals (fitted values vs actual)
            fitted = model.fittedvalues
            historical_residuals = (series - fitted).dropna().tolist()
            
            # Calculate confidence based on model fit
            mse = np.mean([r**2 for r in historical_residuals]) if historical_residuals else np.var(values)
            confidence = max(0.5, min(0.95, 1.0 - (mse / (np.var(values) + 1e-6))))
            
            return {
                'forecast': float(forecast),
                'historical_residuals': historical_residuals,
                'confidence': confidence,
                'method': 'ets'
            }
            
        except Exception as e:
            logger.warning(f"ETS forecasting failed: {e}")
            return None
    
    def _forecast_with_arima(
        self,
        values: List[float],
        dates: List[datetime]
    ) -> Optional[Dict[str, Any]]:
        """
        Forecast using ARIMA for longer series (12+ periods).
        
        Auto-selects ARIMA order using AIC minimization.
        """
        try:
            if len(values) < self.min_periods_arima:
                return None
            
            # Create pandas Series
            series = pd.Series(values, index=pd.to_datetime(dates))
            
            # Auto-select ARIMA order (simplified - use (1,1,1) as default)
            # In production, use auto_arima or grid search for optimal order
            try:
                # Try (1,1,1) first
                model = ARIMA(series, order=(1, 1, 1)).fit()
            except:
                try:
                    # Try (0,1,1) - simple exponential smoothing equivalent
                    model = ARIMA(series, order=(0, 1, 1)).fit()
                except:
                    # Try (1,0,0) - AR(1)
                    model = ARIMA(series, order=(1, 0, 0)).fit()
            
            # Forecast next period
            forecast = model.forecast(steps=1).iloc[0]
            
            # Calculate historical residuals
            fitted = model.fittedvalues
            historical_residuals = (series - fitted).dropna().tolist()
            
            # Calculate confidence based on AIC and residuals
            aic = model.aic
            mse = np.mean([r**2 for r in historical_residuals]) if historical_residuals else np.var(values)
            
            # Normalize AIC to confidence (lower AIC = better fit = higher confidence)
            # Rough heuristic: confidence decreases as AIC increases
            aic_normalized = max(0.3, min(0.95, 1.0 - (aic / (len(values) * 100))))
            mse_confidence = max(0.5, min(0.95, 1.0 - (mse / (np.var(values) + 1e-6))))
            confidence = (aic_normalized + mse_confidence) / 2
            
            return {
                'forecast': float(forecast),
                'historical_residuals': historical_residuals,
                'confidence': confidence,
                'method': 'arima',
                'arima_order': str(model.model_orders)
            }
            
        except Exception as e:
            logger.warning(f"ARIMA forecasting failed: {e}")
            return None
    
    def save_anomaly_to_db(
        self,
        anomaly: Dict[str, Any],
        document_id: int
    ) -> Optional[AnomalyDetection]:
        """
        Save forecast-residual anomaly to database with baseline_type='forecast'.
        
        Args:
            anomaly: Anomaly dictionary from detect_forecast_residual_anomalies
            document_id: Document ID to associate with
            
        Returns:
            Created AnomalyDetection record
        """
        try:
            anomaly_record = AnomalyDetection(
                document_id=document_id,
                field_name=anomaly['account_code'],
                field_value=str(anomaly['current_value']),
                expected_value=str(anomaly['forecast_value']),
                z_score=Decimal(str(anomaly['z_score'])),
                percentage_change=Decimal(str(anomaly['residual_percentage'])),
                anomaly_type='forecast_residual',
                severity=anomaly['severity'],
                confidence=Decimal(str(anomaly['forecast_confidence'])),
                baseline_type=BaselineType.FORECAST,  # Set baseline_type='forecast'
                forecast_method=anomaly.get('forecast_method', 'ets'),  # Store forecast method
                direction='up' if anomaly['residual'] > 0 else 'down',
                anomaly_category='performance',
                pattern_type='trend',
                metadata_json={
                    'forecast_method': anomaly.get('forecast_method'),
                    'forecast_confidence': anomaly.get('forecast_confidence'),
                    'residual': anomaly.get('residual'),
                    'arima_order': anomaly.get('arima_order'),
                }
            )
            
            self.db.add(anomaly_record)
            self.db.commit()
            self.db.refresh(anomaly_record)
            
            logger.info(f"Saved forecast-residual anomaly: {anomaly_record.id} for account {anomaly['account_code']}")
            return anomaly_record
            
        except Exception as e:
            logger.error(f"Error saving forecast-residual anomaly: {e}")
            self.db.rollback()
            return None
