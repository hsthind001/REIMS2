"""
Recalculate Cash Flow Metrics Script

This script recalculates cash flow metrics for periods that have cash flow data
but missing or NULL values in the financial_metrics table.

Usage:
    python -m backend.scripts.recalculate_cash_flow_metrics [--dry-run] [--property-id PROPERTY_ID] [--period-id PERIOD_ID]
"""
import sys
import os
from pathlib import Path

# Add project root to path (scripts are in /app/scripts, app is in /app)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime
import argparse
import logging

from app.db.database import SessionLocal
from app.models.cash_flow_data import CashFlowData
from app.models.financial_metrics import FinancialMetrics
from app.models.financial_period import FinancialPeriod
from app.models.property import Property
from app.services.metrics_service import MetricsService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_periods_needing_recalculation(db: Session, property_id: int = None, period_id: int = None):
    """
    Find periods with cash flow data but NULL or missing metrics
    """
    # Query for periods with cash flow data
    query = db.query(
        FinancialPeriod.property_id,
        FinancialPeriod.id.label('period_id'),
        FinancialPeriod.period_year,
        FinancialPeriod.period_month,
        func.count(CashFlowData.id).label('cf_record_count')
    ).join(
        CashFlowData, 
        and_(
            CashFlowData.property_id == FinancialPeriod.property_id,
            CashFlowData.period_id == FinancialPeriod.id
        )
    ).group_by(
        FinancialPeriod.property_id,
        FinancialPeriod.id,
        FinancialPeriod.period_year,
        FinancialPeriod.period_month
    )
    
    if property_id:
        query = query.filter(FinancialPeriod.property_id == property_id)
    
    if period_id:
        query = query.filter(FinancialPeriod.id == period_id)
    
    periods_with_cf = query.all()
    
    # Filter to only those with NULL metrics
    periods_needing_recalc = []
    for prop_id, period_id_val, year, month, cf_count in periods_with_cf:
        # Check if metrics exist and have NULL cash flow values
        metrics = db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == prop_id,
            FinancialMetrics.period_id == period_id_val
        ).first()
        
        # Need recalculation if:
        # 1. No metrics record exists, OR
        # 2. Metrics exist but cash flow fields are NULL
        needs_recalc = False
        if not metrics:
            needs_recalc = True
        elif (metrics.operating_cash_flow is None and 
              metrics.investing_cash_flow is None and 
              metrics.financing_cash_flow is None and 
              metrics.net_cash_flow is None):
            needs_recalc = True
        
        if needs_recalc:
            property_obj = db.query(Property).filter(Property.id == prop_id).first()
            periods_needing_recalc.append({
                "property_id": prop_id,
                "property_name": property_obj.property_name if property_obj else "Unknown",
                "property_code": property_obj.property_code if property_obj else "Unknown",
                "period_id": period_id_val,
                "period_year": year,
                "period_month": month,
                "cf_record_count": cf_count
            })
    
    return periods_needing_recalc


def recalculate_metrics(db: Session, periods: list, dry_run: bool = True):
    """
    Recalculate metrics for the given periods
    """
    metrics_service = MetricsService(db)
    total_processed = 0
    total_updated = 0
    errors = []
    
    for period_info in periods:
        property_id = period_info["property_id"]
        period_id = period_info["period_id"]
        property_name = period_info["property_name"]
        period_str = f"{period_info['period_year']}-{period_info['period_month']:02d}"
        
        try:
            logger.info(
                f"Processing: {property_name} ({period_info['property_code']}), "
                f"Period: {period_str}, "
                f"Cash Flow Records: {period_info['cf_record_count']}"
            )
            
            if dry_run:
                logger.info(f"  [DRY RUN] Would recalculate metrics for period {period_id}")
            else:
                # Recalculate all metrics (including cash flow)
                metrics = metrics_service.calculate_all_metrics(property_id, period_id)
                
                # Verify cash flow metrics were calculated
                if metrics.operating_cash_flow is not None or metrics.investing_cash_flow is not None:
                    total_updated += 1
                    logger.info(
                        f"  ✅ Updated metrics: "
                        f"Operating={metrics.operating_cash_flow}, "
                        f"Investing={metrics.investing_cash_flow}, "
                        f"Financing={metrics.financing_cash_flow}, "
                        f"Net={metrics.net_cash_flow}"
                    )
                else:
                    logger.warning(f"  ⚠️  Metrics calculated but cash flow values still NULL")
            
            total_processed += 1
            
        except Exception as e:
            error_msg = f"Error processing {property_name} period {period_str}: {str(e)}"
            logger.error(f"  ❌ {error_msg}")
            errors.append(error_msg)
            if not dry_run:
                db.rollback()
    
    if not dry_run:
        db.commit()
    
    return {
        "total_processed": total_processed,
        "total_updated": total_updated,
        "errors": errors,
        "dry_run": dry_run
    }


def main():
    parser = argparse.ArgumentParser(description="Recalculate cash flow metrics")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--property-id",
        type=int,
        help="Limit recalculation to specific property ID"
    )
    parser.add_argument(
        "--period-id",
        type=int,
        help="Limit recalculation to specific period ID"
    )
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        logger.info("🔍 Searching for periods with cash flow data but missing metrics...")
        periods = find_periods_needing_recalculation(db, property_id=args.property_id, period_id=args.period_id)
        
        if not periods:
            logger.info("✅ No periods need recalculation!")
            return
        
        logger.info(f"📊 Found {len(periods)} periods needing recalculation:")
        for period in periods:
            period_str = f"{period['period_year']}-{period['period_month']:02d}"
            logger.info(
                f"  - {period['property_name']} ({period['property_code']}): "
                f"Period {period_str}, {period['cf_record_count']} cash flow records"
            )
        
        if args.dry_run:
            logger.info("\n🔍 DRY RUN MODE - No changes will be made\n")
        else:
            logger.info("\n⚠️  LIVE MODE - Changes will be committed to database\n")
            response = input("Continue? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Aborted.")
                return
        
        result = recalculate_metrics(db, periods, dry_run=args.dry_run)
        
        if args.dry_run:
            logger.info(f"\n✅ DRY RUN complete. Would process {result['total_processed']} periods")
        else:
            logger.info(f"\n✅ Recalculation complete. Processed {result['total_processed']} periods, updated {result['total_updated']} metrics")
            if result['errors']:
                logger.warning(f"⚠️  {len(result['errors'])} errors occurred:")
                for error in result['errors']:
                    logger.warning(f"  - {error}")
            
    except Exception as e:
        logger.error(f"❌ Error during recalculation: {str(e)}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

