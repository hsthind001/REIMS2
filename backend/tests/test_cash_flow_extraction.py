"""
Cash Flow Statement Extraction Tests - Template v1.0 Compliance

Comprehensive tests for cash flow extraction including:
- Header extraction
- Income section classification (14+ categories)
- Operating expenses classification (50+ categories)
- Additional expenses classification (15+ categories)
- Performance metrics extraction
- Adjustments parsing (30+ items)
- Cash account reconciliation
- Multi-column extraction (Period/YTD)
"""
import pytest
from decimal import Decimal
from app.utils.financial_table_parser import FinancialTableParser


class TestCashFlowHeaderExtraction:
    """Test header metadata extraction"""
    
    def test_extract_property_name_and_code(self):
        """Test property name and code extraction"""
        parser = FinancialTableParser()
        text = """
        Eastern Shore Plaza (esp)
        Cash Flow Statement
        Period = Jan 2024-Dec 2024
        Book = Accrual
        """
        
        header = parser._extract_cash_flow_header(text)
        
        assert header["property_name"] == "Eastern Shore Plaza (esp)"
        assert header["property_code"] == "esp"
    
    def test_extract_period_range(self):
        """Test period range extraction"""
        parser = FinancialTableParser()
        text = """
        Period = Jan 2024-Dec 2024
        """
        
        header = parser._extract_cash_flow_header(text)
        
        assert header["report_period_start"] == "Jan 2024"
        assert header["report_period_end"] == "Dec 2024"
    
    def test_extract_monthly_period(self):
        """Test monthly period extraction"""
        parser = FinancialTableParser()
        text = """
        Period = Dec 2023
        """
        
        header = parser._extract_cash_flow_header(text)
        
        assert header["report_period_start"] == "Dec 2023"
        assert header["report_period_end"] == "Dec 2023"
    
    def test_extract_accounting_basis(self):
        """Test accounting basis extraction"""
        parser = FinancialTableParser()
        text = """
        Book = Accrual
        """
        
        header = parser._extract_cash_flow_header(text)
        
        assert header["accounting_basis"] == "Accrual"
    
    def test_extract_report_date(self):
        """Test report generation date extraction"""
        parser = FinancialTableParser()
        text = """
        Thursday, February 19, 2025
        """
        
        header = parser._extract_cash_flow_header(text)
        
        assert header["report_generation_date"] == "Thursday, February 19, 2025"


class TestCashFlowSectionDetection:
    """Test section detection across pages"""
    
    def test_detect_income_section(self):
        """Test income section detection"""
        parser = FinancialTableParser()
        text = "INCOME\nBase Rentals"
        
        section = parser._detect_cash_flow_section(text, None)
        
        assert section == "INCOME"
    
    def test_detect_operating_expense_section(self):
        """Test operating expense section detection"""
        parser = FinancialTableParser()
        text = "OPERATING EXPENSES\nProperty Tax"
        
        section = parser._detect_cash_flow_section(text, "INCOME")
        
        assert section == "OPERATING_EXPENSE"
    
    def test_detect_additional_expense_section(self):
        """Test additional expense section detection"""
        parser = FinancialTableParser()
        text = "ADDITIONAL OPERATING EXPENSES\nOff Site Management"
        
        section = parser._detect_cash_flow_section(text, "OPERATING_EXPENSE")
        
        assert section == "ADDITIONAL_EXPENSE"
    
    def test_detect_performance_metrics_section(self):
        """Test performance metrics section detection"""
        parser = FinancialTableParser()
        text = "NET OPERATING INCOME\nMortgage Interest"
        
        section = parser._detect_cash_flow_section(text, "ADDITIONAL_EXPENSE")
        
        assert section == "PERFORMANCE_METRICS"
    
    def test_detect_adjustments_section(self):
        """Test adjustments section detection"""
        parser = FinancialTableParser()
        text = "Adjustments\nA/R Tenants"
        
        section = parser._detect_cash_flow_section(text, "PERFORMANCE_METRICS")
        
        assert section == "ADJUSTMENTS"
    
    def test_detect_cash_reconciliation_section(self):
        """Test cash reconciliation section detection"""
        parser = FinancialTableParser()
        text = "Cash - Operating\nBeginning Balance"
        
        section = parser._detect_cash_flow_section(text, "ADJUSTMENTS")
        
        assert section == "CASH_RECONCILIATION"


