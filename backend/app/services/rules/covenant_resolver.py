"""
Resolves covenant thresholds: per-property covenant_thresholds table first, then system_config fallback.
Used by AuditRulesMixin, AnalyticsRulesMixin, and CovenantComplianceService (async variant).
"""
import calendar
from datetime import date
from typing import Optional

from sqlalchemy import text, select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CovenantThreshold, SystemConfig


def get_period_end_date(db: Session, period_id: int) -> Optional[date]:
    """Return the last day of the given financial period (year/month)."""
    row = db.execute(
        text(
            "SELECT period_year, period_month FROM financial_periods WHERE id = :period_id"
        ),
        {"period_id": int(period_id)},
    ).fetchone()
    if not row:
        return None
    year, month = int(row[0]), int(row[1])
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def get_covenant_threshold_sync(
    db: Session,
    property_id: int,
    period_id: int,
    covenant_type: str,
) -> Optional[float]:
    """
    Return the effective covenant threshold for this property/period from covenant_thresholds, or None.

    covenant_type: e.g. 'DSCR', 'LTV', 'MIN_LIQUIDITY', 'OCCUPANCY', 'SINGLE_TENANT_MAX'
    """
    period_end = get_period_end_date(db, period_id)
    if not period_end:
        return None
    row = (
        db.query(CovenantThreshold.threshold_value)
        .filter(
            CovenantThreshold.property_id == int(property_id),
            CovenantThreshold.covenant_type == covenant_type,
            CovenantThreshold.is_active.is_(True),
            CovenantThreshold.effective_date <= period_end,
            (CovenantThreshold.expiration_date.is_(None)) | (CovenantThreshold.expiration_date >= period_end),
        )
        .order_by(CovenantThreshold.effective_date.desc())
        .limit(1)
        .first()
    )
    if row is None:
        return None
    return float(row[0])


def get_numeric_config_sync(db: Session, key: str, default: float) -> float:
    """Read a numeric value from system_config. Returns default if missing or unparsable."""
    try:
        row = (
            db.query(SystemConfig.config_value)
            .filter(SystemConfig.config_key == key)
            .limit(1)
            .first()
        )
        if row is None:
            return float(default)
        return float(str(row[0]))
    except Exception:
        return float(default)


# Map covenant_type to system_config key for fallback
COVENANT_TYPE_TO_CONFIG_KEY = {
    "DSCR": "covenant_dscr_minimum",
    "LTV": "covenant_ltv_maximum",
    "MIN_LIQUIDITY": "covenant_liquidity_months",
    "OCCUPANCY": "covenant_occupancy_minimum",
    "SINGLE_TENANT_MAX": "covenant_single_tenant_maximum",
}

COVENANT_CONFIG_DEFAULTS = {
    "DSCR": 1.25,
    "LTV": 75.0,
    "MIN_LIQUIDITY": 3.0,
    "OCCUPANCY": 85.0,
    "SINGLE_TENANT_MAX": 20.0,
}


async def get_period_end_date_async(db: AsyncSession, period_id: int) -> Optional[date]:
    """Return the last day of the given financial period (async)."""
    result = await db.execute(
        text("SELECT period_year, period_month FROM financial_periods WHERE id = :period_id"),
        {"period_id": int(period_id)},
    )
    row = result.fetchone()
    if not row:
        return None
    year, month = int(row[0]), int(row[1])
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


async def get_covenant_threshold_async(
    db: AsyncSession,
    property_id: int,
    period_id: int,
    covenant_type: str,
) -> Optional[float]:
    """Return the effective covenant threshold from covenant_thresholds (async), or None."""
    period_end = await get_period_end_date_async(db, period_id)
    if not period_end:
        return None
    result = await db.execute(
        select(CovenantThreshold.threshold_value)
        .where(
            CovenantThreshold.property_id == int(property_id),
            CovenantThreshold.covenant_type == covenant_type,
            CovenantThreshold.is_active.is_(True),
            CovenantThreshold.effective_date <= period_end,
            (CovenantThreshold.expiration_date.is_(None)) | (CovenantThreshold.expiration_date >= period_end),
        )
        .order_by(CovenantThreshold.effective_date.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return float(row)


async def resolve_covenant_threshold_async(
    db: AsyncSession,
    property_id: int,
    period_id: int,
    covenant_type: str,
) -> float:
    """
    Resolve covenant threshold (async): covenant_thresholds first, else system_config, else default.
    For LTV, stored value is percent; returns ratio for comparison.
    """
    val = await get_covenant_threshold_async(db, property_id, period_id, covenant_type)
    if val is None:
        key = COVENANT_TYPE_TO_CONFIG_KEY.get(covenant_type)
        default = COVENANT_CONFIG_DEFAULTS.get(covenant_type, 0.0)
        result = await db.execute(
            select(SystemConfig.config_value).where(SystemConfig.config_key == key).limit(1)
        )
        row = result.scalar_one_or_none()
        val = float(str(row)) if row is not None else default
    if covenant_type == "LTV" and val > 1.0:
        val = val / 100.0
    return float(val)


def resolve_covenant_threshold_sync(
    db: Session,
    property_id: int,
    period_id: int,
    covenant_type: str,
) -> float:
    """
    Resolve covenant threshold: covenant_thresholds (per-property) first, else system_config, else default.

    For LTV, stored value is percent (e.g. 75); returns ratio (0.75) for comparison with ltv_ratio.
    """
    val = get_covenant_threshold_sync(db, property_id, period_id, covenant_type)
    if val is None:
        key = COVENANT_TYPE_TO_CONFIG_KEY.get(covenant_type)
        default = COVENANT_CONFIG_DEFAULTS.get(covenant_type, 0.0)
        val = get_numeric_config_sync(db, key, default) if key else default
    if covenant_type == "LTV" and val > 1.0:
        val = val / 100.0
    return float(val)
