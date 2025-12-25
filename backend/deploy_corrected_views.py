#!/usr/bin/env python3
"""
Deploy Corrected Forensic Reconciliation Materialized Views
"""

import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def deploy_views():
    """Deploy all corrected forensic reconciliation materialized views"""

    print("\n" + "="*80)
    print("DEPLOYING CORRECTED FORENSIC RECONCILIATION VIEWS")
    print("="*80 + "\n")

    db = SessionLocal()

    try:
        # Read the corrected SQL file
        with open('/app/create_forensic_views_corrected.sql', 'r') as f:
            sql = f.read()

        # Split by semicolons
        statements = [s.strip() for s in sql.split(';') if s.strip()]

        print(f"Executing {len(statements)} SQL statements...\n")

        for i, statement in enumerate(statements, 1):
            try:
                # Determine statement type for better logging
                if 'DROP MATERIALIZED VIEW' in statement.upper():
                    view_name = statement.split('DROP MATERIALIZED VIEW IF EXISTS ')[1].split(' ')[0]
                    print(f"[{i}] Dropping view: {view_name}...")
                elif 'CREATE MATERIALIZED VIEW' in statement.upper():
                    view_name = statement.split('CREATE MATERIALIZED VIEW ')[1].split(' AS')[0].strip()
                    print(f"[{i}] Creating materialized view: {view_name}...")
                elif 'CREATE UNIQUE INDEX' in statement.upper():
                    index_name = statement.split('CREATE UNIQUE INDEX ')[1].split(' ON')[0].strip()
                    print(f"[{i}] Creating unique index: {index_name}...")
                elif 'CREATE INDEX' in statement.upper():
                    index_name = statement.split('CREATE INDEX ')[1].split(' ON')[0].strip()
                    print(f"[{i}] Creating index: {index_name}...")
                else:
                    print(f"[{i}] Executing statement...")

                # Execute
                db.execute(text(statement))
                db.commit()
                print(f"     ✓ Success\n")

            except Exception as e:
                error_msg = str(e)[:200]
                print(f"     ✗ Error: {error_msg}\n")
                db.rollback()

                # For certain errors, we may want to stop
                if 'does not exist' in error_msg and 'column' in error_msg:
                    print(f"\n⚠️  SCHEMA ERROR: {error_msg}")
                    print("     This indicates the field names in the SQL don't match the database.")
                    print("     Continuing to try remaining statements...\n")

        print("="*80)
        print("VIEW DEPLOYMENT COMPLETE")
        print("="*80 + "\n")

        # Verify what was created successfully
        print("Verifying views...")
        views_to_check = [
            'balance_sheet_summary',
            'income_statement_summary',
            'cash_flow_summary',
            'forensic_reconciliation_master'
        ]

        success_count = 0
        for view in views_to_check:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {view}"))
                count = result.scalar()
                print(f"✓ {view}: {count} records")
                success_count += 1
            except Exception as e:
                print(f"✗ {view}: NOT FOUND - {str(e)[:100]}")

        print(f"\n{'='*80}")
        print(f"SUMMARY: {success_count}/{len(views_to_check)} views created successfully")
        print(f"{'='*80}\n")

        if success_count == len(views_to_check):
            print("✅ All forensic reconciliation views created successfully!")
            return 0
        elif success_count > 0:
            print("⚠️  Some views created, but not all. Check errors above.")
            return 1
        else:
            print("✗ No views created successfully. Schema adjustment needed.")
            return 1

    except Exception as e:
        print(f"\n✗ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(deploy_views())
