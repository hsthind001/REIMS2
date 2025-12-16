"""
Query Rewriter Configuration

Configuration for LLM-based query rewriting including
model settings, caching, and synonym handling.
"""
import os
from typing import Dict, Any


class QueryRewriterConfig:
    """
    Configuration for query rewriting service
    
    All parameters are configurable and can be overridden via environment variables.
    """
    
    # LLM Settings
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL: str = os.getenv('QUERY_REWRITER_MODEL', 'gpt-4o')  # Fast, high quality
    OPENAI_TEMPERATURE: float = float(os.getenv('QUERY_REWRITER_TEMPERATURE', '0.7'))
    OPENAI_MAX_TOKENS: int = int(os.getenv('QUERY_REWRITER_MAX_TOKENS', '200'))
    OPENAI_TIMEOUT: int = int(os.getenv('QUERY_REWRITER_TIMEOUT', '5'))  # 5 seconds timeout
    
    # Query Variation Settings
    NUM_VARIATIONS: int = int(os.getenv('QUERY_REWRITER_NUM_VARIATIONS', '3'))
    TARGET_GENERATION_TIME_MS: int = int(os.getenv('QUERY_REWRITER_TARGET_TIME_MS', '500'))
    
    # Caching Settings
    CACHE_ENABLED: bool = os.getenv('QUERY_REWRITER_CACHE_ENABLED', 'true').lower() == 'true'
    CACHE_TTL_HOURS: int = int(os.getenv('QUERY_REWRITER_CACHE_TTL_HOURS', '24'))
    CACHE_MAX_SIZE: int = int(os.getenv('QUERY_REWRITER_CACHE_MAX_SIZE', '1000'))  # Max cached queries
    
    # Fallback Settings
    FALLBACK_TO_ORIGINAL: bool = os.getenv('QUERY_REWRITER_FALLBACK_TO_ORIGINAL', 'true').lower() == 'true'
    USE_SYNONYM_DICT_ON_FAILURE: bool = os.getenv('QUERY_REWRITER_USE_SYNONYM_DICT', 'true').lower() == 'true'
    
    # Synonym Dictionary
    SYNONYM_DICT_PATH: str = os.getenv(
        'QUERY_REWRITER_SYNONYM_DICT_PATH',
        'app/data/financial_synonyms.json'
    )
    
    # Monitoring
    LOG_REWRITING_SUCCESS: bool = os.getenv('QUERY_REWRITER_LOG_SUCCESS', 'true').lower() == 'true'
    TRACK_METRICS: bool = os.getenv('QUERY_REWRITER_TRACK_METRICS', 'true').lower() == 'true'
    
    @classmethod
    def is_openai_available(cls) -> bool:
        """Check if OpenAI API is configured"""
        return bool(cls.OPENAI_API_KEY)
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'openai_available': cls.is_openai_available(),
            'openai_model': cls.OPENAI_MODEL,
            'openai_temperature': cls.OPENAI_TEMPERATURE,
            'num_variations': cls.NUM_VARIATIONS,
            'target_generation_time_ms': cls.TARGET_GENERATION_TIME_MS,
            'cache_enabled': cls.CACHE_ENABLED,
            'cache_ttl_hours': cls.CACHE_TTL_HOURS,
            'cache_max_size': cls.CACHE_MAX_SIZE,
            'fallback_to_original': cls.FALLBACK_TO_ORIGINAL,
            'use_synonym_dict_on_failure': cls.USE_SYNONYM_DICT_ON_FAILURE,
            'synonym_dict_path': cls.SYNONYM_DICT_PATH
        }


# Global configuration instance
query_rewriter_config = QueryRewriterConfig()

