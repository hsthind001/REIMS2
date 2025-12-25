#!/usr/bin/env python3
"""
Deploy Fine-Tuned Forensic Reconciliation Materialized Views
"""

import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Fine-tuned views SQL - embedded to avoid file permission issues
SUMMARY_VIEWS_SQL = """
-- Drop existing views
DROP MATERIALIZED VIEW IF EXISTS forensic_reconciliation_master CASCADE;
DROP MATERIALIZED VIEW IF EXISTS cash_flow_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS income_statement_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS balance_sheet_summary CASCADE;

-- Balance Sheet Summary
CREATE MATERIALIZED VIEW balance_sheet_summary AS
SELECT
    bs.property_id,
    bs.period_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,
    COALESCE(SUM(CASE WHEN bs.account_code = '1999-0000' THEN bs.amount ELSE 0 END), 0) as total_assets,
    COALESCE(SUM(CASE WHEN bs.account_code = '0499-9000' THEN bs.amount ELSE 0 END), 0) as total_current_assets,
    COALESCE(SUM(CASE WHEN bs.account_code IN ('0121-0000', '0122-0000') THEN bs.amount ELSE 0 END), 0) as cash,
    COALESCE(SUM(CASE WHEN bs.account_code = '2999-0000' THEN bs.amount ELSE 0 END), 0) as total_liabilities,
    COALESCE(SUM(CASE WHEN bs.account_code = '2590-0000' THEN bs.amount ELSE 0 END), 0) as total_current_liabilities,
    COALESCE(SUM(CASE WHEN bs.account_code = '2700-0000' THEN bs.amount ELSE 0 END), 0) as long_term_debt,
    COALESCE(SUM(CASE WHEN bs.account_code = '3999-0000' THEN bs.amount ELSE 0 END), 0) as total_equity,
    COALESCE(SUM(CASE WHEN bs.account_code = '3995-0000' THEN bs.amount ELSE 0 END), 0) as retained_earnings,
    COALESCE(SUM(CASE WHEN bs.account_code = '2520-0000' THEN bs.amount ELSE 0 END), 0) as tenant_deposits,
    COALESCE(SUM(CASE WHEN bs.account_code IN ('1310-0000', '1320-0000', '1330-0000') THEN bs.amount ELSE 0 END), 0) as escrow_accounts,
    MAX(bs.extraction_confidence) as avg_extraction_confidence,
    COUNT(DISTINCT bs.id) as line_item_count,
    MIN(bs.created_at) as first_extraction_date,
    MAX(bs.updated_at) as last_updated
FROM balance_sheet_data bs
JOIN properties p ON p.id = bs.property_id
JOIN financial_periods fp ON fp.id = bs.period_id
GROUP BY bs.property_id, bs.period_id, p.property_code, p.property_name, fp.period_year, fp.period_month;

CREATE UNIQUE INDEX idx_bs_summary_property_period ON balance_sheet_summary(property_id, period_id);
CREATE INDEX idx_bs_summary_period ON balance_sheet_summary(period_year, period_month);

-- Income Statement Summary
CREATE MATERIALIZED VIEW income_statement_summary AS
SELECT
    ist.property_id,
    ist.period_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,
    COALESCE(SUM(CASE WHEN ist.account_code LIKE '4%' AND ist.account_code NOT IN ('4060-0000') THEN ist.period_amount ELSE 0 END), 0) as total_income,
    COALESCE(SUM(CASE WHEN ist.account_code = '4010-0000' THEN ist.period_amount ELSE 0 END), 0) as rental_income,
    COALESCE(SUM(CASE WHEN ist.account_code LIKE '4%' AND ist.account_code NOT IN ('4010-0000', '4060-0000') THEN ist.period_amount ELSE 0 END), 0) as other_income,
    COALESCE(SUM(CASE WHEN (ist.account_code LIKE '5%' OR ist.account_code LIKE '6%') AND ist.account_code != '6299-0000' THEN ist.period_amount ELSE 0 END), 0) as total_operating_expenses,
    COALESCE(SUM(CASE WHEN ist.account_code = '6299-0000' THEN ist.period_amount ELSE 0 END), 0) as noi,
    COALESCE(SUM(CASE WHEN ist.account_code = '7010-0000' THEN ist.period_amount ELSE 0 END), 0) as interest_expense,
    COALESCE(SUM(CASE WHEN ist.account_code = '7020-0000' THEN ist.period_amount ELSE 0 END), 0) as depreciation_expense,
    COALESCE(SUM(CASE WHEN ist.account_code = '9090-0000' THEN ist.period_amount ELSE 0 END), 0) as net_income,
    MAX(ist.extraction_confidence) as avg_extraction_confidence,
    COUNT(DISTINCT ist.id) as line_item_count,
    MIN(ist.created_at) as first_extraction_date,
    MAX(ist.updated_at) as last_updated
FROM income_statement_data ist
JOIN properties p ON p.id = ist.property_id
JOIN financial_periods fp ON fp.id = ist.period_id
GROUP BY ist.property_id, ist.period_id, p.property_code, p.property_name, fp.period_year, fp.period_month;

CREATE UNIQUE INDEX idx_is_summary_property_period ON income_statement_summary(property_id, period_id);
CREATE INDEX idx_is_summary_period ON income_statement_summary(period_year, period_month);

-- Cash Flow Summary
CREATE MATERIALIZED VIEW cash_flow_summary AS
SELECT
    cf.property_id,
    cf.period_id,
    p.property_code,
    p.property_name,
    fp.period_year,
    fp.period_month,
    COALESCE(SUM(CASE WHEN cf.account_code IN ('0121-0000', '0122-0000') AND cf.line_category LIKE '%Operating%' THEN cf.period_amount ELSE 0 END), 0) as beginning_cash,
    COALESCE(SUM(CASE WHEN cf.line_section = 'INCOME' OR (cf.cash_flow_category = 'operating' AND (cf.account_code LIKE '5%' OR cf.account_code LIKE '6%')) THEN cf.period_amount ELSE 0 END), 0) as operating_cash_flow,
    COALESCE(SUM(CASE WHEN cf.cash_flow_category = 'investing' THEN cf.period_amount ELSE 0 END), 0) as investing_cash_flow,
    COALESCE(SUM(CASE WHEN cf.cash_flow_category = 'financing' THEN cf.period_amount ELSE 0 END), 0) as financing_cash_flow,
    COALESCE(ABS(SUM(CASE WHEN cf.account_code = '2700-0000' AND cf.cash_flow_category = 'financing' THEN cf.period_amount ELSE 0 END)), 0) as debt_service_payment,
    COALESCE(SUM(cf.period_amount), 0) as net_change_in_cash,
    COALESCE(SUM(CASE WHEN cf.account_code IN ('0121-0000', '0122-0000') THEN cf.period_amount ELSE 0 END), 0) as ending_cash,
    MAX(cf.extraction_confidence) as avg_extraction_confidence,
    COUNT(DISTINCT cf.id) as line_item_count,
    MIN(cf.created_at) as first_extraction_date,
    MAX(cf.updated_at) as last_updated
FROM cash_flow_data cf
JOIN properties p ON p.id = cf.property_id
JOIN financial_periods fp ON fp.id = cf.period_id
GROUP BY cf.property_id, cf.period_id, p.property_code, p.property_name, fp.period_year, fp.period_month;

CREATE UNIQUE INDEX idx_cf_summary_property_period ON cash_flow_summary(property_id, period_id);
CREATE INDEX idx_cf_summary_period ON cash_flow_summary(period_year, period_month);
"""


