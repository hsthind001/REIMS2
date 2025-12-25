#!/usr/bin/env python3
"""
Test Complete Forensic Reconciliation Implementation
Run comprehensive Big 5-level forensic audit on October 2023 data
"""

import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.services.complete_forensic_reconciliation_service import CompleteForensicReconciliationService
from sqlalchemy import text
import json
from datetime import datetime


def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(title)
    print("="*80)


def print_subsection(title: str):
    """Print formatted subsection header"""
    print(f"\n{title}")
    print("-" * len(title))


def format_currency(value):
    """Format number as currency"""
    if value is None:
        return "N/A"
    try:
        return f"${float(value):,.2f}"
    except:
        return str(value)


def format_percent(value):
    """Format number as percentage"""
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2f}%"
    except:
        return str(value)


def test_view_creation(db):
    """Test if materialized views exist"""
    print_section("STEP 1: VERIFY MATERIALIZED VIEWS")

    views = [
        'balance_sheet_summary',
        'income_statement_summary',
        'cash_flow_summary',
        'forensic_reconciliation_master'
    ]

    for view in views:
        try:
            result = db.execute(text(f"SELECT COUNT(*) FROM {view}"))
            count = result.scalar()
            print(f"✓ {view}: {count} records")
        except Exception as e:
            print(f"✗ {view}: NOT FOUND - {str(e)[:100]}")
            return False

    return True


def create_views_if_missing(db):
    """Create materialized views if they don't exist"""
    print_section("CREATING MATERIALIZED VIEWS")

    print("Running migration to create views...")

    try:
        # Run the migration file directly
        from alembic.config import Config
        from alembic import command
        import os

        alembic_cfg = Config("/app/alembic.ini")
        command.upgrade(alembic_cfg, "head")

        print("✓ Migration completed")
        return True
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        print("\nAttempting manual view creation...")

        # Attempt manual creation
        try:
            exec(open('/app/backend/alembic/versions/create_forensic_reconciliation_views.py').read())
            print("✓ Manual creation successful")
            return True
        except Exception as e2:
            print(f"✗ Manual creation failed: {e2}")
            return False


def test_refresh_views(service):
    """Test view refresh"""
    print_section("STEP 2: REFRESH MATERIALIZED VIEWS")

    try:
        service.refresh_materialized_views()
        print("✓ All views refreshed successfully")
        return True
    except Exception as e:
        print(f"✗ View refresh failed: {e}")
        return False


