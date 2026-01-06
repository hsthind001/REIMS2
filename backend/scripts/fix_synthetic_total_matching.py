#!/usr/bin/env python3
"""
Fix Match Rate: Link Synthetic Total Rows to Chart of Accounts

The 60 synthetic total rows (4990, 5990, 6190, 6199, 7090) created in Phase 1
are currently unmatched (account_id = None). This script matches them to their
corresponding accounts in the Chart of Accounts to achieve 100% match rate.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.income_statement_data import IncomeStatementData
from app.models.chart_of_accounts import ChartOfAccounts


def fix_synthetic_total_matching():
    """Match synthetic total rows to Chart of Accounts"""

    print("=" * 80)
    print("Fix Match Rate: Link Synthetic Totals to Chart of Accounts")
    print("=" * 80)
    print()

    session = SessionLocal()

    try:
        # Get all unmatched synthetic totals
        unmatched_synthetics = session.query(IncomeStatementData).filter(
            IncomeStatementData.account_id.is_(None),
            IncomeStatementData.is_calculated == True
        ).all()

        print(f"📊 Found {len(unmatched_synthetics)} unmatched synthetic total rows")
        print()

        if len(unmatched_synthetics) == 0:
            print("✅ All synthetic totals already matched!")
            return

        # Count by account code
        from collections import Counter
        codes = Counter([item.account_code for item in unmatched_synthetics])
        print("Unmatched synthetic totals by account code:")
        for code, count in sorted(codes.items()):
            print(f"  {code}: {count} rows")
        print()

        # Match each synthetic total to its account
        print("🔗 Matching synthetic totals to Chart of Accounts...")
        print()

        matched_count = 0
        not_found = []

        for item in unmatched_synthetics:
            account_code = item.account_code

            # Find account in Chart of Accounts
            account = session.query(ChartOfAccounts).filter(
                ChartOfAccounts.account_code == account_code
            ).first()

            if account:
                item.account_id = account.id
                item.match_confidence = 100.0  # Perfect match for synthetic totals
                matched_count += 1
            else:
                not_found.append(account_code)

        # Commit matches
        if matched_count > 0:
            print(f"💾 Committing {matched_count} account matches...")
            session.commit()
            print("✅ Matches committed successfully")
            print()

        # Report results
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"Synthetic totals matched: {matched_count}")
        if not_found:
            print(f"Accounts not found in COA: {len(set(not_found))}")
            for code in set(not_found):
                print(f"  ⚠️  {code}")
        print()

        # Verify final match rate
        total_items = session.query(IncomeStatementData).count()
        matched_items = session.query(IncomeStatementData).filter(
            IncomeStatementData.account_id.isnot(None)
        ).count()
        match_rate = (matched_items / total_items * 100) if total_items > 0 else 0

        print("FINAL MATCH RATE:")
        print(f"  Total items: {total_items}")
        print(f"  Matched items: {matched_items}")
        print(f"  Match rate: {match_rate:.2f}%")
        print()

        if match_rate >= 100.0:
            print("🎉 100% MATCH RATE ACHIEVED!")
        elif match_rate >= 95.0:
            print("✅ 95%+ match rate achieved")
        else:
            print(f"📊 Current match rate: {match_rate:.2f}%")
            unmatched = total_items - matched_items
            print(f"   Remaining unmatched: {unmatched}")

        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    fix_synthetic_total_matching()
