"""
Anomaly Feature Engineering Service

Creates rich, multi-dimensional features for ML-based anomaly detection.
Transforms raw financial data into features that help ML models detect anomalies.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class AnomalyFeatureEngineer:
    """
    Engineers features for ML-based anomaly detection.
    
    Creates:
    - Temporal features (month, quarter, year-over-year)
    - Statistical features (rolling averages, volatility, momentum)
    - Cross-account relationships
    - Derived metrics
    """
    
    def __init__(self):
        """Initialize feature engineer."""
        pass
    
    def engineer_features(
        self,
        account_code: str,
        values: List[float],
        dates: List[datetime],
        property_type: Optional[str] = None,
        account_category: Optional[str] = None,
        related_accounts: Optional[Dict[str, List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Engineer comprehensive feature set for anomaly detection.
        
        Args:
            account_code: Account code (e.g., "4010-0000")
            values: Historical values (chronological order)
            dates: Corresponding dates
            property_type: Type of property (optional)
            account_category: Account category (revenue, expense, etc.)
            related_accounts: Dict of related account codes -> values
        
        Returns:
            Dict with engineered features
        """
        if len(values) != len(dates) or len(values) < 1:
            return {}
        
        features = {}
        
        # Basic features
        features.update(self._temporal_features(dates))
        features.update(self._statistical_features(values))
        features.update(self._trend_features(values, dates))
        
        # Account-specific features
        features['account_code_numeric'] = self._account_code_to_numeric(account_code)
        features['account_category_encoded'] = self._encode_category(account_category)
        
        # Property type encoding
        features['property_type_encoded'] = self._encode_property_type(property_type)
        
        # Cross-account features
        if related_accounts:
            features.update(self._cross_account_features(values, related_accounts))
        
        # Volatility and momentum
        features.update(self._volatility_features(values))
        features.update(self._momentum_features(values))
        
        return features
    
    def _temporal_features(self, dates: List[datetime]) -> Dict[str, Any]:
        """Extract temporal features from dates."""
        if not dates:
            return {}
        
        latest_date = dates[-1]
        
        return {
            'month': latest_date.month,
            'quarter': (latest_date.month - 1) // 3 + 1,
            'day_of_month': latest_date.day,
            'is_year_end': 1 if latest_date.month == 12 else 0,
            'is_quarter_end': 1 if latest_date.month in [3, 6, 9, 12] else 0,
            'days_since_start': (latest_date - dates[0]).days if len(dates) > 1 else 0,
            'months_since_start': (latest_date.year - dates[0].year) * 12 + (latest_date.month - dates[0].month) if len(dates) > 1 else 0
        }
    
    def _statistical_features(self, values: List[float]) -> Dict[str, Any]:
        """Calculate statistical features."""
        if not values:
            return {}
        
        values_array = np.array(values)
        
        features = {
            'mean': float(np.mean(values_array)),
            'median': float(np.median(values_array)),
            'std': float(np.std(values_array)) if len(values) > 1 else 0.0,
            'min': float(np.min(values_array)),
            'max': float(np.max(values_array)),
            'range': float(np.max(values_array) - np.min(values_array)),
            'coefficient_of_variation': float(np.std(values_array) / np.mean(values_array)) if np.mean(values_array) != 0 else 0.0
        }
        
        # Percentiles
        if len(values) >= 4:
            features['p25'] = float(np.percentile(values_array, 25))
            features['p75'] = float(np.percentile(values_array, 75))
            features['iqr'] = features['p75'] - features['p25']
        
        # Skewness and kurtosis (if scipy available)
        try:
            from scipy import stats
            if len(values) >= 3:
                features['skewness'] = float(stats.skew(values_array))
                features['kurtosis'] = float(stats.kurtosis(values_array))
        except ImportError:
            pass
        
        return features
    
    def _trend_features(self, values: List[float], dates: List[datetime]) -> Dict[str, Any]:
        """Extract trend-related features."""
        if len(values) < 2:
            return {}
        
        features = {}
        
        # Simple linear trend (slope)
        if len(values) >= 2:
            x = np.arange(len(values))
            slope, intercept = np.polyfit(x, values, 1)
            features['trend_slope'] = float(slope)
            features['trend_direction'] = 1 if slope > 0 else -1 if slope < 0 else 0
        
        # Year-over-year change (if we have 12+ months)
        if len(values) >= 12 and len(dates) >= 12:
            current_value = values[-1]
            year_ago_value = values[-12] if len(values) >= 12 else values[0]
            if year_ago_value != 0:
                yoy_change = (current_value - year_ago_value) / year_ago_value
                features['yoy_change'] = float(yoy_change)
                features['yoy_change_pct'] = float(yoy_change * 100)
        
        # Recent vs historical average
        if len(values) >= 6:
            recent_avg = np.mean(values[-3:])  # Last 3 periods
            historical_avg = np.mean(values[:-3])  # All but last 3
            if historical_avg != 0:
                features['recent_vs_historical'] = float((recent_avg - historical_avg) / historical_avg)
        
        return features
    
    def _volatility_features(self, values: List[float]) -> Dict[str, Any]:
        """Calculate volatility-related features."""
        if len(values) < 3:
            return {}
        
        features = {}
        values_array = np.array(values)
        
        # Rolling volatility (standard deviation of recent periods)
        if len(values) >= 6:
            recent_std = np.std(values_array[-6:])
            historical_std = np.std(values_array[:-6]) if len(values) > 6 else recent_std
            features['recent_volatility'] = float(recent_std)
            features['volatility_ratio'] = float(recent_std / historical_std) if historical_std > 0 else 1.0
        
        # Volatility spike detection
        if len(values) >= 12:
            rolling_std = []
            window = 6
            for i in range(window, len(values)):
                rolling_std.append(np.std(values_array[i-window:i]))
            
            if rolling_std:
                current_volatility = rolling_std[-1]
                avg_volatility = np.mean(rolling_std[:-1]) if len(rolling_std) > 1 else current_volatility
                features['volatility_spike'] = float(current_volatility / avg_volatility) if avg_volatility > 0 else 1.0
        
        return features
    
    def _momentum_features(self, values: List[float]) -> Dict[str, Any]:
        """Calculate momentum features."""
        if len(values) < 3:
            return {}
        
        features = {}
        values_array = np.array(values)
        
        # Rate of change
        if len(values) >= 2:
            roc_1 = (values_array[-1] - values_array[-2]) / values_array[-2] if values_array[-2] != 0 else 0
            features['rate_of_change_1'] = float(roc_1)
        
        if len(values) >= 3:
            roc_3 = (values_array[-1] - values_array[-3]) / values_array[-3] if values_array[-3] != 0 else 0
            features['rate_of_change_3'] = float(roc_3)
        
        # Momentum (difference between recent and older periods)
        if len(values) >= 6:
            recent_avg = np.mean(values_array[-3:])
            older_avg = np.mean(values_array[-6:-3])
            features['momentum'] = float(recent_avg - older_avg)
            features['momentum_pct'] = float((recent_avg - older_avg) / older_avg) if older_avg != 0 else 0.0
        
        return features
    
    def _cross_account_features(
        self,
        values: List[float],
        related_accounts: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """Calculate features based on related accounts."""
        features = {}
        
        if not related_accounts:
            return features
        
        current_value = values[-1] if values else 0
        
        for account_code, related_values in related_accounts.items():
            if not related_values or len(related_values) != len(values):
                continue
            
            related_current = related_values[-1] if related_values else 0
            
            # Ratio features
            if related_current != 0:
                ratio = current_value / related_current
                features[f'ratio_{account_code}'] = float(ratio)
            
            # Correlation
            if len(values) >= 6 and len(related_values) >= 6:
                correlation = np.corrcoef(values[-12:], related_values[-12:])[0, 1] if len(values) >= 12 else np.corrcoef(values, related_values)[0, 1]
                features[f'correlation_{account_code}'] = float(correlation) if not np.isnan(correlation) else 0.0
            
            # Change alignment (do they move together?)
            if len(values) >= 2 and len(related_values) >= 2:
                current_change = (values[-1] - values[-2]) / values[-2] if values[-2] != 0 else 0
                related_change = (related_values[-1] - related_values[-2]) / related_values[-2] if related_values[-2] != 0 else 0
                
                # Same direction = 1, opposite = -1, neutral = 0
                if current_change != 0 and related_change != 0:
                    alignment = 1 if (current_change > 0) == (related_change > 0) else -1
                    features[f'alignment_{account_code}'] = alignment
        
        return features
    
    def _account_code_to_numeric(self, account_code: str) -> int:
        """Convert account code to numeric feature."""
        if not account_code:
            return 0
        
        # Extract numeric part (e.g., "4010-0000" -> 4010)
        try:
            parts = account_code.split('-')
            if parts:
                return int(parts[0])
        except (ValueError, AttributeError):
            pass
        
        return 0
    
    def _encode_category(self, category: Optional[str]) -> int:
        """Encode account category as integer."""
        category_map = {
            'revenue': 1,
            'expense': 2,
            'asset': 3,
            'liability': 4,
            'equity': 5,
            'income': 1,
            'operating_expense': 2
        }
        
        if not category:
            return 0
        
        category_lower = category.lower()
        for key, value in category_map.items():
            if key in category_lower:
                return value
        
        return 0
    
    def _encode_property_type(self, property_type: Optional[str]) -> int:
        """Encode property type as integer."""
        type_map = {
            'retail': 1,
            'office': 2,
            'industrial': 3,
            'multifamily': 4,
            'mixed_use': 5
        }
        
        if not property_type:
            return 0
        
        property_lower = property_type.lower().replace(' ', '_')
        return type_map.get(property_lower, 0)
    
    def create_feature_matrix(
        self,
        accounts_data: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Create feature matrix for ML models.
        
        Args:
            accounts_data: List of dicts, each containing account features from engineer_features()
        
        Returns:
            (feature_matrix, feature_names) tuple
        """
        if not accounts_data:
            return np.array([]), []
        
        # Collect all feature names
        all_feature_names = set()
        for account_data in accounts_data:
            if 'features' in account_data:
                all_feature_names.update(account_data['features'].keys())
        
        feature_names = sorted(list(all_feature_names))
        
        # Build matrix
        feature_matrix = []
        for account_data in accounts_data:
            features = account_data.get('features', {})
            row = [features.get(name, 0.0) for name in feature_names]
            feature_matrix.append(row)
        
        return np.array(feature_matrix), feature_names

