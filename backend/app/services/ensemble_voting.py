"""
Ensemble Voting Mechanism

Combines results from multiple extraction engines using weighted voting,
conflict resolution, and numeric normalization.
"""

from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import re
from app.utils.engines.base_extractor import ExtractionResult


class EnsembleVoting:
    """
    Ensemble voting mechanism to combine results from multiple engines.
    
    Uses weighted voting, conflict resolution, and normalization to produce
    the best possible extraction result.
    """
    
    def __init__(self, engine_weights: Optional[Dict[str, float]] = None):
        """
        Initialize ensemble voting.
        
        Args:
            engine_weights: Custom weights for each engine
                Default: Equal weight for all engines
        """
        self.engine_weights = engine_weights or {
            'pymupdf': 0.15,
            'pdfplumber': 0.20,
            'camelot': 0.20,
            'layoutlm': 0.30,     # AI model gets higher weight
            'easyocr': 0.15
        }
    
    def combine_results(
        self,
        extraction_results: List[ExtractionResult],
        field_mappings: Optional[Dict[str, List[Any]]] = None
    ) -> Dict[str, Any]:
        """
        Combine results from multiple extraction engines.
        
        Args:
            extraction_results: List of ExtractionResult from different engines
            field_mappings: Optional mapping of field names to values from each engine
        
        Returns:
            Combined result with resolved conflicts and normalized values
        """
        if not extraction_results:
            return {
                "success": False,
                "error": "No extraction results provided"
            }
        
        # Filter successful results
        successful = [r for r in extraction_results if r.success]
        
        if not successful:
            return {
                "success": False,
                "error": "All engines failed",
                "failed_engines": [r.engine_name for r in extraction_results]
            }
        
        # Aggregate text from all engines
        all_texts = [r.extracted_data.get("text", "") for r in successful]
        
        # Use longest text as base (usually most complete)
        primary_text = max(all_texts, key=len) if all_texts else ""
        
        # Calculate weighted confidence
        total_weight = 0.0
        weighted_conf = 0.0
        
        for result in successful:
            weight = self.engine_weights.get(result.engine_name, 1.0 / len(successful))
            conf = float(result.confidence_score)
            
            weighted_conf += conf * weight
            total_weight += weight
        
        aggregate_confidence = weighted_conf / total_weight if total_weight > 0 else 0.0
        
        # Resolve conflicts if field mappings provided
        resolved_fields = {}
        conflicts = []
        
        if field_mappings:
            for field_name, values in field_mappings.items():
                resolved, conflict_info = self._resolve_field_conflict(
                    field_name,
                    values,
                    extraction_results
                )
                resolved_fields[field_name] = resolved
                if conflict_info:
                    conflicts.append(conflict_info)
        
        return {
            "success": True,
            "combined_text": primary_text,
            "aggregate_confidence": Decimal(str(round(aggregate_confidence, 4))),
            "engines_used": [r.engine_name for r in successful],
            "engines_failed": [r.engine_name for r in extraction_results if not r.success],
            "resolved_fields": resolved_fields,
            "conflicts_detected": len(conflicts),
            "conflict_details": conflicts,
            "primary_engine": max(successful, key=lambda r: r.confidence_score).engine_name
        }
    
    def _resolve_field_conflict(
        self,
        field_name: str,
        values: List[Any],
        extraction_results: List[ExtractionResult]
    ) -> Tuple[Any, Optional[Dict]]:
        """
        Resolve conflicts for a single field.
        
        Args:
            field_name: Name of the field
            values: List of values from different engines
            extraction_results: Corresponding ExtractionResult objects
        
        Returns:
            Tuple of (resolved_value, conflict_info or None)
        """
        # Normalize values
        normalized_values = [self._normalize_value(v) for v in values]
        
        # Check for conflicts
        unique_values = set(str(v) for v in normalized_values if v is not None)
        
        if len(unique_values) <= 1:
            # No conflict
            return values[0] if values else None, None
        
        # Conflict detected - use weighted voting
        value_scores = {}
        
        for value, result in zip(normalized_values, extraction_results):
            if value is None:
                continue
            
            value_key = str(value)
            weight = self.engine_weights.get(result.engine_name, 0.2)
            conf = float(result.confidence_score)
            score = weight * conf
            
            if value_key not in value_scores:
                value_scores[value_key] = {
                    "value": value,
                    "score": 0.0,
                    "engines": []
                }
            
            value_scores[value_key]["score"] += score
            value_scores[value_key]["engines"].append(result.engine_name)
        
        # Select value with highest score
        if value_scores:
            best = max(value_scores.values(), key=lambda x: x["score"])
            
            conflict_info = {
                "field_name": field_name,
                "values": list(value_scores.values()),
                "chosen_value": best["value"],
                "resolution_method": "weighted_vote"
            }
            
            return best["value"], conflict_info
        
        return values[0] if values else None, None
    
    def _normalize_value(self, value: Any) -> Any:
        """
        Normalize a value for comparison.
        
        Handles:
        - String trimming and case normalization
        - Numeric formatting (remove commas, handle decimals)
        - Date formatting
        """
        if value is None or value == "":
            return None
        
        # Convert to string for normalization
        str_value = str(value).strip()
        
        # Try numeric normalization
        normalized = self._normalize_numeric(str_value)
        if normalized is not None:
            return normalized
        
        # String normalization
        return str_value.lower()
    
    def _normalize_numeric(self, value: str) -> Optional[Decimal]:
        """
        Normalize numeric values.
        
        Handles:
        - Remove commas: "1,000.50" → 1000.50
        - Remove $ and %: "$100" → 100
        - Handle parentheses (negative): "(100)" → -100
        """
        if not value:
            return None
        
        # Remove common currency/formatting characters
        cleaned = value.replace(',', '').replace('$', '').replace('%', '').strip()
        
        # Handle parentheses (accounting negative)
        is_negative = cleaned.startswith('(') and cleaned.endswith(')')
        if is_negative:
            cleaned = cleaned[1:-1]
        
        # Try to convert to Decimal
        try:
            number = Decimal(cleaned)
            return -number if is_negative else number
        except:
            return None
    
    def get_consensus_value(
        self,
        values: List[Any],
        confidences: List[float]
    ) -> Tuple[Any, float]:
        """
        Get consensus value using confidence-weighted voting.
        
        Args:
            values: List of values from different engines
            confidences: Corresponding confidence scores
        
        Returns:
            Tuple of (consensus_value, aggregate_confidence)
        """
        if not values or not confidences:
            return None, 0.0
        
        # Normalize values
        normalized = [self._normalize_value(v) for v in values]
        
        # Group by value with weighted scores
        value_scores = {}
        
        for value, conf in zip(normalized, confidences):
            if value is None:
                continue
            
            value_key = str(value)
            if value_key not in value_scores:
                value_scores[value_key] = {
                    "value": value,
                    "total_confidence": 0.0,
                    "count": 0
                }
            
            value_scores[value_key]["total_confidence"] += conf
            value_scores[value_key]["count"] += 1
        
        if not value_scores:
            return None, 0.0
        
        # Select value with highest total confidence
        best = max(value_scores.values(), key=lambda x: x["total_confidence"])
        avg_conf = best["total_confidence"] / best["count"]
        
        return best["value"], avg_conf

