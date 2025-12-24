"""
Test script for self-learning forensic reconciliation system

This script tests the basic functionality of the self-learning system.
Run with: docker compose exec backend python3 test_self_learning_reconciliation.py
"""
import sys
from app.db.database import SessionLocal
from app.services.account_code_discovery_service import AccountCodeDiscoveryService
from app.services.reconciliation_diagnostics_service import ReconciliationDiagnosticsService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

def test_account_discovery():
    """Test account code discovery"""
    print("\n=== Testing Account Code Discovery ===")
    db = SessionLocal()
    try:
        # Get first property and period
        property_obj = db.query(Property).first()
        period = db.query(FinancialPeriod).first()
        
        if not property_obj or not period:
            print("⚠️  No property or period found in database. Skipping discovery test.")
            return
        
        print(f"Testing with Property ID: {property_obj.id}, Period ID: {period.id}")
        
        discovery_service = AccountCodeDiscoveryService(db)
        result = discovery_service.discover_all_account_codes(
            property_id=property_obj.id,
            period_id=period.id
        )
        
        print(f"✓ Discovery completed:")
        print(f"  - Total codes discovered: {result.get('total_codes_discovered', 0)}")
        print(f"  - By document type: {result.get('by_document_type', {})}")
        print(f"  - Patterns created: {result.get('patterns_created', 0)}")
        print(f"  - Semantic mappings created: {result.get('semantic_mappings_created', 0)}")
        
    except Exception as e:
        print(f"✗ Error in account discovery: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def test_diagnostics():
    """Test diagnostics service"""
    print("\n=== Testing Diagnostics Service ===")
    db = SessionLocal()
    try:
        # Get first property and period
        property_obj = db.query(Property).first()
        period = db.query(FinancialPeriod).first()
        
        if not property_obj or not period:
            print("⚠️  No property or period found in database. Skipping diagnostics test.")
            return
        
        print(f"Testing with Property ID: {property_obj.id}, Period ID: {period.id}")
        
        diagnostics_service = ReconciliationDiagnosticsService(db)
        diagnostics = diagnostics_service.get_diagnostics(
            property_id=property_obj.id,
            period_id=period.id
        )
        
        print(f"✓ Diagnostics generated:")
        print(f"  - Data availability: {len(diagnostics.get('data_availability', {}))} document types checked")
        print(f"  - Discovered accounts: {len(diagnostics.get('discovered_accounts', {}))} document types")
        print(f"  - Missing accounts: {sum(len(v) for v in diagnostics.get('missing_accounts', {}).values())} total")
        print(f"  - Suggested fixes: {len(diagnostics.get('suggested_fixes', []))}")
        print(f"  - Recommendations: {len(diagnostics.get('recommendations', []))}")
        
        if diagnostics.get('recommendations'):
            print(f"\n  Recommendations:")
            for rec in diagnostics.get('recommendations', [])[:3]:
                print(f"    - {rec}")
        
    except Exception as e:
        print(f"✗ Error in diagnostics: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def test_adaptive_matching():
    """Test adaptive matching service"""
    print("\n=== Testing Adaptive Matching Service ===")
    db = SessionLocal()
    try:
        from app.services.adaptive_matching_service import AdaptiveMatchingService
        
        # Get first property and period
        property_obj = db.query(Property).first()
        period = db.query(FinancialPeriod).first()
        
        if not property_obj or not period:
            print("⚠️  No property or period found in database. Skipping adaptive matching test.")
            return
        
        print(f"Testing with Property ID: {property_obj.id}, Period ID: {period.id}")
        
        matching_service = AdaptiveMatchingService(db)
        
        # Test discovery first
        discovery_service = matching_service.discovery_service
        discovery_result = discovery_service.discover_all_account_codes(
            property_id=property_obj.id,
            period_id=period.id
        )
        print(f"✓ Account discovery completed: {discovery_result.get('total_codes_discovered', 0)} codes")
        
        # Try to find matches (this will use adaptive rules)
        print("  Attempting to find matches using adaptive rules...")
        matches = matching_service.find_all_matches(
            property_id=property_obj.id,
            period_id=period.id
        )
        print(f"✓ Found {len(matches)} matches using adaptive matching")
        
        if matches:
            print(f"  Sample matches:")
            for match in matches[:3]:
                print(f"    - {match.match_type}: confidence={match.confidence_score:.2f}")
        
    except Exception as e:
        print(f"✗ Error in adaptive matching: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def main():
    """Run all tests"""
    print("=" * 60)
    print("Self-Learning Forensic Reconciliation System Tests")
    print("=" * 60)
    
    test_account_discovery()
    test_diagnostics()
    test_adaptive_matching()
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()

