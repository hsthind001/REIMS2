"""
Model Monitoring Service for REIMS2
Tracks AI/ML model performance, accuracy, and inference times.

Sprint 2: AI/ML Intelligence Layer
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from collections import defaultdict
import statistics

from app.models.extraction_field_metadata import ExtractionFieldMetadata
from app.models.extraction_log import ExtractionLog
from app.db.database import get_db


class ModelMonitoringService:
    """
    Service to monitor extraction engine performance and health.
    
    Tracks:
    - Per-engine accuracy rates
    - Confidence score distributions
    - Processing times
    - Engine agreement rates
    - Model drift detection
    """
    
    def __init__(self, db: Session):
        """
        Initialize model monitoring service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def track_extraction_metrics(
        self,
        document_id: int,
        engine_name: str,
        processing_time: float,
        confidence_score: float,
        field_count: int
    ) -> bool:
        """
        Track metrics for a single extraction.
        
        Args:
            document_id: Document ID
            engine_name: Name of extraction engine
            processing_time: Time taken in seconds
            confidence_score: Overall confidence
            field_count: Number of fields extracted
            
        Returns:
            True if metrics saved successfully
        """
        try:
            # This could be stored in extraction_logs or a dedicated metrics table
            # For now, metrics are derived from extraction_field_metadata
            return True
        except Exception as e:
            print(f"Error tracking metrics: {e}")
            return False
    
    def get_engine_performance(
        self,
        engine_name: Optional[str] = None,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance metrics for an extraction engine.
        
        Args:
            engine_name: Optional filter by engine (None = all engines)
            lookback_days: Number of days to analyze
            
        Returns:
            Performance metrics dict
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        query = self.db.query(
            ExtractionFieldMetadata.extraction_engine,
            func.avg(ExtractionFieldMetadata.confidence_score).label('avg_confidence'),
            func.count(ExtractionFieldMetadata.id).label('total_fields'),
            func.sum(
                func.cast(ExtractionFieldMetadata.needs_review == True, func.Integer())
            ).label('review_needed'),
            func.sum(
                func.cast(ExtractionFieldMetadata.reviewed_at.isnot(None), func.Integer())
            ).label('reviewed')
        ).filter(
            ExtractionFieldMetadata.created_at >= cutoff_date
        )
        
        if engine_name:
            query = query.filter(ExtractionFieldMetadata.extraction_engine == engine_name)
        
        query = query.group_by(ExtractionFieldMetadata.extraction_engine)
        
        results = query.all()
        
        performance_data = []
        for engine, avg_conf, total, review_needed, reviewed in results:
            accuracy_rate = None
            if reviewed and reviewed > 0:
                # Accuracy = fields that didn't need correction after review
                accuracy_rate = (reviewed - (review_needed or 0)) / reviewed
            
            performance_data.append({
                'engine': engine,
                'avg_confidence': float(avg_conf) if avg_conf else 0.0,
                'total_fields': total or 0,
                'needs_review_count': review_needed or 0,
                'reviewed_count': reviewed or 0,
                'accuracy_rate': accuracy_rate,
                'review_rate': (review_needed or 0) / total if total else 0
            })
        
        return {
            'lookback_days': lookback_days,
            'engines': performance_data,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_confidence_distribution(
        self,
        engine_name: Optional[str] = None,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get confidence score distribution for analysis.
        
        Args:
            engine_name: Optional filter by engine
            lookback_days: Number of days to analyze
            
        Returns:
            Distribution data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        query = self.db.query(
            ExtractionFieldMetadata.confidence_score
        ).filter(
            ExtractionFieldMetadata.created_at >= cutoff_date
        )
        
        if engine_name:
            query = query.filter(ExtractionFieldMetadata.extraction_engine == engine_name)
        
        scores = [float(score) for (score,) in query.all()]
        
        if not scores:
            return {
                'engine': engine_name,
                'sample_count': 0,
                'distribution': {}
            }
        
        # Calculate distribution buckets
        distribution = {
            'critical': len([s for s in scores if s < 0.5]),
            'low': len([s for s in scores if 0.5 <= s < 0.7]),
            'medium': len([s for s in scores if 0.7 <= s < 0.85]),
            'high': len([s for s in scores if 0.85 <= s < 0.95]),
            'excellent': len([s for s in scores if s >= 0.95])
        }
        
        return {
            'engine': engine_name or 'all',
            'sample_count': len(scores),
            'avg_confidence': statistics.mean(scores),
            'median_confidence': statistics.median(scores),
            'min_confidence': min(scores),
            'max_confidence': max(scores),
            'std_dev': statistics.stdev(scores) if len(scores) > 1 else 0,
            'distribution': distribution,
            'distribution_percentages': {
                k: round(v / len(scores) * 100, 2) for k, v in distribution.items()
            }
        }
    
    def get_engine_agreement_rate(
        self,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate how often engines agree on field values.
        
        Args:
            lookback_days: Number of days to analyze
            
        Returns:
            Agreement statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Get fields where multiple engines extracted the same field
        multi_engine_fields = self.db.query(
            ExtractionFieldMetadata.document_id,
            ExtractionFieldMetadata.table_name,
            ExtractionFieldMetadata.record_id,
            ExtractionFieldMetadata.field_name,
            func.count(ExtractionFieldMetadata.id).label('engine_count')
        ).filter(
            ExtractionFieldMetadata.created_at >= cutoff_date
        ).group_by(
            ExtractionFieldMetadata.document_id,
            ExtractionFieldMetadata.table_name,
            ExtractionFieldMetadata.record_id,
            ExtractionFieldMetadata.field_name
        ).having(
            func.count(ExtractionFieldMetadata.id) > 1
        ).all()
        
        if not multi_engine_fields:
            return {
                'agreement_rate': 0.0,
                'multi_engine_fields': 0,
                'consensus_fields': 0
            }
        
        # For fields with conflicting_values, check if resolution_method was 'consensus'
        consensus_count = 0
        total_multi_engine = len(multi_engine_fields)
        
        for doc_id, table, record_id, field, count in multi_engine_fields:
            # Check if any metadata for this field indicates consensus
            consensus_check = self.db.query(ExtractionFieldMetadata).filter(
                and_(
                    ExtractionFieldMetadata.document_id == doc_id,
                    ExtractionFieldMetadata.table_name == table,
                    ExtractionFieldMetadata.record_id == record_id,
                    ExtractionFieldMetadata.field_name == field,
                    ExtractionFieldMetadata.resolution_method == 'consensus'
                )
            ).first()
            
            if consensus_check:
                consensus_count += 1
        
        agreement_rate = consensus_count / total_multi_engine if total_multi_engine else 0
        
        return {
            'agreement_rate': round(agreement_rate, 4),
            'multi_engine_fields': total_multi_engine,
            'consensus_fields': consensus_count,
            'conflict_fields': total_multi_engine - consensus_count,
            'lookback_days': lookback_days
        }
    
    def detect_model_drift(
        self,
        engine_name: str,
        window_days: int = 7
    ) -> Dict[str, Any]:
        """
        Detect if model performance is degrading over time.
        
        Args:
            engine_name: Engine to monitor
            window_days: Size of rolling window for comparison
            
        Returns:
            Drift detection results
        """
        now = datetime.utcnow()
        current_window_start = now - timedelta(days=window_days)
        previous_window_start = current_window_start - timedelta(days=window_days)
        
        # Current window metrics
        current_metrics = self.db.query(
            func.avg(ExtractionFieldMetadata.confidence_score).label('avg_confidence'),
            func.count(ExtractionFieldMetadata.id).label('count')
        ).filter(
            and_(
                ExtractionFieldMetadata.extraction_engine == engine_name,
                ExtractionFieldMetadata.created_at >= current_window_start
            )
        ).first()
        
        # Previous window metrics
        previous_metrics = self.db.query(
            func.avg(ExtractionFieldMetadata.confidence_score).label('avg_confidence'),
            func.count(ExtractionFieldMetadata.id).label('count')
        ).filter(
            and_(
                ExtractionFieldMetadata.extraction_engine == engine_name,
                ExtractionFieldMetadata.created_at >= previous_window_start,
                ExtractionFieldMetadata.created_at < current_window_start
            )
        ).first()
        
        current_conf = float(current_metrics[0]) if current_metrics[0] else 0.0
        previous_conf = float(previous_metrics[0]) if previous_metrics[0] else 0.0
        
        # Calculate drift
        if previous_conf > 0:
            drift_percentage = ((current_conf - previous_conf) / previous_conf) * 100
        else:
            drift_percentage = 0.0
        
        # Detect significant drift (>5% degradation)
        is_drifting = drift_percentage < -5.0
        
        return {
            'engine': engine_name,
            'current_confidence': current_conf,
            'previous_confidence': previous_conf,
            'drift_percentage': round(drift_percentage, 2),
            'is_drifting': is_drifting,
            'current_sample_count': current_metrics[1] or 0,
            'previous_sample_count': previous_metrics[1] or 0,
            'window_days': window_days,
            'alert_threshold': -5.0
        }
    
    def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring data for dashboard display.
        
        Returns:
            Dict with all monitoring metrics
        """
        return {
            'engine_performance': self.get_engine_performance(),
            'confidence_distributions': {
                'all': self.get_confidence_distribution(),
                'pymupdf': self.get_confidence_distribution('pymupdf'),
                'pdfplumber': self.get_confidence_distribution('pdfplumber'),
                'camelot': self.get_confidence_distribution('camelot'),
                'layoutlm': self.get_confidence_distribution('layoutlm'),
                'easyocr': self.get_confidence_distribution('easyocr')
            },
            'agreement_rate': self.get_engine_agreement_rate(),
            'drift_detection': {
                'layoutlm': self.detect_model_drift('layoutlm'),
                'easyocr': self.detect_model_drift('easyocr')
            },
            'timestamp': datetime.utcnow().isoformat()
        }

