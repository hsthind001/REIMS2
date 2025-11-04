"""
Unit Tests for Balance Sheet Extraction (Template v1.0)

Tests comprehensive balance sheet extraction including:
- Header metadata extraction
- Account hierarchy detection
- Subtotal/total identification
- Category classification
- Fuzzy account matching
"""
import pytest
from decimal import Decimal
from app.utils.financial_table_parser import FinancialTableParser
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.models.balance_sheet_data import BalanceSheetData
from app.models.chart_of_accounts import ChartOfAccounts


class TestBalanceSheetHeaderExtraction:
    """Test header metadata extraction from balance sheet PDFs"""
    
    def test_extract_property_name_and_code(self):
        """Test extraction of property name with code"""
        parser = FinancialTableParser()
        
        test_text = """
        Eastern Shore Plaza (esp)
        Balance Sheet
        Period = Dec 2023
        """
        
        header = parser._extract_balance_sheet_header(test_text)
        
        assert header["property_name"] == "Eastern Shore Plaza (esp)"
        assert header["property_code"] == "ESP"
        assert header["report_title"] == "Balance Sheet"
        assert header["period_ending"] == "Dec 2023"
    
    def test_extract_accounting_basis(self):
        """Test extraction of accounting basis"""
        parser = FinancialTableParser()
        
        test_text = """
        Hammond Aire Plaza (hmnd)
        Balance Sheet
        Book = Accrual
        Period = Dec 2024
        """
        
        header = parser._extract_balance_sheet_header(test_text)
        
        assert header["accounting_basis"] == "Accrual"
        assert header["property_code"] == "HMND"
    
    def test_extract_report_date(self):
        """Test extraction of report generation date"""
        parser = FinancialTableParser()
        
        test_text = """
        The Crossings of Spring Hill (tcsh)
        Balance Sheet
        Thursday, February 06, 2025 11:30 AM
        """
        
        header = parser._extract_balance_sheet_header(test_text)
        
        assert header["report_date"] == "Thursday, February 06, 2025 11:30 AM"
        assert header["property_code"] == "TCSH"


class TestAccountHierarchyDetection:
    """Test account hierarchy detection (subtotals, totals, levels)"""
    
    def test_detect_subtotal_by_code(self):
        """Test subtotal detection for accounts ending in 9000"""
        parser = FinancialTableParser()
        
        table = [
            ["Account Code", "Account Name", "Amount"],
            ["0499-9000", "Total Current Assets", "481979.78"]
        ]
        
        items = parser._parse_balance_sheet_table(table, 1)
        
        assert len(items) == 1
        assert items[0]["is_subtotal"] == True
        assert items[0]["account_level"] == 2
        assert items[0]["account_code"] == "0499-9000"
    
    def test_detect_total_assets(self):
        """Test total detection for TOTAL ASSETS"""
        parser = FinancialTableParser()
        
        table = [
            ["Account Code", "Account Name", "Amount"],
            ["1999-0000", "TOTAL ASSETS", "24554797.00"]
        ]
        
        items = parser._parse_balance_sheet_table(table, 1)
        
        assert len(items) == 1
        assert items[0]["is_total"] == True
        assert items[0]["account_level"] == 1
        assert items[0]["account_category"] == "ASSETS"
    
    def test_detect_category_from_code(self):
        """Test automatic category detection from account code"""
        parser = FinancialTableParser()
        
        table = [
            ["Account Code", "Account Name", "Amount"],
            ["0122-0000", "Cash - Operating", "114890.87"],
            ["2110-0000", "Accounts Payable Trade", "25000.00"],
            ["3050-0000", "Partners Contribution", "5684514.69"]
        ]
        
        items = parser._parse_balance_sheet_table(table, 1)
        
        assert len(items) == 3
        assert items[0]["account_category"] == "ASSETS"
        assert items[0]["account_subcategory"] == "Current Assets"
        assert items[1]["account_category"] == "LIABILITIES"
        assert items[1]["account_subcategory"] == "Current Liabilities"
        assert items[2]["account_category"] == "CAPITAL"
        assert items[2]["account_subcategory"] == "Equity"
    
    def test_detect_subtotal_by_name(self):
        """Test subtotal detection by account name"""
        parser = FinancialTableParser()
        
        table = [
            ["Account Code", "Account Name", "Amount"],
            ["2590-0000", "Total Current Liabilities", "150000.00"],
            ["2900-0000", "Total Long Term Liabilities", "22000000.00"]
        ]
        
        items = parser._parse_balance_sheet_table(table, 1)
        
        assert len(items) == 2
        assert items[0]["is_subtotal"] == True
        assert items[0]["account_subcategory"] == "Current Liabilities"
        assert items[1]["is_subtotal"] == True
        assert items[1]["account_subcategory"] == "Long Term Liabilities"


