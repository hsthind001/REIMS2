import sys
from sqlalchemy import select, func

# Add /app to path
sys.path.append('/app')

from app.db.database import SessionLocal
from app.models.cash_flow_adjustments import CashFlowAdjustment
from app.models.cash_flow_data import CashFlowData

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print(f"Checking CapEx data for Property {property_id}, Period {period_id}...")
        
        # 1. Check Adjustments
        adjustments = db.execute(
            select(CashFlowAdjustment)
            .where(
                CashFlowAdjustment.property_id == property_id,
                CashFlowAdjustment.period_id == period_id
            )
        ).scalars().all()
        
        print(f"Total Adjustments Found: {len(adjustments)}")
        for adj in adjustments:
            print(f" - [{adj.adjustment_category}] {adj.adjustment_name}: {adj.amount}")
            
        # 2. Check Raw Cash Flow Data (Investing Activities)
        # Often CapEx is in Investing Activities
        cf_items = db.execute(
            select(CashFlowData)
            .where(
                CashFlowData.property_id == property_id,
                CashFlowData.period_id == period_id,
                # Simple check for likely CapEx keywords or section
                CashFlowData.line_section.ilike('%investing%')
            )
        ).scalars().all()
        
        print(f"\nPotential CapEx Items in CashFlowData (Investing Section):")
        for item in cf_items:
            print(f" - {item.account_name} ({item.account_code or 'No Code'}): {item.period_amount}")

        # 3. Check for CapEx keywords anywhere
        capex_keywords = ['improvements', 'construction', 'capex', 'capital', 'renovation', 'roof', 'hvac']
        print(f"\nSearching all CF items for keywords: {capex_keywords}")
        for keyword in capex_keywords:
             keyword_items = db.execute(
                select(CashFlowData)
                .where(
                    CashFlowData.property_id == property_id,
                    CashFlowData.period_id == period_id,
                    CashFlowData.account_name.ilike(f'%{keyword}%')
                )
            ).scalars().all()
             for item in keyword_items:
                 print(f" - [MATCH: {keyword}] [Section: {item.line_section}] {item.account_name}: {item.period_amount}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
