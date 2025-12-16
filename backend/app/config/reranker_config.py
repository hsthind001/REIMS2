"""
Reranker Configuration

Configuration for cross-encoder reranking including Cohere API
and sentence-transformers fallback settings.
"""
import os
from typing import Dict, Any


class RerankerConfig:
    """
    Configuration for cross-encoder reranking
    
    All parameters are configurable and can be overridden via environment variables.
    """
    
    # Cohere Rerank API Settings
    COHERE_API_KEY: str = os.getenv('COHERE_API_KEY', '')
    COHERE_MODEL: str = os.getenv('COHERE_RERANK_MODEL', 'rerank-english-v3.0')  # or rerank-multilingual-v3.0
    COHERE_TOP_N: int = int(os.getenv('COHERE_TOP_N', '50'))  # Number of candidates to rerank
    COHERE_TIMEOUT: int = int(os.getenv('COHERE_TIMEOUT', '10'))  # Request timeout in seconds
    COHERE_MAX_RETRIES: int = int(os.getenv('COHERE_MAX_RETRIES', '3'))
    
    # Fallback Settings (sentence-transformers)
    FALLBACK_MODEL: str = os.getenv('RERANKER_FALLBACK_MODEL', 'cross-encoder/ms-marco-MiniLM-L-12-v2')
    FALLBACK_DEVICE: str = os.getenv('RERANKER_FALLBACK_DEVICE', 'cpu')  # 'cpu' or 'cuda'
    FALLBACK_BATCH_SIZE: int = int(os.getenv('RERANKER_FALLBACK_BATCH_SIZE', '32'))
    
    # Reranking Parameters
    RERANK_TOP_N: int = int(os.getenv('RERANKER_TOP_N', '50'))  # Rerank top N from initial retrieval
    RERANK_TOP_K: int = int(os.getenv('RERANKER_TOP_K', '10'))  # Return top K after reranking
    RERANK_ENABLED: bool = os.getenv('RERANKER_ENABLED', 'true').lower() == 'true'
    
    # Performance Targets
    TARGET_LATENCY_MS: int = int(os.getenv('RERANKER_TARGET_LATENCY_MS', '200'))  # Target <200ms
    
    # Error Handling
    FALLBACK_ON_ERROR: bool = os.getenv('RERANKER_FALLBACK_ON_ERROR', 'true').lower() == 'true'
    RETURN_ORIGINAL_ON_FAILURE: bool = os.getenv('RERANKER_RETURN_ORIGINAL_ON_FAILURE', 'true').lower() == 'true'
    
    @classmethod
    def is_cohere_available(cls) -> bool:
        """Check if Cohere API is configured"""
        return bool(cls.COHERE_API_KEY)
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'cohere_available': cls.is_cohere_available(),
            'cohere_model': cls.COHERE_MODEL,
            'cohere_top_n': cls.COHERE_TOP_N,
            'fallback_model': cls.FALLBACK_MODEL,
            'fallback_device': cls.FALLBACK_DEVICE,
            'rerank_top_n': cls.RERANK_TOP_N,
            'rerank_top_k': cls.RERANK_TOP_K,
            'rerank_enabled': cls.RERANK_ENABLED,
            'target_latency_ms': cls.TARGET_LATENCY_MS,
            'fallback_on_error': cls.FALLBACK_ON_ERROR,
            'return_original_on_failure': cls.RETURN_ORIGINAL_ON_FAILURE
        }


# Global configuration instance
reranker_config = RerankerConfig()

