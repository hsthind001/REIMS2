"""
Unit tests for Mortgage Validation Service
"""
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.validation_service import ValidationService
from app.models.document_upload import DocumentUpload
from app.models.mortgage_statement_data import MortgageStatementData


class TestMortgageValidation:
    """Test mortgage validation rules"""
    
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
        mortgage.principal_balance = Decimal("10000000")
        mortgage.tax_escrow_balance = Decimal("100000")
        mortgage.insurance_escrow_balance = Decimal("50000")
        mortgage.reserve_balance = Decimal("20000")
        mortgage.other_escrow_balance = Decimal("0")
        mortgage.total_loan_balance = Decimal("10120000")
        mortgage.principal_due = Decimal("50000")
        mortgage.interest_due = Decimal("40000")
        mortgage.tax_escrow_due = Decimal("5000")
        mortgage.insurance_escrow_due = Decimal("2000")
        mortgage.reserve_due = Decimal("1000")
        mortgage.late_fees = Decimal("0")
        mortgage.other_fees = Decimal("0")
        mortgage.total_payment_due = Decimal("98000")
        mortgage.ytd_principal_paid = Decimal("600000")
        mortgage.ytd_interest_paid = Decimal("480000")
        mortgage.ytd_total_paid = Decimal("1080000")
        mortgage.interest_rate = Decimal("5.25")
        return mortgage
    
    def test_validate_mortgage_principal_reasonable(self, validation_service, mock_db, mock_upload, mock_mortgage):
        """Test principal balance reasonableness validation"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_mortgage
        
        result = validation_service.validate_mortgage_principal_reasonable(
            mock_upload.id,
            mock_mortgage.id
        )
        
        assert result["passed"] is True
        assert result["actual_value"] == Decimal("10000000")
    
    def test_validate_mortgage_principal_too_large(self, validation_service, mock_db, mock_upload):
        """Test principal balance validation with too large value"""
        large_mortgage = Mock(spec=MortgageStatementData)
        large_mortgage.id = 1
        large_mortgage.principal_balance = Decimal("200000000")  # > $100M
        
        mock_db.query.return_value.filter.return_value.first.return_value = large_mortgage
        
        result = validation_service.validate_mortgage_principal_reasonable(
            mock_upload.id,
            large_mortgage.id
        )
        
        assert result["passed"] is False
    
    def test_validate_mortgage_payment_calculation(self, validation_service, mock_db, mock_upload, mock_mortgage):
        """Test payment calculation validation"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_mortgage
        
        result = validation_service.validate_mortgage_payment_calculation(
            mock_upload.id,
            mock_mortgage.id
        )
        
        # Calculate expected total
        expected = (
            mock_mortgage.principal_due +
            mock_mortgage.interest_due +
            mock_mortgage.tax_escrow_due +
            mock_mortgage.insurance_escrow_due +
            mock_mortgage.reserve_due +
            mock_mortgage.late_fees +
            mock_mortgage.other_fees
        )
        
        assert result["expected_value"] == expected
        assert result["actual_value"] == mock_mortgage.total_payment_due
        # Should pass if difference is <= $1
        assert result["passed"] is True or abs(result["difference"]) <= Decimal("1.00")
    
    def test_validate_mortgage_escrow_total(self, validation_service, mock_db, mock_upload, mock_mortgage):
        """Test escrow balance total validation"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_mortgage
        
        result = validation_service.validate_mortgage_escrow_total(
            mock_upload.id,
            mock_mortgage.id
        )
        
        # Calculate expected total
        expected = (
            mock_mortgage.principal_balance +
            mock_mortgage.tax_escrow_balance +
            mock_mortgage.insurance_escrow_balance +
            mock_mortgage.reserve_balance +
            mock_mortgage.other_escrow_balance
        )
        
        assert result["expected_value"] == expected
        assert result["actual_value"] == mock_mortgage.total_loan_balance
        assert result["passed"] is True or abs(result["difference"]) <= Decimal("1.00")
    
    def test_validate_mortgage_interest_rate_range(self, validation_service, mock_db, mock_upload, mock_mortgage):
        """Test interest rate range validation"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_mortgage
        
        result = validation_service.validate_mortgage_interest_rate_range(
            mock_upload.id,
            mock_mortgage.id
        )
        
        assert result["passed"] is True
        assert result["actual_value"] == Decimal("5.25")
    
    def test_validate_mortgage_interest_rate_out_of_range(self, validation_service, mock_db, mock_upload):
        """Test interest rate validation with out-of-range value"""
        bad_mortgage = Mock(spec=MortgageStatementData)
        bad_mortgage.id = 1
        bad_mortgage.interest_rate = Decimal("25.0")  # > 20%
        
        mock_db.query.return_value.filter.return_value.first.return_value = bad_mortgage
        
        result = validation_service.validate_mortgage_interest_rate_range(
            mock_upload.id,
            bad_mortgage.id
        )
        
        assert result["passed"] is False
    
    def test_validate_mortgage_ytd_total(self, validation_service, mock_db, mock_upload, mock_mortgage):
        """Test YTD totals validation"""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_mortgage
        
        result = validation_service.validate_mortgage_ytd_total(
            mock_upload.id,
            mock_mortgage.id
        )
        
        expected = mock_mortgage.ytd_principal_paid + mock_mortgage.ytd_interest_paid
        assert result["expected_value"] == expected
        assert result["actual_value"] == mock_mortgage.ytd_total_paid
        assert result["passed"] is True or abs(result["difference"]) <= Decimal("1.00")


