"""
Seasonal Analyzer Service

Performs seasonal decomposition and trend analysis for anomaly detection.
Uses STL (Seasonal and Trend decomposition using Loess) to separate
normal seasonal patterns from anomalies.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.seasonal import STL
    from statsmodels.tsa.seasonal import seasonal_decompose
    STL_AVAILABLE = True
except ImportError:
    STL_AVAILABLE = False
    logger.warning("statsmodels not available - seasonal decomposition disabled")


class SeasonalAnalyzer:
    """
    Analyzes seasonal patterns and trends in financial time series data.
    
    Methods:
    - STL decomposition (Seasonal and Trend decomposition using Loess)
    - Seasonal adjustment factors
    - Trend extraction
    - Expected value calculation with seasonality
    """
    
    def __init__(self):
        """Initialize seasonal analyzer."""
        if not STL_AVAILABLE:
            logger.warning("statsmodels not available - seasonal features will be limited")
    
    def decompose_time_series(
        self,
        values: List[float],
        dates: List[datetime],
        period: Optional[int] = None
    ) -> Dict[str, List[float]]:
        """
        Decompose time series into trend, seasonal, and residual components.
        
        Args:
            values: List of numeric values
            dates: List of corresponding dates
            period: Seasonal period (e.g., 12 for monthly data with yearly seasonality)
                    If None, auto-detects from data frequency
        
        Returns:
            Dict with 'trend', 'seasonal', 'residual', 'observed' components
        """
        if not STL_AVAILABLE or len(values) < 24:  # Need at least 2 years for seasonality
            # Fallback: simple trend extraction
            return self._simple_trend_decomposition(values)
        
        try:
            # Create pandas Series with datetime index
            series = pd.Series(values, index=pd.to_datetime(dates))
            
            # Auto-detect period if not provided
            if period is None:
                period = self._detect_seasonal_period(series)
            
            # Use STL if we have enough data points (at least 2 periods)
            if len(values) >= period * 2:
                try:
                    stl = STL(series, seasonal=period, robust=True)
                    result = stl.fit()
                    
                    return {
                        'trend': result.trend.tolist(),
                        'seasonal': result.seasonal.tolist(),
                        'residual': result.resid.tolist(),
                        'observed': values,
                        'period': period
                    }
                except Exception as e:
                    logger.warning(f"STL decomposition failed: {e}, falling back to simple decomposition")
                    return self._simple_trend_decomposition(values)
            else:
                # Use classical decomposition for shorter series
                try:
                    result = seasonal_decompose(series, model='additive', period=period)
                    return {
                        'trend': result.trend.fillna(0).tolist(),
                        'seasonal': result.seasonal.fillna(0).tolist(),
                        'residual': result.resid.fillna(0).tolist(),
                        'observed': values,
                        'period': period
                    }
                except Exception as e:
                    logger.warning(f"Classical decomposition failed: {e}, falling back to simple decomposition")
                    return self._simple_trend_decomposition(values)
        
        except Exception as e:
            logger.error(f"Seasonal decomposition error: {e}")
            return self._simple_trend_decomposition(values)
    
    def calculate_seasonal_expected_value(
        self,
        values: List[float],
        dates: List[datetime],
        target_date: datetime,
        use_seasonality: bool = True
    ) -> Dict[str, float]:
        """
        Calculate expected value using trend + seasonality.
        
        Args:
            values: Historical values
            dates: Historical dates
            target_date: Date to forecast for
            use_seasonality: Whether to include seasonal component
        
        Returns:
            Dict with 'expected_value', 'trend_value', 'seasonal_component', 'confidence'
        """
        if len(values) < 3:
            # Not enough data - use simple mean
            mean_val = np.mean(values) if values else 0.0
            return {
                'expected_value': mean_val,
                'trend_value': mean_val,
                'seasonal_component': 0.0,
                'confidence': 0.3
            }
        
        # Decompose time series
        decomposition = self.decompose_time_series(values, dates)
        
        # Get trend component (use latest trend value or extrapolate)
        trend_values = decomposition.get('trend', [])
        if trend_values:
            # Use last non-null trend value, or extrapolate if needed
            valid_trends = [t for t in trend_values if not (np.isnan(t) if isinstance(t, float) else False)]
            if valid_trends:
                trend_value = valid_trends[-1]
            else:
                trend_value = np.mean(values)
        else:
            trend_value = np.mean(values)
        
        # Get seasonal component for target date
        seasonal_component = 0.0
        if use_seasonality and 'seasonal' in decomposition:
            seasonal_values = decomposition.get('seasonal', [])
            period = decomposition.get('period', 12)
            
            # Find seasonal component for target month/period
            if len(seasonal_values) >= period:
                # Use the seasonal pattern from the same position in the cycle
                target_month = target_date.month
                # Map to seasonal cycle position (0-11 for monthly, 0-3 for quarterly)
                cycle_position = (target_month - 1) % period
                
                # Average seasonal values at this position across all cycles
                seasonal_at_position = []
                for i in range(len(seasonal_values)):
                    if i % period == cycle_position:
                        val = seasonal_values[i]
                        if not (isinstance(val, float) and np.isnan(val)):
                            seasonal_at_position.append(val)
                
                if seasonal_at_position:
                    seasonal_component = np.mean(seasonal_at_position)
        
        expected_value = trend_value + seasonal_component
        
        # Calculate confidence based on data quality
        confidence = min(0.95, 0.5 + (len(values) / 60.0) * 0.45)  # Max confidence at 60 months
        
        return {
            'expected_value': float(expected_value),
            'trend_value': float(trend_value),
            'seasonal_component': float(seasonal_component),
            'confidence': confidence,
            'decomposition_method': 'stl' if STL_AVAILABLE and len(values) >= 24 else 'simple'
        }
    
    def _detect_seasonal_period(self, series: pd.Series) -> int:
        """
        Auto-detect seasonal period from time series frequency.
        
        Returns:
            Seasonal period (e.g., 12 for monthly, 4 for quarterly)
        """
        # Infer frequency from index
        if hasattr(series.index, 'freq') and series.index.freq:
            freq = series.index.freq
        else:
            # Try to infer from date differences
            if len(series) > 1:
                diff = (series.index[-1] - series.index[0]) / (len(series) - 1)
                days = diff.days
                
                if days <= 1:
                    return 7  # Daily -> weekly seasonality
                elif days <= 7:
                    return 4  # Weekly -> monthly seasonality
                elif days <= 31:
                    return 12  # Monthly -> yearly seasonality
                elif days <= 93:
                    return 4  # Quarterly -> yearly seasonality
                else:
                    return 1  # Annual or irregular
        
        # Map common frequencies to periods
        freq_str = str(freq).upper()
        if 'D' in freq_str or 'DAY' in freq_str:
            return 7  # Weekly seasonality for daily data
        elif 'W' in freq_str or 'WEEK' in freq_str:
            return 52  # Yearly seasonality for weekly data
        elif 'M' in freq_str or 'MONTH' in freq_str:
            return 12  # Yearly seasonality for monthly data
        elif 'Q' in freq_str or 'QUARTER' in freq_str:
            return 4  # Yearly seasonality for quarterly data
        else:
            return 12  # Default to monthly/yearly
    
    def _simple_trend_decomposition(self, values: List[float]) -> Dict[str, List[float]]:
        """
        Simple trend decomposition when STL is not available or insufficient data.
        
        Uses moving average for trend and difference for residual.
        """
        if len(values) < 3:
            return {
                'trend': values,
                'seasonal': [0.0] * len(values),
                'residual': [0.0] * len(values),
                'observed': values,
                'period': 1
            }
        
        # Simple moving average for trend (window = min(12, len/2))
        window = min(12, max(3, len(values) // 2))
        trend = pd.Series(values).rolling(window=window, center=True).mean().fillna(method='bfill').fillna(method='ffill').tolist()
        
        # Residual = observed - trend (no seasonality in simple version)
        residual = [v - t for v, t in zip(values, trend)]
        
        return {
            'trend': trend,
            'seasonal': [0.0] * len(values),
            'residual': residual,
            'observed': values,
            'period': 1
        }
    
    def get_seasonal_adjustment_factor(
        self,
        values: List[float],
        dates: List[datetime],
        target_month: int
    ) -> float:
        """
        Get seasonal adjustment factor for a specific month.
        
        Args:
            values: Historical values
            dates: Historical dates
            target_month: Month (1-12) to get adjustment for
        
        Returns:
            Multiplicative adjustment factor (1.0 = no adjustment)
        """
        if len(values) < 12:
            return 1.0  # No adjustment if insufficient data
        
        decomposition = self.decompose_time_series(values, dates)
        seasonal_values = decomposition.get('seasonal', [])
        
        if not seasonal_values:
            return 1.0
        
        # Extract seasonal values for target month across all years
        month_seasonal = []
        for i, date in enumerate(dates):
            if date.month == target_month and i < len(seasonal_values):
                val = seasonal_values[i]
                if not (isinstance(val, float) and np.isnan(val)):
                    month_seasonal.append(val)
        
        if month_seasonal:
            # Convert to multiplicative factor (assuming additive model)
            # Factor = 1 + (seasonal_component / mean_value)
            mean_value = np.mean(values)
            if mean_value != 0:
                avg_seasonal = np.mean(month_seasonal)
                factor = 1.0 + (avg_seasonal / mean_value)
                return float(factor)
        
        return 1.0

