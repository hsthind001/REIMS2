#!/usr/bin/env python3
"""
Verify Forensic Audit Dashboard figures for 2025-10
Checks the actual data in financial_metrics table
"""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def verify_2025_10_figures():
    """Verify financial figures for 2025-10"""
    
    # Connect to database
    DATABASE_URL = "postgresql+asyncpg://reims:reims@postgres:5432/reims"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # First find the period_id for 2025-10
        period_query = text("""
            SELECT fp.id, fp.property_id, p.property_name
            FROM financial_periods fp
            JOIN properties p ON p.id = fp.property_id
            WHERE fp.period_year = 2025 AND fp.period_month = 10
        """)
        
        result = await session.execute(period_query)
        period_row = result.fetchone()
        
        if not period_row:
            print("❌ No period found for 2025-10")
            return
        
        period_id = period_row[0]
        property_id = period_row[1]
        property_name = period_row[2]
        
        print(f"🔍 Checking for Property: {property_name}")
        print(f"   Period ID: {period_id}")
        print(f"   Property ID: {property_id}")
        print()
        
        # Query financial_metrics table
        metrics_query = text("""
            SELECT
                total_revenue,
                total_expenses,
                net_operating_income,
                net_income,
                ending_cash_balance,
                total_cash_position,
                operating_margin,
                occupancy_rate,
                updated_at,
                calculated_at,
                created_at
            FROM financial_metrics
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY updated_at DESC NULLS LAST, calculated_at DESC NULLS LAST, created_at DESC
            LIMIT 1
        """)
        
        result = await session.execute(
            metrics_query,
            {"property_id": property_id, "period_id": period_id}
        )
        metrics_row = result.fetchone()
        
        print("=" * 70)
        print("FINANCIAL METRICS TABLE VALUES FOR 2025-10")
        print("=" * 70)
        
        if not metrics_row:
            print("❌ No financial_metrics record found for 2025-10")
        else:
            total_revenue = float(metrics_row[0]) if metrics_row[0] is not None else 0.0
            total_expenses = float(metrics_row[1]) if metrics_row[1] is not None else 0.0
            noi = float(metrics_row[2]) if metrics_row[2] is not None else 0.0
            net_income = float(metrics_row[3]) if metrics_row[3] is not None else 0.0
            ending_cash = float(metrics_row[4]) if metrics_row[4] is not None else 0.0
            total_cash = float(metrics_row[5]) if metrics_row[5] is not None else 0.0
            
            cash_balance = ending_cash if ending_cash else total_cash
            
            print(f"Total Revenue:       ${total_revenue:,.2f}")
            print(f"Total Expenses:      ${total_expenses:,.2f}")
            print(f"NOI:                 ${noi:,.2f}")
            print(f"Net Income:          ${net_income:,.2f}")
            print(f"Ending Cash Balance: ${ending_cash:,.2f}")
            print(f"Total Cash Position: ${total_cash:,.2f}")
            print(f"Cash Balance (used): ${cash_balance:,.2f}")
            print()
            print(f"Last Updated:        {metrics_row[8]}")
            print(f"Calculated At:       {metrics_row[9]}")
            print(f"Created At:          {metrics_row[10]}")
            
        print()
        print("=" * 70)
        print("UI DASHBOARD SHOWS (from screenshot)")
        print("=" * 70)
        print("Total Revenue:       $565,649")
        print("Net Income:          $32,721")
        print("NOI:                 $338,869")
        print("Cash Balance:        $0")
        print()
        
        if metrics_row:
            print("=" * 70)
            print("COMPARISON")
            print("=" * 70)
            
            ui_revenue = 565649.0
            ui_net_income = 32721.0
            ui_noi = 338869.0
            ui_cash = 0.0
            
            revenue_match = abs(total_revenue - ui_revenue) < 1.0
            net_income_match = abs(net_income - ui_net_income) < 1.0
            noi_match = abs(noi - ui_noi) < 1.0
            cash_match = abs(cash_balance - ui_cash) < 1.0
            
            print(f"Total Revenue:  {'✅ MATCH' if revenue_match else '❌ MISMATCH'}")
            if not revenue_match:
                print(f"  DB: ${total_revenue:,.2f}  vs  UI: ${ui_revenue:,.2f}  (Diff: ${total_revenue - ui_revenue:,.2f})")
            
            print(f"Net Income:     {'✅ MATCH' if net_income_match else '❌ MISMATCH'}")
            if not net_income_match:
                print(f"  DB: ${net_income:,.2f}  vs  UI: ${ui_net_income:,.2f}  (Diff: ${net_income - ui_net_income:,.2f})")
            
            print(f"NOI:            {'✅ MATCH' if noi_match else '❌ MISMATCH'}")
            if not noi_match:
                print(f"  DB: ${noi:,.2f}  vs  UI: ${ui_noi:,.2f}  (Diff: ${noi - ui_noi:,.2f})")
            
            print(f"Cash Balance:   {'✅ MATCH' if cash_match else '❌ MISMATCH'}")
            if not cash_match:
                print(f"  DB: ${cash_balance:,.2f}  vs  UI: ${ui_cash:,.2f}  (Diff: ${cash_balance - ui_cash:,.2f})")
            
            print()
            if revenue_match and net_income_match and noi_match and cash_match:
                print("✅ ALL FIGURES MATCH - Dashboard is displaying correct data!")
            else:
                print("❌ DISCREPANCIES FOUND - Dashboard may have issues!")
        
        # Also check if there are multiple records
        count_query = text("""
            SELECT COUNT(*)
            FROM financial_metrics
            WHERE property_id = :property_id
            AND period_id = :period_id
        """)
        
        result = await session.execute(
            count_query,
            {"property_id": property_id, "period_id": period_id}
        )
        count = result.scalar()
        
        if count > 1:
            print()
            print(f"⚠️  WARNING: Found {count} records in financial_metrics for this period")
            print("   The query uses ORDER BY to get the most recent, but this may indicate duplicate data")


if __name__ == "__main__":
    asyncio.run(verify_2025_10_figures())