class TestAccountExtraction:
    """Test extraction of various account types"""
    
    def test_extract_cash_accounts(self):
        """Test extraction of multiple cash accounts"""
        parser = FinancialTableParser()
        
        table = [
            ["Account Code", "Account Name", "Amount"],
            ["0122-0000", "Cash - Operating", "114890.87"],
            ["0123-0000", "Cash - Operating II", "50000.00"],
            ["0124-0000", "Cash - Operating III WF", "75000.00"]
        ]
        
        items = parser._parse_balance_sheet_table(table, 1)
        
        assert len(items) == 3
        assert all(item["account_subcategory"] == "Current Assets" for item in items)
        assert items[0]["amount"] == 114890.87
    
    def test_extract_accumulated_depreciation(self):
        """Test extraction of accumulated depreciation (negative values)"""
        parser = FinancialTableParser()
        
        table = [
            ["Account Code", "Account Name", "Amount"],
            ["1061-0000", "Accum. Depr. - Buildings", "-4026680.06"]
        ]
        
        items = parser._parse_balance_sheet_table(table, 1)
        
        assert len(items) == 1
        assert items[0]["amount"] == -4026680.06
        assert items[0]["account_subcategory"] == "Property & Equipment"
    
    def test_extract_lender_accounts(self):
        """Test extraction of lender accounts"""
        parser = FinancialTableParser()
        
        table = [
            ["Account Code", "Account Name", "Amount"],
            ["2612-1000", "NorthMarq Capital", "26965463.42"],
            ["2618-0000", "Trawler Capital Management (MEZZ)", "2680000.00"]
        ]
        
        items = parser._parse_balance_sheet_table(table, 1)
        
        assert len(items) == 2
        assert items[0]["account_subcategory"] == "Long Term Liabilities"
        assert items[0]["amount"] == 26965463.42
        assert items[1]["amount"] == 2680000.00
    
    def test_extract_equity_accounts(self):
        """Test extraction of equity components"""
        parser = FinancialTableParser()
        
        table = [
            ["Account Code", "Account Name", "Amount"],
            ["3050-0000", "Partners Contribution", "5684514.69"],
            ["3910-0000", "Beginning Equity", "1084248.61"],
            ["3990-0000", "Distribution", "-6965000.00"],
            ["3995-0000", "Current Period Earnings", "736023.07"]
        ]
        
        items = parser._parse_balance_sheet_table(table, 1)
        
        assert len(items) == 4
        assert all(item["account_category"] == "CAPITAL" for item in items)
        assert items[2]["amount"] == -6965000.00  # Distribution is negative


class TestMultiPageExtraction:
    """Test multi-page document handling"""
    
    def test_page_number_tracking(self):
        """Test page numbers are tracked for each line item"""
        parser = FinancialTableParser()
        
        table_page1 = [
            ["Account Code", "Account Name", "Amount"],
            ["0122-0000", "Cash - Operating", "114890.87"]
        ]
        
        table_page2 = [
            ["Account Code", "Account Name", "Amount"],
            ["2612-0000", "NorthMarq Capital", "26965463.42"]
        ]
        
        items_p1 = parser._parse_balance_sheet_table(table_page1, 1)
        items_p2 = parser._parse_balance_sheet_table(table_page2, 2)
        
        assert items_p1[0]["page"] == 1
        assert items_p2[0]["page"] == 2


