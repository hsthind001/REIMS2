"""
Coreference Resolution Configuration

Configuration for resolving pronouns and implicit references in follow-up queries.
"""
import os
from typing import List


class CoreferenceConfig:
    """
    Configuration for coreference resolution
    
    All parameters are configurable and can be overridden via environment variables.
    """
    
    # LLM Settings
    USE_LLM_RESOLUTION: bool = os.getenv('COREFERENCE_USE_LLM', 'true').lower() == 'true'
    LLM_MODEL: str = os.getenv('COREFERENCE_LLM_MODEL', 'gpt-4o')  # Fast, accurate
    LLM_TEMPERATURE: float = float(os.getenv('COREFERENCE_LLM_TEMPERATURE', '0.2'))  # Low for consistency
    LLM_TIMEOUT: int = int(os.getenv('COREFERENCE_LLM_TIMEOUT', '3'))  # 3 seconds max
    LLM_MAX_TOKENS: int = int(os.getenv('COREFERENCE_LLM_MAX_TOKENS', '200'))  # Short responses
    
    # Performance Targets
    TARGET_RESOLUTION_TIME_MS: int = int(os.getenv('COREFERENCE_TARGET_TIME_MS', '500'))  # <500ms
    TARGET_RESOLUTION_ACCURACY: float = float(os.getenv('COREFERENCE_TARGET_ACCURACY', '0.90'))  # >90%
    
    # Coreference Indicators
    PRONOUNS: List[str] = [
        'that', 'this', 'it', 'they', 'them', 'those', 'these',
        'its', 'their', 'theirs', 'itself', 'themselves'
    ]
    
    IMPLICIT_PHRASES: List[str] = [
        'and for', 'what about', 'how about', 'also', 'too',
        'and', 'for', 'in', 'during', 'on'
    ]
    
    TEMPORAL_INDICATORS: List[str] = [
        'last', 'next', 'previous', 'current', 'this', 'that',
        'prior', 'following', 'upcoming'
    ]
    
    # Detection Patterns
    PRONOUN_PATTERNS: List[str] = [
        r'\bthat\s+\w+',  # "that property"
        r'\bthis\s+\w+',  # "this property"
        r'\bit\s+\w+',    # "it in Q4"
        r'\bthey\s+\w+',  # "they in Q3"
        r'\bthose\s+\w+', # "those properties"
        r'\bthese\s+\w+'  # "these properties"
    ]
    
    IMPLICIT_PATTERNS: List[str] = [
        r'^and\s+for',    # "And for Q4?"
        r'^what\s+about', # "What about Q4?"
        r'^how\s+about',  # "How about December?"
        r'^also\s+for',   # "Also for Q4?"
        r'^and\s+in',     # "And in Q4?"
    ]
    
    TEMPORAL_PATTERNS: List[str] = [
        r'\blast\s+\w+',      # "last quarter"
        r'\bnext\s+\w+',      # "next month"
        r'\bprevious\s+\w+',  # "previous year"
        r'\bcurrent\s+\w+',   # "current period"
    ]
    
    # Resolution Settings
    MIN_CONFIDENCE_THRESHOLD: float = float(os.getenv('COREFERENCE_MIN_CONFIDENCE', '0.7'))
    FALLBACK_TO_RULES: bool = os.getenv('COREFERENCE_FALLBACK_TO_RULES', 'true').lower() == 'true'
    
    # Caching
    CACHE_ENABLED: bool = os.getenv('COREFERENCE_CACHE_ENABLED', 'true').lower() == 'true'
    CACHE_TTL_MINUTES: int = int(os.getenv('COREFERENCE_CACHE_TTL_MINUTES', '30'))  # Cache for 30 minutes
    
    # Context Window
    MAX_HISTORY_TURNS: int = int(os.getenv('COREFERENCE_MAX_HISTORY_TURNS', '5'))  # Last 5 turns
    
    @classmethod
    def get_config_dict(cls) -> dict:
        """Get all configuration as dictionary"""
        return {
            'use_llm_resolution': cls.USE_LLM_RESOLUTION,
            'llm_model': cls.LLM_MODEL,
            'target_resolution_time_ms': cls.TARGET_RESOLUTION_TIME_MS,
            'target_resolution_accuracy': cls.TARGET_RESOLUTION_ACCURACY,
            'pronouns': cls.PRONOUNS,
            'implicit_phrases': cls.IMPLICIT_PHRASES,
            'temporal_indicators': cls.TEMPORAL_INDICATORS,
            'min_confidence_threshold': cls.MIN_CONFIDENCE_THRESHOLD,
            'fallback_to_rules': cls.FALLBACK_TO_RULES,
            'cache_enabled': cls.CACHE_ENABLED,
            'cache_ttl_minutes': cls.CACHE_TTL_MINUTES,
            'max_history_turns': cls.MAX_HISTORY_TURNS
        }


# Global configuration instance
coreference_config = CoreferenceConfig()

