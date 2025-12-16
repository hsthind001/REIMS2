"""
Hallucination Detection Configuration

Configuration for detecting and verifying numeric claims in LLM-generated answers.
"""
import os
from typing import Dict, Any


class HallucinationConfig:
    """
    Configuration for hallucination detection
    
    All parameters are configurable and can be overridden via environment variables.
    """
    
    # Tolerance Settings
    CURRENCY_TOLERANCE_PERCENT: float = float(os.getenv('HALLUCINATION_CURRENCY_TOLERANCE', '5.0'))  # ±5%
    PERCENTAGE_TOLERANCE_PERCENT: float = float(os.getenv('HALLUCINATION_PERCENTAGE_TOLERANCE', '2.0'))  # ±2%
    RATIO_TOLERANCE_PERCENT: float = float(os.getenv('HALLUCINATION_RATIO_TOLERANCE', '5.0'))  # ±5%
    DATE_TOLERANCE_DAYS: int = int(os.getenv('HALLUCINATION_DATE_TOLERANCE_DAYS', '0'))  # Exact match for dates
    
    # Confidence Penalty
    CONFIDENCE_PENALTY_PERCENT: float = float(os.getenv('HALLUCINATION_CONFIDENCE_PENALTY', '20.0'))  # -20%
    
    # Performance Targets
    TARGET_VERIFICATION_TIME_MS: int = int(os.getenv('HALLUCINATION_TARGET_TIME_MS', '100'))  # <100ms
    TARGET_HALLUCINATION_RATE: float = float(os.getenv('HALLUCINATION_TARGET_RATE', '0.05'))  # <5%
    
    # Verification Settings
    VERIFY_CURRENCY: bool = os.getenv('HALLUCINATION_VERIFY_CURRENCY', 'true').lower() == 'true'
    VERIFY_PERCENTAGES: bool = os.getenv('HALLUCINATION_VERIFY_PERCENTAGES', 'true').lower() == 'true'
    VERIFY_DATES: bool = os.getenv('HALLUCINATION_VERIFY_DATES', 'true').lower() == 'true'
    VERIFY_RATIOS: bool = os.getenv('HALLUCINATION_VERIFY_RATIOS', 'true').lower() == 'true'
    
    # Data Sources
    VERIFY_AGAINST_DATABASE: bool = os.getenv('HALLUCINATION_VERIFY_DB', 'true').lower() == 'true'
    VERIFY_AGAINST_DOCUMENTS: bool = os.getenv('HALLUCINATION_VERIFY_DOCS', 'true').lower() == 'true'
    MAX_SOURCE_CHECKS: int = int(os.getenv('HALLUCINATION_MAX_SOURCE_CHECKS', '10'))  # Max sources to check per claim
    
    # Review Queue
    AUTO_FLAG_UNVERIFIED: bool = os.getenv('HALLUCINATION_AUTO_FLAG', 'true').lower() == 'true'
    REVIEW_QUEUE_ENABLED: bool = os.getenv('HALLUCINATION_REVIEW_QUEUE', 'true').lower() == 'true'
    
    # Logging
    LOG_UNVERIFIED_CLAIMS: bool = os.getenv('HALLUCINATION_LOG_CLAIMS', 'true').lower() == 'true'
    LOG_VERIFIED_CLAIMS: bool = os.getenv('HALLUCINATION_LOG_VERIFIED', 'false').lower() == 'true'
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'currency_tolerance_percent': cls.CURRENCY_TOLERANCE_PERCENT,
            'percentage_tolerance_percent': cls.PERCENTAGE_TOLERANCE_PERCENT,
            'ratio_tolerance_percent': cls.RATIO_TOLERANCE_PERCENT,
            'date_tolerance_days': cls.DATE_TOLERANCE_DAYS,
            'confidence_penalty_percent': cls.CONFIDENCE_PENALTY_PERCENT,
            'target_verification_time_ms': cls.TARGET_VERIFICATION_TIME_MS,
            'target_hallucination_rate': cls.TARGET_HALLUCINATION_RATE,
            'verify_currency': cls.VERIFY_CURRENCY,
            'verify_percentages': cls.VERIFY_PERCENTAGES,
            'verify_dates': cls.VERIFY_DATES,
            'verify_ratios': cls.VERIFY_RATIOS,
            'auto_flag_unverified': cls.AUTO_FLAG_UNVERIFIED,
            'review_queue_enabled': cls.REVIEW_QUEUE_ENABLED
        }


# Global configuration instance
hallucination_config = HallucinationConfig()