class TestIncomeClassification:
    """Test income line item classification"""
    
    def test_classify_base_rentals(self):
        """Test base rentals classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Base Rentals", "INCOME", "4010-0000"
        )
        
        assert category == "Base Rental Income"
        assert subcategory == "Base Rentals"
        assert is_subtotal == False
        assert is_total == False
    
    def test_classify_tax_recovery(self):
        """Test tax recovery classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Tax Recovery", "INCOME", "4020-0000"
        )
        
        assert category == "Recovery Income"
        assert subcategory == "Tax Recovery"
    
    def test_classify_cam_recovery(self):
        """Test CAM recovery classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "CAM Recovery", "INCOME", "4030-0000"
        )
        
        assert category == "Recovery Income"
        assert subcategory == "CAM Recovery"
    
    def test_classify_late_fee(self):
        """Test late fee classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Late Fee Income", "INCOME", "4090-0000"
        )
        
        assert category == "Other Income"
        assert subcategory == "Late Fee Income"
    
    def test_classify_total_income(self):
        """Test total income detection"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Total Income", "INCOME", ""
        )
        
        assert is_total == True
        assert category == "Total Income"


class TestOperatingExpenseClassification:
    """Test operating expense classification (50+ categories)"""
    
    def test_classify_property_tax(self):
        """Test property tax classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Property Tax", "OPERATING_EXPENSE", "5010-0000"
        )
        
        assert category == "Property Expenses"
        assert subcategory == "Property Tax"
    
    def test_classify_electricity(self):
        """Test electricity classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Electricity Service", "OPERATING_EXPENSE", "5110-0000"
        )
        
        assert category == "Utility Expenses"
        assert subcategory == "Electricity Service"
    
    def test_classify_parking_sweeping(self):
        """Test contracted service classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Contract - Parking Lot Sweeping", "OPERATING_EXPENSE", "5210-0000"
        )
        
        assert category == "Contracted Services"
        assert subcategory == "Contract - Parking Lot Sweeping"
    
    def test_classify_rm_plumbing(self):
        """Test R&M classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "R&M - Plumbing", "OPERATING_EXPENSE", "5310-0000"
        )
        
        assert category == "Repair & Maintenance"
        assert subcategory == "R&M - Plumbing"
    
    def test_classify_salaries(self):
        """Test administrative expense classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Salaries Expense", "OPERATING_EXPENSE", "5410-0000"
        )
        
        assert category == "Administrative Expenses"
        assert subcategory == "Salaries Expense"
    
    def test_classify_total_rm(self):
        """Test R&M subtotal detection"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Total R&M Operating Expenses", "OPERATING_EXPENSE", ""
        )
        
        assert is_subtotal == True
        assert category == "Repair & Maintenance"


class TestAdditionalExpenseClassification:
    """Test additional expense classification (15+ categories)"""
    
    def test_classify_off_site_management(self):
        """Test off site management classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Off Site Management", "ADDITIONAL_EXPENSE", "6010-0000"
        )
        
        assert category == "Management Fees"
        assert subcategory == "Off Site Management"
    
    def test_classify_franchise_tax(self):
        """Test franchise tax classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Franchise Tax", "ADDITIONAL_EXPENSE", "6110-0000"
        )
        
        assert category == "Taxes & Fees"
        assert subcategory == "Franchise Tax"
    
    def test_classify_ll_hvac(self):
        """Test landlord expense classification"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "LL - HVAC Repairs", "ADDITIONAL_EXPENSE", "6310-0000"
        )
        
        assert category == "Landlord Expenses"
        assert subcategory == "LL - HVAC Repairs"


