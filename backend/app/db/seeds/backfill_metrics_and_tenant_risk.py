"""
Utility to backfill financial_metrics and tenant_risk_analysis for all property/periods.

Safe to re-run; uses upserts where possible.
"""
from datetime import date
from decimal import Decimal
from typing import List, Tuple

from sqlalchemy import text

import importlib.util
import os

from app.db.database import SessionLocal
from app.models.property import Property
from app.models.financial_period import FinancialPeriod


def _load_metrics_service():
    """Load MetricsService without importing heavy app.services package."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    path = os.path.join(base_dir, "services", "metrics_service.py")
    spec = importlib.util.spec_from_file_location("metrics_service", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module.MetricsService


def _calc_months_diff(base_year: int, base_month: int, target_date) -> int:
    """Months between period start (base_year/base_month) and target_date."""
    if not target_date:
        return 10_000
    return (target_date.year - base_year) * 12 + (target_date.month - base_month)


def _compute_tenant_risk_for_period(db, property_id: int, period: FinancialPeriod) -> None:
    """Compute tenant risk aggregates and upsert into tenant_risk_analysis."""
    rows = db.execute(
        text(
            """
            SELECT monthly_rent, annual_rent, unit_area_sqft, lease_end_date, occupancy_status, lease_status
            FROM rent_roll_data
            WHERE property_id = :property_id AND period_id = :period_id
            """
        ),
        {"property_id": property_id, "period_id": period.id},
    ).fetchall()

    if not rows:
        return

    # Occupancy and rent aggregates
    total_units = len(rows)
    occupied_units = sum(
        1
        for r in rows
        if (r.occupancy_status or "").lower() == "occupied"
        or (r.lease_status or "").lower() == "active"
    )
    occupancy_rate = (
        (Decimal(str(occupied_units)) / Decimal(str(total_units))) * Decimal("100")
        if total_units > 0
        else Decimal("0")
    )

    tenant_rents: List[Tuple[Decimal, any]] = []
    total_rent = Decimal("0")
    for r in rows:
        monthly = Decimal(str(r.monthly_rent or 0))
        annual = Decimal(str(r.annual_rent)) if r.annual_rent is not None else monthly * Decimal("12")
        tenant_rents.append((annual, r.lease_end_date))
        total_rent += annual

    tenant_rents.sort(key=lambda x: x[0], reverse=True)

    def _pct_top(n: int) -> Decimal:
        if total_rent == 0 or not tenant_rents:
            return Decimal("0")
        return sum(val for val, _ in tenant_rents[:n]) / total_rent * Decimal("100")

    top1 = _pct_top(1)
    top3 = _pct_top(3)
    top5 = _pct_top(5)
    top10 = _pct_top(10)

    # Lease rollover using period start
    base_year = period.period_year
    base_month = period.period_month
    rollover_12 = Decimal("0")
    rollover_24 = Decimal("0")
    rollover_36 = Decimal("0")
    for annual, lease_end in tenant_rents:
        months_out = _calc_months_diff(base_year, base_month, lease_end)
        if months_out <= 12:
            rollover_12 += annual
        if months_out <= 24:
            rollover_24 += annual
        if months_out <= 36:
            rollover_36 += annual

    def _pct(part: Decimal) -> Decimal:
        return (part / total_rent * Decimal("100")) if total_rent > 0 else Decimal("0")

    data = {
        "property_id": property_id,
        "period_id": period.id,
        "top_1_tenant_pct": top1,
        "top_3_tenant_pct": top3,
        "top_5_tenant_pct": top5,
        "top_10_tenant_pct": top10,
        "lease_rollover_12mo_pct": _pct(rollover_12),
        "lease_rollover_24mo_pct": _pct(rollover_24),
        "lease_rollover_36mo_pct": _pct(rollover_36),
        "occupancy_rate": occupancy_rate,
    }

    db.execute(
        text(
            """
            INSERT INTO tenant_risk_analysis (
                property_id, period_id,
                top_1_tenant_pct, top_3_tenant_pct, top_5_tenant_pct, top_10_tenant_pct,
                lease_rollover_12mo_pct, lease_rollover_24mo_pct, lease_rollover_36mo_pct,
                occupancy_rate, updated_at
            ) VALUES (
                :property_id, :period_id,
                :top_1_tenant_pct, :top_3_tenant_pct, :top_5_tenant_pct, :top_10_tenant_pct,
                :lease_rollover_12mo_pct, :lease_rollover_24mo_pct, :lease_rollover_36mo_pct,
                :occupancy_rate, now()
            )
            ON CONFLICT (property_id, period_id) DO UPDATE SET
                top_1_tenant_pct = EXCLUDED.top_1_tenant_pct,
                top_3_tenant_pct = EXCLUDED.top_3_tenant_pct,
                top_5_tenant_pct = EXCLUDED.top_5_tenant_pct,
                top_10_tenant_pct = EXCLUDED.top_10_tenant_pct,
                lease_rollover_12mo_pct = EXCLUDED.lease_rollover_12mo_pct,
                lease_rollover_24mo_pct = EXCLUDED.lease_rollover_24mo_pct,
                lease_rollover_36mo_pct = EXCLUDED.lease_rollover_36mo_pct,
                occupancy_rate = EXCLUDED.occupancy_rate,
                updated_at = now()
            """
        ),
        data,
    )


def backfill_all_metrics_and_tenant_risk() -> None:
    """Backfill metrics and tenant risk for all properties/periods."""
    db = SessionLocal()
    try:
        MetricsService = _load_metrics_service()
        metrics_service = MetricsService(db)
        properties = db.query(Property).all()
        for prop in properties:
            periods = db.query(FinancialPeriod).filter(FinancialPeriod.property_id == prop.id).all()
            for period in periods:
                # Metrics upsert
                try:
                    metrics_service.calculate_all_metrics(property_id=prop.id, period_id=period.id)
                except Exception as exc:
                    # Continue with other periods even if one fails
                    print(f"Metrics calc failed for property {prop.id} period {period.id}: {exc}")

                # Tenant risk upsert
                try:
                    _compute_tenant_risk_for_period(db, prop.id, period)
                except Exception as exc:
                    print(f"Tenant risk calc failed for property {prop.id} period {period.id}: {exc}")
        db.commit()
        print("✓ Backfill complete for metrics and tenant risk")
    finally:
        db.close()


if __name__ == "__main__":
    backfill_all_metrics_and_tenant_risk()
