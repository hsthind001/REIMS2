"""
DSCR Diagnostic Script - Comprehensive Analysis

This script diagnoses why DSCR is showing N/A or 0.0 in the dashboard.

Checks:
1. Data availability (income statements, mortgage statements)
2. Latest complete period detection
3. NOI calculation correctness
4. Debt service calculation correctness
5. DSCR calculation in financial_metrics
6. Frontend data flow

Usage:
    python backend/scripts/diagnose_dscr_issues.py
"""
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
from datetime import datetime
import json

# Database connection
# Use postgres hostname when running in container, localhost when running locally
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://reims:reims@postgres:5432/reims")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subsection(title):
    """Print a subsection header"""
    print(f"\n--- {title} ---")


def diagnose_property(db, property_id: int, property_code: str, year: int = 2025):
    """
    Comprehensive DSCR diagnosis for a single property
    """
    print_section(f"Property: {property_code} (ID: {property_id}) - Year {year}")

    # Step 1: Check data availability for all periods
    print_subsection("1. Document Availability by Period")

    query = text("""
        SELECT
            fp.id as period_id,
            fp.period_year || '-' || LPAD(fp.period_month::text, 2, '0') as period,
            COUNT(DISTINCT CASE WHEN isd.id IS NOT NULL THEN isd.header_id END) as income_stmt_count,
            COUNT(DISTINCT msd.id) as mortgage_stmt_count,
            COUNT(DISTINCT du.id) FILTER (WHERE du.document_type = 'income_statement'
                AND du.extraction_status = 'completed') as income_docs,
            COUNT(DISTINCT du.id) FILTER (WHERE du.document_type = 'mortgage_statement'
                AND du.extraction_status = 'completed') as mortgage_docs,
            CASE
                WHEN COUNT(DISTINCT CASE WHEN isd.id IS NOT NULL THEN isd.header_id END) > 0
                    AND COUNT(DISTINCT msd.id) > 0
                THEN 'COMPLETE'
                WHEN COUNT(DISTINCT CASE WHEN isd.id IS NOT NULL THEN isd.header_id END) > 0
                THEN 'INCOME ONLY'
                WHEN COUNT(DISTINCT msd.id) > 0
                THEN 'MORTGAGE ONLY'
                ELSE 'NO DATA'
            END as data_status
        FROM financial_periods fp
        LEFT JOIN income_statement_data isd ON isd.period_id = fp.id AND isd.property_id = fp.property_id
        LEFT JOIN mortgage_statement_data msd ON msd.period_id = fp.id AND msd.property_id = fp.property_id
        LEFT JOIN document_uploads du ON du.period_id = fp.id AND du.property_id = fp.property_id
        WHERE fp.property_id = :property_id
            AND fp.period_year = :year
        GROUP BY fp.id, fp.period_year, fp.period_month
        ORDER BY fp.period_month DESC
    """)

    result = db.execute(query, {"property_id": property_id, "year": year})
    periods = result.fetchall()

    print(f"{'Period':<10} {'Income Stmt':<13} {'Mortgage Stmt':<15} {'Income Docs':<13} {'Mortgage Docs':<15} {'Status':<15}")
    print("-" * 90)

    complete_periods = []
    latest_complete_period = None

    for row in periods:
        period_id, period, income_count, mortgage_count, income_docs, mortgage_docs, status = row
        print(f"{period:<10} {income_count:<13} {mortgage_count:<15} {income_docs:<13} {mortgage_docs:<15} {status:<15}")

        if status == 'COMPLETE':
            complete_periods.append((period_id, period))
            if latest_complete_period is None:
                latest_complete_period = (period_id, period)

    if latest_complete_period:
        print(f"\n✓ Latest Complete Period: {latest_complete_period[1]} (ID: {latest_complete_period[0]})")
    else:
        print(f"\n✗ No complete periods found (missing both income statement AND mortgage data)")
        return None

    period_id, period_label = latest_complete_period

    # Step 2: Analyze NOI Calculation
    print_subsection(f"2. NOI Calculation Analysis - Period {period_label}")

    query = text("""
        SELECT
            SUM(CASE WHEN account_code LIKE '4%' AND NOT is_calculated THEN period_amount ELSE 0 END) as revenue,
            SUM(CASE WHEN account_code LIKE '5%' AND NOT is_calculated THEN period_amount ELSE 0 END) as operating_expenses_5xxx,
            SUM(CASE WHEN account_code LIKE '6%' AND account_code != '6299-0000' AND NOT is_calculated THEN period_amount ELSE 0 END) as other_6xxx_accounts,
            SUM(CASE WHEN (account_code LIKE '5%' OR account_code LIKE '6%')
                AND account_code != '6299-0000' AND NOT is_calculated THEN period_amount ELSE 0 END) as operating_expenses_5xxx_6xxx,
            MAX(CASE WHEN account_code = '6299-0000' THEN period_amount END) as stored_noi,
            MAX(CASE WHEN account_code = '4090-0000' THEN period_amount END) as other_income
        FROM income_statement_data
        WHERE period_id = :period_id
    """)

    result = db.execute(query, {"period_id": period_id})
    noi_data = result.fetchone()

    revenue, op_exp_5xxx, other_6xxx, op_exp_5xxx_6xxx, stored_noi, other_income = noi_data

    print(f"Revenue (4xxx):                    ${revenue:>15,.2f}")
    print(f"Operating Expenses (5xxx only):    ${op_exp_5xxx:>15,.2f}")
    print(f"Other 6xxx accounts (excl 6299):   ${other_6xxx:>15,.2f}")
    print(f"Operating Expenses (5xxx+6xxx):    ${op_exp_5xxx_6xxx:>15,.2f}")
    print(f"Stored NOI (6299-0000):            ${stored_noi:>15,.2f}")
    print(f"Other Income (4090-0000):          ${other_income:>15,.2f}")

    # Calculate NOI different ways
    calculated_noi_correct = revenue - op_exp_5xxx
    calculated_noi_wrong = revenue - op_exp_5xxx_6xxx

    print(f"\nCalculated NOI (Revenue - 5xxx):        ${calculated_noi_correct:>15,.2f}  ← CORRECT")
    print(f"Calculated NOI (Revenue - 5xxx-6xxx):   ${calculated_noi_wrong:>15,.2f}  ← WRONG (current bug)")
    print(f"Stored NOI (from 6299-0000):            ${stored_noi:>15,.2f}  ← Should match correct")

    # Check if calculations match
    if abs(calculated_noi_correct - stored_noi) < 0.01:
        print("\n✓ Calculated NOI matches stored NOI")
    else:
        print(f"\n✗ Calculated NOI differs from stored NOI by ${abs(calculated_noi_correct - stored_noi):,.2f}")

    if abs(calculated_noi_wrong) < 0.01:
        print("✗ BUG CONFIRMED: Current logic produces NOI = $0.00 (includes 6xxx in expenses)")

    # Step 3: Check financial_metrics table
    print_subsection(f"3. Financial Metrics Table - Period {period_label}")

    query = text("""
        SELECT
            total_revenue,
            net_operating_income,
            total_annual_debt_service,
            dscr
        FROM financial_metrics
        WHERE property_id = :property_id AND period_id = :period_id
    """)

    result = db.execute(query, {"property_id": property_id, "period_id": period_id})
    metrics = result.fetchone()

    if metrics:
        stored_revenue, stored_noi_fm, stored_debt_service, stored_dscr = metrics
        print(f"Total Revenue:          ${stored_revenue:>15,.2f}")
        print(f"Net Operating Income:   ${stored_noi_fm:>15,.2f}")
        print(f"Annual Debt Service:    ${stored_debt_service:>15,.2f}")
        print(f"DSCR:                   {stored_dscr if stored_dscr else 'NULL':>15}")

        # Check for issues
        issues = []
        if stored_noi_fm == 0:
            issues.append("NOI is $0.00 (should be ${:,.2f})".format(stored_noi))
        if stored_dscr is None:
            issues.append("DSCR is NULL")

        if issues:
            print("\n✗ Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✓ Metrics look correct")
    else:
        print("✗ No metrics record found for this period")

    # Step 4: Check mortgage data and debt service calculation
    print_subsection(f"4. Debt Service Calculation - Period {period_label}")

    query = text("""
        SELECT
            loan_number,
            principal_balance,
            interest_rate,
            monthly_debt_service,
            annual_debt_service,
            principal_due,
            interest_due
        FROM mortgage_statement_data
        WHERE property_id = :property_id AND period_id = :period_id
    """)

    result = db.execute(query, {"property_id": property_id, "period_id": period_id})
    mortgages = result.fetchall()

    if mortgages:
        print(f"Found {len(mortgages)} mortgage(s):")
        total_annual = Decimal('0')
        for mortgage in mortgages:
            loan_num, principal, rate, monthly, annual, p_due, i_due = mortgage
            print(f"\n  Loan #: {loan_num}")
            print(f"    Principal Balance:    ${principal:>15,.2f}")
            print(f"    Interest Rate:        {rate:>15.4f}%")
            print(f"    Monthly Debt Service: ${monthly:>15,.2f}")
            print(f"    Annual Debt Service:  ${annual:>15,.2f}")
            if annual:
                total_annual += annual
            elif monthly:
                total_annual += monthly * 12

        print(f"\n  Total Annual Debt Service: ${total_annual:>15,.2f}")
    else:
        print("✗ No mortgage data found for this period")

        # Check if there's mortgage data in earlier periods (fallback)
        query = text("""
            SELECT
                fp.period_year || '-' || LPAD(fp.period_month::text, 2, '0') as period,
                COUNT(*) as mortgage_count
            FROM mortgage_statement_data msd
            JOIN financial_periods fp ON fp.id = msd.period_id
            WHERE msd.property_id = :property_id
                AND fp.period_year = :year
                AND fp.period_month < (SELECT period_month FROM financial_periods WHERE id = :period_id)
            GROUP BY fp.period_year, fp.period_month
            ORDER BY fp.period_month DESC
            LIMIT 1
        """)

        result = db.execute(query, {"property_id": property_id, "year": year, "period_id": period_id})
        earlier = result.fetchone()

        if earlier:
            print(f"  Note: Found mortgage data in earlier period {earlier[0]} (fallback available)")

    # Step 5: Calculate what DSCR should be
    print_subsection(f"5. Expected DSCR Calculation")

    if stored_noi and total_annual > 0:
        expected_dscr = stored_noi / total_annual
        print(f"Expected DSCR = NOI / Annual Debt Service")
        print(f"Expected DSCR = ${stored_noi:,.2f} / ${total_annual:,.2f}")
        print(f"Expected DSCR = {expected_dscr:.4f}")

        # Status determination
        if expected_dscr >= 1.25:
            status = "HEALTHY"
            color = "🟢"
        elif expected_dscr >= 1.10:
            status = "WARNING"
            color = "🟡"
        else:
            status = "CRITICAL"
            color = "🔴"

        print(f"\nStatus: {color} {status}")

        # Compare with stored value
        if metrics and stored_dscr:
            if abs(expected_dscr - stored_dscr) < 0.01:
                print(f"✓ Stored DSCR ({stored_dscr:.4f}) matches expected")
            else:
                print(f"✗ Stored DSCR ({stored_dscr:.4f}) differs from expected ({expected_dscr:.4f})")
        elif metrics:
            print(f"✗ DSCR should be {expected_dscr:.4f} but is NULL in database")
    else:
        print("✗ Cannot calculate DSCR - missing NOI or debt service data")

    return {
        "property_id": property_id,
        "property_code": property_code,
        "latest_complete_period": latest_complete_period,
        "stored_noi": stored_noi,
        "calculated_noi_correct": calculated_noi_correct,
        "calculated_noi_wrong": calculated_noi_wrong,
        "stored_noi_in_metrics": stored_noi_fm if metrics else None,
        "total_annual_debt_service": total_annual if mortgages else None,
        "expected_dscr": expected_dscr if stored_noi and total_annual > 0 else None,
        "stored_dscr": stored_dscr if metrics else None,
        "has_complete_data": bool(complete_periods),
    }


