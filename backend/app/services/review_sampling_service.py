"""
Review Sampling Service

Randomly samples 1-2% of high-confidence extractions for audit.
Detects systemic drift in extraction quality.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import random
import numpy as np
import logging

from app.models.document_upload import DocumentUpload
from app.models.extraction_field_metadata import ExtractionFieldMetadata

logger = logging.getLogger(__name__)


class ReviewSamplingService:
    """
    Sampling-based QA service.
    
    Features:
    - Random sampling (1-2% of high-confidence extractions)
    - Systemic drift detection
    - Alert generation for quality degradation
    """
    
    def __init__(self, db: Session):
        """Initialize sampling service."""
        self.db = db
        self.sampling_rate = 0.015  # 1.5% default
        self.confidence_threshold = 0.95  # High confidence threshold
        self.drift_threshold = 0.10  # 10% degradation threshold
    
    def sample_for_audit(
        self,
        document_ids: Optional[List[int]] = None,
        sample_rate: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Randomly sample high-confidence extractions for audit.
        
        Args:
            document_ids: Optional list of document IDs to sample from
            sample_rate: Optional custom sampling rate (default: 1.5%)
            
        Returns:
            List of sampled items for audit
        """
        rate = sample_rate or self.sampling_rate
        
        # Get high-confidence extractions
        query = self.db.query(ExtractionFieldMetadata).filter(
            ExtractionFieldMetadata.extraction_confidence >= self.confidence_threshold
        )
        
        if document_ids:
            query = query.filter(ExtractionFieldMetadata.document_id.in_(document_ids))
        
        all_extractions = query.all()
        
        if not all_extractions:
            return []
        
        # Random sampling
        sample_size = max(1, int(len(all_extractions) * rate))
        sampled = random.sample(all_extractions, min(sample_size, len(all_extractions)))
        
        # Format results
        results = []
        for item in sampled:
            results.append({
                'extraction_id': item.id,
                'document_id': item.document_id,
                'field_name': item.field_name,
                'extraction_confidence': float(item.extraction_confidence) if item.extraction_confidence else None,
                'extracted_value': item.extracted_value,
                'table_name': item.table_name,
                'record_id': item.record_id,
                'sampled_at': datetime.utcnow().isoformat()
            })
        
        logger.info(f"Sampled {len(results)} items from {len(all_extractions)} high-confidence extractions")
        
        return results
    
    def detect_systemic_drift(
        self,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Detect systemic drift in extraction quality.
        
        Args:
            lookback_days: Days to analyze
            
        Returns:
            Dict with drift detection results
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        midpoint = datetime.utcnow() - timedelta(days=lookback_days / 2)
        
        # Get early period metrics
        early_period = self.db.query(
            func.avg(ExtractionFieldMetadata.extraction_confidence).label('avg_confidence'),
            func.count(ExtractionFieldMetadata.id).label('count')
        ).filter(
            and_(
                ExtractionFieldMetadata.created_at >= cutoff_date,
                ExtractionFieldMetadata.created_at < midpoint
            )
        ).first()
        
        # Get recent period metrics
        recent_period = self.db.query(
            func.avg(ExtractionFieldMetadata.extraction_confidence).label('avg_confidence'),
            func.count(ExtractionFieldMetadata.id).label('count')
        ).filter(
            ExtractionFieldMetadata.created_at >= midpoint
        ).first()
        
        if not early_period or not recent_period:
            return {
                'drift_detected': False,
                'reason': 'insufficient_data'
            }
        
        early_confidence = float(early_period.avg_confidence) if early_period.avg_confidence else 0.0
        recent_confidence = float(recent_period.avg_confidence) if recent_period.avg_confidence else 0.0
        
        # Calculate drift
        confidence_change = recent_confidence - early_confidence
        drift_percentage = (confidence_change / early_confidence * 100) if early_confidence > 0 else 0.0
        
        drift_detected = abs(drift_percentage) > (self.drift_threshold * 100)
        
        result = {
            'drift_detected': drift_detected,
            'early_period_confidence': early_confidence,
            'recent_period_confidence': recent_confidence,
            'confidence_change': confidence_change,
            'drift_percentage': drift_percentage,
            'early_period_count': early_period.count,
            'recent_period_count': recent_period.count
        }
        
        if drift_detected:
            result['severity'] = 'high' if abs(drift_percentage) > 20 else 'medium'
            result['message'] = f"Systemic drift detected: {drift_percentage:+.1f}% change in extraction confidence"
            
            # Generate alert (would integrate with alert system)
            logger.warning(f"Systemic drift detected: {result['message']}")
        
        return result