def deploy_views():
    """Deploy all fine-tuned forensic reconciliation materialized views"""

    print("\n" + "="*80)
    print("DEPLOYING FINE-TUNED FORENSIC RECONCILIATION VIEWS")
    print("="*80 + "\n")

    db = SessionLocal()

    try:
        # Split and execute statements
        statements = [s.strip() for s in SUMMARY_VIEWS_SQL.split(';') if s.strip()]

        print(f"Executing {len(statements)} SQL statements...\n")

        for i, statement in enumerate(statements, 1):
            try:
                # Determine statement type for better logging
                if 'DROP MATERIALIZED VIEW' in statement.upper():
                    print(f"[{i}] Dropping views...")
                elif 'CREATE MATERIALIZED VIEW balance_sheet_summary' in statement.upper():
                    print(f"[{i}] Creating balance_sheet_summary...")
                elif 'CREATE MATERIALIZED VIEW income_statement_summary' in statement.upper():
                    print(f"[{i}] Creating income_statement_summary...")
                elif 'CREATE MATERIALIZED VIEW cash_flow_summary' in statement.upper():
                    print(f"[{i}] Creating cash_flow_summary...")
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

        print("="*80)
        print("VIEW DEPLOYMENT COMPLETE - STEP 1 OF 2")
        print("="*80 + "\n")

        # Verify what was created successfully
        print("Verifying summary views...")
        views_to_check = [
            'balance_sheet_summary',
            'income_statement_summary',
            'cash_flow_summary'
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
        print(f"SUMMARY: {success_count}/{len(views_to_check)} summary views created successfully")
        print(f"{'='*80}\n")

        if success_count == len(views_to_check):
            print("✅ All summary views created successfully!")
            print("Next: Deploy master reconciliation view")
            return 0
        else:
            print("⚠️  Some views failed. Check errors above.")
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
