"""
Full Validation Rules Seeder

Loads the comprehensive rule set from SQL scripts (balance sheet, income statement, mortgage, prevention/auto-resolution where applicable).
Safe to re-run; ignores duplicate errors.
"""
import os
from sqlalchemy import text

from app.db.database import SessionLocal


_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SQL_FILES = [
    os.path.join(_BASE_DIR, "scripts", "01_balance_sheet_rules.sql"),
    os.path.join(_BASE_DIR, "scripts", "02_income_statement_rules.sql"),
    os.path.join(_BASE_DIR, "scripts", "seed_mortgage_validation_rules.sql"),
    os.path.join(_BASE_DIR, "scripts", "seed_validation_rules.sql"),
]


def _execute_sql_file(db, path: str) -> int:
    if not os.path.exists(path):
        print(f"⚠️  SQL file not found: {path}")
        return 0

    with open(path, "r") as f:
        sql_content = f.read()

    # Split on semicolon while keeping statements simple (files are already flat)
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
    executed = 0
    for stmt in statements:
        # Only run INSERTs into validation_rules to avoid destructive ops
        if "INSERT INTO VALIDATION_RULES" not in stmt.upper():
            continue
        try:
            db.execute(text(stmt))
            db.commit()
            executed += 1
        except Exception as exc:
            db.rollback()
            # Likely duplicate rule_name unique constraint; continue
            print(f"Skipping statement due to error ({str(exc)[:80]}): {stmt[:80]}...")
    return executed


def seed_full_validation_rules():
    db = SessionLocal()
    executed_total = 0
    try:
        for path in SQL_FILES:
            executed_total += _execute_sql_file(db, path)
        db.commit()
        print(f"✓ Full validation rules seed executed ({executed_total} statements run)")
    except Exception as exc:
        db.rollback()
        print(f"✗ Error seeding validation rules: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_full_validation_rules()
