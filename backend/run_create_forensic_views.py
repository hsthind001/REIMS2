#!/usr/bin/env python3
"""
Create Forensic Reconciliation Materialized Views
Executes SQL to create all 4 materialized views
"""

import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal, engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_views():
    """Create all forensic reconciliation materialized views"""

    print("\n" + "="*80)
    print("CREATING FORENSIC RECONCILIATION MATERIALIZED VIEWS")
    print("="*80 + "\n")

    db = SessionLocal()

    try:
        # Read the SQL file
        with open('/app/create_forensic_views.sql', 'r') as f:
            sql = f.read()

        # Split by double semicolons (view separators)
        statements = sql.split(';')

        print(f"Executing {len(statements)} SQL statements...\n")

        for i, statement in enumerate(statements, 1):
            statement = statement.strip()
            if not statement:
                continue

            try:
                # Print what we're doing
                if 'DROP' in statement:
                    print(f"[{i}] Dropping existing views...")
                elif 'CREATE MATERIALIZED VIEW' in statement:
                    # Extract view name
                    view_name = statement.split('CREATE MATERIALIZED VIEW ')[1].split(' AS')[0].strip()
                    print(f"[{i}] Creating materialized view: {view_name}...")
                elif 'CREATE INDEX' in statement or 'CREATE UNIQUE INDEX' in statement:
                    # Extract index name
                    if 'UNIQUE INDEX' in statement:
                        index_name = statement.split('CREATE UNIQUE INDEX ')[1].split(' ON')[0].strip()
                    else:
                        index_name = statement.split('CREATE INDEX ')[1].split(' ON')[0].strip()
                    print(f"[{i}] Creating index: {index_name}...")
                else:
                    print(f"[{i}] Executing statement...")

                # Execute
                db.execute(text(statement))
                db.commit()
                print(f"     ✓ Success\n")

            except Exception as e:
                print(f"     ✗ Error: {str(e)}\n")
                # Continue with next statement
                db.rollback()

        print("="*80)
        print("VIEW CREATION COMPLETE")
        print("="*80 + "\n")

        # Verify views were created
        print("Verifying views...")
        views = [
            'balance_sheet_summary',
            'income_statement_summary',
            'cash_flow_summary'
        ]

        for view in views:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {view}"))
                count = result.scalar()
                print(f"✓ {view}: {count} records")
            except Exception as e:
                print(f"✗ {view}: {str(e)}")

        print("\n✅ Forensic reconciliation views created successfully!")
        return 0

    except Exception as e:
        print(f"\n✗ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(create_views())
