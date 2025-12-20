"""
Test Account Code Mapping

Tests the _extract_parent_account_code method
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import SessionLocal
from app.services.variance_analysis_service import VarianceAnalysisService

def test_account_mapping():
    """Test account code mapping logic"""
    db = SessionLocal()
    service = VarianceAnalysisService(db)

    test_cases = [
        ("4010-0000", "40000"),
        ("4020-0000", "40000"),
        ("4030-0000", "40000"),
        ("5010-0000", "50000"),
        ("5110-0000", "51000"),
        ("5200-0000", "52000"),
        ("40000", "40000"),
        ("50000", "50000"),
        ("41000", "41000"),
    ]

    print("\n" + "="*70)
    print("Testing Account Code Mapping")
    print("="*70 + "\n")

    all_passed = True

    for input_code, expected_output in test_cases:
        actual_output = service._extract_parent_account_code(input_code)
        passed = actual_output == expected_output

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {input_code:15} -> {actual_output:10} (expected: {expected_output})")

        if not passed:
            all_passed = False

    print("\n" + "="*70)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("="*70 + "\n")

    db.close()

if __name__ == "__main__":
    test_account_mapping()
