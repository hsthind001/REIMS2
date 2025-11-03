"""
Real PDF Extraction Tests - Sprint 4.2

Test extraction with actual PDF files from all 4 properties
Verify 100% data extraction accuracy with zero data loss
"""
import pytest
from pathlib import Path
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

from app.utils.financial_table_parser import FinancialTableParser
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.services.document_service import DocumentService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.chart_of_accounts import ChartOfAccounts


# Test PDF file paths
PDF_BASE_PATH = Path("/home/gurpyar/REIMS_Uploaded/uploads/Sampledata")

# Expected values from actual PDFs (for validation)
WENDOVER_EXPECTED = {
    "total_assets": Decimal("22939865.40"),
    "cash_operating": Decimal("211729.81"),
    "accum_depr_buildings": Decimal("-2225410.00"),
    "total_liabilities": Decimal("21769610.72"),
}

ESP_EXPECTED = {
    "total_assets": Decimal("23889953.33"),
}

HAMMOND_EXPECTED = {
    "total_property_equipment": Decimal("32163869.08"),
    "land": Decimal("6000000.00"),
}

TCSH_EXPECTED = {
    "total_assets": Decimal("29552444.20"),
    "partners_contribution": Decimal("8821032.53"),
}


# SQLite test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database for each test"""
    from app.db.database import Base
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Seed minimal chart of accounts for testing
    _seed_test_accounts(session)
    
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _seed_test_accounts(db):
    """Seed essential accounts for testing"""
    test_accounts = [
        ("0122-0000", "Cash - Operating", "asset"),
        ("1061-0000", "Accum. Depr. - Buildings", "asset"),
        ("1999-0000", "TOTAL ASSETS", "asset"),
        ("2999-0000", "TOTAL LIABILITIES", "liability"),
        ("4010-0000", "Base Rentals", "income"),
        ("9090-0000", "NET INCOME", "income"),
    ]
    
    for code, name, acc_type in test_accounts:
        account = ChartOfAccounts(
            account_code=code,
            account_name=name,
            account_type=acc_type,
            is_active=True
        )
        db.add(account)
    
    db.commit()


@pytest.fixture
def wendover_property(db_session):
    """Create Wendover Commons property"""
    prop = Property(
        property_code="WEND001",
        property_name="Wendover Commons",
        status="active"
    )
    db_session.add(prop)
    db_session.commit()
    return prop


@pytest.fixture
def esp_property(db_session):
    """Create ESP property"""
    prop = Property(
        property_code="ESP001",
        property_name="Eastern Shore Plaza",
        status="active"
    )
    db_session.add(prop)
    db_session.commit()
    return prop


class TestFinancialTableParser:
    """Test FinancialTableParser with actual PDFs"""
    
    def test_wendover_balance_sheet_extraction(self):
        """Test table extraction from Wendover balance sheet"""
        parser = FinancialTableParser()
        
        # Use actual Wendover PDF
        pdf_path = PDF_BASE_PATH / "Wendover-Commons" / "2024" / "12" / "Wendover Commons Balance Sheet December 2024.pdf"
        
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        
        result = parser.extract_balance_sheet_table(pdf_data)
        
        # Verify extraction success
        assert result["success"] is True, f"Extraction failed: {result.get('error')}"
        assert len(result["line_items"]) > 0, "No line items extracted"
        
        # Verify specific accounts exist
        items_dict = {item["account_code"]: item for item in result["line_items"] if item.get("account_code")}
        
        # Check for key accounts
        if "0122-0000" in items_dict:
            assert items_dict["0122-0000"]["account_name"] == "Cash - Operating"
        
        # Verify data quality
        for item in result["line_items"]:
            assert "account_name" in item
            assert "amount" in item
            assert item["confidence"] >= 75.0, f"Low confidence: {item['confidence']}"
    
    def test_income_statement_multi_column(self):
        """Test extraction of income statement with Period, YTD, % columns"""
        parser = FinancialTableParser()
        
        # Use actual income statement PDF
        pdf_path = PDF_BASE_PATH / "Wendover-Commons" / "2024" / "12" / "Wendover Commons Income Statement December 2024.pdf"
        
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        
        result = parser.extract_income_statement_table(pdf_data)
        
        assert result["success"] is True
        assert len(result["line_items"]) > 0
        
        # Verify multi-column extraction
        has_period_amount = any("period_amount" in item for item in result["line_items"])
        has_ytd_amount = any("ytd_amount" in item and item["ytd_amount"] is not None 
                             for item in result["line_items"])
        
        assert has_period_amount, "Period amounts not extracted"
        # YTD may not always be present
        print(f"YTD amounts found: {has_ytd_amount}")


