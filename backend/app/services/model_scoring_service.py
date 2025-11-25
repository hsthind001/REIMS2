"""
Model Scoring Service

Evaluates extraction models based on client-defined factors.
Models do NOT calculate their own confidence - this service scores them externally.
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScoringFactors:
    """
    Client-defined factors for scoring extraction models.
    All weights should sum to approximately 1.0 for normalized scoring.
    """
    # Text extraction factors
    text_length_weight: float = 0.20  # Weight for text length adequacy
    text_quality_weight: float = 0.25  # Weight for text quality (coherence, structure)
    
    # Table extraction factors
    table_detection_weight: float = 0.15  # Weight for table detection
    table_structure_weight: float = 0.10  # Weight for table structure quality
    
    # Performance factors
    processing_speed_weight: float = 0.10  # Weight for processing speed (faster = better)
    
    # Accuracy factors
    accuracy_weight: float = 0.15  # Weight for extraction accuracy (if available)
    
    # Model-specific bonuses/penalties
    model_type_bonus: Dict[str, float] = None  # Bonus points for specific model types
    
    # Thresholds
    min_text_length: int = 100  # Minimum expected text length
    max_processing_time_ms: float = 10000.0  # Maximum acceptable processing time (ms)
    
    def __post_init__(self):
        """Validate and normalize weights"""
        if self.model_type_bonus is None:
            self.model_type_bonus = {}
        
        # Normalize weights to sum to 1.0
        total_weight = (
            self.text_length_weight +
            self.text_quality_weight +
            self.table_detection_weight +
            self.table_structure_weight +
            self.processing_speed_weight +
            self.accuracy_weight
        )
        
        if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Scoring weights sum to {total_weight}, not 1.0. Normalizing...")
            # Normalize
            self.text_length_weight /= total_weight
            self.text_quality_weight /= total_weight
            self.table_detection_weight /= total_weight
            self.table_structure_weight /= total_weight
            self.processing_speed_weight /= total_weight
            self.accuracy_weight /= total_weight


class ModelScoringService:
    """
    Service to score extraction models based on client-defined factors.
    
    This service evaluates model outputs externally - models themselves
    do NOT calculate confidence scores.
    """
    
    def __init__(self, scoring_factors: Optional[ScoringFactors] = None):
        """
        Initialize scoring service with client-defined factors.
        
        Args:
            scoring_factors: Custom scoring factors. If None, uses defaults.
        """
        self.factors = scoring_factors or ScoringFactors()
        logger.info(f"ModelScoringService initialized with factors: {self.factors}")
    
    def score_extraction_result(
        self,
        model_name: str,
        extracted_data: Dict[str, Any],
        processing_time_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Score an extraction result based on client-defined factors.
        
        Args:
            model_name: Name of the extraction model
            extracted_data: Dictionary with extracted data (text, tables, etc.)
            processing_time_ms: Processing time in milliseconds
            success: Whether extraction was successful
            error: Error message if extraction failed
        
        Returns:
            dict: {
                "score": float (1-10),
                "confidence": float (0.0-1.0),
                "score_breakdown": {
                    "text_length_score": float,
                    "text_quality_score": float,
                    "table_detection_score": float,
                    "table_structure_score": float,
                    "speed_score": float,
                    "accuracy_score": float,
                    "model_bonus": float
                },
                "factors_used": {...}
            }
        """
        if not success or error:
            return {
                "score": 1.0,
                "confidence": 0.0,
                "score_breakdown": {
                    "text_length_score": 0.0,
                    "text_quality_score": 0.0,
                    "table_detection_score": 0.0,
                    "table_structure_score": 0.0,
                    "speed_score": 0.0,
                    "accuracy_score": 0.0,
                    "model_bonus": 0.0,
                    "error": error
                },
                "factors_used": self.factors.__dict__
            }
        
        # Extract data
        text = extracted_data.get('text', '')
        text_length = len(text) if text else 0
        tables = extracted_data.get('tables', [])
        total_pages = extracted_data.get('total_pages', 1)
        
        # Calculate individual component scores (0.0 to 1.0)
        score_breakdown = {}
        
        # 1. Text Length Score
        if text_length >= self.factors.min_text_length:
            text_length_score = 1.0
        else:
            text_length_score = min(text_length / self.factors.min_text_length, 1.0)
        score_breakdown['text_length_score'] = text_length_score
        
        # 2. Text Quality Score
        text_quality_score = self._calculate_text_quality(text)
        score_breakdown['text_quality_score'] = text_quality_score
        
        # 3. Table Detection Score
        if tables and len(tables) > 0:
            table_detection_score = min(len(tables) / max(total_pages, 1), 1.0)
        else:
            table_detection_score = 0.0
        score_breakdown['table_detection_score'] = table_detection_score
        
        # 4. Table Structure Score
        if tables:
            table_structure_score = self._calculate_table_structure_score(tables)
        else:
            table_structure_score = 0.0
        score_breakdown['table_structure_score'] = table_structure_score
        
        # 5. Processing Speed Score (faster = better)
        if processing_time_ms <= 0:
            speed_score = 1.0  # Instant
        elif processing_time_ms >= self.factors.max_processing_time_ms:
            speed_score = 0.0  # Too slow
        else:
            # Linear scale: 0ms = 1.0, max_time_ms = 0.0
            speed_score = 1.0 - (processing_time_ms / self.factors.max_processing_time_ms)
        score_breakdown['speed_score'] = max(0.0, min(1.0, speed_score))
        
        # 6. Accuracy Score (if available in extracted_data)
        accuracy_score = extracted_data.get('accuracy', 0.0)
        if isinstance(accuracy_score, (int, float)):
            accuracy_score = float(accuracy_score)
            if accuracy_score > 1.0:
                accuracy_score = accuracy_score / 100.0  # Convert percentage to 0-1
        else:
            accuracy_score = 0.0
        score_breakdown['accuracy_score'] = max(0.0, min(1.0, accuracy_score))
        
        # 7. Model Type Bonus
        model_bonus = self.factors.model_type_bonus.get(model_name.lower(), 0.0)
        score_breakdown['model_bonus'] = model_bonus
        
        # Calculate weighted total score (0.0 to 1.0)
        weighted_score = (
            (text_length_score * self.factors.text_length_weight) +
            (text_quality_score * self.factors.text_quality_weight) +
            (table_detection_score * self.factors.table_detection_weight) +
            (table_structure_score * self.factors.table_structure_weight) +
            (speed_score * self.factors.processing_speed_weight) +
            (accuracy_score * self.factors.accuracy_weight) +
            model_bonus  # Bonus is added directly (can exceed 1.0)
        )
        
        # Normalize to 0.0-1.0 range
        confidence = max(0.0, min(1.0, weighted_score))
        
        # Convert to 1-10 scale
        score = 1.0 + (confidence * 9.0)
        
        return {
            "score": round(score, 1),
            "confidence": round(confidence, 4),
            "score_breakdown": {k: round(v, 4) for k, v in score_breakdown.items()},
            "factors_used": {
                "text_length_weight": self.factors.text_length_weight,
                "text_quality_weight": self.factors.text_quality_weight,
                "table_detection_weight": self.factors.table_detection_weight,
                "table_structure_weight": self.factors.table_structure_weight,
                "processing_speed_weight": self.factors.processing_speed_weight,
                "accuracy_weight": self.factors.accuracy_weight,
                "model_type_bonus": self.factors.model_type_bonus
            }
        }
    
    def _calculate_text_quality(self, text: str) -> float:
        """
        Calculate text quality score based on various heuristics.
        
        Returns score between 0.0 and 1.0.
        """
        if not text or len(text.strip()) == 0:
            return 0.0
        
        score = 0.0
        
        # Alphanumeric ratio (0-0.3)
        alpha_count = sum(c.isalnum() for c in text)
        alpha_ratio = alpha_count / len(text) if len(text) > 0 else 0
        score += 0.3 * alpha_ratio
        
        # Word coherence (0-0.3)
        words = text.split()
        if len(words) > 0:
            avg_word_length = sum(len(w) for w in words) / len(words)
            # Average word length between 4-8 is ideal
            if 4 <= avg_word_length <= 8:
                score += 0.3
            elif avg_word_length < 4:
                score += 0.3 * (avg_word_length / 4)
            else:
                score += 0.3 * (8 / avg_word_length)
        
        # Sentence structure (0-0.2)
        sentence_indicators = text.count('.') + text.count('!') + text.count('?')
        if sentence_indicators > 0:
            score += 0.2
        elif len(text) > 100:
            score += 0.1
        
        # Special character ratio (0-0.2) - lower is better
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / len(text) if len(text) > 0 else 0
        if special_ratio < 0.1:  # Less than 10% special chars is good
            score += 0.2
        elif special_ratio < 0.2:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_table_structure_score(self, tables: List[Dict]) -> float:
        """
        Calculate table structure quality score.
        
        Returns score between 0.0 and 1.0.
        """
        if not tables:
            return 0.0
        
        total_score = 0.0
        
        for table in tables:
            score = 0.0
            
            # Table structure (0-0.5)
            if 'headers' in table and table['headers']:
                score += 0.25
            if 'rows' in table and len(table.get('rows', [])) > 0:
                score += 0.25
            
            # Data completeness (0-0.5)
            if 'rows' in table:
                rows = table['rows']
                if rows:
                    total_cells = sum(len(row) for row in rows)
                    empty_cells = sum(
                        1 for row in rows 
                        for cell in row 
                        if not cell or str(cell).strip() == ''
                    )
                    if total_cells > 0:
                        completeness = 1 - (empty_cells / total_cells)
                        score += 0.5 * completeness
            
            total_score += score
        
        # Average across all tables
        return min(total_score / len(tables), 1.0)

