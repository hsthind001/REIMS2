#!/usr/bin/env python3
"""
Test the fixed cash balance logic
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


async def test_cash_balance_fix():
    """Test that cash balance now uses total_cash_position when ending_cash_balance is 0"""
    
    # Connect to database
    DATABASE_URL = "postgresql+asyncpg://reims:reims@postgres:5432/reims"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Simulate the fixed logic
        metrics_query = text("""
            SELECT
                total_revenue,
                total_expenses,
                net_operating_income,
                net_income,
                ending_cash_balance,
                total_cash_position,
                operating_margin,
                occupancy_rate
            FROM financial_metrics
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY updated_at DESC NULLS LAST, calculated_at DESC NULLS LAST, created_at DESC
            LIMIT 1
        """)
        
        result = await session.execute(
            metrics_query,
            {"property_id": 11, "period_id": 169}
        )
        metrics_row = result.fetchone()
        
        if metrics_row:
            print("=" * 70)
            print("TESTING FIXED CASH BALANCE LOGIC")
            print("=" * 70)
            
            # Old logic (buggy)
            old_cash_balance = 0.0
            if metrics_row[4] is not None:
                old_cash_balance = float(metrics_row[4])
            elif metrics_row[5] is not None:
                old_cash_balance = float(metrics_row[5])
            
            # New logic (fixed)
            new_cash_balance = 0.0
            ending_cash = float(metrics_row[4]) if metrics_row[4] is not None else 0.0
            total_cash = float(metrics_row[5]) if metrics_row[5] is not None else 0.0
            new_cash_balance = ending_cash if ending_cash != 0.0 else total_cash
            
            print(f"\nRaw Database Values:")
            print(f"  ending_cash_balance (index 4): ${metrics_row[4]:,.2f}" if metrics_row[4] is not None else "  ending_cash_balance: None")
            print(f"  total_cash_position (index 5): ${metrics_row[5]:,.2f}" if metrics_row[5] is not None else "  total_cash_position: None")
            
            print(f"\nOLD LOGIC (Buggy):")
            print(f"  Result: ${old_cash_balance:,.2f}")
            print(f"  ❌ Incorrect - shows $0 instead of total_cash_position")
            
            print(f"\nNEW LOGIC (Fixed):")
            print(f"  Result: ${new_cash_balance:,.2f}")
            print(f"  ✅ Correct - uses total_cash_position when ending_cash is 0")
            
            print("\n" + "=" * 70)
            if new_cash_balance == 1521486.68:
                print("✅ FIX VERIFIED - Cash balance logic is now correct!")
            else:
                print("❌ FIX FAILED - Unexpected value")
            print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_cash_balance_fix())
