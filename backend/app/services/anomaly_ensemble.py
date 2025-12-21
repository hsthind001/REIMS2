"""
Anomaly Ensemble Service

Combines multiple anomaly detection methods (statistical + ML) with weighted voting
to reduce false positives and improve accuracy.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
import numpy as np
import logging

logger = logging.getLogger(__name__)


class AnomalyEnsemble:
    """
    Combines results from multiple anomaly detection methods.
    
    Methods:
    - Weighted voting based on confidence
    - Majority voting with tie-breaking
    - Confidence-based weighting
    """
    
    def __init__(self):
        """Initialize ensemble detector."""
        # Default weights for different detection methods
        self.method_weights = {
            'prophet_forecast': 0.15,
            'arima_forecast': 0.12,
            'ets_forecast': 0.10,
            'seasonal_decomposition': 0.13,
            'ewma': 0.10,
            'z_score': 0.12,
            'percentile': 0.10,
            'percentage_change': 0.08,
            'isolation_forest': 0.15,
            'lof': 0.12,
            'autoencoder': 0.15,
            'lstm': 0.15,
            'one_class_svm': 0.13
        }
    
    def combine_detections(
        self,
        detection_results: List[Dict[str, Any]],
        min_agreement: int = 2,
        confidence_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        Combine multiple anomaly detection results.
        
        Args:
            detection_results: List of detection result dicts, each with:
                - 'anomalies': List of detected anomalies
                - 'method': Detection method name
                - 'confidence': Overall confidence (0-1)
            min_agreement: Minimum number of methods that must agree
            confidence_threshold: Minimum confidence to include an anomaly
        
        Returns:
            Combined result with consensus anomalies
        """
        if not detection_results:
            return {
                'anomalies': [],
                'methods_used': [],
                'consensus_count': 0
            }
        
        # Collect all anomalies with their methods
        anomaly_votes = {}  # (field_name, anomaly_type) -> list of (anomaly_dict, method, confidence)
        
        for result in detection_results:
            method = result.get('method', 'unknown')
            method_confidence = result.get('confidence', 0.7)
            anomalies = result.get('anomalies', [])
            
            for anomaly in anomalies:
                field_name = anomaly.get('field_name', 'unknown')
                anomaly_type = anomaly.get('type', 'unknown')
                key = (field_name, anomaly_type)
                
                if key not in anomaly_votes:
                    anomaly_votes[key] = []
                
                # Calculate anomaly-specific confidence
                anomaly_confidence = anomaly.get('confidence', method_confidence)
                method_weight = self.method_weights.get(method, 0.1)
                
                # Combined confidence = method confidence * anomaly confidence * method weight
                combined_confidence = method_confidence * anomaly_confidence * method_weight
                
                anomaly_votes[key].append({
                    'anomaly': anomaly,
                    'method': method,
                    'confidence': combined_confidence,
                    'weight': method_weight
                })
        
        # Build consensus anomalies
        consensus_anomalies = []
        methods_used = set()
        
        for key, votes in anomaly_votes.items():
            field_name, anomaly_type = key
            
            # Count methods that detected this anomaly
            method_count = len(votes)
            
            # Calculate weighted average confidence
            total_weight = sum(v['weight'] for v in votes)
            if total_weight == 0:
                total_weight = len(votes)
            
            weighted_confidence = sum(
                v['confidence'] * v['weight'] for v in votes
            ) / total_weight
            
            # Check if we have enough agreement and confidence
            if method_count >= min_agreement and weighted_confidence >= confidence_threshold:
                # Use the anomaly from the highest confidence method
                best_vote = max(votes, key=lambda v: v['confidence'])
                consensus_anomaly = best_vote['anomaly'].copy()
                
                # Add ensemble metadata
                consensus_anomaly['ensemble_confidence'] = round(weighted_confidence, 4)
                consensus_anomaly['methods_agreed'] = method_count
                consensus_anomaly['detection_methods'] = [v['method'] for v in votes]
                consensus_anomaly['is_consensus'] = True
                
                consensus_anomalies.append(consensus_anomaly)
                
                # Track methods used
                methods_used.update(v['method'] for v in votes)
        
        # Sort by ensemble confidence (highest first)
        consensus_anomalies.sort(key=lambda a: a.get('ensemble_confidence', 0), reverse=True)
        
        return {
            'anomalies': consensus_anomalies,
            'methods_used': list(methods_used),
            'consensus_count': len(consensus_anomalies),
            'total_detections': sum(len(r.get('anomalies', [])) for r in detection_results),
            'consensus_rate': len(consensus_anomalies) / max(1, sum(len(r.get('anomalies', [])) for r in detection_results))
        }
    
    def weighted_voting(
        self,
        anomalies_by_method: Dict[str, List[Dict[str, Any]]],
        method_confidences: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform weighted voting across methods.
        
        Args:
            anomalies_by_method: Dict mapping method_name -> list of anomalies
            method_confidences: Optional dict of method -> confidence (uses defaults if not provided)
        
        Returns:
            List of consensus anomalies with weights
        """
        if not anomalies_by_method:
            return []
        
        if method_confidences is None:
            method_confidences = {}
        
        # Group anomalies by field and type
        grouped = {}
        
        for method, anomalies in anomalies_by_method.items():
            method_weight = self.method_weights.get(method, 0.1)
            method_confidence = method_confidences.get(method, 0.7)
            
            for anomaly in anomalies:
                field_name = anomaly.get('field_name', 'unknown')
                anomaly_type = anomaly.get('type', 'unknown')
                key = (field_name, anomaly_type)
                
                if key not in grouped:
                    grouped[key] = {
                        'anomaly': anomaly,
                        'votes': [],
                        'total_weight': 0.0
                    }
                
                vote_weight = method_weight * method_confidence
                grouped[key]['votes'].append({
                    'method': method,
                    'weight': vote_weight,
                    'confidence': method_confidence
                })
                grouped[key]['total_weight'] += vote_weight
        
        # Select anomalies with sufficient weight
        consensus = []
        for key, group in grouped.items():
            if group['total_weight'] >= 0.3:  # Threshold for consensus
                consensus_anomaly = group['anomaly'].copy()
                consensus_anomaly['ensemble_weight'] = round(group['total_weight'], 4)
                consensus_anomaly['vote_count'] = len(group['votes'])
                consensus_anomaly['voting_methods'] = [v['method'] for v in group['votes']]
                consensus.append(consensus_anomaly)
        
        return consensus
    
    def majority_voting(
        self,
        anomalies_by_method: Dict[str, List[Dict[str, Any]]],
        tie_breaker: str = 'highest_confidence'
    ) -> List[Dict[str, Any]]:
        """
        Perform majority voting (simple count-based).
        
        Args:
            anomalies_by_method: Dict mapping method_name -> list of anomalies
            tie_breaker: How to break ties ('highest_confidence', 'first', 'random')
        
        Returns:
            List of anomalies detected by majority
        """
        if not anomalies_by_method:
            return []
        
        method_count = len(anomalies_by_method)
        majority_threshold = (method_count // 2) + 1
        
        # Count votes per anomaly
        vote_counts = {}
        
        for method, anomalies in anomalies_by_method.items():
            for anomaly in anomalies:
                field_name = anomaly.get('field_name', 'unknown')
                anomaly_type = anomaly.get('type', 'unknown')
                key = (field_name, anomaly_type)
                
                if key not in vote_counts:
                    vote_counts[key] = {
                        'anomaly': anomaly,
                        'votes': [],
                        'count': 0
                    }
                
                vote_counts[key]['votes'].append(method)
                vote_counts[key]['count'] += 1
        
        # Select anomalies with majority votes
        consensus = []
        for key, group in vote_counts.items():
            if group['count'] >= majority_threshold:
                consensus_anomaly = group['anomaly'].copy()
                consensus_anomaly['vote_count'] = group['count']
                consensus_anomaly['voting_methods'] = group['votes']
                consensus.append(consensus_anomaly)
        
        return consensus
    
    def set_method_weight(self, method: str, weight: float):
        """Set custom weight for a detection method."""
        if 0 <= weight <= 1:
            self.method_weights[method] = weight
        else:
            logger.warning(f"Invalid weight {weight} for method {method}, must be 0-1")
    
    def get_method_weight(self, method: str) -> float:
        """Get current weight for a detection method."""
        return self.method_weights.get(method, 0.1)

