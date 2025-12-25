"""
Unit tests for ReconciliationService helpers
"""
from decimal import Decimal
from unittest.mock import Mock

from app.services.reconciliation_service import ReconciliationService


class DummyMortgageRecord:
    """Simple record for mortgage data tests"""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, name):
        # Return None for unspecified attributes so float() is not invoked on Mock objects
        return None


def test_get_mortgage_statement_pdf_data_returns_account_info():
    mock_db = Mock()
    service = ReconciliationService(mock_db)

    record = DummyMortgageRecord(
        id=7,
        loan_number="L-007",
        borrower_name="Eastern Shore Loan",
        property_address="10200 Eastern Shore Blvd",
        principal_balance=Decimal("22270577.83"),
        total_loan_balance=Decimal("22270577.83"),
        extraction_confidence=Decimal("91.5"),
        needs_review=False,
        extraction_method="template_patterns",
        validation_score=Decimal("99.0"),
        has_errors=False
    )

    query = Mock()
    mock_db.query.return_value = query
    query.filter.return_value = query
    query.all.return_value = [record]

    data = service._get_mortgage_statement_pdf_data(1, 1)
    key = str(record.id)
    assert key in data

    entry = data[key]
    assert entry["account_code"] == "L-007"
    assert "Principal Balance" in entry["account_name"]
    assert entry["amount"] == float(record.principal_balance)
    assert entry["extraction_confidence"] == float(record.extraction_confidence)
    assert entry["needs_review"] is False
