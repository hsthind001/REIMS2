"""
Ensemble Voting Engine for REIMS2
Combines results from multiple extraction engines using weighted voting and conflict resolution.

Sprint 2: AI/ML Intelligence Layer
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from decimal import Decimal
import statistics
import re

from app.utils.engines.base_extractor import ExtractionResult


@dataclass
class FieldResult:
    """Result for a single field from multiple engines."""
    field_name: str
    values: List[Tuple[str, float, str]]  # (value, confidence, engine_name)
    final_value: Optional[str] = None
    final_confidence: float = 0.0
    extraction_engine: str = "ensemble"
    conflicting_values: Optional[Dict[str, Any]] = None
    resolution_method: str = "consensus"
    needs_review: bool = False
    
    
@dataclass
class EnsembleResult:
    """Combined result from ensemble voting."""
    fields: Dict[str, FieldResult]
    overall_confidence: float
    engines_used: List[str]
    consensus_fields: int = 0
    conflicting_fields: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnsembleEngine:
    """
    Ensemble voting engine that combines results from multiple extraction engines.
    
    Uses weighted voting based on:
    - Engine reliability scores
    - Individual extraction confidence
    - Consensus bonuses
    - Conflict detection and resolution
    """
    
    # Engine reliability weights (0-1 scale)
    ENGINE_WEIGHTS = {
        'pymupdf': 0.85,       # High for text-based PDFs
        'pdfplumber': 0.90,    # Very high for table extraction
        'camelot': 0.95,       # Highest for complex tables
        'layoutlm': 0.92,      # Very high for document understanding
        'easyocr': 0.75,       # Good for scanned documents
        'tesseract': 0.70,     # Baseline OCR
        'ensemble': 1.0        # Perfect score for final result
    }
    
    # Conflict resolution thresholds
    CONSENSUS_THRESHOLD = 0.66  # 66% agreement = consensus
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    REVIEW_THRESHOLD = 0.70  # Below this = needs review
    
    def __init__(self):
        """Initialize ensemble engine."""
        self.numeric_normalizer = NumericNormalizer()
        
    def combine_results(
        self,
        results: List[ExtractionResult],
        document_type: str = "balance_sheet"
    ) -> EnsembleResult:
        """
        Combine results from multiple extraction engines using weighted voting.
        
        Args:
            results: List of ExtractionResult from different engines
            document_type: Type of document being processed
            
        Returns:
            EnsembleResult with voted values and metadata
        """
        if not results:
            return EnsembleResult(
                fields={},
                overall_confidence=0.0,
                engines_used=[],
                metadata={'error': 'No results to combine'}
            )
        
        # Group results by field name
        field_results = self._group_results_by_field(results)
        
        # Vote on each field
        voted_fields = {}
        consensus_count = 0
        conflict_count = 0
        
        for field_name, field_data in field_results.items():
            field_result = self._resolve_field(field_name, field_data)
            voted_fields[field_name] = field_result
            
            if field_result.resolution_method == 'consensus':
                consensus_count += 1
            if field_result.conflicting_values:
                conflict_count += 1
        
        # Calculate overall confidence
        if voted_fields:
            confidences = [f.final_confidence for f in voted_fields.values()]
            overall_confidence = statistics.mean(confidences)
            
            # Apply consensus bonus
            if consensus_count > len(voted_fields) * 0.5:
                overall_confidence = min(1.0, overall_confidence * 1.1)  # 10% bonus
        else:
            overall_confidence = 0.0
        
        engines_used = list(set(r.engine_name for r in results))
        
        return EnsembleResult(
            fields=voted_fields,
            overall_confidence=overall_confidence,
            engines_used=engines_used,
            consensus_fields=consensus_count,
            conflicting_fields=conflict_count,
            metadata={
                'total_engines': len(engines_used),
                'total_fields': len(voted_fields),
                'consensus_rate': consensus_count / len(voted_fields) if voted_fields else 0,
                'document_type': document_type
            }
        )
    
    def _group_results_by_field(
        self,
        results: List[ExtractionResult]
    ) -> Dict[str, List[Tuple[str, float, str]]]:
        """
        Group extraction results by field name.
        
        Returns:
            Dict mapping field_name -> [(value, confidence, engine_name), ...]
        """
        field_data = defaultdict(list)
        
        for result in results:
            if not result.data:
                continue
            
            for field_name, field_value in result.data.items():
                # Skip None or empty values
                if field_value is None or (isinstance(field_value, str) and not field_value.strip()):
                    continue
                
                # Convert to string for comparison
                value_str = str(field_value)
                
                field_data[field_name].append((
                    value_str,
                    result.confidence,
                    result.engine_name
                ))
        
        return dict(field_data)
    
    def _resolve_field(
        self,
        field_name: str,
        field_data: List[Tuple[str, float, str]]
    ) -> FieldResult:
        """
        Resolve a single field using weighted voting.
        
        Args:
            field_name: Name of the field
            field_data: List of (value, confidence, engine_name) tuples
            
        Returns:
            FieldResult with voted value and metadata
        """
        if not field_data:
            return FieldResult(
                field_name=field_name,
                values=[],
                final_value=None,
                final_confidence=0.0,
                needs_review=True
            )
        
        # Single engine result
        if len(field_data) == 1:
            value, confidence, engine = field_data[0]
            return FieldResult(
                field_name=field_name,
                values=field_data,
                final_value=value,
                final_confidence=confidence,
                extraction_engine=engine,
                resolution_method='single_engine',
                needs_review=confidence < self.REVIEW_THRESHOLD
            )
        
        # Normalize numeric values for comparison
        normalized_data = []
        for value, confidence, engine in field_data:
            normalized_value = self.numeric_normalizer.normalize(value)
            normalized_data.append((normalized_value, value, confidence, engine))
        
        # Detect conflicts (different values)
        unique_values = set(nv for nv, _, _, _ in normalized_data)
        has_conflict = len(unique_values) > 1
        
        # Calculate weighted scores for each value
        value_scores = defaultdict(lambda: {'score': 0.0, 'engines': [], 'original': None})
        
        for normalized_value, original_value, confidence, engine in normalized_data:
            engine_weight = self.ENGINE_WEIGHTS.get(engine, 0.5)
            weighted_score = confidence * engine_weight
            
            value_scores[normalized_value]['score'] += weighted_score
            value_scores[normalized_value]['engines'].append(engine)
            if value_scores[normalized_value]['original'] is None:
                value_scores[normalized_value]['original'] = original_value
        
        # Find highest scoring value
        if not value_scores:
            return FieldResult(
                field_name=field_name,
                values=field_data,
                final_value=None,
                final_confidence=0.0,
                needs_review=True
            )
        
        best_normalized_value = max(value_scores.keys(), key=lambda v: value_scores[v]['score'])
        best_score = value_scores[best_normalized_value]['score']
        best_original_value = value_scores[best_normalized_value]['original']
        best_engines = value_scores[best_normalized_value]['engines']
        
        # Calculate final confidence
        num_engines = len(field_data)
        num_agreeing = len(best_engines)
        agreement_rate = num_agreeing / num_engines
        
        # Base confidence is the weighted score normalized
        final_confidence = min(1.0, best_score / num_engines)
        
        # Consensus bonus: if >66% of engines agree, add 10% boost
        if agreement_rate >= self.CONSENSUS_THRESHOLD:
            final_confidence = min(1.0, final_confidence * 1.1)
            resolution_method = 'consensus'
        else:
            resolution_method = 'weighted_vote'
        
        # Prepare conflict information
        conflicting_values = None
        if has_conflict:
            conflicting_values = {
                norm_val: {
                    'value': data['original'],
                    'engines': data['engines'],
                    'score': data['score']
                }
                for norm_val, data in value_scores.items()
            }
        
        return FieldResult(
            field_name=field_name,
            values=field_data,
            final_value=best_original_value,
            final_confidence=final_confidence,
            extraction_engine=f"ensemble({len(best_engines)}/{num_engines})",
            conflicting_values=conflicting_values,
            resolution_method=resolution_method,
            needs_review=final_confidence < self.REVIEW_THRESHOLD or (has_conflict and agreement_rate < 0.5)
        )


class NumericNormalizer:
    """
    Utility to normalize numeric values across different formats.
    Handles: $1,234.56, 1234.56, (1,234.56), 1234.5600, etc.
    """
    
    def normalize(self, value: Any) -> str:
        """
        Normalize a value for comparison.
        
        Args:
            value: Value to normalize (string or numeric)
            
        Returns:
            Normalized string representation
        """
        if value is None:
            return "NULL"
        
        value_str = str(value).strip()
        
        # Try to parse as number
        if self._is_numeric(value_str):
            try:
                # Remove currency symbols, commas, parentheses
                cleaned = re.sub(r'[$,\(\)]', '', value_str)
                
                # Handle negative numbers in parentheses
                if '(' in str(value):
                    cleaned = '-' + cleaned
                
                # Convert to float and format to 2 decimal places
                num = float(cleaned)
                
                # Return normalized format
                return f"{num:.2f}"
            except (ValueError, TypeError):
                pass
        
        # For non-numeric values, just normalize whitespace and case
        return ' '.join(value_str.split()).lower()
    
    def _is_numeric(self, value_str: str) -> bool:
        """Check if string represents a numeric value."""
        # Remove common numeric formatting characters
        cleaned = re.sub(r'[$,\(\)\s]', '', value_str)
        
        # Check if it's a number (including negatives and decimals)
        try:
            float(cleaned)
            return True
        except (ValueError, TypeError):
            return False


# Convenience function for direct use
def combine_extraction_results(
    results: List[ExtractionResult],
    document_type: str = "balance_sheet"
) -> EnsembleResult:
    """
    Convenience function to combine extraction results.
    
    Args:
        results: List of ExtractionResult from different engines
        document_type: Type of document being processed
        
    Returns:
        EnsembleResult with voted values
    """
    engine = EnsembleEngine()
    return engine.combine_results(results, document_type)