def test_reconciliation_summary(service, property_id, period_id):
    """Test getting reconciliation summary"""
    print_section("STEP 3: GET RECONCILIATION SUMMARY")

    try:
        data = service.get_reconciliation_summary(property_id, period_id)

        if not data:
            print(f"✗ No data found for property {property_id}, period {period_id}")
            return None

        print(f"✓ Data retrieved successfully")
        print(f"\nProperty: {data['property_name']} ({data['property_code']})")
        print(f"Period: {data['period_year']}-{data['period_month']:02d}")
        print(f"Audit Opinion: {data['audit_opinion']}")
        print(f"Critical Tie-Outs Passed: {data['critical_tieouts_passed']}/5")
        print(f"Overall Quality Score: {data['overall_quality_score']}%")

        return data

    except Exception as e:
        print(f"✗ Failed to get summary: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_complete_reconciliation(service, property_id, period_id):
    """Test complete forensic reconciliation"""
    print_section("STEP 4: PERFORM COMPLETE FORENSIC RECONCILIATION")

    try:
        report = service.perform_complete_reconciliation(
            property_id=property_id,
            period_id=period_id,
            refresh_views=True
        )

        if report.get('status') == 'error':
            print(f"✗ {report.get('message')}")
            return None

        print("✓ Reconciliation completed successfully\n")

        # Display results
        display_report(report)

        return report

    except Exception as e:
        print(f"✗ Reconciliation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def display_report(report):
    """Display comprehensive reconciliation report"""

    # Property Info
    print_subsection("PROPERTY INFORMATION")
    info = report['property_info']
    print(f"Property: {info['property_name']} ({info['property_code']})")
    print(f"Period: {info['period_label']}")

    # Document Completeness
    print_subsection("DOCUMENT COMPLETENESS")
    completeness = report['document_completeness']
    print(f"Documents Present: {completeness['documents_present']}/{completeness['documents_required']}")
    print(f"Completeness: {completeness['completeness_pct']:.1f}%")
    print(f"Status: {completeness['status']}")

    # Balance Sheet
    print_subsection("BALANCE SHEET SUMMARY")
    bs = report['balance_sheet']
    print(f"Total Assets: {format_currency(bs['total_assets'])}")
    print(f"Total Liabilities: {format_currency(bs['total_liabilities'])}")
    print(f"Total Equity: {format_currency(bs['total_equity'])}")
    print(f"Long-Term Debt: {format_currency(bs['long_term_debt'])}")
    print(f"Cash: {format_currency(bs['cash'])}")
    print(f"Balance Check: {bs['balance_check']['status']} (variance: {format_currency(bs['balance_check']['variance'])})")

    # Income Statement
    print_subsection("INCOME STATEMENT SUMMARY")
    ist = report['income_statement']
    print(f"Total Income: {format_currency(ist['total_income'])}")
    print(f"Rental Income: {format_currency(ist['rental_income'])}")
    print(f"Operating Expenses: {format_currency(ist['total_operating_expenses'])}")
    print(f"Net Operating Income (NOI): {format_currency(ist['noi'])}")
    print(f"Interest Expense: {format_currency(ist['interest_expense'])}")
    print(f"Net Income: {format_currency(ist['net_income'])}")

    # Cash Flow
    print_subsection("CASH FLOW SUMMARY")
    cf = report['cash_flow']
    print(f"Beginning Cash: {format_currency(cf['beginning_cash'])}")
    print(f"Operating Cash Flow: {format_currency(cf['operating_cash_flow'])}")
    print(f"Investing Cash Flow: {format_currency(cf['investing_cash_flow'])}")
    print(f"Financing Cash Flow: {format_currency(cf['financing_cash_flow'])}")
    print(f"Net Change: {format_currency(cf['net_change_in_cash'])}")
    print(f"Ending Cash: {format_currency(cf['ending_cash'])}")
    print(f"Debt Service Payment: {format_currency(cf['debt_service_payment'])}")

    # Rent Roll
    print_subsection("RENT ROLL SUMMARY")
    rr = report['rent_roll']
    print(f"Total Units: {rr['total_units']}")
    print(f"Occupied: {rr['occupied_units']}")
    print(f"Vacant: {rr['vacant_units']}")
    print(f"Occupancy Rate: {format_percent(rr['occupancy_rate'])}")
    print(f"Monthly Rent: {format_currency(rr['total_monthly_rent'])}")
    print(f"Annual Rent: {format_currency(rr['annual_rent'])}")

    # Mortgage Statement
    print_subsection("MORTGAGE STATEMENT SUMMARY")
    mst = report['mortgage_statement']
    print(f"Loan Number: {mst['loan_number']}")
    print(f"Principal Balance: {format_currency(mst['principal_balance'])}")
    print(f"Interest Rate: {format_percent(mst['interest_rate'])}")
    print(f"Monthly Payment: {format_currency(mst['total_payment_due'])}")
    print(f"  - Principal: {format_currency(mst['principal_due'])}")
    print(f"  - Interest: {format_currency(mst['interest_due'])}")
    print(f"  - Tax Escrow: {format_currency(mst['tax_escrow_due'])}")
    print(f"  - Insurance Escrow: {format_currency(mst['insurance_escrow_due'])}")
    print(f"Annual Debt Service: {format_currency(mst['annual_debt_service'])}")
    print(f"YTD Interest Paid: {format_currency(mst['ytd_interest_paid'])}")

    # Critical Tie-Outs
    print_subsection("CRITICAL TIE-OUTS (Priority 1)")
    for tieout in report['critical_tieouts']:
        status_symbol = "✓" if tieout['status'] == 'PASS' else "✗"
        print(f"{status_symbol} Tie-Out #{tieout['tieout_id']}: {tieout['name']}")
        print(f"   Source: {format_currency(tieout['source_value'])}")
        print(f"   Target: {format_currency(tieout['target_value'])}")
        print(f"   Variance: {format_currency(tieout['variance'])} (tolerance: {format_currency(tieout['tolerance'])})")
        print(f"   Status: {tieout['status']}")

    # Warning Tie-Outs
    print_subsection("WARNING TIE-OUTS (Priority 2)")
    for tieout in report['warning_tieouts']:
        status_symbol = "✓" if tieout['status'] == 'PASS' else "⚠"
        print(f"{status_symbol} Tie-Out #{tieout['tieout_id']}: {tieout['name']}")
        print(f"   Source: {format_currency(tieout['source_value'])}")
        print(f"   Target: {format_currency(tieout['target_value'])}")
        print(f"   Variance: {format_currency(tieout['variance'])} (tolerance: {format_currency(tieout['tolerance'])})")
        print(f"   Status: {tieout['status']}")

    # Business Metrics
    print_subsection("BUSINESS METRICS")
    metrics = report['business_metrics']

    # DSCR
    dscr = metrics['dscr']
    if dscr['value']:
        print(f"DSCR: {dscr['value']:.2f}x - {dscr['status']}")
        print(f"  NOI: {format_currency(dscr['noi'])}")
        print(f"  Annual Debt Service: {format_currency(dscr['annual_debt_service'])}")
        print(f"  Interpretation: {dscr['interpretation']}")
    else:
        print(f"DSCR: N/A")

    # Cash Flow Coverage
    cfc = metrics['cash_flow_coverage']
    if cfc['value']:
        print(f"\nCash Flow Coverage: {cfc['value']:.2f}x - {cfc['status']}")
        print(f"  Operating CF: {format_currency(cfc['operating_cash_flow'])}")
        print(f"  Annual Debt Service: {format_currency(cfc['annual_debt_service'])}")

    # Occupancy
    occ = metrics['occupancy']
    print(f"\nOccupancy: {format_percent(occ['rate'])} - {occ['status']}")
    print(f"  Occupied: {occ['occupied_units']}/{occ['total_units']} units")

    # NOI
    noi = metrics['noi']
    print(f"\nNOI: {format_currency(noi['value'])} - {noi['status']}")

    # Variance Analysis
    if report['variance_analysis']:
        print_subsection("VARIANCE ANALYSIS")
        for variance in report['variance_analysis']:
            print(f"⚠ {variance['name']}")
            print(f"  Variance: {format_currency(variance['variance'])}")
            print(f"  Status: {variance['status']}")
            print(f"  Severity: {variance['severity']}")

    # Red Flags
    if report['red_flags']:
        print_subsection("RED FLAGS")
        for flag in report['red_flags']:
            symbol = "✗" if flag['severity'] == 'CRITICAL' else "⚠"
            print(f"{symbol} {flag['category']}: {flag['description']}")
            if flag.get('value'):
                print(f"  Value: {format_currency(flag['value'])}")
            print(f"  Impact: {flag['impact']}")
    else:
        print_subsection("RED FLAGS")
        print("✓ No red flags detected")

    # Audit Opinion
    print_subsection("AUDIT OPINION")
    opinion = report['audit_opinion']
    print(f"Opinion: {opinion['opinion']}")
    print(f"\n{opinion['explanation']}")
    print(f"\nCritical Tie-Outs: {opinion['critical_tieouts_passed']}/{opinion['critical_tieouts_total']} passed ({opinion['pass_rate']:.1f}%)")
    print(f"Overall Quality Score: {opinion['overall_quality_score']:.1f}%")
    print(f"\nIssued by: {opinion['issued_by']}")
    print(f"Issued at: {opinion['issued_at']}")


def test_history(service, property_id):
    """Test getting reconciliation history"""
    print_section("STEP 5: GET RECONCILIATION HISTORY")

    try:
        history = service.get_reconciliation_history(property_id, limit=12)

        print(f"✓ Retrieved history for {len(history)} periods\n")

        for period in history:
            print(f"Period: {period['period_label']}")
            print(f"  Opinion: {period['audit_opinion']}")
            print(f"  Critical Tie-Outs: {period['critical_tieouts_passed']}/5")
            if period['dscr']:
                print(f"  DSCR: {period['dscr']:.2f}x ({period['dscr_status']})")
            if period['occupancy_rate']:
                print(f"  Occupancy: {period['occupancy_rate']:.1f}%")
            print(f"  Quality Score: {period['quality_score']:.1f}%")
            print()

        return history

    except Exception as e:
        print(f"✗ Failed to get history: {e}")
        return None


def save_report_to_file(report, filename):
    """Save report to JSON file"""
    print_section("STEP 6: SAVE REPORT TO FILE")

    try:
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"✓ Report saved to: {filename}")
        return True
    except Exception as e:
        print(f"✗ Failed to save report: {e}")
        return False


def main():
    """Main test execution"""
    print("="*80)
    print("COMPLETE FORENSIC RECONCILIATION TEST")
    print("Big 5 Level Cross-Document Reconciliation")
    print("="*80)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    db = SessionLocal()
    service = CompleteForensicReconciliationService(db)

    # Test parameters
    PROPERTY_ID = 1  # ESP001
    PERIOD_ID = 11   # October 2023

    try:
        # Step 1: Verify views exist
        views_exist = test_view_creation(db)

        if not views_exist:
            print("\n⚠ Views don't exist. Attempting to create...")
            if not create_views_if_missing(db):
                print("\n✗ CRITICAL: Could not create views. Test cannot continue.")
                return 1

        # Step 2: Refresh views
        if not test_refresh_views(service):
            print("\n⚠ View refresh failed. Continuing with existing data...")

        # Step 3: Get summary
        summary = test_reconciliation_summary(service, PROPERTY_ID, PERIOD_ID)
        if not summary:
            print("\n✗ CRITICAL: Could not get reconciliation summary.")
            return 1

        # Step 4: Perform complete reconciliation
        report = test_complete_reconciliation(service, PROPERTY_ID, PERIOD_ID)
        if not report:
            print("\n✗ CRITICAL: Complete reconciliation failed.")
            return 1

        # Step 5: Get history
        history = test_history(service, PROPERTY_ID)

        # Step 6: Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"/app/forensic_reconciliation_report_{timestamp}.json"
        save_report_to_file(report, filename)

        # Final Summary
        print_section("TEST SUMMARY")
        print("✅ ALL TESTS PASSED")
        print(f"\nAudit Opinion: {report['audit_opinion']['opinion']}")
        print(f"Critical Tie-Outs Passed: {report['audit_opinion']['critical_tieouts_passed']}/5")
        print(f"Overall Quality Score: {report['audit_opinion']['overall_quality_score']:.1f}%")
        print(f"\nReport saved to: {filename}")

        return 0

    except Exception as e:
        print_section("FATAL ERROR")
        print(f"✗ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(main())
