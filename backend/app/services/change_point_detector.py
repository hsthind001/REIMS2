"""
Change Point Detection Service

Detects structural breaks in time series using PELT (Pruned Exact Linear Time) algorithm.
Handles regime changes (e.g., property renovation, market shifts).
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

try:
    import ruptures as rpt
    RUPTURES_AVAILABLE = True
except ImportError:
    RUPTURES_AVAILABLE = False
    logger.warning("ruptures not available - change point detection disabled")


class ChangePointDetector:
    """
    Detects change points in time series data.
    
    Uses PELT algorithm to identify structural breaks where the statistical
    properties of the time series change significantly.
    """
    
    def __init__(self):
        """Initialize change point detector."""
        if not RUPTURES_AVAILABLE:
            logger.warning("Change point detection will be limited without ruptures")
    
    def detect_change_points(
        self,
        values: List[float],
        dates: Optional[List[datetime]] = None,
        min_size: int = 2,
        penalty: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect change points in time series.
        
        Args:
            values: Time series values (chronological order)
            dates: Optional corresponding dates
            min_size: Minimum segment size between change points
            penalty: Penalty parameter (auto-selected if None)
        
        Returns:
            Dict with change points and segment information
        """
        if len(values) < min_size * 2:
            return {
                'change_points': [],
                'segments': [],
                'has_changes': False
            }
        
        if not RUPTURES_AVAILABLE:
            # Fallback: simple variance-based detection
            return self._simple_change_detection(values, dates)
        
        try:
            # Convert to numpy array
            signal = np.array(values).reshape(-1, 1)
            
            # Auto-select penalty if not provided
            if penalty is None:
                # Use BIC (Bayesian Information Criterion) for penalty selection
                penalty = self._select_penalty(signal, min_size)
            
            # Detect change points using PELT
            algo = rpt.Pelt(model="rbf").fit(signal)
            change_indices = algo.predict(pen=penalty)
            
            # Remove last index (end of series)
            if change_indices and change_indices[-1] == len(values):
                change_indices = change_indices[:-1]
            
            # Build segments
            segments = []
            start_idx = 0
            
            for cp_idx in change_indices:
                segment_values = values[start_idx:cp_idx]
                segment_dates = dates[start_idx:cp_idx] if dates else None
                
                segments.append({
                    'start_index': start_idx,
                    'end_index': cp_idx - 1,
                    'start_date': segment_dates[0] if segment_dates else None,
                    'end_date': segment_dates[-1] if segment_dates else None,
                    'values': segment_values,
                    'mean': float(np.mean(segment_values)),
                    'std': float(np.std(segment_values)) if len(segment_values) > 1 else 0.0,
                    'length': len(segment_values)
                })
                
                start_idx = cp_idx
            
            # Add final segment
            if start_idx < len(values):
                segment_values = values[start_idx:]
                segment_dates = dates[start_idx:] if dates else None
                segments.append({
                    'start_index': start_idx,
                    'end_index': len(values) - 1,
                    'start_date': segment_dates[0] if segment_dates else None,
                    'end_date': segment_dates[-1] if segment_dates else None,
                    'values': segment_values,
                    'mean': float(np.mean(segment_values)),
                    'std': float(np.std(segment_values)) if len(segment_values) > 1 else 0.0,
                    'length': len(segment_values)
                })
            
            # Convert indices to dates if available
            change_points = []
            for cp_idx in change_indices:
                change_point = {
                    'index': cp_idx,
                    'date': dates[cp_idx] if dates and cp_idx < len(dates) else None,
                    'value': values[cp_idx] if cp_idx < len(values) else None
                }
                change_points.append(change_point)
            
            return {
                'change_points': change_points,
                'segments': segments,
                'has_changes': len(change_points) > 0,
                'penalty_used': penalty,
                'method': 'pelt'
            }
        
        except Exception as e:
            logger.error(f"Change point detection error: {e}")
            return self._simple_change_detection(values, dates)
    
    def get_baseline_for_period(
        self,
        values: List[float],
        dates: List[datetime],
        target_date: datetime,
        lookback_months: int = 12
    ) -> Dict[str, Any]:
        """
        Get appropriate baseline for a target period, accounting for change points.
        
        If a change point occurred recently, uses post-change-point data.
        Otherwise, uses standard lookback period.
        
        Args:
            values: Historical values
            dates: Historical dates
            target_date: Date to get baseline for
            lookback_months: Standard lookback if no change points
        
        Returns:
            Dict with baseline statistics and change point info
        """
        # Detect change points
        change_result = self.detect_change_points(values, dates)
        
        if not change_result.get('has_changes'):
            # No change points - use standard lookback
            cutoff_date = target_date - pd.DateOffset(months=lookback_months)
            recent_values = [
                v for v, d in zip(values, dates)
                if d >= cutoff_date
            ]
            
            return {
                'baseline_mean': float(np.mean(recent_values)) if recent_values else 0.0,
                'baseline_std': float(np.std(recent_values)) if len(recent_values) > 1 else 0.0,
                'baseline_count': len(recent_values),
                'has_change_point': False,
                'change_point_date': None
            }
        
        # Find most recent change point before target date
        change_points = change_result.get('change_points', [])
        relevant_cp = None
        
        for cp in change_points:
            cp_date = cp.get('date')
            if cp_date and cp_date < target_date:
                if relevant_cp is None or cp_date > relevant_cp.get('date'):
                    relevant_cp = cp
        
        if relevant_cp:
            # Use data after change point
            cp_date = relevant_cp['date']
            post_cp_values = [
                v for v, d in zip(values, dates)
                if d >= cp_date and d < target_date
            ]
            
            return {
                'baseline_mean': float(np.mean(post_cp_values)) if post_cp_values else 0.0,
                'baseline_std': float(np.std(post_cp_values)) if len(post_cp_values) > 1 else 0.0,
                'baseline_count': len(post_cp_values),
                'has_change_point': True,
                'change_point_date': cp_date.isoformat() if cp_date else None,
                'change_point_index': relevant_cp.get('index')
            }
        else:
            # No relevant change point - use standard lookback
            cutoff_date = target_date - pd.DateOffset(months=lookback_months)
            recent_values = [
                v for v, d in zip(values, dates)
                if d >= cutoff_date
            ]
            
            return {
                'baseline_mean': float(np.mean(recent_values)) if recent_values else 0.0,
                'baseline_std': float(np.std(recent_values)) if len(recent_values) > 1 else 0.0,
                'baseline_count': len(recent_values),
                'has_change_point': False,
                'change_point_date': None
            }
    
    def _select_penalty(self, signal: np.ndarray, min_size: int) -> float:
        """
        Auto-select penalty parameter using BIC.
        
        Tries multiple penalty values and selects based on BIC score.
        """
        try:
            # Try a range of penalty values
            penalties = [1, 2, 5, 10, 20, 50]
            best_penalty = penalties[0]
            best_bic = float('inf')
            
            for pen in penalties:
                try:
                    algo = rpt.Pelt(model="rbf", min_size=min_size).fit(signal)
                    change_indices = algo.predict(pen=pen)
                    
                    # Calculate BIC (simplified)
                    n = len(signal)
                    k = len(change_indices) - 1  # Number of change points
                    
                    # Calculate likelihood (simplified)
                    segments = []
                    start = 0
                    for cp in change_indices:
                        if cp < n:
                            segments.append(signal[start:cp])
                            start = cp
                    
                    # Calculate BIC
                    log_likelihood = sum(
                        -len(seg) * np.log(np.std(seg) + 1e-10)
                        for seg in segments if len(seg) > 0
                    )
                    bic = -2 * log_likelihood + k * np.log(n)
                    
                    if bic < best_bic:
                        best_bic = bic
                        best_penalty = pen
                except Exception:
                    continue
            
            return float(best_penalty)
        except Exception:
            # Default penalty
            return 10.0
    
    def _simple_change_detection(
        self,
        values: List[float],
        dates: Optional[List[datetime]]
    ) -> Dict[str, Any]:
        """
        Simple variance-based change detection (fallback when ruptures unavailable).
        
        Detects significant changes in mean and variance.
        """
        if len(values) < 6:
            return {
                'change_points': [],
                'segments': [],
                'has_changes': False,
                'method': 'simple'
            }
        
        change_points = []
        segments = []
        
        # Use rolling window to detect variance changes
        window_size = max(3, len(values) // 4)
        variances = []
        
        for i in range(window_size, len(values)):
            window = values[i - window_size:i]
            variances.append(np.var(window))
        
        if variances:
            mean_var = np.mean(variances)
            std_var = np.std(variances) if len(variances) > 1 else 0
            
            # Detect significant variance changes
            for i, var in enumerate(variances):
                if std_var > 0 and abs(var - mean_var) > 2 * std_var:
                    cp_idx = i + window_size
                    if cp_idx < len(values) and cp_idx not in [cp['index'] for cp in change_points]:
                        change_points.append({
                            'index': cp_idx,
                            'date': dates[cp_idx] if dates and cp_idx < len(dates) else None,
                            'value': values[cp_idx] if cp_idx < len(values) else None
                        })
        
        # Build segments
        if change_points:
            start_idx = 0
            for cp in change_points:
                cp_idx = cp['index']
                segment_values = values[start_idx:cp_idx]
                segment_dates = dates[start_idx:cp_idx] if dates else None
                
                segments.append({
                    'start_index': start_idx,
                    'end_index': cp_idx - 1,
                    'start_date': segment_dates[0] if segment_dates else None,
                    'end_date': segment_dates[-1] if segment_dates else None,
                    'values': segment_values,
                    'mean': float(np.mean(segment_values)),
                    'std': float(np.std(segment_values)) if len(segment_values) > 1 else 0.0,
                    'length': len(segment_values)
                })
                
                start_idx = cp_idx
        
        return {
            'change_points': change_points,
            'segments': segments,
            'has_changes': len(change_points) > 0,
            'method': 'simple'
        }

