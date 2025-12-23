"""
Model Performance Monitoring Service

Tracks detection coverage, runtime, latency, alert volumes, and false-positive ratios.
"""

from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
import logging
import time
from contextlib import contextmanager
from functools import wraps
from collections import defaultdict
import threading

from app.models.anomaly_detection import AnomalyDetection
from app.models.anomaly_feedback import AnomalyFeedback
from app.models.committee_alert import CommitteeAlert, AlertSeverity
from app.models.model_performance_metrics import ModelPerformanceMetrics

logger = logging.getLogger(__name__)

# Thread-safe timing data storage
_timing_data = defaultdict(list)
_timing_lock = threading.Lock()


class ModelMonitoringService:
    """
    Monitors model performance metrics.
    
    Tracks:
    - Detection coverage (% of accounts/periods scanned)
    - Model runtime per batch
    - Queue latency
    - Alert volumes by severity
    - False-positive ratios over time
    """
    
    def __init__(self, db: Session):
        """Initialize monitoring service."""
        self.db = db
    
    def calculate_performance_metrics(
        self,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate all performance metrics.
        
        Args:
            lookback_days: Days to look back
            
        Returns:
            Dict with all performance metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # 1. Detection coverage
        coverage = self._calculate_coverage(cutoff_date)
        
        # 2. Alert volumes by severity
        alert_volumes = self._calculate_alert_volumes(cutoff_date)
        
        # 3. False positive ratio
        fpr = self._calculate_false_positive_ratio(cutoff_date)
        
        # 4. Model runtime (would need actual runtime data - placeholder)
        runtime_metrics = self._estimate_runtime_metrics(cutoff_date)
        
        return {
            'detection_coverage': coverage,
            'alert_volumes': alert_volumes,
            'false_positive_ratio': fpr,
            'runtime_metrics': runtime_metrics,
            'lookback_days': lookback_days,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _calculate_coverage(self, cutoff_date: datetime) -> Dict[str, float]:
        """Calculate detection coverage."""
        # Get total accounts
        from app.models.chart_of_accounts import ChartOfAccounts
        total_accounts = self.db.query(func.count(ChartOfAccounts.id)).scalar()
        
        # Get accounts with detections
        accounts_with_detections = self.db.query(
            func.count(func.distinct(AnomalyDetection.field_name))
        ).filter(
            AnomalyDetection.detected_at >= cutoff_date
        ).scalar()
        
        # Get total periods
        from app.models.financial_period import FinancialPeriod
        total_periods = self.db.query(func.count(FinancialPeriod.id)).scalar()
        
        # Get periods with detections
        periods_with_detections = self.db.query(
            func.count(func.distinct(AnomalyDetection.document_id))
        ).join(
            'document'
        ).filter(
            AnomalyDetection.detected_at >= cutoff_date
        ).scalar()
        
        account_coverage = (accounts_with_detections / total_accounts * 100) if total_accounts > 0 else 0.0
        period_coverage = (periods_with_detections / total_periods * 100) if total_periods > 0 else 0.0
        
        return {
            'account_coverage_percentage': round(account_coverage, 2),
            'period_coverage_percentage': round(period_coverage, 2),
            'accounts_scanned': accounts_with_detections,
            'total_accounts': total_accounts,
            'periods_scanned': periods_with_detections,
            'total_periods': total_periods
        }
    
    def _calculate_alert_volumes(self, cutoff_date: datetime) -> Dict[str, int]:
        """Calculate alert volumes by severity."""
        alerts = self.db.query(CommitteeAlert).filter(
            CommitteeAlert.created_at >= cutoff_date
        ).all()
        
        volumes = {
            'urgent': 0,
            'critical': 0,
            'warning': 0,
            'info': 0,
            'total': len(alerts)
        }
        
        for alert in alerts:
            severity_str = alert.severity.value.lower() if hasattr(alert.severity, 'value') else str(alert.severity).lower()
            if severity_str in volumes:
                volumes[severity_str] += 1
        
        return volumes
    
    def _calculate_false_positive_ratio(
        self,
        cutoff_date: datetime
    ) -> Dict[str, float]:
        """Calculate false positive ratio over time."""
        feedback = self.db.query(AnomalyFeedback).filter(
            AnomalyFeedback.created_at >= cutoff_date
        ).all()
        
        if len(feedback) == 0:
            return {
                'false_positive_rate': 0.0,
                'sample_size': 0
            }
        
        false_positives = sum(
            1 for fb in feedback
            if fb.feedback_type == 'dismissed' or (not fb.is_anomaly and fb.feedback_type != 'confirmed')
        )
        
        fpr = false_positives / len(feedback)
        
        return {
            'false_positive_rate': round(fpr, 4),
            'false_positives': false_positives,
            'total_feedback': len(feedback),
            'sample_size': len(feedback)
        }
    
    def _estimate_runtime_metrics(
        self,
        cutoff_date: datetime
    ) -> Dict[str, Any]:
        """
        Calculate actual runtime metrics from collected timing data.
        
        Queries stored timing data from model_performance_metrics table
        and calculates averages for the lookback period.
        """
        try:
            # Query stored runtime metrics from database
            stored_metrics = self.db.query(ModelPerformanceMetrics).filter(
                ModelPerformanceMetrics.recorded_at >= cutoff_date,
                ModelPerformanceMetrics.runtime_per_batch_ms.isnot(None)
            ).all()
            
            if not stored_metrics:
                # Fallback: try to get from in-memory timing data
                with _timing_lock:
                    if _timing_data.get('batch_runtimes'):
                        runtimes = _timing_data['batch_runtimes']
                        latencies = _timing_data.get('queue_latencies', [])
                        
                        if runtimes:
                            avg_runtime = sum(runtimes) / len(runtimes)
                            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
                            
                            return {
                                'avg_runtime_per_batch_seconds': avg_runtime,
                                'queue_latency_seconds': avg_latency,
                                'batches_processed': len(runtimes)
                            }
                
                # No data available - return zeros instead of placeholders
                logger.warning("No runtime metrics available - returning zeros")
                return {
                    'avg_runtime_per_batch_seconds': 0.0,
                    'queue_latency_seconds': 0.0,
                    'batches_processed': 0
                }
            
            # Calculate averages from stored metrics
            runtimes = [m.runtime_per_batch_ms / 1000.0 for m in stored_metrics if m.runtime_per_batch_ms is not None]
            latencies = [m.queue_latency_ms / 1000.0 for m in stored_metrics if m.queue_latency_ms is not None]
            
            avg_runtime = sum(runtimes) / len(runtimes) if runtimes else 0.0
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            
            return {
                'avg_runtime_per_batch_seconds': round(avg_runtime, 2),
                'queue_latency_seconds': round(avg_latency, 2),
                'batches_processed': len(stored_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error calculating runtime metrics: {e}", exc_info=True)
            return {
                'avg_runtime_per_batch_seconds': 0.0,
                'queue_latency_seconds': 0.0,
                'batches_processed': 0
            }
    
    def store_metrics(
        self,
        metrics: Dict[str, Any],
        model_name: str = "anomaly_detection_ensemble",
        model_type: str = "anomaly_detection",
        detector_method: Optional[str] = None,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None,
        batch_id: Optional[str] = None
    ) -> bool:
        """
        Store metrics in model_performance_metrics table.
        
        Args:
            metrics: Dictionary containing performance metrics
            model_name: Name of the model (e.g., "isolation_forest", "autoencoder")
            model_type: Type of model (e.g., "anomaly_detection", "extraction")
            detector_method: Specific detector method used
            property_id: Optional property ID for property-specific metrics
            period_id: Optional period ID for period-specific metrics
            batch_id: Optional batch identifier
            
        Returns:
            True if metrics were stored successfully
        """
        try:
            # Extract metrics from the dictionary
            coverage = metrics.get('detection_coverage', {})
            alert_volumes = metrics.get('alert_volumes', {})
            fpr = metrics.get('false_positive_ratio', {})
            runtime_metrics = metrics.get('runtime_metrics', {})
            
            # Calculate overall detection coverage
            detection_coverage = None
            if coverage:
                account_coverage = coverage.get('account_coverage_percentage', 0)
                period_coverage = coverage.get('period_coverage_percentage', 0)
                # Average of account and period coverage
                detection_coverage = (account_coverage + period_coverage) / 2.0 if (account_coverage or period_coverage) else None
            
            # Extract runtime metrics
            runtime_per_batch_ms = None
            if runtime_metrics:
                runtime_seconds = runtime_metrics.get('avg_runtime_per_batch_seconds')
                if runtime_seconds:
                    runtime_per_batch_ms = runtime_seconds * 1000.0
            
            queue_latency_ms = None
            if runtime_metrics:
                latency_seconds = runtime_metrics.get('queue_latency_seconds')
                if latency_seconds:
                    queue_latency_ms = latency_seconds * 1000.0
            
            # Extract alert volumes
            alert_volume_total = alert_volumes.get('total', 0)
            alert_volume_critical = alert_volumes.get('critical', 0)
            alert_volume_high = alert_volumes.get('urgent', 0)  # Map urgent to high
            alert_volume_medium = alert_volumes.get('warning', 0)
            alert_volume_low = alert_volumes.get('info', 0)
            
            # Extract false positive rate
            false_positive_rate = fpr.get('false_positive_rate') if fpr else None
            
            # Store additional metrics in JSONB
            additional_metrics = {
                'coverage_details': coverage,
                'fpr_details': fpr,
                'runtime_details': runtime_metrics,
                'lookback_days': metrics.get('lookback_days'),
                'timestamp': metrics.get('timestamp')
            }
            
            # Create and store the metrics record
            metrics_record = ModelPerformanceMetrics(
                model_name=model_name,
                model_type=model_type,
                detector_method=detector_method,
                detection_coverage=detection_coverage,
                runtime_per_batch_ms=runtime_per_batch_ms,
                queue_latency_ms=queue_latency_ms,
                alert_volume_total=alert_volume_total,
                alert_volume_critical=alert_volume_critical,
                alert_volume_high=alert_volume_high,
                alert_volume_medium=alert_volume_medium,
                alert_volume_low=alert_volume_low,
                false_positive_rate=false_positive_rate,
                additional_metrics=additional_metrics,
                property_id=property_id,
                period_id=period_id,
                batch_id=batch_id
            )
            
            self.db.add(metrics_record)
            self.db.commit()
            self.db.refresh(metrics_record)
            
            logger.info(f"Stored model performance metrics: {metrics_record.id} for model {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store model performance metrics: {str(e)}", exc_info=True)
            self.db.rollback()
            return False


# Timing utilities for collecting actual runtime data

@contextmanager
def time_batch_processing(batch_id: Optional[str] = None):
    """
    Context manager to time batch processing operations.
    
    Usage:
        with time_batch_processing(batch_id="batch_123"):
            # Your batch processing code
            process_batch()
    
    The timing data is automatically stored for later retrieval.
    """
    start_time = time.time()
    queue_start = time.time()  # Assume queue latency is time until processing starts
    
    try:
        yield
    finally:
        end_time = time.time()
        runtime = end_time - start_time
        
        # Store timing data (thread-safe)
        with _timing_lock:
            _timing_data['batch_runtimes'].append(runtime)
            # Keep only last 1000 entries to prevent memory issues
            if len(_timing_data['batch_runtimes']) > 1000:
                _timing_data['batch_runtimes'] = _timing_data['batch_runtimes'][-1000:]
            
            if batch_id:
                _timing_data['batch_ids'].append(batch_id)
        
        logger.debug(f"Batch processing completed in {runtime:.2f} seconds (batch_id: {batch_id})")


def track_queue_latency(latency_seconds: float):
    """
    Track queue latency for a batch.
    
    Args:
        latency_seconds: Time spent in queue before processing started
    """
    with _timing_lock:
        _timing_data['queue_latencies'].append(latency_seconds)
        # Keep only last 1000 entries
        if len(_timing_data['queue_latencies']) > 1000:
            _timing_data['queue_latencies'] = _timing_data['queue_latencies'][-1000:]


def timing_decorator(func):
    """
    Decorator to automatically time function execution.
    
    Usage:
        @timing_decorator
        def process_batch():
            # Your code
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            runtime = time.time() - start_time
            with _timing_lock:
                _timing_data['batch_runtimes'].append(runtime)
                if len(_timing_data['batch_runtimes']) > 1000:
                    _timing_data['batch_runtimes'] = _timing_data['batch_runtimes'][-1000:]
            logger.debug(f"Function {func.__name__} executed in {runtime:.2f} seconds")
    return wrapper


def get_recent_timing_stats(lookback_seconds: int = 3600) -> Dict[str, Any]:
    """
    Get recent timing statistics from in-memory data.
    
    Args:
        lookback_seconds: How far back to look (default: 1 hour)
        
    Returns:
        Dictionary with timing statistics
    """
    with _timing_lock:
        runtimes = _timing_data.get('batch_runtimes', [])
        latencies = _timing_data.get('queue_latencies', [])
        
        if not runtimes:
            return {
                'avg_runtime_per_batch_seconds': 0.0,
                'queue_latency_seconds': 0.0,
                'batches_processed': 0
            }
        
        avg_runtime = sum(runtimes) / len(runtimes) if runtimes else 0.0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        
        return {
            'avg_runtime_per_batch_seconds': round(avg_runtime, 2),
            'queue_latency_seconds': round(avg_latency, 2),
            'batches_processed': len(runtimes),
            'min_runtime': round(min(runtimes), 2) if runtimes else 0.0,
            'max_runtime': round(max(runtimes), 2) if runtimes else 0.0
        }
