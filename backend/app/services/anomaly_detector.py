"""
Statistical Anomaly Detector Service

Detects anomalies using Z-score, percentage change, missing data detection,
and historical baseline comparison.

Enhanced with:
- Time series forecasting (Prophet, ARIMA, ETS)
- Weighted historical averages (EWMA)
- Seasonal decomposition
- Multiple detection windows
- Percentile-based detection
"""

from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import statistics
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Optional imports for advanced forecasting
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("Prophet not available - time series forecasting will be limited")

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("statsmodels not available - ARIMA/ETS forecasting disabled")

# Import seasonal analyzer
try:
    from app.services.seasonal_analyzer import SeasonalAnalyzer
    SEASONAL_AVAILABLE = True
except ImportError:
    SEASONAL_AVAILABLE = False
    logger.warning("SeasonalAnalyzer not available")


class StatisticalAnomalyDetector:
    """
    Statistical anomaly detection using multiple methods.
    
    Enhanced with intelligent forecasting and weighted averages.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.z_score_threshold = 2.0  # Lowered from 3.0 to 2.0 for more sensitive detection (2 sigma)
        self.percentage_change_threshold = 0.15  # Lowered from 0.25 to 0.15 (15% change) for more sensitive detection
        
        # Initialize seasonal analyzer if available
        if SEASONAL_AVAILABLE:
            self.seasonal_analyzer = SeasonalAnalyzer()
        else:
            self.seasonal_analyzer = None
    
    def detect_anomalies(
        self,
        document_id: int,
        field_name: str,
        current_value: float,
        historical_values: List[float],
        threshold_value: Optional[float] = None,
        historical_dates: Optional[List[datetime]] = None,
        current_date: Optional[datetime] = None,
        use_forecasting: bool = True,
        use_weighted_avg: bool = True
    ) -> Dict[str, Any]:
        """
        Detect anomalies using multiple statistical methods.
        
        Enhanced with intelligent forecasting and weighted averages.
        
        Args:
            document_id: Document ID
            field_name: Field/account code name
            current_value: Current period value
            historical_values: List of historical values for comparison
            threshold_value: Percentage threshold as decimal (e.g., 0.01 = 1%). If >= 100, treated as absolute value for backward compatibility.
            historical_dates: Optional list of dates corresponding to historical_values (for forecasting)
            current_date: Optional current period date (for forecasting)
            use_forecasting: Whether to use time series forecasting for expected value
            use_weighted_avg: Whether to use weighted averages (EWMA) instead of simple mean
        
        Returns:
            Dict with anomaly detection results
        """
        anomalies = []
        
        if len(historical_values) < 1:
            return {"anomalies": [], "insufficient_data": True}
        
        # Calculate expected value using enhanced methods
        expected_value_result = self._calculate_expected_value(
            historical_values,
            historical_dates,
            current_date,
            use_forecasting=use_forecasting and len(historical_values) >= 12,  # Need 12+ months for forecasting
            use_weighted_avg=use_weighted_avg
        )
        
        expected_value = expected_value_result.get('expected_value', statistics.mean(historical_values))
        forecast_method = expected_value_result.get('method', 'mean')
        
        # Z-score detection (requires 2+ values for standard deviation)
        if len(historical_values) >= 2:
            z_anomaly = self._detect_z_score_anomaly(current_value, historical_values, expected_value)
            if z_anomaly:
                z_anomaly['forecast_method'] = forecast_method
                anomalies.append(z_anomaly)
        
        # Percentile-based detection (more robust to outliers)
        if len(historical_values) >= 5:
            percentile_anomaly = self._detect_percentile_anomaly(current_value, historical_values)
            if percentile_anomaly:
                percentile_anomaly['forecast_method'] = forecast_method
                anomalies.append(percentile_anomaly)
        
        # Absolute value or percentage change detection (works with 1+ values)
        if threshold_value is not None:
            # Use enhanced expected value for threshold comparison
            abs_anomaly = self._detect_absolute_value_anomaly(
                current_value, 
                historical_values, 
                threshold_value,
                expected_value=expected_value
            )
            if abs_anomaly:
                abs_anomaly['forecast_method'] = forecast_method
                anomalies.append(abs_anomaly)
        else:
            # Fallback to percentage-based detection (for backward compatibility)
            pct_anomaly = self._detect_percentage_change(
                current_value, 
                historical_values,
                expected_value=expected_value
            )
            if pct_anomaly:
                pct_anomaly['forecast_method'] = forecast_method
                anomalies.append(pct_anomaly)
        
        return {
            "anomalies": anomalies,
            "field_name": field_name,
            "current_value": current_value,
            "expected_value": expected_value,
            "forecast_method": forecast_method,
            "forecast_details": expected_value_result
        }
    
    def _calculate_expected_value(
        self,
        historical_values: List[float],
        historical_dates: Optional[List[datetime]] = None,
        current_date: Optional[datetime] = None,
        use_forecasting: bool = True,
        use_weighted_avg: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate expected value using intelligent methods.
        
        Priority:
        1. Time series forecasting (Prophet/ARIMA/ETS) if dates available and sufficient data
        2. Seasonal decomposition + trend if seasonal analyzer available
        3. Weighted moving average (EWMA) if enabled
        4. Simple mean (fallback)
        
        Returns:
            Dict with expected_value, method, confidence, and details
        """
        if len(historical_values) < 1:
            return {
                'expected_value': 0.0,
                'method': 'insufficient_data',
                'confidence': 0.0
            }
        
        # Method 1: Time series forecasting (requires dates and 12+ months)
        if use_forecasting and historical_dates and current_date and len(historical_values) >= 12:
            forecast_result = self._forecast_expected_value(
                historical_values,
                historical_dates,
                current_date
            )
            if forecast_result and forecast_result.get('expected_value') is not None:
                return forecast_result
        
        # Method 2: Seasonal decomposition (if analyzer available and dates provided)
        if (self.seasonal_analyzer and historical_dates and current_date and 
            len(historical_values) >= 12):
            seasonal_result = self.seasonal_analyzer.calculate_seasonal_expected_value(
                historical_values,
                historical_dates,
                current_date
            )
            if seasonal_result and seasonal_result.get('expected_value') is not None:
                return {
                    'expected_value': seasonal_result['expected_value'],
                    'method': 'seasonal_decomposition',
                    'confidence': seasonal_result.get('confidence', 0.7),
                    'trend_value': seasonal_result.get('trend_value'),
                    'seasonal_component': seasonal_result.get('seasonal_component')
                }
        
        # Method 3: Weighted moving average (EWMA)
        if use_weighted_avg and len(historical_values) >= 3:
            ewma_value = self._calculate_ewma(historical_values)
            return {
                'expected_value': ewma_value,
                'method': 'ewma',
                'confidence': min(0.85, 0.5 + (len(historical_values) / 60.0) * 0.35)
            }
        
        # Method 4: Simple mean (fallback)
        mean_value = statistics.mean(historical_values)
        return {
            'expected_value': mean_value,
            'method': 'mean',
            'confidence': 0.6
        }
    
    def _forecast_expected_value(
        self,
        historical_values: List[float],
        historical_dates: List[datetime],
        target_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Forecast expected value using ensemble of forecasting models.
        
        Tries Prophet, ARIMA, and ETS, then combines with weighted voting.
        """
        if len(historical_values) < 12 or len(historical_dates) != len(historical_values):
            return None
        
        forecasts = []
        
        # Try Prophet (best for seasonality)
        if PROPHET_AVAILABLE and len(historical_values) >= 24:
            try:
                prophet_forecast = self._prophet_forecast(historical_values, historical_dates, target_date)
                if prophet_forecast:
                    forecasts.append(prophet_forecast)
            except Exception as e:
                logger.debug(f"Prophet forecast failed: {e}")
        
        # Try ARIMA (good for trends)
        if STATSMODELS_AVAILABLE and len(historical_values) >= 12:
            try:
                arima_forecast = self._arima_forecast(historical_values, historical_dates, target_date)
                if arima_forecast:
                    forecasts.append(arima_forecast)
            except Exception as e:
                logger.debug(f"ARIMA forecast failed: {e}")
        
        # Try Exponential Smoothing (good for short-term)
        if STATSMODELS_AVAILABLE and len(historical_values) >= 12:
            try:
                ets_forecast = self._ets_forecast(historical_values, historical_dates, target_date)
                if ets_forecast:
                    forecasts.append(ets_forecast)
            except Exception as e:
                logger.debug(f"ETS forecast failed: {e}")
        
        # Combine forecasts with weighted voting
        if forecasts:
            return self._ensemble_forecast(forecasts)
        
        return None
    
    def _prophet_forecast(
        self,
        values: List[float],
        dates: List[datetime],
        target_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """Forecast using Facebook Prophet."""
        try:
            # Prepare data for Prophet
            df = pd.DataFrame({
                'ds': pd.to_datetime(dates),
                'y': values
            })
            
            # Fit model
            model = Prophet(
                yearly_seasonality=True if len(values) >= 24 else False,
                weekly_seasonality=False,  # Financial data is typically monthly
                daily_seasonality=False,
                seasonality_mode='additive'
            )
            model.fit(df)
            
            # Forecast
            future = model.make_future_dataframe(periods=1)
            forecast = model.predict(future)
            
            # Get forecast for target date
            target_forecast = forecast[forecast['ds'] == pd.to_datetime(target_date)]
            
            if not target_forecast.empty:
                expected = float(target_forecast['yhat'].iloc[0])
                lower_bound = float(target_forecast['yhat_lower'].iloc[0])
                upper_bound = float(target_forecast['yhat_upper'].iloc[0])
                
                return {
                    'expected_value': expected,
                    'method': 'prophet',
                    'confidence': 0.85,
                    'lower_bound': lower_bound,
                    'upper_bound': upper_bound,
                    'weight': 0.4  # Weight for ensemble
                }
        except Exception as e:
            logger.warning(f"Prophet forecasting error: {e}")
            return None
    
    def _arima_forecast(
        self,
        values: List[float],
        dates: List[datetime],
        target_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """Forecast using ARIMA model."""
        try:
            # Convert to pandas Series
            series = pd.Series(values, index=pd.to_datetime(dates))
            
            # Auto-select ARIMA order (simplified - could use auto_arima)
            # For monthly data, try (1,1,1) or (2,1,2)
            try:
                model = ARIMA(series, order=(1, 1, 1))
                fitted = model.fit()
                
                # Forecast 1 step ahead
                forecast = fitted.forecast(steps=1)
                conf_int = fitted.get_forecast(steps=1).conf_int()
                
                expected = float(forecast.iloc[0])
                lower_bound = float(conf_int.iloc[0, 0])
                upper_bound = float(conf_int.iloc[0, 1])
                
                return {
                    'expected_value': expected,
                    'method': 'arima',
                    'confidence': 0.80,
                    'lower_bound': lower_bound,
                    'upper_bound': upper_bound,
                    'weight': 0.35
                }
            except Exception:
                # Try simpler model
                model = ARIMA(series, order=(0, 1, 0))  # Simple random walk
                fitted = model.fit()
                forecast = fitted.forecast(steps=1)
                expected = float(forecast.iloc[0])
                
                return {
                    'expected_value': expected,
                    'method': 'arima_simple',
                    'confidence': 0.70,
                    'weight': 0.25
                }
        except Exception as e:
            logger.warning(f"ARIMA forecasting error: {e}")
            return None
    
    def _ets_forecast(
        self,
        values: List[float],
        dates: List[datetime],
        target_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """Forecast using Exponential Smoothing (ETS)."""
        try:
            series = pd.Series(values, index=pd.to_datetime(dates))
            
            # Fit exponential smoothing model
            model = ExponentialSmoothing(
                series,
                seasonal_periods=12 if len(values) >= 24 else None,
                trend='add',
                seasonal='add' if len(values) >= 24 else None
            )
            fitted = model.fit()
            
            # Forecast
            forecast = fitted.forecast(steps=1)
            expected = float(forecast.iloc[0])
            
            return {
                'expected_value': expected,
                'method': 'ets',
                'confidence': 0.75,
                'weight': 0.25
            }
        except Exception as e:
            logger.warning(f"ETS forecasting error: {e}")
            return None
    
    def _ensemble_forecast(self, forecasts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine multiple forecasts using weighted voting.
        
        Weights are based on model confidence and historical accuracy.
        """
        if not forecasts:
            return None
        
        # Calculate weighted average
        total_weight = sum(f.get('weight', 0.33) for f in forecasts)
        if total_weight == 0:
            total_weight = len(forecasts)
        
        weighted_sum = sum(f['expected_value'] * f.get('weight', 0.33) for f in forecasts)
        expected_value = weighted_sum / total_weight
        
        # Average confidence
        avg_confidence = np.mean([f.get('confidence', 0.7) for f in forecasts])
        
        # Combine bounds if available
        lower_bounds = [f.get('lower_bound') for f in forecasts if f.get('lower_bound')]
        upper_bounds = [f.get('upper_bound') for f in forecasts if f.get('upper_bound')]
        
        result = {
            'expected_value': expected_value,
            'method': 'ensemble',
            'confidence': avg_confidence,
            'models_used': [f.get('method') for f in forecasts],
            'model_count': len(forecasts)
        }
        
        if lower_bounds:
            result['lower_bound'] = np.mean(lower_bounds)
        if upper_bounds:
            result['upper_bound'] = np.mean(upper_bounds)
        
        return result
    
    def _calculate_ewma(
        self,
        values: List[float],
        decay_factor: float = 0.1
    ) -> float:
        """
        Calculate Exponential Weighted Moving Average.
        
        Args:
            values: Historical values (most recent last)
            decay_factor: Decay factor (lambda) - higher = more weight on recent values
        
        Returns:
            EWMA expected value
        """
        if not values:
            return 0.0
        
        # Reverse to get chronological order (oldest first)
        values_chrono = list(reversed(values))
        
        # Calculate weights: w_i = e^(-λ * age_in_periods)
        weights = []
        for i in range(len(values_chrono)):
            age = len(values_chrono) - 1 - i  # Age in periods (0 = most recent)
            weight = np.exp(-decay_factor * age)
            weights.append(weight)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return statistics.mean(values)
        
        # Weighted average
        weighted_sum = sum(v * w for v, w in zip(values_chrono, weights))
        return weighted_sum / total_weight
    
    def _detect_z_score_anomaly(
        self,
        value: float,
        historical_values: List[float],
        expected_value: Optional[float] = None
    ) -> Optional[Dict]:
        """Detect anomaly using Z-score"""
        if len(historical_values) < 2:
            return None
        
        # Use provided expected_value or calculate mean
        if expected_value is not None:
            mean = expected_value
        else:
            mean = statistics.mean(historical_values)
        
        stdev = statistics.stdev(historical_values) if len(historical_values) > 1 else 0
        
        if stdev == 0:
            return None
        
        z_score = (value - mean) / stdev
        
        if abs(z_score) > self.z_score_threshold:
            return {
                "type": "z_score",
                "z_score": round(z_score, 4),
                "severity": "critical" if abs(z_score) > 4 else "high",
                "expected_range": (mean - 3 * stdev, mean + 3 * stdev)
            }
        
        return None
    
    def _detect_percentile_anomaly(
        self,
        value: float,
        historical_values: List[float],
        lower_percentile: float = 5.0,
        upper_percentile: float = 95.0
    ) -> Optional[Dict]:
        """
        Detect anomaly using percentile-based method (more robust to outliers).
        
        Args:
            value: Current value
            historical_values: Historical values
            lower_percentile: Lower percentile threshold (default 5th)
            upper_percentile: Upper percentile threshold (default 95th)
        
        Returns:
            Anomaly dict if detected, None otherwise
        """
        if len(historical_values) < 5:
            return None
        
        # Calculate percentiles
        p_lower = np.percentile(historical_values, lower_percentile)
        p_upper = np.percentile(historical_values, upper_percentile)
        
        # Check if value is outside percentile range
        if value < p_lower or value > p_upper:
            # Calculate how far outside
            if value < p_lower:
                deviation = (p_lower - value) / (p_upper - p_lower) if (p_upper - p_lower) > 0 else 0
                severity = "critical" if deviation > 0.5 else "high" if deviation > 0.25 else "medium"
            else:
                deviation = (value - p_upper) / (p_upper - p_lower) if (p_upper - p_lower) > 0 else 0
                severity = "critical" if deviation > 0.5 else "high" if deviation > 0.25 else "medium"
            
            return {
                "type": "percentile",
                "percentile_lower": round(p_lower, 2),
                "percentile_upper": round(p_upper, 2),
                "percentile_range": (lower_percentile, upper_percentile),
                "severity": severity,
                "deviation_ratio": round(deviation, 4)
            }
        
        return None
    
    def _detect_absolute_value_anomaly(
        self,
        value: float,
        historical_values: List[float],
        threshold_value: float,
        expected_value: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Detect anomaly using percentage-based threshold.
        
        Threshold is stored as a decimal (e.g., 0.01 = 1%).
        Anomaly is detected if: abs(percentage_change) > threshold_value
        
        For backward compatibility: if threshold_value >= 100, treat as absolute value threshold.
        
        Args:
            expected_value: Optional expected value (from forecasting). If None, uses mean.
        """
        if not historical_values:
            return None
        
        # Use provided expected_value or calculate mean
        if expected_value is not None:
            recent_avg = expected_value
        else:
            recent_avg = statistics.mean(historical_values) if len(historical_values) > 0 else None
        
        if recent_avg is None or recent_avg == 0:
            return None
        
        # Calculate percentage change (as decimal, e.g., 0.05 = 5%)
        pct_change = abs((value - recent_avg) / recent_avg)
        
        # Determine if threshold is percentage-based (< 1.0) or absolute (>= 100)
        # Thresholds between 1.0 and 100 are ambiguous, so we'll treat < 1.0 as percentage
        if threshold_value < 1.0:
            # Percentage-based threshold (e.g., 0.01 = 1%)
            threshold_exceeded = pct_change > threshold_value
            threshold_display = threshold_value * 100  # Convert to percentage for display
        else:
            # Absolute value threshold (backward compatibility)
            absolute_difference = abs(value - recent_avg)
            threshold_exceeded = absolute_difference > threshold_value
            threshold_display = threshold_value
            # Calculate percentage for display
            pct_change_display = pct_change * 100
        
        if threshold_exceeded:
            # Determine severity based on how much the threshold is exceeded
            if threshold_value < 1.0:
                # Percentage-based: compare percentage change to threshold percentage
                threshold_exceeded_ratio = pct_change / threshold_value if threshold_value > 0 else 0
                pct_change_display = pct_change * 100  # Convert to percentage for display
            else:
                # Absolute-based: compare absolute difference to threshold
                absolute_difference = abs(value - recent_avg)
                threshold_exceeded_ratio = absolute_difference / threshold_value if threshold_value > 0 else 0
                pct_change_display = pct_change * 100
            
            severity = "critical" if threshold_exceeded_ratio > 3.0 else "high" if threshold_exceeded_ratio > 2.0 else "medium"
            
            return {
                "type": "percentage_change" if threshold_value < 1.0 else "absolute_value_change",
                "absolute_difference": round(abs(value - recent_avg), 2) if threshold_value >= 1.0 else None,
                "percentage_change": round(pct_change_display, 2),  # Percentage for display
                "threshold_value": threshold_display,
                "threshold_type": "percentage" if threshold_value < 1.0 else "absolute",
                "severity": severity
            }
        
        return None
    
    def _detect_percentage_change(
        self,
        value: float,
        historical_values: List[float],
        expected_value: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Detect anomaly using percentage change (legacy method for backward compatibility).
        
        Args:
            expected_value: Optional expected value (from forecasting). If None, uses mean.
        """
        if not historical_values:
            return None
        
        # Use provided expected_value or calculate mean
        if expected_value is not None:
            recent_avg = expected_value
        else:
            recent_avg = statistics.mean(historical_values) if len(historical_values) > 0 else None
        
        if recent_avg is None or recent_avg == 0:
            return None
        
        # Calculate percentage change preserving the sign (positive = increase, negative = decrease)
        pct_change = (value - recent_avg) / recent_avg
        pct_change_abs = abs(pct_change)
        
        # Check threshold using absolute value, but store the signed value
        if pct_change_abs > self.percentage_change_threshold:
            return {
                "type": "percentage_change",
                "percentage_change": round(pct_change * 100, 2),  # Preserve sign: positive for increase, negative for decrease
                "severity": "critical" if pct_change_abs > 0.5 else "high" if pct_change_abs > 0.25 else "medium"
            }
        
        return None
    
    def detect_anomalies_multi_window(
        self,
        document_id: int,
        field_name: str,
        current_value: float,
        historical_values: List[float],
        historical_dates: Optional[List[datetime]] = None,
        current_date: Optional[datetime] = None,
        threshold_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect anomalies using multiple time windows.
        
        Combines signals from:
        - Short-term (3 months): Catches sudden changes
        - Medium-term (12 months): Current default
        - Long-term (24 months): Catches gradual drift
        
        Args:
            document_id: Document ID
            field_name: Field/account code name
            current_value: Current period value
            historical_values: List of historical values (most recent last)
            historical_dates: Optional list of dates
            current_date: Optional current date
            threshold_value: Percentage threshold
        
        Returns:
            Dict with anomalies from all windows and combined result
        """
        if len(historical_values) < 3:
            return {"anomalies": [], "insufficient_data": True}
        
        all_anomalies = []
        window_results = {}
        
        # Short-term window (3 months)
        if len(historical_values) >= 3:
            short_term_values = historical_values[-3:]
            short_term_dates = historical_dates[-3:] if historical_dates else None
            
            short_result = self.detect_anomalies(
                document_id=document_id,
                field_name=field_name,
                current_value=current_value,
                historical_values=short_term_values,
                historical_dates=short_term_dates,
                current_date=current_date,
                threshold_value=threshold_value,
                use_forecasting=False,  # Not enough data for forecasting
                use_weighted_avg=True
            )
            
            if short_result.get('anomalies'):
                for anomaly in short_result['anomalies']:
                    anomaly['window'] = 'short_term'
                    anomaly['window_months'] = 3
                all_anomalies.extend(short_result['anomalies'])
            
            window_results['short_term'] = {
                'anomalies_count': len(short_result.get('anomalies', [])),
                'expected_value': short_result.get('expected_value')
            }
        
        # Medium-term window (12 months)
        if len(historical_values) >= 6:
            medium_term_values = historical_values[-12:] if len(historical_values) >= 12 else historical_values
            medium_term_dates = historical_dates[-12:] if historical_dates and len(historical_dates) >= 12 else historical_dates
            
            medium_result = self.detect_anomalies(
                document_id=document_id,
                field_name=field_name,
                current_value=current_value,
                historical_values=medium_term_values,
                historical_dates=medium_term_dates,
                current_date=current_date,
                threshold_value=threshold_value,
                use_forecasting=len(medium_term_values) >= 12,
                use_weighted_avg=True
            )
            
            if medium_result.get('anomalies'):
                for anomaly in medium_result['anomalies']:
                    anomaly['window'] = 'medium_term'
                    anomaly['window_months'] = len(medium_term_values)
                all_anomalies.extend(medium_result['anomalies'])
            
            window_results['medium_term'] = {
                'anomalies_count': len(medium_result.get('anomalies', [])),
                'expected_value': medium_result.get('expected_value')
            }
        
        # Long-term window (24 months)
        if len(historical_values) >= 12:
            long_term_values = historical_values[-24:] if len(historical_values) >= 24 else historical_values
            long_term_dates = historical_dates[-24:] if historical_dates and len(historical_dates) >= 24 else historical_dates
            
            long_result = self.detect_anomalies(
                document_id=document_id,
                field_name=field_name,
                current_value=current_value,
                historical_values=long_term_values,
                historical_dates=long_term_dates,
                current_date=current_date,
                threshold_value=threshold_value,
                use_forecasting=len(long_term_values) >= 24,
                use_weighted_avg=True
            )
            
            if long_result.get('anomalies'):
                for anomaly in long_result['anomalies']:
                    anomaly['window'] = 'long_term'
                    anomaly['window_months'] = len(long_term_values)
                all_anomalies.extend(long_result['anomalies'])
            
            window_results['long_term'] = {
                'anomalies_count': len(long_result.get('anomalies', [])),
                'expected_value': long_result.get('expected_value')
            }
        
        # Combine results: anomaly detected if found in 2+ windows
        window_counts = {}
        for anomaly in all_anomalies:
            anomaly_type = anomaly.get('type', 'unknown')
            if anomaly_type not in window_counts:
                window_counts[anomaly_type] = set()
            window_counts[anomaly_type].add(anomaly.get('window', 'unknown'))
        
        # Filter: keep anomalies detected in multiple windows
        significant_anomalies = []
        for anomaly in all_anomalies:
            anomaly_type = anomaly.get('type', 'unknown')
            windows_detected = window_counts.get(anomaly_type, set())
            
            # Keep if detected in 2+ windows, or if it's a critical severity
            if len(windows_detected) >= 2 or anomaly.get('severity') == 'critical':
                anomaly['windows_detected'] = len(windows_detected)
                significant_anomalies.append(anomaly)
        
        return {
            "anomalies": significant_anomalies,
            "field_name": field_name,
            "current_value": current_value,
            "window_results": window_results,
            "total_windows_checked": len(window_results)
        }

