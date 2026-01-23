#!/usr/bin/env python3
"""
Manually regenerate scorecard for property 11, period 169
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.services.audit_scorecard_generator_service import AuditScorecardGeneratorService
from app.core.database import get_session_context
from uuid import UUID


async def regenerate_scorecard():
    """Regenerate scorecard with fixed logic"""
    
    property_id = UUID("00000000-0000-0000-0000-00000000000b")  # ID 11
    period_id = UUID("00000000-0000-0000-0000-0000000000a9")    # ID 169
    
    print(f"Regenerating scorecard for property {property_id}, period {period_id}")
    
    async with get_session_context() as db:
        service = AuditScorecardGeneratorService(db)
        
        try:
            scorecard = await service.generate_scorecard(property_id, period_id)
            
            cash_balance = scorecard.get("financial_summary", {}).get("cash_balance", 0)
            
            print(f"\n✅ Scorecard generated successfully!")
            print(f"Cash Balance in scorecard: ${cash_balance:,.2f}")
            
            if cash_balance > 1500000:
                print(f"✅ SUCCESS! Cash balance shows correct value!")
            else:
                print(f"❌ ISSUE! Cash balance is still $0")
                
        except Exception as e:
            print(f"❌ Error generating scorecard: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(regenerate_scorecard())
