#!/usr/bin/env python3
"""
Cleanup script to remove duplicate cash flow data that violates constraints.

This script identifies and removes duplicate records that would violate
the old uq_cf_property_period_account constraint before we drop it.

Run this BEFORE applying the migration to remove the old constraint.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.cash_flow_data import CashFlowData
from sqlalchemy import func
from sqlalchemy.orm import Session


def find_duplicates(db: Session) -> list:
    """
    Find duplicate cash flow records that violate the old constraint.
    
    Returns list of (property_id, period_id, account_code, count) tuples
    where count > 1, meaning there are multiple records with the same
    property_id, period_id, and account_code.
    """
    duplicates = db.query(
        CashFlowData.property_id,
        CashFlowData.period_id,
        CashFlowData.account_code,
        func.count(CashFlowData.id).label('count')
    ).group_by(
        CashFlowData.property_id,
        CashFlowData.period_id,
        CashFlowData.account_code
    ).having(func.count(CashFlowData.id) > 1).all()
    
    return duplicates


def cleanup_duplicates(db: Session, dry_run: bool = True) -> dict:
    """
    Remove duplicate cash flow records, keeping the one with highest confidence.
    
    Args:
        db: Database session
        dry_run: If True, only report what would be deleted without actually deleting
    
    Returns:
        dict with statistics about cleanup
    """
    duplicates = find_duplicates(db)
    
    stats = {
        'duplicate_groups': len(duplicates),
        'total_duplicates': 0,
        'records_to_delete': 0,
        'records_kept': 0
    }
    
    if not duplicates:
        print("✅ No duplicate records found. Database is clean.")
        return stats
    
    print(f"⚠️  Found {len(duplicates)} groups of duplicate records")
    print("\nAnalyzing duplicates...")
    
    for prop_id, period_id, account_code, count in duplicates:
        # Get all records for this property/period/account combination
        records = db.query(CashFlowData).filter(
            CashFlowData.property_id == prop_id,
            CashFlowData.period_id == period_id,
            CashFlowData.account_code == account_code
        ).order_by(
            CashFlowData.extraction_confidence.desc().nulls_last(),
            CashFlowData.id.desc()  # Keep newest if confidence is same
        ).all()
        
        if len(records) <= 1:
            continue
        
        # Keep the first one (highest confidence/newest)
        record_to_keep = records[0]
        records_to_delete = records[1:]
        
        stats['total_duplicates'] += len(records)
        stats['records_to_delete'] += len(records_to_delete)
        stats['records_kept'] += 1
        
        if not dry_run:
            print(f"  Deleting {len(records_to_delete)} duplicate(s) for property_id={prop_id}, period_id={period_id}, account_code={account_code}")
            print(f"    Keeping record ID {record_to_keep.id} (confidence: {record_to_keep.extraction_confidence})")
            
            for record in records_to_delete:
                print(f"    Deleting record ID {record.id} (confidence: {record.extraction_confidence})")
                db.delete(record)
        else:
            print(f"  Would delete {len(records_to_delete)} duplicate(s) for property_id={prop_id}, period_id={period_id}, account_code={account_code}")
            print(f"    Would keep record ID {record_to_keep.id} (confidence: {record_to_keep.extraction_confidence})")
    
    if not dry_run:
        db.commit()
        print(f"\n✅ Cleanup complete. Deleted {stats['records_to_delete']} duplicate records.")
    else:
        print(f"\n📊 Dry run complete. Would delete {stats['records_to_delete']} duplicate records.")
        print("   Run with --execute to actually delete the records.")
    
    return stats


def main():
    """Main entry point for the cleanup script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Cleanup duplicate cash flow data before removing old constraint'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually delete duplicates (default is dry-run)'
    )
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("Cash Flow Duplicate Data Cleanup")
        print("=" * 80)
        print()
        
        if args.execute:
            print("⚠️  EXECUTE MODE: Records will be permanently deleted!")
            response = input("Are you sure you want to proceed? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                return
            print()
        else:
            print("🔍 DRY RUN MODE: No records will be deleted.")
            print()
        
        stats = cleanup_duplicates(db, dry_run=not args.execute)
        
        print()
        print("=" * 80)
        print("Summary:")
        print(f"  Duplicate groups found: {stats['duplicate_groups']}")
        print(f"  Total duplicate records: {stats['total_duplicates']}")
        print(f"  Records to delete: {stats['records_to_delete']}")
        print(f"  Records to keep: {stats['records_kept']}")
        print("=" * 80)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during cleanup: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    main()

