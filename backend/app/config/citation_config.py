"""
Citation Extraction Configuration

Configuration for extracting granular citations from LLM answers.
"""
import os
from typing import Dict, Any


class CitationConfig:
    """
    Configuration for citation extraction
    
    All parameters are configurable and can be overridden via environment variables.
    """
    
    # Citation Settings
    EXTRACT_FOR_ALL_CLAIMS: bool = os.getenv('CITATION_EXTRACT_ALL', 'true').lower() == 'true'
    MIN_CONFIDENCE_THRESHOLD: float = float(os.getenv('CITATION_MIN_CONFIDENCE', '0.7'))
    MAX_SOURCES_PER_CLAIM: int = int(os.getenv('CITATION_MAX_SOURCES', '3'))
    
    # Matching Settings
    FUZZY_MATCH_THRESHOLD: float = float(os.getenv('CITATION_FUZZY_THRESHOLD', '0.8'))
    EXCERPT_WINDOW: int = int(os.getenv('CITATION_EXCERPT_WINDOW', '100'))  # Characters before/after match
    INCLUDE_SQL_CITATIONS: bool = os.getenv('CITATION_INCLUDE_SQL', 'true').lower() == 'true'
    
    # Citation Format
    CITATION_FORMAT: str = os.getenv('CITATION_FORMAT', 'detailed')  # 'detailed', 'compact', 'inline'
    INCLUDE_PAGE_NUMBER: bool = os.getenv('CITATION_INCLUDE_PAGE', 'true').lower() == 'true'
    INCLUDE_LINE_NUMBER: bool = os.getenv('CITATION_INCLUDE_LINE', 'true').lower() == 'true'
    INCLUDE_EXCERPT: bool = os.getenv('CITATION_INCLUDE_EXCERPT', 'true').lower() == 'true'
    
    # Deduplication
    DEDUPLICATE_SOURCES: bool = os.getenv('CITATION_DEDUPLICATE', 'true').lower() == 'true'
    DEDUPLICATION_THRESHOLD: float = float(os.getenv('CITATION_DEDUP_THRESHOLD', '0.9'))
    
    # Performance
    TARGET_EXTRACTION_TIME_MS: int = int(os.getenv('CITATION_TARGET_TIME_MS', '200'))  # <200ms
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'extract_for_all_claims': cls.EXTRACT_FOR_ALL_CLAIMS,
            'min_confidence_threshold': cls.MIN_CONFIDENCE_THRESHOLD,
            'max_sources_per_claim': cls.MAX_SOURCES_PER_CLAIM,
            'fuzzy_match_threshold': cls.FUZZY_MATCH_THRESHOLD,
            'excerpt_window': cls.EXCERPT_WINDOW,
            'include_sql_citations': cls.INCLUDE_SQL_CITATIONS,
            'citation_format': cls.CITATION_FORMAT,
            'include_page_number': cls.INCLUDE_PAGE_NUMBER,
            'include_line_number': cls.INCLUDE_LINE_NUMBER,
            'include_excerpt': cls.INCLUDE_EXCERPT,
            'deduplicate_sources': cls.DEDUPLICATE_SOURCES,
            'deduplication_threshold': cls.DEDUPLICATION_THRESHOLD,
            'target_extraction_time_ms': cls.TARGET_EXTRACTION_TIME_MS
        }


# Global configuration instance
citation_config = CitationConfig()

