"""
Fixed RRF Configuration

Improvements:
- Higher default alpha (favor semantic more)
- Adaptive alpha based on query type
"""
import os


class FixedRRFConfig:
    """
    Fixed RRF configuration with accuracy improvements.
    """
    
    # Increased alpha to favor semantic search more (was 0.7)
    ALPHA = float(os.getenv("RRF_ALPHA", "0.85"))  # 85% semantic, 15% keyword
    
    # RRF constant
    K = int(os.getenv("RRF_K", "60"))
    
    # Adaptive alpha thresholds
    CONCEPTUAL_QUERY_ALPHA = 0.90  # For conceptual queries
    KEYWORD_QUERY_ALPHA = 0.75  # For keyword-heavy queries
    
    @classmethod
    def validate_alpha(cls, alpha: Optional[float]) -> float:
        """Validate alpha value."""
        if alpha is None:
            return cls.ALPHA
        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"Alpha must be between 0 and 1, got {alpha}")
        return alpha
    
    @classmethod
    def validate_k(cls, k: Optional[int]) -> int:
        """Validate k value."""
        if k is None:
            return cls.K
        if k < 1:
            raise ValueError(f"K must be >= 1, got {k}")
        return k

