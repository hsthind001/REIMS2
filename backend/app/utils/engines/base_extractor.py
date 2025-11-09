from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal


@dataclass
class ExtractionResult:
    """
    Dataclass to encapsulate extraction results with confidence scores.
    
    This standardizes the output format across all extraction engines.
    """
    
    # Core extraction data
    engine_name: str
    extracted_data: Dict[str, Any]
    success: bool = True
    
    # Confidence and quality metrics
    confidence_score: Decimal = field(default_factory=lambda: Decimal('0.0'))
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    processing_time_ms: Optional[float] = None
    page_count: Optional[int] = None
    
    # Quality indicators
    text_quality_score: Optional[float] = None
    table_detection_score: Optional[float] = None
    ocr_confidence: Optional[float] = None
    
    # Conflicts and alternatives
    conflicting_values: Optional[Dict[str, List[Any]]] = None
    alternative_interpretations: Optional[List[Dict]] = None
    
    # Error handling
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    # Engine-specific metadata
    engine_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize confidence score"""
        if isinstance(self.confidence_score, (int, float)):
            self.confidence_score = Decimal(str(self.confidence_score))
        
        # Ensure confidence is between 0 and 1
        if self.confidence_score < Decimal('0.0'):
            self.confidence_score = Decimal('0.0')
        elif self.confidence_score > Decimal('1.0'):
            self.confidence_score = Decimal('1.0')
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if extraction has high confidence (>= 95%)"""
        return self.confidence_score >= Decimal('0.95')
    
    @property
    def is_low_confidence(self) -> bool:
        """Check if extraction has low confidence (< 70%)"""
        return self.confidence_score < Decimal('0.70')
    
    @property
    def needs_review(self) -> bool:
        """Determine if extraction results need manual review"""
        return (
            not self.success or
            self.is_low_confidence or
            (self.conflicting_values and len(self.conflicting_values) > 0) or
            len(self.warnings) > 0
        )