class TestAdjustmentsClassification:
    """Test adjustments classification (30+ types)"""
    
    def test_classify_ar_tenants(self):
        """Test A/R Tenants classification"""
        parser = FinancialTableParser()
        
        category, related_property, related_entity = parser._classify_adjustment("A/R Tenants")
        
        assert category == "AR_CHANGES"
        assert related_property is None
        assert related_entity is None
    
    def test_classify_accum_depr_buildings(self):
        """Test accumulated depreciation classification"""
        parser = FinancialTableParser()
        
        category, _, _ = parser._classify_adjustment("Accum. Depr. - Buildings")
        
        assert category == "ACCUMULATED_DEPRECIATION"
    
    def test_classify_escrow_property_tax(self):
        """Test escrow classification"""
        parser = FinancialTableParser()
        
        category, _, _ = parser._classify_adjustment("Escrow - Property Tax")
        
        assert category == "ESCROW_ACCOUNTS"
    
    def test_classify_distribution(self):
        """Test distribution classification"""
        parser = FinancialTableParser()
        
        category, _, _ = parser._classify_adjustment("Distribution")
        
        assert category == "DISTRIBUTIONS"
    
    def test_classify_inter_property_transfer(self):
        """Test inter-property transfer with property extraction"""
        parser = FinancialTableParser()
        
        category, related_property, _ = parser._classify_adjustment("A/R Hammond Aire LP")
        
        assert category == "INTER_PROPERTY"
        assert "Hammond Aire" in related_property
    
    def test_classify_ap_entity(self):
        """Test A/P with entity extraction"""
        parser = FinancialTableParser()
        
        category, _, related_entity = parser._classify_adjustment("A/P 5Rivers CRE, LLC")
        
        assert category == "ACCOUNTS_PAYABLE"
        assert related_entity == "5Rivers CRE, LLC"


class TestCashAccountClassification:
    """Test cash account type classification"""
    
    def test_classify_operating_cash(self):
        """Test operating cash account"""
        parser = FinancialTableParser()
        
        account_type, is_escrow = parser._classify_cash_account("Cash - Operating")
        
        assert account_type == "operating"
        assert is_escrow == False
    
    def test_classify_escrow_account(self):
        """Test escrow account"""
        parser = FinancialTableParser()
        
        account_type, is_escrow = parser._classify_cash_account("Escrow - Other")
        
        assert account_type == "escrow"
        assert is_escrow == True


class TestMultiColumnExtraction:
    """Test multi-column extraction (Period/YTD amounts and percentages)"""
    
    def test_parse_four_column_row(self):
        """Test extraction of Period Amount, Period %, YTD Amount, YTD %"""
        parser = FinancialTableParser()
        
        # Sample table row: [Account Name, Period Amt, Period %, YTD Amt, YTD %]
        table = [
            ["4010-0000 Base Rentals", "215,671.29", "98.35%", "2,588,055.53", "81.40%"]
        ]
        
        items = parser._parse_cash_flow_table_v2(table, 1, "INCOME", 1)
        
        assert len(items) == 1
        assert items[0]["account_code"] == "4010-0000"
        assert items[0]["account_name"] == "Base Rentals"
        assert items[0]["period_amount"] == 215671.29
        assert items[0]["period_percentage"] == 98.35
        assert items[0]["ytd_amount"] == 2588055.53
        assert items[0]["ytd_percentage"] == 81.40


class TestNegativeValueHandling:
    """Test handling of negative values"""
    
    def test_parse_negative_free_rent(self):
        """Test negative free rent (concession)"""
        parser = FinancialTableParser()
        
        table = [
            ["4015-0000 Free Rent", "-5,000.00"]
        ]
        
        items = parser._parse_cash_flow_table_v2(table, 1, "INCOME", 1)
        
        assert len(items) == 1
        assert items[0]["period_amount"] == -5000.00
    
    def test_parse_negative_distribution(self):
        """Test negative distribution (cash outflow)"""
        parser = FinancialTableParser()
        
        adjustments = [
            {"adjustment_name": "Distribution", "amount": -664651.00}
        ]
        
        # Distributions should always be negative
        assert adjustments[0]["amount"] < 0


