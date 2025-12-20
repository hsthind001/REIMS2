"""
Application Constants and Configuration

Centralizes all hardcoded values, thresholds, and configuration
to improve maintainability and allow runtime configuration.
"""

from decimal import Decimal
from typing import Dict, List
from pydantic import Field
from pydantic_settings import BaseSettings


class FinancialThresholds(BaseSettings):
    """Financial calculation thresholds and tolerances"""

    # NOI Calculation Thresholds
    noi_large_negative_adjustment_threshold: Decimal = Field(
        default=Decimal("10000"),
        description="Threshold for large negative adjustments in NOI calculation (absolute value)"
    )
    noi_large_negative_adjustment_percentage: Decimal = Field(
        default=Decimal("0.10"),
        description="Percentage threshold for large negative adjustments (10% of gross revenue)"
    )

    # Variance Analysis Thresholds
    variance_warning_threshold_pct: Decimal = Field(
        default=Decimal("10.0"),
        description="Variance percentage threshold for WARNING severity"
    )
    variance_critical_threshold_pct: Decimal = Field(
        default=Decimal("25.0"),
        description="Variance percentage threshold for CRITICAL severity"
    )
    variance_urgent_threshold_pct: Decimal = Field(
        default=Decimal("50.0"),
        description="Variance percentage threshold for URGENT severity"
    )

    # Budget Tolerances
    default_budget_tolerance_pct: Decimal = Field(
        default=Decimal("10.0"),
        description="Default budget tolerance percentage if not specified"
    )
    default_forecast_tolerance_pct: Decimal = Field(
        default=Decimal("15.0"),
        description="Default forecast tolerance percentage (more lenient than budget)"
    )

    # Debt Service Coverage Ratio (DSCR) Thresholds
    dscr_warning_threshold: Decimal = Field(
        default=Decimal("1.25"),
        description="DSCR below this triggers a warning alert"
    )
    dscr_critical_threshold: Decimal = Field(
        default=Decimal("1.10"),
        description="DSCR below this triggers a critical alert"
    )

    # Occupancy Thresholds
    occupancy_warning_threshold: Decimal = Field(
        default=Decimal("90.0"),
        description="Occupancy percentage below this triggers a warning"
    )
    occupancy_critical_threshold: Decimal = Field(
        default=Decimal("80.0"),
        description="Occupancy percentage below this triggers a critical alert"
    )

    # Liquidity Thresholds
    current_ratio_minimum: Decimal = Field(
        default=Decimal("1.5"),
        description="Minimum current ratio for healthy liquidity"
    )
    quick_ratio_minimum: Decimal = Field(
        default=Decimal("1.0"),
        description="Minimum quick ratio for healthy liquidity"
    )

    class Config:
        env_prefix = "REIMS_THRESHOLD_"
        case_sensitive = False


class ExtractionConstants(BaseSettings):
    """Document extraction and OCR constants"""

    # Confidence Thresholds
    extraction_confidence_threshold: Decimal = Field(
        default=Decimal("85.0"),
        description="Minimum extraction confidence to auto-approve (0-100)"
    )
    match_confidence_threshold: Decimal = Field(
        default=Decimal("80.0"),
        description="Minimum account matching confidence to auto-approve (0-100)"
    )

    # Review Queue Thresholds
    needs_review_confidence_threshold: Decimal = Field(
        default=Decimal("70.0"),
        description="Below this confidence, send to review queue"
    )

    # OCR Settings
    ocr_language: str = Field(
        default="eng",
        description="OCR language (eng, fra, deu, etc.)"
    )
    ocr_dpi: int = Field(
        default=300,
        description="DPI for OCR processing"
    )

    # PDF Processing
    pdf_table_extraction_method: str = Field(
        default="lattice",
        description="Camelot table extraction method (lattice or stream)"
    )

    class Config:
        env_prefix = "REIMS_EXTRACTION_"
        case_sensitive = False


