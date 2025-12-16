"""
Fusion Configuration

Configuration for result fusion including RRF parameters,
tuning settings, and evaluation metrics.
"""
import os
from typing import Dict, Any, Tuple


class FusionConfig:
    """
    Configuration for result fusion
    
    All parameters are configurable and can be overridden via environment variables.
    """
    
    # RRF Algorithm Parameters
    ALPHA: float = float(os.getenv('FUSION_ALPHA', '0.7'))  # Weight for semantic search (0-1)
    K: int = int(os.getenv('FUSION_K', '60'))  # RRF constant (typically 60)
    
    # Parameter Tuning
    TUNING_ALPHA_MIN: float = 0.0
    TUNING_ALPHA_MAX: float = 1.0
    TUNING_ALPHA_STEP: float = 0.1
    TUNING_K_MIN: int = 30
    TUNING_K_MAX: int = 100
    TUNING_K_STEP: int = 10
    
    # Evaluation Metrics
    EVALUATION_TOP_K: int = int(os.getenv('FUSION_EVAL_TOP_K', '20'))  # Top-k for precision@k
    EVALUATION_METRICS: list = ['precision_at_k', 'recall_at_k', 'f1_at_k', 'ndcg']
    
    # Logging
    LOG_FUSION_SCORES: bool = os.getenv('FUSION_LOG_SCORES', 'false').lower() == 'true'
    LOG_LEVEL: str = os.getenv('FUSION_LOG_LEVEL', 'INFO')
    
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
    def get_alpha_range(cls) -> Tuple[float, float]:
        """Get alpha tuning range"""
        return (cls.TUNING_ALPHA_MIN, cls.TUNING_ALPHA_MAX)
    
    @classmethod
    def get_k_range(cls) -> Tuple[int, int]:
        """Get k tuning range"""
        return (cls.TUNING_K_MIN, cls.TUNING_K_MAX)
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'alpha': cls.ALPHA,
            'k': cls.K,
            'semantic_weight': cls.ALPHA,
            'keyword_weight': 1.0 - cls.ALPHA,
            'tuning_alpha_range': cls.get_alpha_range(),
            'tuning_alpha_step': cls.TUNING_ALPHA_STEP,
            'tuning_k_range': cls.get_k_range(),
            'tuning_k_step': cls.TUNING_K_STEP,
            'evaluation_top_k': cls.EVALUATION_TOP_K,
            'evaluation_metrics': cls.EVALUATION_METRICS,
            'log_fusion_scores': cls.LOG_FUSION_SCORES
        }


# Global configuration instance
fusion_config = FusionConfig()

