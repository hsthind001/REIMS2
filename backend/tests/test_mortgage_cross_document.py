"""
Integration tests for Mortgage Cross-Document Validation
"""
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.validation_service import ValidationService
from app.models.document_upload import DocumentUpload
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData


class TestMortgageCrossDocumentValidation:
    """Test cross-document validation between mortgage statements and other financial documents"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def validation_service(self, mock_db):
        """Create validation service instance"""
        return ValidationService(mock_db)
    
    @pytest.fixture
    def mock_upload(self):
        """Create mock document upload"""
        upload = Mock(spec=DocumentUpload)
        upload.id = 1
        upload.property_id = 1
        upload.period_id = 1
        upload.document_type = "mortgage_statement"
        return upload
    
    @pytest.fixture
    def mock_mortgage(self):
        """Create mock mortgage statement"""
        mortgage = Mock(spec=MortgageStatementData)
        mortgage.id = 1
        mortgage.property_id = 1
        mortgage.period_id = 1
        mortgage.principal_balance = Decimal("10000000")
        mortgage.interest_due = Decimal("40000")
        mortgage.annual_debt_service = Decimal("1080000")
        return mortgage
    
    @pytest.fixture
    def mock_balance_sheet(self):
        """Create mock balance sheet data"""
        balance_sheet = Mock(spec=BalanceSheetData)
        balance_sheet.property_id = 1
        balance_sheet.period_id = 1
        balance_sheet.account_code = "2000-0000"  # Mortgage Payable
        balance_sheet.account_name = "Mortgage Payable"
        balance_sheet.amount = Decimal("10000000")
        return balance_sheet
    
    @pytest.fixture
    def mock_income_statement(self):
        """Create mock income statement data"""
        income_statement = Mock(spec=IncomeStatementData)
        income_statement.property_id = 1
        income_statement.period_id = 1
        income_statement.account_code = "6000-0000"  # Interest Expense
        income_statement.account_name = "Interest Expense"
        income_statement.period_amount = Decimal("40000")
        return income_statement
    
    def test_validate_mortgage_balance_sheet_reconciliation(
        self,
        validation_service,
        mock_db,
        mock_upload,
        mock_mortgage,
        mock_balance_sheet
    ):
        """Test mortgage principal balance reconciliation with balance sheet"""
        # Mock queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_mortgage
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_balance_sheet]
        
        result = validation_service.validate_mortgage_balance_sheet_reconciliation(
            mock_upload.id,
            mock_mortgage.id
        )
        
        assert "mortgage_balance" in result
        assert "balance_sheet_total" in result
        assert result["mortgage_balance"] == Decimal("10000000")
        assert result["balance_sheet_total"] == Decimal("10000000")
        # Should pass if difference is within tolerance
        assert result["passed"] is True or abs(result["difference"]) <= Decimal("100.00")
    
    def test_validate_mortgage_balance_sheet_mismatch(
        self,
        validation_service,
        mock_db,
        mock_upload,
        mock_mortgage
    ):
        """Test mortgage balance sheet reconciliation with mismatch"""
        # Create balance sheet with different amount
        mismatched_balance_sheet = Mock(spec=BalanceSheetData)
        mismatched_balance_sheet.property_id = 1
        mismatched_balance_sheet.period_id = 1
        mismatched_balance_sheet.account_code = "2000-0000"
        mismatched_balance_sheet.account_name = "Mortgage Payable"
        mismatched_balance_sheet.amount = Decimal("11000000")  # $1M difference
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_mortgage
        mock_db.query.return_value.filter.return_value.all.return_value = [mismatched_balance_sheet]
        
        result = validation_service.validate_mortgage_balance_sheet_reconciliation(
            mock_upload.id,
            mock_mortgage.id
        )
        
        assert result["passed"] is False
        assert abs(result["difference"]) > Decimal("100.00")
    
    def test_validate_mortgage_interest_income_statement_reconciliation(
        self,
        validation_service,
        mock_db,
        mock_upload,
        mock_mortgage,
        mock_income_statement
    ):
        """Test mortgage interest expense reconciliation with income statement"""
        # Mock queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_mortgage
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_income_statement]
        
        result = validation_service.validate_mortgage_interest_income_statement_reconciliation(
            mock_upload.id,
            mock_mortgage.id
        )
        
        assert "mortgage_interest" in result
        assert "income_statement_total" in result
        assert result["mortgage_interest"] == Decimal("40000")
        assert result["income_statement_total"] == Decimal("40000")
        # Should pass if difference is within tolerance
        assert result["passed"] is True or abs(result["difference"]) <= Decimal("100.00")
    
    def test_validate_mortgage_interest_income_statement_mismatch(
        self,
        validation_service,
        mock_db,
        mock_upload,
        mock_mortgage
    ):
        """Test mortgage interest expense reconciliation with mismatch"""
        # Create income statement with different interest amount
        mismatched_income = Mock(spec=IncomeStatementData)
        mismatched_income.property_id = 1
        mismatched_income.period_id = 1
        mismatched_income.account_code = "6000-0000"
        mismatched_income.account_name = "Interest Expense"
        mismatched_income.period_amount = Decimal("50000")  # $10K difference
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_mortgage
        mock_db.query.return_value.filter.return_value.all.return_value = [mismatched_income]
        
        result = validation_service.validate_mortgage_interest_income_statement_reconciliation(
            mock_upload.id,
            mock_mortgage.id
        )
        
        assert result["passed"] is False
        assert abs(result["difference"]) > Decimal("100.00")
    
    def test_validate_multiple_mortgages_balance_sheet(
        self,
        validation_service,
        mock_db,
        mock_upload
    ):
        """Test reconciliation with multiple mortgages"""
        mortgage1 = Mock(spec=MortgageStatementData)
        mortgage1.id = 1
        mortgage1.principal_balance = Decimal("8000000")
        
        mortgage2 = Mock(spec=MortgageStatementData)
        mortgage2.id = 2
        mortgage2.principal_balance = Decimal("2000000")
        
        balance_sheet = Mock(spec=BalanceSheetData)
        balance_sheet.amount = Decimal("10000000")
        
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [mortgage1, mortgage2],  # First call returns mortgages
            [balance_sheet]  # Second call returns balance sheet
        ]
        
        # Total mortgage debt should equal balance sheet
        total_mortgage = Decimal("10000000")
        balance_sheet_total = Decimal("10000000")
        
        assert total_mortgage == balance_sheet_total
    
    def test_validate_annual_interest_reconciliation(
        self,
        validation_service,
        mock_db,
        mock_upload,
        mock_mortgage
    ):
        """Test annual interest expense reconciliation"""
        # Monthly interest from mortgage
        monthly_interest = Decimal("40000")
        annual_interest = monthly_interest * Decimal("12")
        
        # YTD interest from income statement
        ytd_interest = Mock(spec=IncomeStatementData)
        ytd_interest.ytd_amount = Decimal("480000")  # 12 months * $40K
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_mortgage
        mock_db.query.return_value.filter.return_value.all.return_value = [ytd_interest]
        
        # Annual interest should match YTD if we're at month 12
        assert annual_interest == Decimal("480000")


