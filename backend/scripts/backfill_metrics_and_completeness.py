"""
Backfill financial_metrics and period_document_completeness.

Usage:
  python /app/scripts/backfill_metrics_and_completeness.py --property-code ESP001 --year 2023 --yes
  python /app/scripts/backfill_metrics_and_completeness.py --all --yes
  python /app/scripts/backfill_metrics_and_completeness.py --dry-run --all
"""
import sys
from pathlib import Path
import argparse
import logging

from sqlalchemy.orm import Session

# Add project root to path (scripts are in /app/scripts, app is in /app)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import SessionLocal
from app.core.redis_client import invalidate_portfolio_cache
from app.models.document_upload import DocumentUpload
from app.models.financial_period import FinancialPeriod
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.period_document_completeness import PeriodDocumentCompleteness
from app.models.property import Property
from app.services.metrics_service import MetricsService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def resolve_property_ids(db: Session, property_id: int | None, property_code: str | None, all_properties: bool) -> list[int]:
    if all_properties:
        props = db.query(Property).all()
        return [p.id for p in props]

    if property_id:
        return [property_id]

    if property_code:
        prop = db.query(Property).filter(Property.property_code == property_code).first()
        if not prop:
            raise ValueError(f"Property code not found: {property_code}")
        return [prop.id]

    raise ValueError("Provide --property-id, --property-code, or --all")


def get_periods(db: Session, property_id: int, year: int | None) -> list[FinancialPeriod]:
    query = db.query(FinancialPeriod).filter(FinancialPeriod.property_id == property_id)
    if year:
        query = query.filter(FinancialPeriod.period_year == year)
    return query.order_by(FinancialPeriod.period_year, FinancialPeriod.period_month).all()


def get_completed_upload_types(db: Session, property_id: int, period_id: int) -> set[str]:
    uploads = db.query(DocumentUpload.document_type).filter(
        DocumentUpload.property_id == property_id,
        DocumentUpload.period_id == period_id,
        DocumentUpload.extraction_status == "completed"
    ).all()
    return {row[0] for row in uploads}


def has_mortgage_data(db: Session, property_id: int, period_id: int) -> bool:
    return db.query(MortgageStatementData.id).filter(
        MortgageStatementData.property_id == property_id,
        MortgageStatementData.period_id == period_id
    ).first() is not None


def upsert_completeness(
    db: Session,
    property_id: int,
    period_id: int,
    upload_types: set[str],
    mortgage_present: bool
) -> PeriodDocumentCompleteness:
    completeness = db.query(PeriodDocumentCompleteness).filter(
        PeriodDocumentCompleteness.property_id == property_id,
        PeriodDocumentCompleteness.period_id == period_id
    ).first()

    if not completeness:
        completeness = PeriodDocumentCompleteness(
            property_id=property_id,
            period_id=period_id
        )
        db.add(completeness)

    completeness.has_balance_sheet = "balance_sheet" in upload_types
    completeness.has_income_statement = "income_statement" in upload_types
    completeness.has_cash_flow = "cash_flow" in upload_types
    completeness.has_rent_roll = "rent_roll" in upload_types
    completeness.has_mortgage_statement = mortgage_present or ("mortgage_statement" in upload_types)
    completeness.update_completeness()
    return completeness


def backfill(
    db: Session,
    property_ids: list[int],
    year: int | None,
    dry_run: bool,
    recalc_metrics: bool
) -> dict:
    metrics_service = MetricsService(db)
    totals = {
        "periods_seen": 0,
        "periods_skipped": 0,
        "completeness_updated": 0,
        "metrics_recalculated": 0,
        "errors": []
    }

    for prop_id in property_ids:
        periods = get_periods(db, prop_id, year)
        for period in periods:
            totals["periods_seen"] += 1

            upload_types = get_completed_upload_types(db, prop_id, period.id)
            mortgage_present = has_mortgage_data(db, prop_id, period.id)

            if not upload_types and not mortgage_present:
                totals["periods_skipped"] += 1
                continue

            period_label = f"{period.period_year}-{period.period_month:02d}"
            try:
                if dry_run:
                    logger.info(
                        "[DRY RUN] property_id=%s period=%s uploads=%s mortgage=%s",
                        prop_id,
                        period_label,
                        sorted(upload_types),
                        mortgage_present
                    )
                    totals["completeness_updated"] += 1
                    if recalc_metrics:
                        totals["metrics_recalculated"] += 1
                    continue

                upsert_completeness(db, prop_id, period.id, upload_types, mortgage_present)
                totals["completeness_updated"] += 1

                if recalc_metrics:
                    metrics_service.calculate_all_metrics(prop_id, period.id)
                    totals["metrics_recalculated"] += 1
                else:
                    db.commit()

            except Exception as exc:
                db.rollback()
                error_msg = f"property_id={prop_id} period={period_label} error={exc}"
                logger.error(error_msg, exc_info=True)
                totals["errors"].append(error_msg)

    if not dry_run:
        invalidate_portfolio_cache()

    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill metrics and completeness")
    parser.add_argument("--property-id", type=int, help="Target a specific property ID")
    parser.add_argument("--property-code", type=str, help="Target a specific property code")
    parser.add_argument("--year", type=int, help="Limit to a specific year (e.g., 2023)")
    parser.add_argument("--all", action="store_true", help="Process all properties")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without changes")
    parser.add_argument("--skip-metrics", action="store_true", help="Only rebuild completeness flags")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    db = SessionLocal()
    try:
        property_ids = resolve_property_ids(db, args.property_id, args.property_code, args.all)

        logger.info("Preparing backfill for %s properties", len(property_ids))
        if args.year:
            logger.info("Year filter: %s", args.year)

        if args.dry_run:
            logger.info("DRY RUN mode - no changes will be made")
        elif not args.yes:
            response = input("This will update completeness and metrics. Continue? (yes/no): ")
            if response.strip().lower() != "yes":
                logger.info("Aborted.")
                return

        result = backfill(
            db,
            property_ids=property_ids,
            year=args.year,
            dry_run=args.dry_run,
            recalc_metrics=not args.skip_metrics
        )

        logger.info(
            "Done. Periods seen=%s skipped=%s completeness_updated=%s metrics_recalculated=%s errors=%s",
            result["periods_seen"],
            result["periods_skipped"],
            result["completeness_updated"],
            result["metrics_recalculated"],
            len(result["errors"])
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
