"""
Query Router Configuration

Configuration for query complexity routing including
classification thresholds, routing strategies, and performance targets.
"""
import os
from typing import Dict, Any, List


class QueryRouterConfig:
    """
    Configuration for query complexity routing
    
    All parameters are configurable and can be overridden via environment variables.
    """
    
    # Classification Settings
    USE_LLM_CLASSIFICATION: bool = os.getenv('QUERY_ROUTER_USE_LLM', 'true').lower() == 'true'
    LLM_MODEL: str = os.getenv('QUERY_ROUTER_LLM_MODEL', 'gpt-4o')  # Fast, accurate
    LLM_TEMPERATURE: float = float(os.getenv('QUERY_ROUTER_LLM_TEMPERATURE', '0.3'))  # Low for classification
    LLM_TIMEOUT: int = int(os.getenv('QUERY_ROUTER_LLM_TIMEOUT', '3'))  # 3 seconds max
    
    # Performance Targets
    TARGET_DECISION_TIME_MS: int = int(os.getenv('QUERY_ROUTER_DECISION_TIME_MS', '100'))  # <100ms
    TARGET_ROUTING_ACCURACY: float = float(os.getenv('QUERY_ROUTER_TARGET_ACCURACY', '0.90'))  # >90%
    
    # Simple Query Patterns
    SIMPLE_KEYWORDS: List[str] = [
        'what is', 'what was', 'what are', 'show me', 'give me',
        'tell me', 'get', 'fetch', 'retrieve', 'find'
    ]
    SIMPLE_PATTERNS: List[str] = [
        r'what (is|was|are) .+ (for|in|of)',
        r'show me .+ (for|in|of)',
        r'get .+ (for|in|of)'
    ]
    
    # Medium Query Patterns
    MEDIUM_KEYWORDS: List[str] = [
        'compare', 'comparison', 'trend', 'trends', 'across', 'between',
        'all properties', 'all periods', 'multiple', 'various'
    ]
    MEDIUM_PATTERNS: List[str] = [
        r'compare .+ (across|between)',
        r'trend .+ (over|across)',
        r'all .+ (properties|periods)'
    ]
    
    # Complex Query Patterns
    COMPLEX_KEYWORDS: List[str] = [
        'why', 'how', 'explain', 'analyze', 'analysis', 'predict', 'prediction',
        'reason', 'reasoning', 'cause', 'caused', 'impact', 'effect'
    ]
    COMPLEX_PATTERNS: List[str] = [
        r'why (did|does|is|was)',
        r'how (did|does|is|was)',
        r'explain .+ (why|how)',
        r'analyze .+ (trend|change|decrease|increase)',
        r'predict .+ (will|future)'
    ]
    
    # Routing Thresholds
    SIMPLE_CONFIDENCE_THRESHOLD: float = float(os.getenv('QUERY_ROUTER_SIMPLE_THRESHOLD', '0.85'))
    MEDIUM_CONFIDENCE_THRESHOLD: float = float(os.getenv('QUERY_ROUTER_MEDIUM_THRESHOLD', '0.80'))
    COMPLEX_CONFIDENCE_THRESHOLD: float = float(os.getenv('QUERY_ROUTER_COMPLEX_THRESHOLD', '0.75'))
    
    # Route Configuration
    SIMPLE_ROUTE: str = 'direct_sql'  # Direct SQL execution
    MEDIUM_ROUTE: str = 'hybrid_rag_sql'  # Hybrid RAG + SQL
    COMPLEX_ROUTE: str = 'multi_step_reasoning'  # Multi-step reasoning
    
    # Caching
    CACHE_ENABLED: bool = os.getenv('QUERY_ROUTER_CACHE_ENABLED', 'true').lower() == 'true'
    CACHE_TTL_MINUTES: int = int(os.getenv('QUERY_ROUTER_CACHE_TTL_MINUTES', '60'))  # Cache for 1 hour
    
    # Monitoring
    TRACK_ROUTING_ACCURACY: bool = os.getenv('QUERY_ROUTER_TRACK_ACCURACY', 'true').lower() == 'true'
    LOG_ROUTING_DECISIONS: bool = os.getenv('QUERY_ROUTER_LOG_DECISIONS', 'true').lower() == 'true'
    
    # Fallback Strategy
    DEFAULT_ROUTE: str = 'hybrid_rag_sql'  # Default if classification fails
    FALLBACK_TO_RULES: bool = os.getenv('QUERY_ROUTER_FALLBACK_TO_RULES', 'true').lower() == 'true'
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'use_llm_classification': cls.USE_LLM_CLASSIFICATION,
            'llm_model': cls.LLM_MODEL,
            'target_decision_time_ms': cls.TARGET_DECISION_TIME_MS,
            'target_routing_accuracy': cls.TARGET_ROUTING_ACCURACY,
            'simple_keywords': cls.SIMPLE_KEYWORDS,
            'medium_keywords': cls.MEDIUM_KEYWORDS,
            'complex_keywords': cls.COMPLEX_KEYWORDS,
            'simple_route': cls.SIMPLE_ROUTE,
            'medium_route': cls.MEDIUM_ROUTE,
            'complex_route': cls.COMPLEX_ROUTE,
            'default_route': cls.DEFAULT_ROUTE,
            'cache_enabled': cls.CACHE_ENABLED,
            'cache_ttl_minutes': cls.CACHE_TTL_MINUTES
        }


# Global configuration instance
query_router_config = QueryRouterConfig()