class BaseExtractor(ABC):
    """
    Abstract base class for all extraction engines.
    
    Standardizes the interface and ensures all extractors implement
    confidence calculation and return structured results.
    """
    
    def __init__(self, engine_name: str):
        """
        Initialize the base extractor.
        
        Args:
            engine_name: Identifier for the extraction engine
        """
        self.engine_name = engine_name
        self._start_time: Optional[datetime] = None
    
    @abstractmethod
    def extract(self, pdf_data: bytes, **kwargs) -> ExtractionResult:
        """
        Extract data from PDF document.
        
        This is the main extraction method that all engines must implement.
        
        Args:
            pdf_data: Binary PDF data
            **kwargs: Engine-specific options
        
        Returns:
            ExtractionResult with extracted data and confidence scores
        """
        pass
    
    @abstractmethod
    def calculate_confidence(self, extraction_data: Dict[str, Any]) -> Decimal:
        """
        Calculate confidence score for the extraction.
        
        Args:
            extraction_data: Raw extraction data from the engine
        
        Returns:
            Confidence score as Decimal between 0.0 and 1.0
        """
        pass
    
    # Helper methods for confidence calculation
    
    def _start_timer(self) -> None:
        """Start timing the extraction process"""
        self._start_time = datetime.now()
    
    def _get_processing_time_ms(self) -> float:
        """
        Get processing time in milliseconds.
        
        Returns:
            Processing time in milliseconds, or 0.0 if timer not started
        """
        if self._start_time is None:
            return 0.0
        
        delta = datetime.now() - self._start_time
        return delta.total_seconds() * 1000
    
    def _calculate_text_quality(
        self,
        text: str,
        expected_min_length: int = 100
    ) -> float:
        """
        Calculate text quality score based on various heuristics.
        
        Args:
            text: Extracted text content
            expected_min_length: Minimum expected text length
        
        Returns:
            Quality score between 0.0 and 1.0
        """
        if not text or len(text.strip()) == 0:
            return 0.0
        
        score = 0.0
        
        # Length adequacy (0-0.3)
        if len(text) >= expected_min_length:
            score += 0.3
        else:
            score += 0.3 * (len(text) / expected_min_length)
        
        # Alphanumeric ratio (0-0.3)
        alpha_count = sum(c.isalnum() for c in text)
        alpha_ratio = alpha_count / len(text) if len(text) > 0 else 0
        score += 0.3 * alpha_ratio
        
        # Word coherence (0-0.2)
        words = text.split()
        if len(words) > 0:
            avg_word_length = sum(len(w) for w in words) / len(words)
            # Average word length between 4-8 is ideal
            if 4 <= avg_word_length <= 8:
                score += 0.2
            elif avg_word_length < 4:
                score += 0.2 * (avg_word_length / 4)
            else:
                score += 0.2 * (8 / avg_word_length)
        
        # Sentence structure (0-0.2)
        sentence_indicators = text.count('.') + text.count('!') + text.count('?')
        if sentence_indicators > 0:
            score += 0.2
        elif len(text) > expected_min_length:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_table_confidence(
        self,
        tables: List[Dict],
        expected_columns: Optional[List[str]] = None
    ) -> float:
        """
        Calculate confidence for table extraction.
        
        Args:
            tables: List of extracted tables
            expected_columns: Optional list of expected column names
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not tables or len(tables) == 0:
            return 0.0
        
        total_score = 0.0
        
        for table in tables:
            score = 0.0
            
            # Table structure (0-0.4)
            if 'headers' in table and table['headers']:
                score += 0.2
            if 'rows' in table and len(table.get('rows', [])) > 0:
                score += 0.2
            
            # Data completeness (0-0.3)
            if 'rows' in table:
                rows = table['rows']
                if rows:
                    # Check for empty cells
                    total_cells = sum(len(row) for row in rows)
                    empty_cells = sum(
                        1 for row in rows 
                        for cell in row 
                        if not cell or str(cell).strip() == ''
                    )
                    if total_cells > 0:
                        completeness = 1 - (empty_cells / total_cells)
                        score += 0.3 * completeness
            
            # Expected columns match (0-0.3)
            if expected_columns and 'headers' in table:
                headers = [h.lower() for h in table['headers']]
                matches = sum(
                    1 for expected in expected_columns 
                    if any(expected.lower() in h for h in headers)
                )
                if len(expected_columns) > 0:
                    score += 0.3 * (matches / len(expected_columns))
            else:
                score += 0.15  # Partial credit if no expected columns
            
            total_score += score
        
        # Average across all tables
        return min(total_score / len(tables), 1.0)
    
    def _calculate_aggregate_confidence(
        self,
        text_confidence: float,
        table_confidence: Optional[float] = None,
        ocr_confidence: Optional[float] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> Decimal:
        """
        Calculate aggregate confidence from multiple sources.
        
        Args:
            text_confidence: Confidence score for text extraction
            table_confidence: Optional confidence for table extraction
            ocr_confidence: Optional confidence from OCR
            weights: Optional custom weights for each component
        
        Returns:
            Aggregate confidence score as Decimal
        """
        if weights is None:
            weights = {
                'text': 0.4,
                'table': 0.4,
                'ocr': 0.2
            }
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        # Text confidence
        weighted_sum += text_confidence * weights['text']
        total_weight += weights['text']
        
        # Table confidence
        if table_confidence is not None:
            weighted_sum += table_confidence * weights['table']
            total_weight += weights['table']
        
        # OCR confidence
        if ocr_confidence is not None:
            weighted_sum += ocr_confidence * weights['ocr']
            total_weight += weights['ocr']
        
        # Calculate weighted average
        if total_weight > 0:
            final_confidence = weighted_sum / total_weight
        else:
            final_confidence = 0.0
        
        return Decimal(str(round(final_confidence, 4)))
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(engine='{self.engine_name}')>"