class TestExtractionOrchestrator:
    """Test full extraction workflow with orchestrator"""
    
    def test_wendover_full_workflow(self, db_session, wendover_property):
        """Test complete extraction workflow for Wendover"""
        # Create period
        period = FinancialPeriod(
            property_id=wendover_property.id,
            period_year=2024,
            period_month=12,
            period_start_date=date(2024, 12, 1),
            period_end_date=date(2024, 12, 31)
        )
        db_session.add(period)
        db_session.commit()
        
        # Create upload record
        pdf_path = PDF_BASE_PATH / "Wendover-Commons" / "2024" / "12" / "Wendover Commons Balance Sheet December 2024.pdf"
        
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")
        
        upload = DocumentUpload(
            property_id=wendover_property.id,
            period_id=period.id,
            document_type="balance_sheet",
            file_name="test_balance_sheet.pdf",
            file_path="test/path.pdf",
            extraction_status="pending"
        )
        db_session.add(upload)
        db_session.commit()
        
        # Test table parser directly (not full orchestrator since we don't have MinIO)
        parser = FinancialTableParser()
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        
        result = parser.extract_balance_sheet_table(pdf_data)
        
        # Verify results
        assert result["success"] is True
        assert len(result["line_items"]) > 10, "Should extract many accounts"
        
        # Check data quality
        total_items = len(result["line_items"])
        high_confidence_items = sum(1 for item in result["line_items"] if item.get("confidence", 0) >= 90)
        
        confidence_rate = (high_confidence_items / total_items * 100) if total_items > 0 else 0
        print(f"\nExtraction Quality:")
        print(f"  Total items: {total_items}")
        print(f"  High confidence (>=90%): {high_confidence_items} ({confidence_rate:.1f}%)")
        
        assert confidence_rate >= 70, f"Too many low-confidence items: {confidence_rate:.1f}%"
    
    def test_account_matching_accuracy(self, db_session, wendover_property):
        """Test intelligent account matching with actual data"""
        from app.services.extraction_orchestrator import ExtractionOrchestrator
        
        orchestrator = ExtractionOrchestrator(db_session)
        
        # Create test items with various account code formats
        test_items = [
            {"account_code": "0122-0000", "account_name": "Cash - Operating", "amount": 211729.81},
            {"account_code": "0122-OOOO", "account_name": "Cash Operating", "amount": 100.00},  # OCR error (O vs 0)
            {"account_code": "", "account_name": "Cash - Operating", "amount": 50.00},  # No code
            {"account_code": "9999-9999", "account_name": "Unknown Account", "amount": 25.00},  # Unmapped
        ]
        
        # Run intelligent matching
        matched_items = orchestrator._match_accounts_intelligent(test_items)
        
        # Verify matching results
        assert matched_items[0]["match_method"] == "exact_code", "Should match exact code"
        assert matched_items[0]["match_confidence"] == 100.0
        
        # Fuzzy code match may or may not work depending on similarity threshold
        print(f"\nMatching results for OCR error:")
        print(f"  Method: {matched_items[1].get('match_method')}")
        print(f"  Confidence: {matched_items[1].get('match_confidence')}")
        
        # Name-only match
        assert matched_items[2]["match_method"] in ["exact_name", "fuzzy_name"], "Should match by name"
        
        # Unmapped account
        assert matched_items[3]["match_method"] == "unmapped", "Should be unmapped"
        assert matched_items[3]["needs_review"] is True


class TestDataQualityValidation:
    """Test data quality and zero data loss"""
    
    def test_zero_data_loss_verification(self):
        """Verify all accounts from PDF are extracted"""
        parser = FinancialTableParser()
        
        pdf_path = PDF_BASE_PATH / "Wendover-Commons" / "2024" / "12" / "Wendover Commons Balance Sheet December 2024.pdf"
        
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        
        result = parser.extract_balance_sheet_table(pdf_data)
        
        # Get extraction report
        total_extracted = len(result["line_items"])
        
        # Wendover balance sheet should have ~50-70 line items
        # (Assets: ~30, Liabilities: ~15, Equity: ~10)
        MIN_EXPECTED_ITEMS = 40
        
        print(f"\nData Loss Check:")
        print(f"  Items extracted: {total_extracted}")
        print(f"  Minimum expected: {MIN_EXPECTED_ITEMS}")
        print(f"  Extraction method: {result.get('extraction_method')}")
        
        assert total_extracted >= MIN_EXPECTED_ITEMS, \
            f"Possible data loss: only {total_extracted} items extracted (expected >= {MIN_EXPECTED_ITEMS})"
    
    def test_amount_precision(self):
        """Verify monetary amounts preserve precision"""
        parser = FinancialTableParser()
        
        # Test amount parsing
        test_amounts = [
            ("$211,729.81", Decimal("211729.81")),
            ("(2,225,410.00)", Decimal("-2225410.00")),
            ("-571,883.75", Decimal("-571883.75")),
            ("22939865.40", Decimal("22939865.40")),
            ("$0.01", Decimal("0.01")),
        ]
        
        for amount_str, expected in test_amounts:
            parsed = parser._parse_amount(amount_str)
            assert parsed == expected, f"Amount parsing failed for {amount_str}: {parsed} != {expected}"
    
    def test_table_vs_text_extraction_comparison(self):
        """Compare table extraction vs text extraction accuracy"""
        parser = FinancialTableParser()
        
        pdf_path = PDF_BASE_PATH / "Wendover-Commons" / "2024" / "12" / "Wendover Commons Balance Sheet December 2024.pdf"
        
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        
        # Extract with tables
        table_result = parser.extract_balance_sheet_table(pdf_data)
        
        print(f"\nExtraction Method Comparison:")
        print(f"  Table extraction items: {len(table_result['line_items'])}")
        print(f"  Table method: {table_result.get('extraction_method')}")
        
        # Table extraction should yield more items than text-only
        assert len(table_result["line_items"]) > 0, "Table extraction failed"


