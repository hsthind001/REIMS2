"""
Run Forensic Audit for Property 11, Period 169

Populate Financial Integrity Hub with reconciliation data
"""
import sys
import asyncio
sys.path.append('/app')

from app.db.database import SessionLocal
from app.services.cross_document_reconciliation_service import CrossDocumentReconciliationService
from app.db.database import AsyncSessionWrapper

async def run_audit():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print("=" * 80)
        print("RUNNING FORENSIC AUDIT / CROSS-DOCUMENT RECONCILIATIONS")
        print("=" * 80)
        print(f"Property: {property_id}, Period: {period_id}\n")
        
        # Wrap sync session for async service
        async_db = AsyncSessionWrapper(db)
        service = CrossDocumentReconciliationService(async_db)
        
        print("Executing all reconciliations...")
        results = await service.run_all_reconciliations(property_id, period_id)
        
        print(f"\n✅ Reconciliation complete!")
        print(f"Total reconciliations: {len(results)}")
        
        # Show summary
        passed = sum(1 for r in results if r.get('status') == 'PASS')
        failed = sum(1 for r in results if r.get('status') == 'FAIL')
        warnings = sum(1 for r in results if r.get('status') == 'WARNING')
        
        print(f"\nResults:")
        print(f"  ✅ Passed: {passed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  ⚠️  Warnings: {warnings}")
        
        print(f"\nReconciliation Details:")
        for r in results:
            status_icon = "✅" if r.get('status') == 'PASS' else ("⚠️" if r.get('status') == 'WARNING' else "❌")
            print(f"  {status_icon} {r.get('reconciliation_type')}: {r.get('status')}")
            if r.get('variance_amount'):
                print(f"     Variance: ${float(r.get('variance_amount')):,.2f}")
        
        return results

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        return []
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_audit())
