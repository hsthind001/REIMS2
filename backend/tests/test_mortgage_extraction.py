"""
Unit tests for Mortgage Extraction Service
"""
import pytest
from decimal import Decimal
from datetime import date, datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.mortgage_extraction_service import MortgageExtractionService
from app.models.extraction_template import ExtractionTemplate


class TestMortgageExtractionService:
    """Test mortgage extraction service"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_template(self):
        """Create mock extraction template"""
        template = Mock(spec=ExtractionTemplate)
        template.template_structure = {
            "field_patterns": {
                "loan_number": {
                    "patterns": ["Loan Number[:\\s]+(\\d+)"],
                    "field_type": "text",
                    "required": True
                },
                "principal_balance": {
                    "patterns": ["Principal Balance[:\\s]+\\$?([0-9,]+\\.\\d{2})"],
                    "field_type": "currency",
                    "required": True
                },
                "statement_date": {
                    "patterns": ["Statement Date[:\\s]+(\\d{1,2}/\\d{1,2}/\\d{4})"],
                    "field_type": "date",
                    "required": True
                },
                "interest_rate": {
                    "patterns": ["Interest Rate[:\\s]+(\\d+\\.\\d+)%"],
                    "field_type": "percentage",
                    "required": False
                }
            },
            "required_fields": ["loan_number", "statement_date", "principal_balance"]
        }
        return template
    
    @pytest.fixture
    def service(self, mock_db):
        """Create mortgage extraction service instance"""
        return MortgageExtractionService(mock_db)
    
    def test_parse_currency(self, service):
        """Test currency parsing"""
        assert service._parse_currency("$21,499,905.17") == Decimal("21499905.17")
        assert service._parse_currency("1,234.56") == Decimal("1234.56")
        assert service._parse_currency("") is None
        assert service._parse_currency(None) is None
    
    def test_parse_date(self, service):
        """Test date parsing"""
        assert service._parse_date("12/31/2024") == date(2024, 12, 31)
        assert service._parse_date("01/15/2025") == date(2025, 1, 15)
        assert service._parse_date("") is None
        assert service._parse_date(None) is None
    
    def test_parse_percentage(self, service):
        """Test percentage parsing"""
        assert service._parse_percentage("5.25%") == Decimal("5.25")
        assert service._parse_percentage("10.5%") == Decimal("10.5")
        assert service._parse_percentage("") is None
        assert service._parse_percentage(None) is None
    
    def test_extract_mortgage_data_success(self, service, mock_db, mock_template):
        """Test successful mortgage data extraction"""
        # Mock template query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        
        # Sample extracted text
        extracted_text = """
        Loan Number: 306891008
        Statement Date: 12/31/2024
        Principal Balance: $21,499,905.17
        Interest Rate: 5.25%
        Total Payment Due: $206,762.78
        """
        
        result = service.extract_mortgage_data(extracted_text)
        
        assert result["success"] is True
        assert "mortgage_data" in result
        assert result["mortgage_data"]["loan_number"] == "306891008"
        assert result["mortgage_data"]["principal_balance"] == Decimal("21499905.17")
        assert result["mortgage_data"]["interest_rate"] == Decimal("5.25")
    
    def test_extract_mortgage_data_no_template(self, service, mock_db):
        """Test extraction when template is not found"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = service.extract_mortgage_data("Some text")
        
        assert result["success"] is False
        assert "template not found" in result["error"].lower()
    
    def test_calculate_derived_fields(self, service):
        """Test derived field calculations"""
        fields = {
            "principal_balance": Decimal("1000000"),
            "tax_escrow_balance": Decimal("10000"),
            "insurance_escrow_balance": Decimal("5000"),
            "reserve_balance": Decimal("2000"),
            "ytd_principal_paid": Decimal("50000"),
            "ytd_interest_paid": Decimal("25000"),
            "principal_due": Decimal("10000"),
            "interest_due": Decimal("5000"),
            "maturity_date": date(2030, 12, 31),
            "statement_date": date(2024, 12, 31)
        }
        
        result = service._calculate_derived_fields(fields)
        
        assert result["total_loan_balance"] == Decimal("1017000")  # 1000000 + 10000 + 5000 + 2000
        assert result["ytd_total_paid"] == Decimal("75000")  # 50000 + 25000
        assert result["monthly_debt_service"] == Decimal("15000")  # 10000 + 5000
        assert result["annual_debt_service"] == Decimal("180000")  # 15000 * 12
        assert result["remaining_term_months"] == 72  # 6 years * 12
    
    def test_calculate_confidence(self, service):
        """Test confidence score calculation"""
        template_structure = {
            "required_fields": ["loan_number", "statement_date", "principal_balance"]
        }
        
        # All required fields present
        fields1 = {
            "loan_number": "123",
            "statement_date": date(2024, 12, 31),
            "principal_balance": Decimal("1000000")
        }
        confidence1 = service._calculate_confidence(fields1, template_structure)
        assert confidence1 == 100.0
        
        # Missing one required field
        fields2 = {
            "loan_number": "123",
            "statement_date": date(2024, 12, 31)
        }
        confidence2 = service._calculate_confidence(fields2, template_structure)
        assert confidence2 < 100.0
        
        # Invalid principal balance
        fields3 = {
            "loan_number": "123",
            "statement_date": date(2024, 12, 31),
            "principal_balance": Decimal("200000000")  # > $100M
        }
        confidence3 = service._calculate_confidence(fields3, template_structure)
        assert confidence3 < 100.0  # Should have quality penalty