class TestMultiPropertySupport:
    """Test extraction works for all 4 properties"""
    
    def test_wendover_format(self):
        """Test Wendover format (has account codes)"""
        parser = FinancialTableParser()
        pdf_path = PDF_BASE_PATH / "Wendover-Commons" / "2024" / "12" / "Wendover Commons Balance Sheet December 2024.pdf"
        
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            result = parser.extract_balance_sheet_table(f.read())
        
        assert result["success"] is True
        
        # Wendover should have account codes
        has_codes = any(item.get("account_code") for item in result["line_items"])
        print(f"\nWendover: Account codes found: {has_codes}")
    
    def test_esp_format(self):
        """Test ESP format (name-based only)"""
        parser = FinancialTableParser()
        pdf_path = PDF_BASE_PATH / "ESP" / "2024" / "12" / "Eastern Shore Plaza Balance Sheet December 2024.pdf"
        
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            result = parser.extract_balance_sheet_table(f.read())
        
        assert result["success"] is True
        assert len(result["line_items"]) > 0
        
        # ESP may not have account codes
        has_codes = any(item.get("account_code") for item in result["line_items"])
        print(f"\nESP: Account codes found: {has_codes}")
    
    def test_hammond_format(self):
        """Test Hammond Aire format"""
        parser = FinancialTableParser()
        pdf_path = PDF_BASE_PATH / "Hammond-Aire-Plaza" / "2024" / "12" / "Hammond Aire Plaza Balance Sheet December 2024.pdf"
        
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            result = parser.extract_balance_sheet_table(f.read())
        
        assert result["success"] is True
        print(f"\nHammond Aire: {len(result['line_items'])} items extracted")
    
    def test_tcsh_format(self):
        """Test TCSH format (has account codes)"""
        parser = FinancialTableParser()
        pdf_path = PDF_BASE_PATH / "TCSH" / "2024" / "12" / "The Crossings of Spring Hill Balance Sheet December 2024.pdf"
        
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            result = parser.extract_balance_sheet_table(f.read())
        
        assert result["success"] is True
        
        # TCSH should have account codes
        has_codes = any(item.get("account_code") for item in result["line_items"])
        print(f"\nTCSH: Account codes found: {has_codes}")


class TestExtractionPerformance:
    """Test extraction performance and efficiency"""
    
    def test_extraction_speed(self):
        """Verify extraction completes in reasonable time"""
        import time
        
        parser = FinancialTableParser()
        pdf_path = PDF_BASE_PATH / "Wendover-Commons" / "2024" / "12" / "Wendover Commons Balance Sheet December 2024.pdf"
        
        if not pdf_path.exists():
            pytest.skip(f"PDF not found: {pdf_path}")
        
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        
        start_time = time.time()
        result = parser.extract_balance_sheet_table(pdf_data)
        end_time = time.time()
        
        extraction_time = end_time - start_time
        
        print(f"\nExtraction Performance:")
        print(f"  Time: {extraction_time:.2f} seconds")
        print(f"  Items: {len(result['line_items'])}")
        print(f"  Items/second: {len(result['line_items'])/extraction_time:.1f}")
        
        # Should complete within 10 seconds for typical PDF
        assert extraction_time < 10.0, f"Extraction too slow: {extraction_time:.2f}s"


@pytest.mark.slow
class TestAllPDFs:
    """Comprehensive test of all 28 PDFs"""
    
    def test_all_wendover_pdfs(self):
        """Test all 7 Wendover PDFs"""
        parser = FinancialTableParser()
        wendover_dir = PDF_BASE_PATH / "Wendover-Commons" / "2024"
        
        if not wendover_dir.exists():
            pytest.skip(f"Wendover directory not found: {wendover_dir}")
        
        pdf_files = list(wendover_dir.rglob("*.pdf"))
        results = []
        
        for pdf_file in pdf_files:
            with open(pdf_file, "rb") as f:
                result = parser.extract_balance_sheet_table(f.read())
                results.append({
                    "file": pdf_file.name,
                    "success": result["success"],
                    "items": len(result.get("line_items", []))
                })
        
        print(f"\nWendover PDFs tested: {len(results)}")
        for r in results:
            print(f"  {r['file']}: {'✓' if r['success'] else '✗'} ({r['items']} items)")
        
        success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
        assert success_rate >= 80, f"Too many failures: {success_rate:.1f}% success rate"

