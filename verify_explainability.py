
from app.services.forensic_reconciliation_service import ForensicReconciliationService
from app.models.forensic_match import ForensicMatch
from app.db.database import SessionLocal
from decimal import Decimal

# Helper to mock match
def create_mock_match(confidence, amount_diff, match_type):
    return ForensicMatch(
        id=1,
        session_id=1,
        source_document_type='balance_sheet',
        source_record_id=100,
        source_amount=Decimal('1000.00'),
        target_document_type='general_ledger',
        target_record_id=200,
        target_amount=Decimal('1000.00') + Decimal(str(amount_diff)),
        match_type=match_type,
        confidence_score=confidence,
        amount_difference=Decimal(str(amount_diff)),
        amount_difference_percent=Decimal(str(amount_diff)) / 10 if amount_diff != 0 else 0,
        match_algorithm='exact_match' if match_type == 'exact' else 'fuzzy_string',
        status='pending'
    )

def verify_explainability():
    service = ForensicReconciliationService(SessionLocal())
    
    # Case 1: High Confidence
    match1 = create_mock_match(95.0, 0, 'exact')
    reasons1 = service._generate_match_reasons(match1)
    print(f"Match 1 (95% Conf): {reasons1}")
    
    # Case 2: Low Confidence + Variance
    match2 = create_mock_match(60.0, 500, 'fuzzy')
    reasons2 = service._generate_match_reasons(match2)
    print(f"Match 2 (60% Conf, diff 500): {reasons2}")
    
    # Test _match_to_dict
    match_dict = service._match_to_dict(match2)
    print(f"Match 2 Dict keys: {match_dict.keys()}")
    print(f"Match 2 Reasons in dict: {match_dict.get('reasons')}")
    print(f"Match 2 Prior Period Amount: {match_dict.get('prior_period_amount')}")

if __name__ == "__main__":
    verify_explainability()
