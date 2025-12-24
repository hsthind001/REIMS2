"""
Test reconciliation for ESP001, Period 2023-10
This tests the self-learning system with the actual problematic case.
"""
import sys
from app.db.database import SessionLocal
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.services.forensic_reconciliation_service import ForensicReconciliationService
from app.services.account_code_discovery_service import AccountCodeDiscoveryService
from app.services.adaptive_matching_service import AdaptiveMatchingService

def test_esp001_reconciliation():
    """Test reconciliation for ESP001, Period 2023-10"""
    print("=" * 70)
    print("Testing Self-Learning Reconciliation for ESP001, Period 2023-10")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        # Find ESP001 property
        property_obj = db.query(Property).filter(Property.property_code == 'ESP001').first()
        if not property_obj:
            print("❌ Property ESP001 not found in database")
            return
        
        # Find period 2023-10
        period = db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_obj.id,
            FinancialPeriod.period_year == 2023,
            FinancialPeriod.period_month == 10
        ).first()
        
        if not period:
            print("❌ Period 2023-10 not found for ESP001")
            return
        
        print(f"\n✓ Found Property: {property_obj.property_code} (ID: {property_obj.id})")
        print(f"✓ Found Period: {period.period_year}-{period.period_month:02d} (ID: {period.id})")
        
        # Step 1: Discover account codes
        print("\n" + "-" * 70)
        print("Step 1: Account Code Discovery")
        print("-" * 70)
        
        discovery_service = AccountCodeDiscoveryService(db)
        discovery_result = discovery_service.discover_all_account_codes(
            property_id=property_obj.id,
            period_id=period.id
        )
        
        print(f"✓ Discovered {discovery_result['total_codes_discovered']} account codes")
        for doc_type, count in discovery_result['by_document_type'].items():
            if count > 0:
                print(f"  - {doc_type}: {count} codes")
        
        # Step 2: Check what accounts are available for matching
        print("\n" + "-" * 70)
        print("Step 2: Available Accounts for Matching")
        print("-" * 70)
        
        discovered_codes = discovery_service.get_discovered_codes(
            property_id=property_obj.id,
            period_id=period.id
        )
        
        # Group by document type
        by_doc_type = {}
        for code in discovered_codes:
            doc_type = code.document_type
            if doc_type not in by_doc_type:
                by_doc_type[doc_type] = []
            by_doc_type[doc_type].append(code)
        
        for doc_type, codes in by_doc_type.items():
            print(f"\n{doc_type.upper()} ({len(codes)} codes):")
            # Show key accounts that might be used for matching
            key_accounts = ['earnings', 'income', 'rent', 'cash', 'debt', 'mortgage', 'interest']
            for code in codes[:20]:  # Show first 20
                account_lower = code.account_name.lower()
                if any(keyword in account_lower for keyword in key_accounts):
                    print(f"  ⭐ {code.account_code}: {code.account_name} (seen {code.occurrence_count} times)")
        
        # Step 3: Try adaptive matching
        print("\n" + "-" * 70)
        print("Step 3: Adaptive Matching")
        print("-" * 70)
        
        matching_service = AdaptiveMatchingService(db)
        matches = matching_service.find_all_matches(
            property_id=property_obj.id,
            period_id=period.id
        )
        
        print(f"✓ Found {len(matches)} matches using adaptive matching")
        
        if matches:
            print("\nMatch Details:")
            for i, match in enumerate(matches[:10], 1):
                print(f"  {i}. Type: {match.match_type}, Confidence: {match.confidence_score:.2f}%")
                if hasattr(match, 'source_record_id'):
                    print(f"     Source Record ID: {match.source_record_id}")
                if hasattr(match, 'target_record_id'):
                    print(f"     Target Record ID: {match.target_record_id}")
                if hasattr(match, 'amount_difference'):
                    print(f"     Amount Difference: {match.amount_difference}")
        else:
            print("⚠️  No matches found. This could indicate:")
            print("   - Missing required account codes")
            print("   - Account codes don't match expected patterns")
            print("   - Data not yet extracted")
        
        # Step 4: Check diagnostics
        print("\n" + "-" * 70)
        print("Step 4: Diagnostics & Recommendations")
        print("-" * 70)
        
        from app.services.reconciliation_diagnostics_service import ReconciliationDiagnosticsService
        diagnostics_service = ReconciliationDiagnosticsService(db)
        diagnostics = diagnostics_service.get_diagnostics(property_obj.id, period.id)
        
        print("\nMissing Accounts:")
        missing_found = False
        for doc_type, missing_list in diagnostics['missing_accounts'].items():
            if missing_list:
                missing_found = True
                print(f"  {doc_type}:")
                for missing in missing_list[:5]:
                    print(f"    - {missing}")
        
        if not missing_found:
            print("  ✓ No critical accounts missing")
        
        print("\nRecommendations:")
        for rec in diagnostics['recommendations']:
            print(f"  • {rec}")
        
        # Step 5: Summary
        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"✓ Account codes discovered: {discovery_result['total_codes_discovered']}")
        print(f"✓ Matches found: {len(matches)}")
        print(f"✓ Patterns created: {discovery_result.get('patterns_created', 0)}")
        print(f"✓ Semantic mappings: {discovery_result.get('semantic_mappings_created', 0)}")
        
        if len(matches) > 0:
            print("\n✅ SUCCESS: Adaptive matching found matches!")
            print("   The self-learning system is working correctly.")
        else:
            print("\n⚠️  WARNING: No matches found.")
            print("   Check recommendations above for next steps.")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_esp001_reconciliation()

