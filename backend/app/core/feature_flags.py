"""
Feature Flags Module

Manages feature flags for gradual rollout of new features.
All flags are read from environment variables.
"""

import os
from typing import Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class FeatureFlags:
    """
    Feature flags for anomaly detection enhancements.
    
    All flags default to False if not set in environment.
    """
    
    # Phase 1: Foundation & Infrastructure
    PYOD_ENABLED = os.getenv('FEATURE_FLAG_PYOD', 'false').lower() == 'true'
    MODEL_CACHE_ENABLED = os.getenv('FEATURE_FLAG_MODEL_CACHE', 'true').lower() == 'true'
    BATCH_REPROCESSING_ENABLED = os.getenv('FEATURE_FLAG_BATCH_REPROCESSING', 'true').lower() == 'true'
    
    # Phase 2: Active Learning
    ACTIVE_LEARNING_ENABLED = os.getenv('FEATURE_FLAG_ACTIVE_LEARNING', 'false').lower() == 'true'
    AUTO_SUPPRESSION_ENABLED = os.getenv('FEATURE_FLAG_AUTO_SUPPRESSION', 'false').lower() == 'true'
    
    # Phase 3: Explainability
    SHAP_ENABLED = os.getenv('FEATURE_FLAG_SHAP', 'false').lower() == 'true'
    LIME_ENABLED = os.getenv('FEATURE_FLAG_LIME', 'false').lower() == 'true'
    
    # Phase 4: Cross-Property Intelligence
    PORTFOLIO_BENCHMARKS_ENABLED = os.getenv('FEATURE_FLAG_PORTFOLIO_BENCHMARKS', 'false').lower() == 'true'
    
    # Phase 5: ML Coordinate Prediction
    LAYOUTLM_ENABLED = os.getenv('FEATURE_FLAG_LAYOUTLM', 'false').lower() == 'true'
    
    # Phase 6: Model Optimization
    INCREMENTAL_LEARNING_ENABLED = os.getenv('FEATURE_FLAG_INCREMENTAL_LEARNING', 'false').lower() == 'true'
    GPU_ACCELERATION_ENABLED = os.getenv('FEATURE_FLAG_GPU', 'false').lower() == 'true'
    
    @classmethod
    def get_all_flags(cls) -> Dict[str, bool]:
        """
        Get all feature flags as a dictionary.
        
        Returns:
            Dict mapping flag names to boolean values
        """
        return {
            'PYOD_ENABLED': cls.PYOD_ENABLED,
            'MODEL_CACHE_ENABLED': cls.MODEL_CACHE_ENABLED,
            'BATCH_REPROCESSING_ENABLED': cls.BATCH_REPROCESSING_ENABLED,
            'ACTIVE_LEARNING_ENABLED': cls.ACTIVE_LEARNING_ENABLED,
            'AUTO_SUPPRESSION_ENABLED': cls.AUTO_SUPPRESSION_ENABLED,
            'SHAP_ENABLED': cls.SHAP_ENABLED,
            'LIME_ENABLED': cls.LIME_ENABLED,
            'PORTFOLIO_BENCHMARKS_ENABLED': cls.PORTFOLIO_BENCHMARKS_ENABLED,
            'LAYOUTLM_ENABLED': cls.LAYOUTLM_ENABLED,
            'INCREMENTAL_LEARNING_ENABLED': cls.INCREMENTAL_LEARNING_ENABLED,
            'GPU_ACCELERATION_ENABLED': cls.GPU_ACCELERATION_ENABLED,
        }
    
    @classmethod
    def is_enabled(cls, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_name: Name of the feature flag (e.g., 'PYOD_ENABLED')
        
        Returns:
            True if enabled, False otherwise
        """
        return getattr(cls, flag_name, False)
    
    @classmethod
    def log_status(cls):
        """Log current feature flag status."""
        flags = cls.get_all_flags()
        enabled = [name for name, value in flags.items() if value]
        disabled = [name for name, value in flags.items() if not value]
        
        logger.info(f"Feature flags - Enabled: {len(enabled)}, Disabled: {len(disabled)}")
        if enabled:
            logger.info(f"  Enabled: {', '.join(enabled)}")
        if disabled:
            logger.debug(f"  Disabled: {', '.join(disabled)}")


# Create singleton instance
feature_flags = FeatureFlags()

# Log status on import
feature_flags.log_status()

