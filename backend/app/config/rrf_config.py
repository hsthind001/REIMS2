"""
Reciprocal Rank Fusion (RRF) Configuration

Configurable parameters for RRF-based result fusion.
"""
import os
from typing import Dict, Any


class RRFConfig:
    """
    Configuration for Reciprocal Rank Fusion
    
    RRF Formula: score = α/(k + semantic_rank) + (1-α)/(k + keyword_rank)
    
    All parameters are configurable and can be overridden via environment variables.
    """
    
    # RRF Algorithm Parameters
    ALPHA: float = float(os.getenv('RRF_ALPHA', '0.7'))  # Weight for semantic search (0-1)
    K: int = int(os.getenv('RRF_K', '60'))  # RRF constant (typically 60)
    
    # Validation
    MIN_ALPHA: float = 0.0
    MAX_ALPHA: float = 1.0
    MIN_K: int = 1
    MAX_K: int = 1000
    
    @classmethod
    def validate_alpha(cls, alpha: float) -> float:
        """
        Validate and clamp alpha parameter
        
        Args:
            alpha: Alpha value to validate
        
        Returns:
            Clamped alpha value
        """
        return max(cls.MIN_ALPHA, min(cls.MAX_ALPHA, alpha))
    
    @classmethod
    def validate_k(cls, k: int) -> int:
        """
        Validate and clamp k parameter
        
        Args:
            k: K value to validate
        
        Returns:
            Clamped k value
        """
        return max(cls.MIN_K, min(cls.MAX_K, k))
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'alpha': cls.ALPHA,
            'k': cls.K,
            'semantic_weight': cls.ALPHA,
            'keyword_weight': 1.0 - cls.ALPHA
        }
    
    @classmethod
    def get_semantic_weight(cls) -> float:
        """Get semantic search weight (alpha)"""
        return cls.ALPHA
    
    @classmethod
    def get_keyword_weight(cls) -> float:
        """Get keyword search weight (1 - alpha)"""
        return 1.0 - cls.ALPHA


# Global configuration instance
rrf_config = RRFConfig()

