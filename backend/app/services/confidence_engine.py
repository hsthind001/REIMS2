from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from app.utils.engines.base_extractor import ExtractionResult


class FieldResult:
    """Represents extraction result for a single field from one or more engines"""
    
    def __init__(self, field_name: str, table_name: str, record_id: int):
        self.field_name = field_name
        self.table_name = table_name
        self.record_id = record_id
        self.engine_results: List[Dict[str, Any]] = []
    
    def add_engine_result(
        self,
        engine_name: str,
        value: Any,
        confidence: Decimal
    ):
        """Add an extraction result from an engine"""
        self.engine_results.append({
            "engine": engine_name,
            "value": value,
            "confidence": float(confidence)
        })
    
    def has_conflicts(self) -> bool:
        """Check if different engines returned different values"""
        if len(self.engine_results) <= 1:
            return False
        
        values = [r["value"] for r in self.engine_results]
        unique_values = set(str(v) for v in values if v is not None)
        
        return len(unique_values) > 1
    
    def get_conflicting_values(self) -> List[Dict[str, Any]]:
        """Get list of conflicting values with their engines and confidences"""
        if not self.has_conflicts():
            return []
        
        return self.engine_results


class ConfidenceEngine:
    """
    Service to calculate aggregate confidence across multiple extraction engines
    and detect conflicts.
    
    This is the core intelligence layer that determines final confidence scores
    and recommends resolution strategies when engines disagree.
    """
    
    def __init__(self, engine_weights: Optional[Dict[str, float]] = None):
        """
        Initialize the Confidence Engine.
        
        Args:
            engine_weights: Optional custom weights for each engine
                Default: {'pymupdf': 0.3, 'pdfplumber': 0.4, 'camelot': 0.3}
        """
        self.engine_weights = engine_weights or {
            'pymupdf': 0.3,      # Good for text
            'pdfplumber': 0.4,   # Best for tables
            'camelot': 0.3       # Best for complex tables
        }
    
    def calculate_field_confidence(
        self,
        extraction_results: List[ExtractionResult],
        field_name: str,
        field_values: List[Any]
    ) -> Tuple[Decimal, str, Optional[List[Dict]]]:
        """
        Calculate aggregate confidence for a single field using weighted voting.
        
        Args:
            extraction_results: List of ExtractionResult from different engines
            field_name: Name of the field being evaluated
            field_values: Values extracted by each engine (same order as results)
        
        Returns:
            Tuple of (confidence_score, resolution_method, conflicting_values)
        """
        if not extraction_results or not field_values:
            return Decimal('0.0'), 'no_data', None
        
        # Build field result
        field_result = FieldResult(field_name, "unknown", 0)
        
        for result, value in zip(extraction_results, field_values):
            field_result.add_engine_result(
                result.engine_name,
                value,
                result.confidence_score
            )
        
        # Check for conflicts
        if field_result.has_conflicts():
            conflicting = field_result.get_conflicting_values()
            # Calculate confidence using conflict resolution
            confidence, method = self._resolve_conflict_confidence(conflicting)
            return confidence, method, conflicting
        
        # No conflicts - calculate weighted average
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for result in extraction_results:
            engine_name = result.engine_name
            weight = self.engine_weights.get(engine_name, 0.33)
            confidence = float(result.confidence_score)
            
            weighted_confidence += confidence * weight
            total_weight += weight
        
        if total_weight > 0:
            final_confidence = weighted_confidence / total_weight
        else:
            final_confidence = 0.0
        
        # Consensus method (all engines agree)
        method = 'consensus' if len(extraction_results) > 1 else 'single_engine'
        
        return Decimal(str(round(final_confidence, 4))), method, None
    
    def detect_conflicts(
        self,
        extraction_results: List[ExtractionResult],
        field_mappings: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts across multiple extraction results.
        
        Args:
            extraction_results: List of ExtractionResult from different engines
            field_mappings: Dict mapping field names to lists of values from each engine
        
        Returns:
            List of conflicts with field names, values, engines, and confidences
        """
        conflicts = []
        
        for field_name, values in field_mappings.items():
            # Create field result
            field_result = FieldResult(field_name, "unknown", 0)
            
            for result, value in zip(extraction_results, values):
                field_result.add_engine_result(
                    result.engine_name,
                    value,
                    result.confidence_score
                )
            
            # Check if this field has conflicts
            if field_result.has_conflicts():
                conflicting_values = field_result.get_conflicting_values()
                
                # Determine severity
                confidences = [c["confidence"] for c in conflicting_values]
                max_conf_diff = max(confidences) - min(confidences)
                
                if max_conf_diff > 0.3:
                    severity = "high"  # Large confidence gap
                elif max_conf_diff > 0.15:
                    severity = "medium"
                else:
                    severity = "low"
                
                conflicts.append({
                    "field_name": field_name,
                    "conflicting_values": conflicting_values,
                    "severity": severity,
                    "confidence_spread": max_conf_diff,
                    "engines_count": len(conflicting_values)
                })
        
        return conflicts
    
    def recommend_resolution_strategy(
        self,
        conflicting_values: List[Dict[str, Any]],
        field_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Recommend a resolution strategy for conflicting values.
        
        Args:
            conflicting_values: List of dicts with engine, value, confidence
            field_metadata: Optional metadata about the field (type, importance, etc.)
        
        Returns:
            Dict with recommended strategy, chosen value, and reasoning
        """
        if not conflicting_values or len(conflicting_values) == 0:
            return {
                "strategy": "no_conflict",
                "chosen_value": None,
                "confidence": Decimal('0.0'),
                "reasoning": "No conflicting values provided"
            }
        
        if len(conflicting_values) == 1:
            single = conflicting_values[0]
            return {
                "strategy": "single_engine",
                "chosen_value": single["value"],
                "confidence": Decimal(str(single["confidence"])),
                "reasoning": f"Only one engine ({single['engine']}) provided a value"
            }
        
        # Sort by confidence (highest first)
        sorted_values = sorted(
            conflicting_values,
            key=lambda x: x["confidence"],
            reverse=True
        )
        
        highest = sorted_values[0]
        second_highest = sorted_values[1] if len(sorted_values) > 1 else None
        
        # Strategy 1: Clear winner (>20% confidence gap)
        if second_highest and (highest["confidence"] - second_highest["confidence"]) > 0.20:
            return {
                "strategy": "weighted_vote",
                "chosen_value": highest["value"],
                "confidence": Decimal(str(highest["confidence"])),
                "reasoning": (
                    f"{highest['engine']} has significantly higher confidence "
                    f"({highest['confidence']:.2%}) than other engines"
                ),
                "engine": highest["engine"]
            }
        
        # Strategy 2: Consensus among high-confidence engines
        high_conf_values = [
            v for v in conflicting_values 
            if v["confidence"] >= 0.70
        ]
        
        if len(high_conf_values) >= 2:
            # Check if majority agree
            value_counts = {}
            for v in high_conf_values:
                val_str = str(v["value"])
                if val_str not in value_counts:
                    value_counts[val_str] = {
                        "value": v["value"],
                        "count": 0,
                        "total_confidence": 0.0,
                        "engines": []
                    }
                value_counts[val_str]["count"] += 1
                value_counts[val_str]["total_confidence"] += v["confidence"]
                value_counts[val_str]["engines"].append(v["engine"])
            
            # Find consensus
            majority = max(value_counts.values(), key=lambda x: (x["count"], x["total_confidence"]))
            
            if majority["count"] >= 2:
                avg_confidence = majority["total_confidence"] / majority["count"]
                return {
                    "strategy": "consensus",
                    "chosen_value": majority["value"],
                    "confidence": Decimal(str(round(avg_confidence, 4))),
                    "reasoning": (
                        f"{majority['count']} high-confidence engines agree "
                        f"({', '.join(majority['engines'])})"
                    ),
                    "engines": majority["engines"]
                }
        
        # Strategy 3: All values low confidence - needs human review
        all_low = all(v["confidence"] < 0.70 for v in conflicting_values)
        
        if all_low:
            return {
                "strategy": "human_review",
                "chosen_value": highest["value"],  # Tentative
                "confidence": Decimal(str(highest["confidence"])),
                "reasoning": (
                    "All engines have low confidence (<70%). "
                    "Manual review recommended."
                ),
                "needs_review": True,
                "review_priority": "high"
            }
        
        # Strategy 4: AI override recommended for complex conflicts
        if len(conflicting_values) >= 3:
            # Calculate weighted average of confidences
            total_conf = sum(v["confidence"] for v in conflicting_values)
            avg_conf = total_conf / len(conflicting_values)
            
            return {
                "strategy": "ai_override",
                "chosen_value": highest["value"],  # Tentative
                "confidence": Decimal(str(round(avg_conf, 4))),
                "reasoning": (
                    f"Complex conflict with {len(conflicting_values)} different values. "
                    "AI analysis or human review recommended."
                ),
                "needs_review": True,
                "review_priority": "medium"
            }
        
        # Default: Weighted vote (highest confidence wins)
        return {
            "strategy": "weighted_vote",
            "chosen_value": highest["value"],
            "confidence": Decimal(str(highest["confidence"])),
            "reasoning": f"Selected value from {highest['engine']} with highest confidence",
            "engine": highest["engine"]
        }
    
    def _resolve_conflict_confidence(
        self,
        conflicting_values: List[Dict[str, Any]]
    ) -> Tuple[Decimal, str]:
        """
        Calculate confidence score for conflicting values.
        
        Confidence is reduced when conflicts exist, based on:
        - Number of conflicting values
        - Confidence spread
        - Agreement among high-confidence engines
        
        Args:
            conflicting_values: List of engine results with conflicts
        
        Returns:
            Tuple of (confidence_score, resolution_method)
        """
        if not conflicting_values:
            return Decimal('0.0'), 'no_data'
        
        # Get highest confidence
        confidences = [v["confidence"] for v in conflicting_values]
        max_confidence = max(confidences)
        min_confidence = min(confidences)
        confidence_spread = max_confidence - min_confidence
        
        # Reduce confidence based on conflict severity
        conflict_penalty = 0.0
        
        # Penalty for multiple conflicting values
        if len(conflicting_values) >= 3:
            conflict_penalty += 0.15  # 15% penalty for 3+ conflicts
        elif len(conflicting_values) == 2:
            conflict_penalty += 0.10  # 10% penalty for 2 conflicts
        
        # Penalty for wide confidence spread
        if confidence_spread > 0.3:
            conflict_penalty += 0.15  # High disagreement
        elif confidence_spread > 0.15:
            conflict_penalty += 0.10  # Medium disagreement
        
        # Calculate weighted average with penalties
        total_weight = sum(self.engine_weights.get(v["engine"], 0.33) for v in conflicting_values)
        weighted_sum = sum(
            v["confidence"] * self.engine_weights.get(v["engine"], 0.33)
            for v in conflicting_values
        )
        
        if total_weight > 0:
            base_confidence = weighted_sum / total_weight
        else:
            base_confidence = max_confidence
        
        # Apply conflict penalty
        final_confidence = base_confidence * (1 - conflict_penalty)
        
        # Determine method
        if confidence_spread > 0.3:
            method = 'human_review'
        elif len(conflicting_values) >= 3:
            method = 'ai_override'
        else:
            method = 'weighted_vote'
        
        return Decimal(str(round(final_confidence, 4))), method
    
    def aggregate_extraction_results(
        self,
        extraction_results: List[ExtractionResult]
    ) -> Dict[str, Any]:
        """
        Aggregate multiple extraction results into a single result.
        
        Args:
            extraction_results: List of ExtractionResult from different engines
        
        Returns:
            Dict with aggregated data, confidence, conflicts, and metadata
        """
        if not extraction_results:
            return {
                "success": False,
                "error": "No extraction results provided"
            }
        
        # Filter successful results
        successful_results = [r for r in extraction_results if r.success]
        
        if not successful_results:
            return {
                "success": False,
                "error": "All extraction engines failed",
                "failed_engines": [r.engine_name for r in extraction_results]
            }
        
        # Calculate aggregate confidence (weighted average)
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for result in successful_results:
            weight = self.engine_weights.get(result.engine_name, 0.33)
            confidence = float(result.confidence_score)
            
            weighted_confidence += confidence * weight
            total_weight += weight
        
        aggregate_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
        
        # Collect all warnings
        all_warnings = []
        for result in extraction_results:
            all_warnings.extend(result.warnings)
        
        # Determine if review needed
        needs_review = (
            aggregate_confidence < 0.70 or
            len(all_warnings) > 0 or
            any(not r.success for r in extraction_results)
        )
        
        # Determine review priority
        if aggregate_confidence < 0.50:
            review_priority = 'critical'
        elif aggregate_confidence < 0.70:
            review_priority = 'high'
        elif len(all_warnings) > 0:
            review_priority = 'medium'
        else:
            review_priority = 'low'
        
        return {
            "success": True,
            "aggregate_confidence": Decimal(str(round(aggregate_confidence, 4))),
            "engines_used": [r.engine_name for r in successful_results],
            "engines_failed": [r.engine_name for r in extraction_results if not r.success],
            "needs_review": needs_review,
            "review_priority": review_priority if needs_review else None,
            "warnings": all_warnings,
            "processing_times": {
                r.engine_name: r.processing_time_ms 
                for r in extraction_results 
                if r.processing_time_ms
            },
            "total_engines": len(extraction_results),
            "successful_engines": len(successful_results)
        }
    
    def get_best_value_from_conflict(
        self,
        conflicting_values: List[Dict[str, Any]]
    ) -> Tuple[Any, Decimal, str]:
        """
        Select the best value from conflicting results.
        
        Args:
            conflicting_values: List of dicts with engine, value, confidence
        
        Returns:
            Tuple of (chosen_value, confidence, engine_name)
        """
        if not conflicting_values:
            return None, Decimal('0.0'), 'unknown'
        
        # Sort by confidence
        sorted_values = sorted(
            conflicting_values,
            key=lambda x: x["confidence"],
            reverse=True
        )
        
        best = sorted_values[0]
        return best["value"], Decimal(str(best["confidence"])), best["engine"]
    
    def calculate_ensemble_confidence(
        self,
        pymupdf_result: Optional[ExtractionResult] = None,
        pdfplumber_result: Optional[ExtractionResult] = None,
        camelot_result: Optional[ExtractionResult] = None
    ) -> Dict[str, Any]:
        """
        Calculate ensemble confidence from all three main engines.
        
        This is a convenience method for the standard 3-engine setup.
        
        Args:
            pymupdf_result: Result from PyMuPDF engine
            pdfplumber_result: Result from PDFPlumber engine
            camelot_result: Result from Camelot engine
        
        Returns:
            Dict with ensemble confidence and metadata
        """
        results = []
        if pymupdf_result:
            results.append(pymupdf_result)
        if pdfplumber_result:
            results.append(pdfplumber_result)
        if camelot_result:
            results.append(camelot_result)
        
        return self.aggregate_extraction_results(results)
    
    def should_flag_for_review(
        self,
        confidence: Decimal,
        has_conflicts: bool,
        warnings: List[str]
    ) -> Tuple[bool, str, str]:
        """
        Determine if a field should be flagged for manual review.
        
        Args:
            confidence: Aggregate confidence score
            has_conflicts: Whether engines produced conflicting values
            warnings: List of warning messages
        
        Returns:
            Tuple of (needs_review, priority, reason)
        """
        # Critical priority (< 50% confidence)
        if float(confidence) < 0.50:
            return True, 'critical', f'Very low confidence: {confidence:.2%}'
        
        # High priority (< 70% confidence or conflicts)
        if float(confidence) < 0.70:
            return True, 'high', f'Low confidence: {confidence:.2%}'
        
        if has_conflicts:
            return True, 'high', 'Conflicting values from multiple engines'
        
        # Medium priority (warnings present)
        if len(warnings) > 2:
            return True, 'medium', f'{len(warnings)} warnings detected'
        
        if len(warnings) > 0:
            return True, 'low', f'{len(warnings)} warning(s): {warnings[0]}'
        
        # No review needed
        return False, None, None

