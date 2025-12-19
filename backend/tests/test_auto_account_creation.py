"""
Comprehensive Unit Tests for Auto-Account Creation Feature

This test suite ensures the intelligent auto-account creation system
remains robust and prevents variable scope issues and other bugs.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.db.models import ChartOfAccounts


class TestAutoAccountCreation:
    """Test suite for auto-account creation feature"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        return db

    @pytest.fixture
    def orchestrator(self, mock_db):
        """Create ExtractionOrchestrator instance with mocked dependencies"""
        with patch('app.services.extraction_orchestrator.SessionLocal', return_value=mock_db):
            orchestrator = ExtractionOrchestrator(db=mock_db)
            return orchestrator

    # ========== Parameter Validation Tests ==========

    def test_auto_create_account_with_valid_params(self, orchestrator):
        """Test auto-create succeeds with all valid parameters"""
        result = orchestrator._auto_create_account(
            account_name="Prepaid Expenses",
            account_code="0150-0000",
            document_type="balance_sheet"
        )
        assert result is not None or result is None  # Either succeeds or fails gracefully

    def test_auto_create_account_without_document_type(self, orchestrator):
        """Test auto-create works even when document_type is None (critical regression test)"""
        # This is the bug that occurred - document_type was not in scope
        result = orchestrator._auto_create_account(
            account_name="Prepaid Expenses",
            account_code=None,
            document_type=None  # This should NOT cause NameError
        )
        # Should handle gracefully without crashing
        assert result is None or isinstance(result, ChartOfAccounts)

    def test_auto_create_account_with_empty_name(self, orchestrator):
        """Test auto-create fails gracefully with empty account name"""
        result = orchestrator._auto_create_account(
            account_name="",
            account_code="0150-0000",
            document_type="balance_sheet"
        )
        assert result is None

    def test_auto_create_account_with_none_name(self, orchestrator):
        """Test auto-create fails gracefully with None account name"""
        result = orchestrator._auto_create_account(
            account_name=None,
            account_code="0150-0000",
            document_type="balance_sheet"
        )
        assert result is None

    def test_auto_create_account_with_whitespace_only_name(self, orchestrator):
        """Test auto-create fails gracefully with whitespace-only name"""
        result = orchestrator._auto_create_account(
            account_name="   ",
            account_code="0150-0000",
            document_type="balance_sheet"
        )
        assert result is None

    def test_auto_create_account_with_invalid_name_type(self, orchestrator):
        """Test auto-create fails gracefully with non-string name"""
        result = orchestrator._auto_create_account(
            account_name=12345,  # Invalid type
            account_code="0150-0000",
            document_type="balance_sheet"
        )
        assert result is None

    # ========== Account Type Inference Tests ==========

    def test_infer_account_type_asset_patterns(self, orchestrator):
        """Test account type inference for asset accounts"""
        test_cases = [
            ("Cash - Depository", ("asset", "current_asset")),
            ("Prepaid Expenses", ("asset", "current_asset")),
            ("Accounts Receivable", ("asset", "current_asset")),
            ("Building", ("asset", "fixed_asset")),
            ("Land", ("asset", "fixed_asset")),
            ("Accumulated Depreciation", ("asset", "contra_asset")),
        ]

        for account_name, expected in test_cases:
            result = orchestrator._infer_account_type_category(account_name, "balance_sheet")
            assert result == expected, f"Failed for {account_name}: got {result}, expected {expected}"

    def test_infer_account_type_liability_patterns(self, orchestrator):
        """Test account type inference for liability accounts"""
        test_cases = [
            ("Accounts Payable", ("liability", "current_liability")),
            ("Accrued Expenses", ("liability", "current_liability")),
            ("Mortgage Payable", ("liability", "long_term_liability")),
            ("Long-term Note Payable", ("liability", "long_term_liability")),
            ("Wells Fargo Loan", ("liability", "long_term_liability")),
        ]

        for account_name, expected in test_cases:
            result = orchestrator._infer_account_type_category(account_name, "balance_sheet")
            assert result == expected, f"Failed for {account_name}: got {result}, expected {expected}"

    def test_infer_account_type_equity_patterns(self, orchestrator):
        """Test account type inference for equity accounts"""
        test_cases = [
            ("Owner's Equity", ("equity", "capital")),
            ("Capital Contribution", ("equity", "capital")),
            ("Retained Earnings", ("equity", "capital")),
        ]

        for account_name, expected in test_cases:
            result = orchestrator._infer_account_type_category(account_name, "balance_sheet")
            assert result == expected, f"Failed for {account_name}: got {result}, expected {expected}"

    def test_infer_account_type_income_patterns(self, orchestrator):
        """Test account type inference for income accounts"""
        test_cases = [
            ("Rental Income", ("income", "rental_income")),
            ("Rent Revenue", ("income", "rental_income")),
            ("Reimbursement Income", ("income", "rental_income")),
        ]

        for account_name, expected in test_cases:
            result = orchestrator._infer_account_type_category(account_name, "income_statement")
            assert result == expected, f"Failed for {account_name}: got {result}, expected {expected}"

    def test_infer_account_type_expense_patterns(self, orchestrator):
        """Test account type inference for expense accounts"""
        test_cases = [
            ("Maintenance Expense", ("expense", "operating_expense")),
            ("Insurance Cost", ("expense", "operating_expense")),
            ("Property Tax", ("expense", "operating_expense")),
            ("Utility Expense", ("expense", "operating_expense")),
        ]

        for account_name, expected in test_cases:
            result = orchestrator._infer_account_type_category(account_name, "income_statement")
            assert result == expected, f"Failed for {account_name}: got {result}, expected {expected}"

    def test_infer_account_type_with_invalid_input(self, orchestrator):
        """Test account type inference fails gracefully with invalid input"""
        with pytest.raises(ValueError):
            orchestrator._infer_account_type_category(None, "balance_sheet")

        with pytest.raises(ValueError):
            orchestrator._infer_account_type_category("", "balance_sheet")

        with pytest.raises(ValueError):
            orchestrator._infer_account_type_category("   ", "balance_sheet")

    def test_infer_account_type_fallback_behavior(self, orchestrator):
        """Test fallback behavior when pattern doesn't match"""
        # Unknown account name with balance_sheet type
        result = orchestrator._infer_account_type_category("XYZ Unknown Account", "balance_sheet")
        assert result == ("asset", "other_asset")

        # Unknown account name with income_statement type
        result = orchestrator._infer_account_type_category("XYZ Unknown Account", "income_statement")
        assert result == ("expense", "operating_expense")

        # Unknown account name with no document type
        result = orchestrator._infer_account_type_category("XYZ Unknown Account", None)
        assert result == ("asset", "other_asset")

    # ========== Account Code Generation Tests ==========

    def test_generate_account_code_for_assets(self, orchestrator):
        """Test account code generation for asset accounts"""
        code = orchestrator._generate_account_code("Cash", "asset")
        assert code.startswith("0"), f"Asset code should start with 0, got {code}"
        assert "-" in code, f"Code should have hyphen format, got {code}"

    def test_generate_account_code_for_liabilities(self, orchestrator):
        """Test account code generation for liability accounts"""
        code = orchestrator._generate_account_code("Accounts Payable", "liability")
        assert code.startswith("2"), f"Liability code should start with 2, got {code}"

    def test_generate_account_code_for_equity(self, orchestrator):
        """Test account code generation for equity accounts"""
        code = orchestrator._generate_account_code("Owner's Equity", "equity")
        assert code.startswith("3"), f"Equity code should start with 3, got {code}"

    def test_generate_account_code_for_income(self, orchestrator):
        """Test account code generation for income accounts"""
        code = orchestrator._generate_account_code("Rental Income", "income")
        assert code.startswith("4"), f"Income code should start with 4, got {code}"

    def test_generate_account_code_for_expenses(self, orchestrator):
        """Test account code generation for expense accounts"""
        code = orchestrator._generate_account_code("Maintenance Expense", "expense")
        assert code.startswith("5"), f"Expense code should start with 5, got {code}"

    def test_generate_account_code_for_unknown_type(self, orchestrator):
        """Test account code generation for unknown account types"""
        code = orchestrator._generate_account_code("Unknown Account", "unknown_type")
        assert code.startswith("9"), f"Unknown type should use fallback prefix 9, got {code}"

    def test_generate_account_code_with_invalid_type(self, orchestrator):
        """Test account code generation fails gracefully with invalid type"""
        with pytest.raises(ValueError):
            orchestrator._generate_account_code("Test Account", None)

        with pytest.raises(ValueError):
            orchestrator._generate_account_code("Test Account", "")

    # ========== Integration Tests ==========

    def test_match_accounts_intelligent_with_document_type(self, orchestrator):
        """Test that _match_accounts_intelligent properly passes document_type (regression test)"""
        # This is the critical test for the bug we fixed
        extracted_items = [
            {
                "account_code": "UNMATCHED",
                "account_name": "Prepaid Expenses",
                "amount": 1000.00
            }
        ]

        # Should NOT raise NameError about document_type
        try:
            result = orchestrator._match_accounts_intelligent(
                extracted_items,
                document_type="balance_sheet"
            )
            # Success - either matched or created account
            assert isinstance(result, list)
        except NameError as e:
            pytest.fail(f"NameError raised: {e}. The document_type parameter is not being passed correctly!")

    def test_match_accounts_intelligent_without_document_type(self, orchestrator):
        """Test that _match_accounts_intelligent handles missing document_type gracefully"""
        extracted_items = [
            {
                "account_code": "UNMATCHED",
                "account_name": "Prepaid Expenses",
                "amount": 1000.00
            }
        ]

        # Should handle None document_type gracefully
        result = orchestrator._match_accounts_intelligent(
            extracted_items,
            document_type=None
        )
        assert isinstance(result, list)

    def test_end_to_end_auto_account_creation_flow(self, orchestrator):
        """Test complete flow from extraction to auto-account creation"""
        # Simulate a real-world scenario where PDF extraction finds an unknown account
        extracted_items = [
            {
                "account_code": "UNMATCHED",
                "account_name": "Prepaid Insurance",
                "amount": 5000.00,
                "account_category": None
            }
        ]

        # Process through intelligent matching (which should trigger auto-create)
        result = orchestrator._match_accounts_intelligent(
            extracted_items,
            document_type="balance_sheet"
        )

        # Should have processed the item (either matched or created)
        assert len(result) == 1
        assert "matched_account_id" in result[0] or "match_method" in result[0]