class AccountCodeConstants:
    """Account code ranges and classifications"""

    # Account Code Ranges
    REVENUE_CODES = ["4"]  # 4xxxx
    OPERATING_EXPENSE_CODES = ["5"]  # 5xxxx
    ADDITIONAL_EXPENSE_CODES = ["6"]  # 6xxxx
    MORTGAGE_INTEREST_CODES = ["7"]  # 7xxxx
    DEPRECIATION_CODES = ["8"]  # 8xxxx

    # Special Unit Types (excluded from occupancy calculations)
    SPECIAL_UNIT_TYPES = [
        "COMMON",  # Common areas
        "ATM",     # ATM spaces
        "LAND",    # Land parcels
        "SIGN",    # Signage spaces
        "STORAGE", # Storage units (non-leasable)
        "MECH",    # Mechanical rooms
        "ELEC",    # Electrical rooms
    ]

    # Account Categories
    INCOME_CATEGORIES = [
        "Base Rentals",
        "Recovery Income",
        "Other Income",
        "Parking Income",
    ]

    OPERATING_EXPENSE_CATEGORIES = [
        "Utility Expense",
        "Contracted Services",
        "Repairs & Maintenance",
        "Administrative",
        "Other Operating Expenses",
    ]

    ADDITIONAL_EXPENSE_CATEGORIES = [
        "Management Fee",
        "Leasing Fee",
        "Landlord Expenses",
    ]

    # Below-the-Line Categories
    BELOW_THE_LINE_CATEGORIES = [
        "Mortgage Interest",
        "Depreciation",
        "Amortization",
    ]

    @classmethod
    def is_revenue_account(cls, account_code: str) -> bool:
        """Check if account code is a revenue account"""
        return any(account_code.startswith(prefix) for prefix in cls.REVENUE_CODES)

    @classmethod
    def is_operating_expense(cls, account_code: str) -> bool:
        """Check if account code is an operating expense (5xxx or 6xxx)"""
        return any(account_code.startswith(prefix)
                  for prefix in cls.OPERATING_EXPENSE_CODES + cls.ADDITIONAL_EXPENSE_CODES)

    @classmethod
    def is_below_the_line(cls, account_code: str) -> bool:
        """Check if account code is below-the-line (7xxx or 8xxx)"""
        return any(account_code.startswith(prefix)
                  for prefix in cls.MORTGAGE_INTEREST_CODES + cls.DEPRECIATION_CODES)

    @classmethod
    def is_special_unit_type(cls, unit_number: str) -> bool:
        """Check if unit is a special type (excluded from occupancy)"""
        if not unit_number:
            return False
        unit_upper = str(unit_number).upper()
        return any(special_type in unit_upper for special_type in cls.SPECIAL_UNIT_TYPES)


class AlertConstants(BaseSettings):
    """Risk alert configuration"""

    # Alert Frequencies
    alert_check_frequency_minutes: int = Field(
        default=60,
        description="How often to check for new alerts (in minutes)"
    )

    # Email Settings
    alert_email_enabled: bool = Field(
        default=True,
        description="Enable email notifications for alerts"
    )
    alert_email_batch_minutes: int = Field(
        default=30,
        description="Batch alerts and send email every N minutes"
    )

    # Alert Retention
    alert_history_retention_days: int = Field(
        default=365,
        description="How long to keep alert history (in days)"
    )

    # Auto-Resolution
    alert_auto_resolve_enabled: bool = Field(
        default=True,
        description="Automatically resolve alerts when condition clears"
    )

    class Config:
        env_prefix = "REIMS_ALERT_"
        case_sensitive = False


class PaginationConstants(BaseSettings):
    """API pagination defaults"""

    default_page_size: int = Field(
        default=50,
        description="Default number of items per page"
    )
    max_page_size: int = Field(
        default=1000,
        description="Maximum allowed page size"
    )

    class Config:
        env_prefix = "REIMS_PAGINATION_"
        case_sensitive = False


class CacheConstants(BaseSettings):
    """Caching configuration"""

    # Cache TTLs (in seconds)
    metrics_cache_ttl: int = Field(
        default=300,  # 5 minutes
        description="Cache TTL for financial metrics"
    )
    property_cache_ttl: int = Field(
        default=3600,  # 1 hour
        description="Cache TTL for property data"
    )
    user_cache_ttl: int = Field(
        default=900,  # 15 minutes
        description="Cache TTL for user data"
    )

    # Semantic Cache
    semantic_cache_similarity_threshold: float = Field(
        default=0.95,
        description="Similarity threshold for semantic cache hits (0-1)"
    )

    class Config:
        env_prefix = "REIMS_CACHE_"
        case_sensitive = False


# Singleton instances
financial_thresholds = FinancialThresholds()
extraction_constants = ExtractionConstants()
account_codes = AccountCodeConstants()
alert_constants = AlertConstants()
pagination_constants = PaginationConstants()
cache_constants = CacheConstants()


# Export all constants
__all__ = [
    'FinancialThresholds',
    'ExtractionConstants',
    'AccountCodeConstants',
    'AlertConstants',
    'PaginationConstants',
    'CacheConstants',
    'financial_thresholds',
    'extraction_constants',
    'account_codes',
    'alert_constants',
    'pagination_constants',
    'cache_constants',
]