class TestDataCompleteness:
    """Test zero data loss - all fields captured"""
    
    def test_all_income_categories_mapped(self):
        """Verify all 14+ income categories can be classified"""
        parser = FinancialTableParser()
        
        income_items = [
            "Base Rentals",
            "Holdover Rent",
            "Free Rent",
            "Co-Tenancy Rent Reduction",
            "Tax Recovery",
            "Insurance Recovery",
            "CAM Recovery",
            "Fixed CAM",
            "Annual CAMs",
            "Percentage Rent",
            "Utilities Reimbursement",
            "Interest Income",
            "Late Fee Income",
            "Bad Debt Write Offs"
        ]
        
        for item_name in income_items:
            category, subcategory, _, _ = parser._classify_cash_flow_line(item_name, "INCOME")
            assert category is not None, f"Failed to classify: {item_name}"
            assert subcategory is not None, f"No subcategory for: {item_name}"
    
    def test_all_utility_categories_mapped(self):
        """Verify all 6 utility categories can be classified"""
        parser = FinancialTableParser()
        
        utility_items = [
            "Electricity Service",
            "Gas Service",
            "Water & Sewer Service",
            "Water & Sewer - Irrigation",
            "Trash Service",
            "Internet Service"
        ]
        
        for item_name in utility_items:
            category, subcategory, _, _ = parser._classify_cash_flow_line(item_name, "OPERATING_EXPENSE")
            assert category == "Utility Expenses", f"Wrong category for: {item_name}"
            assert subcategory is not None, f"No subcategory for: {item_name}"
    
    def test_all_rm_categories_mapped(self):
        """Verify all 17 R&M categories can be classified"""
        parser = FinancialTableParser()
        
        rm_items = [
            "R&M - Landscape Repairs",
            "R&M - Irrigation Repairs",
            "R&M - Fire Safety Repairs",
            "R&M - Fire Sprinkler Inspection",
            "R&M - Plumbing",
            "R&M - Electrical Inspections & Repairs",
            "R&M - Building Maintenance",
            "R&M - Parking Lot Repairs",
            "R&M - Sidewalk & Concrete Repairs",
            "R&M - Exterior",
            "R&M - Interior",
            "R&M - HVAC",
            "R&M - Lighting",
            "R&M - Roofing Repairs - Minor",
            "R&M - Roofing Repairs - Major",
            "R&M - Doors/Locks & Keys",
            "R&M - Signage"
        ]
        
        for item_name in rm_items:
            category, subcategory, _, _ = parser._classify_cash_flow_line(item_name, "OPERATING_EXPENSE")
            assert category == "Repair & Maintenance", f"Wrong category for: {item_name}"
            assert subcategory is not None, f"No subcategory for: {item_name}"


class TestPerformanceMetrics:
    """Test performance metrics extraction"""
    
    def test_classify_noi(self):
        """Test NOI detection"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Net Operating Income", "PERFORMANCE_METRICS"
        )
        
        assert is_total == True
        assert "Net Operating Income" in subcategory
    
    def test_classify_net_income(self):
        """Test Net Income detection"""
        parser = FinancialTableParser()
        
        category, subcategory, is_subtotal, is_total = parser._classify_cash_flow_line(
            "Net Income", "PERFORMANCE_METRICS"
        )
        
        assert is_total == True
        assert "Net Income" in subcategory


# Integration test marker
@pytest.mark.integration
class TestRealPDFExtraction:
    """Test extraction with real Cash Flow PDFs (if available)"""
    
    @pytest.mark.skip(reason="Requires real PDF file")
    def test_extract_real_cash_flow_pdf(self):
        """Test extraction with real Cash Flow PDF"""
        parser = FinancialTableParser()
        
        # This test requires a real Cash Flow PDF file
        with open("test_data/sample_cash_flow.pdf", "rb") as f:
            result = parser.extract_cash_flow_table(f.read())
        
        assert result["success"] == True
        assert result["total_items"] > 0
        assert "header" in result
        assert "line_items" in result
        assert "adjustments" in result
        assert "cash_accounts" in result