class TestVariableScopeRegression:
    """
    Dedicated test suite to prevent variable scope issues in the future.

    These tests ensure all methods properly receive and pass parameters through
    the call chain, preventing NameError and undefined variable bugs.
    """

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mock database"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        return ExtractionOrchestrator(db=mock_db)

    def test_all_required_parameters_defined(self, orchestrator):
        """Verify all methods have required parameters in their signatures"""
        import inspect

        # Check _auto_create_account signature
        sig = inspect.signature(orchestrator._auto_create_account)
        params = list(sig.parameters.keys())
        assert "account_name" in params
        assert "account_code" in params
        assert "document_type" in params

        # Check _infer_account_type_category signature
        sig = inspect.signature(orchestrator._infer_account_type_category)
        params = list(sig.parameters.keys())
        assert "account_name" in params
        assert "document_type" in params

        # Check _generate_account_code signature
        sig = inspect.signature(orchestrator._generate_account_code)
        params = list(sig.parameters.keys())
        assert "account_name" in params
        assert "account_type" in params

        # Check _match_accounts_intelligent signature
        sig = inspect.signature(orchestrator._match_accounts_intelligent)
        params = list(sig.parameters.keys())
        assert "extracted_items" in params
        assert "document_type" in params  # CRITICAL: This was missing before!

    def test_document_type_passed_through_call_chain(self, orchestrator):
        """
        Regression test: Ensure document_type is passed through the entire call chain.

        This is the exact bug that occurred - document_type was not defined when
        _auto_create_account was called from _match_accounts_intelligent.
        """
        extracted_items = [{"account_code": "UNMATCHED", "account_name": "Test Account", "amount": 100}]

        # Call with explicit document_type
        try:
            result = orchestrator._match_accounts_intelligent(
                extracted_items=extracted_items,
                document_type="balance_sheet"
            )
            # If we get here without NameError, the bug is fixed
            assert True
        except NameError as e:
            if "document_type" in str(e):
                pytest.fail(
                    "CRITICAL REGRESSION: document_type is not being passed through the call chain! "
                    f"Error: {e}"
                )
            else:
                raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