def main():
    """Run comprehensive DSCR diagnostics"""
    print_section("DSCR Comprehensive Diagnostic Report")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    db = SessionLocal()

    try:
        # Get all properties
        query = text("SELECT id, property_code, property_name FROM properties ORDER BY property_code")
        result = db.execute(query)
        properties = result.fetchall()

        print(f"\nFound {len(properties)} properties")

        # Diagnose each property
        results = []
        for prop_id, prop_code, prop_name in properties:
            result = diagnose_property(db, prop_id, prop_code, year=2025)
            if result:
                results.append(result)

        # Summary report
        print_section("Summary Report")

        print(f"\n{'Property':<10} {'Period':<10} {'Expected DSCR':<15} {'Stored DSCR':<15} {'Status':<15}")
        print("-" * 70)

        for result in results:
            prop_code = result['property_code']
            period = result['latest_complete_period'][1] if result['latest_complete_period'] else 'N/A'
            expected = f"{result['expected_dscr']:.4f}" if result['expected_dscr'] else 'N/A'
            stored = f"{result['stored_dscr']:.4f}" if result['stored_dscr'] else 'NULL'

            # Determine status
            if result['expected_dscr'] and result['stored_dscr']:
                if abs(result['expected_dscr'] - result['stored_dscr']) < 0.01:
                    status = "✓ CORRECT"
                else:
                    status = "✗ MISMATCH"
            elif result['expected_dscr'] and not result['stored_dscr']:
                status = "✗ NULL"
            else:
                status = "✗ NO DATA"

            print(f"{prop_code:<10} {period:<10} {expected:<15} {stored:<15} {status:<15}")

        # Root cause summary
        print_section("Root Cause Summary")

        noi_issues = sum(1 for r in results if r['stored_noi_in_metrics'] == 0 and r['stored_noi'] > 0)
        dscr_null_issues = sum(1 for r in results if r['expected_dscr'] and not r['stored_dscr'])
        data_missing_issues = sum(1 for r in results if not r['has_complete_data'])

        print(f"\n1. NOI Calculation Bug (stored as $0.00):        {noi_issues} properties")
        print(f"2. DSCR NULL (should be calculated):             {dscr_null_issues} properties")
        print(f"3. Missing Complete Data (income or mortgage):   {data_missing_issues} properties")

        print("\n" + "=" * 80)
        print("Diagnosis Complete!")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()