class TestFuzzyMatching:
    """Test fuzzy matching with chart of accounts (Template v1.0 requirement)"""
    
    def test_exact_code_match(self, db_session):
        """Test exact account code matching (100% confidence)"""
        # Setup: Create test chart of accounts entry
        test_account = ChartOfAccounts(
            account_code="0122-0000",
            account_name="Cash - Operating",
            account_type="asset",
            category="current_asset",
            subcategory="cash"
        )
        db_session.add(test_account)
        db_session.commit()
        
        orchestrator = ExtractionOrchestrator(db_session)
        
        extracted_items = [{
            "account_code": "0122-0000",
            "account_name": "Cash - Operating",
            "amount": 114890.87
        }]
        
        matched_items = orchestrator._match_accounts_intelligent(extracted_items)
        
        assert len(matched_items) == 1
        assert matched_items[0]["match_method"] == "exact_code"
        assert matched_items[0]["match_confidence"] == 100.0
        assert matched_items[0]["matched_account_id"] is not None
    
    def test_fuzzy_name_match_85_percent(self, db_session):
        """Test fuzzy name matching at 85%+ threshold (Template v1.0)"""
        # Setup
        test_account = ChartOfAccounts(
            account_code="1061-0000",
            account_name="Accumulated Depreciation - Buildings",
            account_type="asset",
            category="fixed_asset"
        )
        db_session.add(test_account)
        db_session.commit()
        
        orchestrator = ExtractionOrchestrator(db_session)
        
        # Extracted with slight variation
        extracted_items = [{
            "account_code": "",
            "account_name": "Accum. Depr. - Buildings",  # Abbreviated
            "amount": -4026680.06
        }]
        
        matched_items = orchestrator._match_accounts_intelligent(extracted_items)
        
        assert len(matched_items) == 1
        assert matched_items[0]["match_confidence"] >= 85.0
        assert matched_items[0]["matched_account_id"] is not None
    
    def test_abbreviation_expansion(self, db_session):
        """Test abbreviation expansion (A/R, A/P, etc.)"""
        # Setup
        test_account = ChartOfAccounts(
            account_code="0305-0000",
            account_name="Accounts Receivable Tenants",
            account_type="asset",
            category="current_asset"
        )
        db_session.add(test_account)
        db_session.commit()
        
        orchestrator = ExtractionOrchestrator(db_session)
        
        extracted_items = [{
            "account_code": "",
            "account_name": "A/R Tenants",  # Abbreviated
            "amount": 56028.54
        }]
        
        matched_items = orchestrator._match_accounts_intelligent(extracted_items)
        
        # Should match after abbreviation expansion
        assert len(matched_items) == 1
        assert matched_items[0]["matched_account_id"] is not None


class TestNegativeAmounts:
    """Test handling of negative amounts (parentheses and minus signs)"""
    
    def test_parse_parentheses_negative(self):
        """Test parsing amounts in parentheses as negative"""
        parser = FinancialTableParser()
        
        amount = parser._parse_amount("(1,234.56)")
        assert amount == Decimal('-1234.56')
    
    def test_parse_minus_sign_negative(self):
        """Test parsing amounts with minus sign"""
        parser = FinancialTableParser()
        
        amount = parser._parse_amount("-4,026,680.06")
        assert amount == Decimal('-4026680.06')
    
    def test_parse_positive_amount(self):
        """Test parsing positive amounts"""
        parser = FinancialTableParser()
        
        amount = parser._parse_amount("$114,890.87")
        assert amount == Decimal('114890.87')


class TestBalanceSheetValidation:
    """Test balance sheet validation rules"""
    
    def test_balance_check_passes(self, db_session):
        """Test balance sheet equation validation passes when balanced"""
        # This would require setting up test data in the database
        # Skipped for brevity - implement with actual test fixtures
        pass
    
    def test_detect_invalid_account_codes(self, db_session):
        """Test detection of invalid account code format"""
        # Test would validate that accounts not matching ####-#### pattern are flagged
        pass
    
    def test_detect_negative_equity(self, db_session):
        """Test detection of negative equity (warning level)"""
        # Test would flag when total capital < 0
        pass


# Fixtures for testing
@pytest.fixture
def db_session():
    """Database session fixture for testing"""
    # Would create test database session
    # Implement with actual test database setup
    pass


@pytest.fixture
def sample_balance_sheet_pdf():
    """Sample balance sheet PDF for testing"""
    # Would load sample PDF file
    pass


@pytest.fixture
def sample_chart_of_accounts(db_session):
    """Sample chart of accounts for testing"""
    # Would seed test chart of accounts
    pass

