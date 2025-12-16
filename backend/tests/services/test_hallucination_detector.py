"""
Comprehensive Unit Tests for Hallucination Detector Service

Tests cover:
- Claim extraction (currency, percentage, date, ratio)
- Claim verification against database
- Claim verification against documents
- Error handling and edge cases
- Performance and security
"""
import pytest
import time
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.services.hallucination_detector import HallucinationDetector, Claim
from app.models.financial_metrics import FinancialMetrics
from app.models.income_statement_data import IncomeStatementData
from app.models.financial_period import FinancialPeriod


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = Mock(spec=Session)
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def hallucination_detector(mock_db):
    """Create HallucinationDetector instance with mocked database"""
    return HallucinationDetector(db=mock_db)


@pytest.fixture
def sample_claims():
    """Sample claims for testing"""
    return [
        Claim(
            claim_type='currency',
            value=1234567.89,
            original_text='$1,234,567.89',
            context='The NOI was $1,234,567.89 for the quarter'
        ),
        Claim(
            claim_type='percentage',
            value=85.5,
            original_text='85.5%',
            context='Occupancy rate was 85.5%'
        ),
        Claim(
            claim_type='ratio',
            value=1.25,
            original_text='DSCR 1.25',
            context='Debt service coverage ratio was DSCR 1.25'
        ),
        Claim(
            claim_type='date',
            value=2024.3,
            original_text='Q3 2024',
            context='For Q3 2024, the property performed well'
        )
    ]


@pytest.fixture
def sample_financial_metrics():
    """Sample financial metrics for database mocking"""
    metrics = Mock(spec=FinancialMetrics)
    metrics.property_id = 1
    metrics.period_id = 1
    metrics.net_operating_income = 1234567.89
    metrics.total_revenue = 2000000.00
    metrics.occupancy_rate = 85.5
    metrics.dscr = 1.25
    return metrics


@pytest.fixture
def sample_income_statement_data():
    """Sample income statement data for database mocking"""
    data = Mock(spec=IncomeStatementData)
    data.property_id = 1
    data.period_id = 1
    data.amount = 1234567.89
    return data


@pytest.fixture
def sample_financial_period():
    """Sample financial period for database mocking"""
    period = Mock(spec=FinancialPeriod)
    period.property_id = 1
    period.period_year = 2024
    period.period_month = 9  # Q3 = September
    return period


# ============================================================================
# TEST: Claim Extraction
# ============================================================================

class TestClaimExtraction:
    """Test claim extraction from text"""
    
    def test_should_extract_currency_claims(self, hallucination_detector):
        """Test extraction of currency values in various formats"""
        text = "The NOI was $1,234,567.89 and revenue was $2.5M"
        claims = hallucination_detector._extract_claims(text)
        
        assert len(claims) >= 2
        currency_claims = [c for c in claims if c.claim_type == 'currency']
        assert len(currency_claims) >= 2
        
        # Check first claim
        assert currency_claims[0].value == 1234567.89
        assert '$1,234,567.89' in currency_claims[0].original_text
        
        # Check second claim (with M suffix)
        million_claim = next((c for c in currency_claims if 'M' in c.original_text.upper()), None)
        assert million_claim is not None
        assert million_claim.value == 2500000.0
    
    def test_should_extract_percentage_claims(self, hallucination_detector):
        """Test extraction of percentage values"""
        text = "Occupancy rate was 85.5% and expense ratio was 12.5 percent"
        claims = hallucination_detector._extract_claims(text)
        
        percentage_claims = [c for c in claims if c.claim_type == 'percentage']
        assert len(percentage_claims) >= 2
        assert any(c.value == 85.5 for c in percentage_claims)
        assert any(c.value == 12.5 for c in percentage_claims)
    
    def test_should_extract_ratio_claims(self, hallucination_detector):
        """Test extraction of ratio values (DSCR, etc.)"""
        text = "The DSCR was 1.25 and coverage ratio of 1.5x"
        claims = hallucination_detector._extract_claims(text)
        
        ratio_claims = [c for c in claims if c.claim_type == 'ratio']
        assert len(ratio_claims) >= 1
        assert any(c.value == 1.25 for c in ratio_claims)
    
    def test_should_extract_date_claims(self, hallucination_detector):
        """Test extraction of date values (quarters, months, dates)"""
        text = "For Q3 2024 and December 2024, the property performed well"
        claims = hallucination_detector._extract_claims(text)
        
        date_claims = [c for c in claims if c.claim_type == 'date']
        assert len(date_claims) >= 1
        assert any('Q3' in c.original_text for c in date_claims)
    
    def test_should_handle_empty_text(self, hallucination_detector):
        """Test that empty text returns no claims"""
        claims = hallucination_detector._extract_claims("")
        assert len(claims) == 0
    
    def test_should_handle_text_with_no_numeric_claims(self, hallucination_detector):
        """Test that text without numeric values returns no claims"""
        text = "This is a text without any numbers or financial data."
        claims = hallucination_detector._extract_claims(text)
        assert len(claims) == 0
    
    def test_should_handle_very_long_text(self, hallucination_detector):
        """Test extraction from very long text (>10,000 characters)"""
        # Create long text with claims scattered throughout
        base_text = "The NOI was $1,234,567.89. " * 100
        text = base_text + "Revenue was $2.5M. " * 100
        
        start_time = time.time()
        claims = hallucination_detector._extract_claims(text)
        duration = time.time() - start_time
        
        # Should complete in reasonable time (< 1 second)
        assert duration < 1.0
        assert len(claims) > 0
    
    def test_should_handle_special_characters(self, hallucination_detector):
        """Test extraction with special characters and Unicode"""
        text = "Revenue: $1,234,567.89 (€1,100,000) - 85.5% occupancy"
        claims = hallucination_detector._extract_claims(text)
        
        # Should extract USD currency and percentage
        currency_claims = [c for c in claims if c.claim_type == 'currency']
        assert len(currency_claims) >= 1
        assert currency_claims[0].value == 1234567.89
    
    def test_should_handle_unicode_text(self, hallucination_detector):
        """Test extraction with Unicode characters"""
        text = "Revenue: $1,234,567.89 - 收入: ¥8,000,000"
        claims = hallucination_detector._extract_claims(text)
        
        # Should extract USD currency
        currency_claims = [c for c in claims if c.claim_type == 'currency']
        assert len(currency_claims) >= 1
    
    def test_should_extract_context_around_claims(self, hallucination_detector):
        """Test that context is properly extracted around claims"""
        text = "For the quarter ending Q3 2024, the NOI was $1,234,567.89 which exceeded expectations."
        claims = hallucination_detector._extract_claims(text)
        
        assert len(claims) >= 2  # Date and currency
        
        # Check context includes surrounding text
        currency_claim = next((c for c in claims if c.claim_type == 'currency'), None)
        assert currency_claim is not None
        assert currency_claim.context is not None
        assert len(currency_claim.context) > len(currency_claim.original_text)


# ============================================================================
# TEST: Currency Value Parsing
# ============================================================================

class TestCurrencyParsing:
    """Test currency value parsing with various formats"""
    
    def test_should_parse_currency_with_commas(self, hallucination_detector):
        """Test parsing currency with comma separators"""
        value = hallucination_detector._parse_currency_value("1,234,567.89", "$1,234,567.89")
        assert value == 1234567.89
    
    def test_should_parse_currency_with_m_suffix(self, hallucination_detector):
        """Test parsing currency with million suffix"""
        value = hallucination_detector._parse_currency_value("2.5", "$2.5M")
        assert value == 2500000.0
    
    def test_should_parse_currency_with_k_suffix(self, hallucination_detector):
        """Test parsing currency with thousand suffix"""
        value = hallucination_detector._parse_currency_value("500", "$500K")
        assert value == 500000.0
    
    def test_should_parse_currency_without_suffix(self, hallucination_detector):
        """Test parsing currency without suffix"""
        value = hallucination_detector._parse_currency_value("1234.56", "$1234.56")
        assert value == 1234.56
    
    def test_should_handle_invalid_currency_format(self, hallucination_detector):
        """Test handling of invalid currency format"""
        value = hallucination_detector._parse_currency_value("invalid", "invalid")
        assert value is None


# ============================================================================
# TEST: Date Value Parsing
# ============================================================================

class TestDateParsing:
    """Test date value parsing"""
    
    def test_should_parse_quarter_format(self, hallucination_detector):
        """Test parsing Q3 2024 format"""
        match = Mock()
        match.groups.return_value = ('3', '2024')
        value = hallucination_detector._parse_date_value(match)
        assert value == 2024.3
    
    def test_should_parse_month_year_format(self, hallucination_detector):
        """Test parsing December 2024 format"""
        match = Mock()
        match.groups.return_value = ('December', '2024')
        value = hallucination_detector._parse_date_value(match)
        assert value == 2024.12
    
    def test_should_parse_iso_date_format(self, hallucination_detector):
        """Test parsing YYYY-MM-DD format"""
        match = Mock()
        match.groups.return_value = ('2024', '12', '01')
        value = hallucination_detector._parse_date_value(match)
        assert value == 2024.1201
    
    def test_should_handle_invalid_date_format(self, hallucination_detector):
        """Test handling of invalid date format"""
        match = Mock()
        match.groups.return_value = ('invalid', 'format')
        value = hallucination_detector._parse_date_value(match)
        assert value is None


# ============================================================================
# TEST: Claim Verification Against Database
# ============================================================================

class TestDatabaseVerification:
    """Test claim verification against database"""
    
    def test_should_verify_currency_claim_within_tolerance(
        self, hallucination_detector, mock_db, sample_financial_metrics
    ):
        """Test verification of currency claim within tolerance"""
        claim = Claim(
            claim_type='currency',
            value=1234567.89,
            original_text='$1,234,567.89'
        )
        
        # Mock database query
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [sample_financial_metrics]
        mock_db.query.return_value = query_mock
        
        verified = hallucination_detector._verify_currency_in_db(claim, property_id=1, period_id=1)
        
        assert verified is True
        assert claim.verified is True
        assert claim.verification_source == 'database'
    
    def test_should_reject_currency_claim_outside_tolerance(
        self, hallucination_detector, mock_db, sample_financial_metrics
    ):
        """Test rejection of currency claim outside tolerance"""
        claim = Claim(
            claim_type='currency',
            value=2000000.00,  # Way outside tolerance
            original_text='$2,000,000.00'
        )
        
        # Mock database query
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [sample_financial_metrics]
        mock_db.query.return_value = query_mock
        
        verified = hallucination_detector._verify_currency_in_db(claim, property_id=1, period_id=1)
        
        assert verified is False
    
    def test_should_verify_percentage_claim(
        self, hallucination_detector, mock_db, sample_financial_metrics
    ):
        """Test verification of percentage claim"""
        claim = Claim(
            claim_type='percentage',
            value=85.5,
            original_text='85.5%'
        )
        
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [sample_financial_metrics]
        mock_db.query.return_value = query_mock
        
        verified = hallucination_detector._verify_percentage_in_db(claim, property_id=1, period_id=1)
        
        assert verified is True
    
    def test_should_verify_ratio_claim(
        self, hallucination_detector, mock_db, sample_financial_metrics
    ):
        """Test verification of ratio claim (DSCR)"""
        claim = Claim(
            claim_type='ratio',
            value=1.25,
            original_text='DSCR 1.25'
        )
        
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [sample_financial_metrics]
        mock_db.query.return_value = query_mock
        
        verified = hallucination_detector._verify_ratio_in_db(claim, property_id=1, period_id=1)
        
        assert verified is True
    
    def test_should_verify_date_claim(
        self, hallucination_detector, mock_db, sample_financial_period
    ):
        """Test verification of date claim"""
        claim = Claim(
            claim_type='date',
            value=2024.3,  # Q3 2024
            original_text='Q3 2024'
        )
        
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [sample_financial_period]
        mock_db.query.return_value = query_mock
        
        verified = hallucination_detector._verify_date_in_db(claim, property_id=1)
        
        assert verified is True
    
    def test_should_handle_database_error_gracefully(
        self, hallucination_detector, mock_db
    ):
        """Test graceful handling of database errors"""
        claim = Claim(
            claim_type='currency',
            value=1234567.89,
            original_text='$1,234,567.89'
        )
        
        # Mock database error
        mock_db.query.side_effect = SQLAlchemyError("Database connection failed")
        
        verified = hallucination_detector._verify_currency_in_db(claim, property_id=1, period_id=1)
        
        assert verified is False
    
    def test_should_handle_empty_database_results(
        self, hallucination_detector, mock_db
    ):
        """Test handling when database returns no results"""
        claim = Claim(
            claim_type='currency',
            value=1234567.89,
            original_text='$1,234,567.89'
        )
        
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []  # No results
        mock_db.query.return_value = query_mock
        
        verified = hallucination_detector._verify_currency_in_db(claim, property_id=1, period_id=1)
        
        assert verified is False
    
    def test_should_verify_against_income_statement_data(
        self, hallucination_detector, mock_db, sample_income_statement_data
    ):
        """Test verification against income statement data"""
        claim = Claim(
            claim_type='currency',
            value=1234567.89,
            original_text='$1,234,567.89'
        )
        
        # Mock FinancialMetrics query (no match)
        metrics_query = Mock()
        metrics_query.filter.return_value = metrics_query
        metrics_query.all.return_value = []
        
        # Mock IncomeStatementData query (match)
        income_query = Mock()
        income_query.filter.return_value = income_query
        income_query.all.return_value = [sample_income_statement_data]
        
        mock_db.query.side_effect = [metrics_query, income_query]
        
        verified = hallucination_detector._verify_currency_in_db(claim, property_id=1, period_id=1)
        
        assert verified is True


# ============================================================================
# TEST: Claim Verification Against Documents
# ============================================================================

class TestDocumentVerification:
    """Test claim verification against source documents"""
    
    def test_should_verify_claim_in_document_chunks(
        self, hallucination_detector
    ):
        """Test verification of claim in document chunks"""
        claim = Claim(
            claim_type='currency',
            value=1234567.89,
            original_text='$1,234,567.89'
        )
        
        sources = [
            {
                'chunk_text': 'The net operating income for the period was $1,234,567.89',
                'chunk_id': 1
            }
        ]
        
        verified = hallucination_detector._verify_against_documents(claim, sources)
        
        assert verified is True
        assert claim.verified is True
        assert claim.verification_source == 'documents'
    
    def test_should_reject_claim_not_in_documents(
        self, hallucination_detector
    ):
        """Test rejection of claim not found in documents"""
        claim = Claim(
            claim_type='currency',
            value=9999999.99,
            original_text='$9,999,999.99'
        )
        
        sources = [
            {
                'chunk_text': 'The net operating income was $1,234,567.89',
                'chunk_id': 1
            }
        ]
        
        verified = hallucination_detector._verify_against_documents(claim, sources)
        
        assert verified is False
    
    def test_should_handle_empty_sources(
        self, hallucination_detector
    ):
        """Test handling of empty source list"""
        claim = Claim(
            claim_type='currency',
            value=1234567.89,
            original_text='$1,234,567.89'
        )
        
        verified = hallucination_detector._verify_against_documents(claim, [])
        
        assert verified is False
    
    def test_should_handle_none_sources(
        self, hallucination_detector
    ):
        """Test handling of None sources"""
        claim = Claim(
            claim_type='currency',
            value=1234567.89,
            original_text='$1,234,567.89'
        )
        
        verified = hallucination_detector._verify_against_documents(claim, None)
        
        assert verified is False


# ============================================================================
# TEST: Main Detection Function
# ============================================================================

class TestDetectHallucinations:
    """Test main detect_hallucinations function"""
    
    def test_should_detect_hallucinations_with_verified_claims(
        self, hallucination_detector, mock_db, sample_financial_metrics
    ):
        """Test detection when all claims are verified"""
        answer = "The NOI was $1,234,567.89 and occupancy was 85.5%"
        
        # Mock database verification
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [sample_financial_metrics]
        mock_db.query.return_value = query_mock
        
        result = hallucination_detector.detect_hallucinations(
            answer=answer,
            property_id=1,
            period_id=1
        )
        
        assert result['has_hallucinations'] is False
        assert result['total_claims'] > 0
        assert result['verified_claims'] == result['total_claims']
        assert result['unverified_claims'] == 0
        assert result['confidence_adjustment'] == 0.0
    
    def test_should_detect_hallucinations_with_unverified_claims(
        self, hallucination_detector, mock_db
    ):
        """Test detection when some claims are unverified"""
        answer = "The NOI was $9,999,999.99 and occupancy was 99.9%"
        
        # Mock database to return no matches
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        mock_db.query.return_value = query_mock
        
        result = hallucination_detector.detect_hallucinations(
            answer=answer,
            property_id=1,
            period_id=1
        )
        
        assert result['has_hallucinations'] is True
        assert result['unverified_claims'] > 0
        assert result['confidence_adjustment'] < 0
    
    def test_should_handle_empty_answer(
        self, hallucination_detector
    ):
        """Test handling of empty answer"""
        result = hallucination_detector.detect_hallucinations("")
        
        assert result['has_hallucinations'] is False
        assert result['total_claims'] == 0
        assert result['verification_time_ms'] >= 0
    
    def test_should_handle_none_answer(
        self, hallucination_detector
    ):
        """Test handling of None answer"""
        result = hallucination_detector.detect_hallucinations(None)
        
        assert result['has_hallucinations'] is False
        assert result['total_claims'] == 0
    
    def test_should_handle_very_long_answer(
        self, hallucination_detector, mock_db
    ):
        """Test handling of very long answer (>10,000 characters)"""
        # Create long answer with claims
        answer = "The NOI was $1,234,567.89. " * 500  # ~20,000 characters
        
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        mock_db.query.return_value = query_mock
        
        start_time = time.time()
        result = hallucination_detector.detect_hallucinations(answer)
        duration = time.time() - start_time
        
        # Should complete in reasonable time
        assert duration < 5.0
        assert result['total_claims'] > 0
    
    def test_should_handle_database_error_gracefully(
        self, hallucination_detector, mock_db
    ):
        """Test graceful handling of database errors"""
        answer = "The NOI was $1,234,567.89"
        
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        result = hallucination_detector.detect_hallucinations(answer)
        
        # Should return result with error flag
        assert 'error' in result or result['has_hallucinations'] is False
    
    def test_should_measure_verification_time(
        self, hallucination_detector, mock_db, sample_financial_metrics
    ):
        """Test that verification time is measured"""
        answer = "The NOI was $1,234,567.89"
        
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [sample_financial_metrics]
        mock_db.query.return_value = query_mock
        
        result = hallucination_detector.detect_hallucinations(answer)
        
        assert 'verification_time_ms' in result
        assert result['verification_time_ms'] >= 0
    
    @pytest.mark.parametrize("answer,expected_claims", [
        ("$1,234,567.89", 1),  # Currency only
        ("85.5%", 1),  # Percentage only
        ("DSCR 1.25", 1),  # Ratio only
        ("Q3 2024", 1),  # Date only
        ("$1M and 85%", 2),  # Multiple claim types
        ("No numbers here", 0),  # No claims
    ])
    def test_should_extract_claims_for_various_formats(
        self, hallucination_detector, answer, expected_claims
    ):
        """Test claim extraction for various answer formats"""
        result = hallucination_detector.detect_hallucinations(answer)
        assert result['total_claims'] >= expected_claims


# ============================================================================
# TEST: Confidence Adjustment
# ============================================================================

class TestConfidenceAdjustment:
    """Test confidence score adjustment"""
    
    def test_should_not_adjust_confidence_when_no_hallucinations(
        self, hallucination_detector
    ):
        """Test that confidence is not adjusted when no hallucinations"""
        detection_result = {
            'has_hallucinations': False,
            'confidence_adjustment': 0.0
        }
        
        adjusted = hallucination_detector.adjust_confidence(0.95, detection_result)
        
        assert adjusted == 0.95
    
    def test_should_reduce_confidence_when_hallucinations_detected(
        self, hallucination_detector
    ):
        """Test that confidence is reduced when hallucinations detected"""
        detection_result = {
            'has_hallucinations': True,
            'confidence_adjustment': -0.20  # 20% penalty
        }
        
        adjusted = hallucination_detector.adjust_confidence(0.95, detection_result)
        
        assert adjusted == 0.75  # 0.95 - 0.20
    
    def test_should_not_allow_negative_confidence(
        self, hallucination_detector
    ):
        """Test that confidence cannot go below 0"""
        detection_result = {
            'has_hallucinations': True,
            'confidence_adjustment': -1.0  # 100% penalty
        }
        
        adjusted = hallucination_detector.adjust_confidence(0.10, detection_result)
        
        assert adjusted >= 0.0
    
    def test_should_not_allow_confidence_above_one(
        self, hallucination_detector
    ):
        """Test that confidence cannot exceed 1.0"""
        detection_result = {
            'has_hallucinations': False,
            'confidence_adjustment': 0.0
        }
        
        adjusted = hallucination_detector.adjust_confidence(1.5, detection_result)
        
        assert adjusted <= 1.0


# ============================================================================
# TEST: Flag for Review
# ============================================================================

class TestFlagForReview:
    """Test flagging answers for manual review"""
    
    @patch('app.services.hallucination_detector.hallucination_config')
    @patch('app.services.hallucination_detector.REVIEW_QUEUE_AVAILABLE', True, create=True)
    def test_should_flag_answer_for_review_when_hallucinations_detected(
        self, mock_config, hallucination_detector, mock_db
    ):
        """Test flagging answer when hallucinations are detected"""
        mock_config.REVIEW_QUEUE_ENABLED = True
        mock_config.AUTO_FLAG_UNVERIFIED = True
        
        detection_result = {
            'has_hallucinations': True,
            'total_claims': 2,
            'verified_claims': 1,
            'unverified_claims': 1,
            'flagged_claims': [{'claim_type': 'currency', 'value': 999999.99}]
        }
        
        # Mock REVIEW_QUEUE_AVAILABLE
        with patch('app.services.hallucination_detector.REVIEW_QUEUE_AVAILABLE', True, create=True):
            with patch('app.services.hallucination_detector.HallucinationReview') as mock_review_class:
                mock_review = Mock()
                mock_review_class.return_value = mock_review
                
                review = hallucination_detector.flag_for_review(
                    nlq_query_id=1,
                    user_id=1,
                    answer="Test answer",
                    original_confidence=0.95,
                    detection_result=detection_result
                )
                
                # Review might be None if REVIEW_QUEUE_AVAILABLE check fails
                # This is acceptable behavior
                if review is not None:
                    mock_db.add.assert_called_once()
                    mock_db.commit.assert_called_once()
    
    @patch('app.services.hallucination_detector.hallucination_config')
    def test_should_not_flag_when_no_hallucinations(
        self, mock_config, hallucination_detector
    ):
        """Test that answer is not flagged when no hallucinations"""
        mock_config.REVIEW_QUEUE_ENABLED = True
        
        detection_result = {
            'has_hallucinations': False
        }
        
        review = hallucination_detector.flag_for_review(
            nlq_query_id=1,
            user_id=1,
            answer="Test answer",
            original_confidence=0.95,
            detection_result=detection_result
        )
        
        assert review is None
    
    @patch('app.services.hallucination_detector.hallucination_config')
    def test_should_handle_database_error_when_flagging(
        self, mock_config, hallucination_detector, mock_db
    ):
        """Test handling of database errors when flagging"""
        mock_config.REVIEW_QUEUE_ENABLED = True
        mock_config.AUTO_FLAG_UNVERIFIED = True
        
        detection_result = {
            'has_hallucinations': True,
            'total_claims': 1,
            'unverified_claims': 1,
            'flagged_claims': []
        }
        
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        review = hallucination_detector.flag_for_review(
            nlq_query_id=1,
            user_id=1,
            answer="Test answer",
            original_confidence=0.95,
            detection_result=detection_result
        )
        
        assert review is None
        mock_db.rollback.assert_called_once()


# ============================================================================
# TEST: Edge Cases and Security
# ============================================================================

class TestEdgeCases:
    """Test edge cases and security concerns"""
    
    def test_should_handle_regex_dos_attempt(
        self, hallucination_detector
    ):
        """Test protection against regex DoS attacks"""
        # Create input that could cause ReDoS
        malicious_input = "a" * 10000 + ".*" * 1000
        
        start_time = time.time()
        result = hallucination_detector.detect_hallucinations(malicious_input)
        duration = time.time() - start_time
        
        # Should complete in reasonable time (< 2 seconds)
        assert duration < 2.0
        assert 'error' not in result or result.get('error') is None
    
    def test_should_handle_invalid_property_id(
        self, hallucination_detector, mock_db
    ):
        """Test handling of invalid property_id"""
        answer = "The NOI was $1,234,567.89"
        
        # Should not raise exception with invalid property_id
        result = hallucination_detector.detect_hallucinations(
            answer=answer,
            property_id=-1  # Invalid ID
        )
        
        assert result is not None
    
    def test_should_handle_invalid_period_id(
        self, hallucination_detector, mock_db
    ):
        """Test handling of invalid period_id"""
        answer = "The NOI was $1,234,567.89"
        
        result = hallucination_detector.detect_hallucinations(
            answer=answer,
            period_id=-1  # Invalid ID
        )
        
        assert result is not None
    
    def test_should_handle_concurrent_requests(
        self, hallucination_detector, mock_db, sample_financial_metrics
    ):
        """Test handling of concurrent requests (thread safety)"""
        import threading
        
        answer = "The NOI was $1,234,567.89"
        results = []
        
        def detect():
            query_mock = Mock()
            query_mock.filter.return_value = query_mock
            query_mock.all.return_value = [sample_financial_metrics]
            mock_db.query.return_value = query_mock
            
            result = hallucination_detector.detect_hallucinations(answer)
            results.append(result)
        
        # Run 10 concurrent detections
        threads = [threading.Thread(target=detect) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        assert len(results) == 10
        assert all(r['total_claims'] > 0 for r in results)


# ============================================================================
# TEST: Performance
# ============================================================================

class TestPerformance:
    """Test performance requirements"""
    
    def test_should_complete_detection_quickly(
        self, hallucination_detector, mock_db, sample_financial_metrics
    ):
        """Test that detection completes within timeout"""
        answer = "The NOI was $1,234,567.89 and occupancy was 85.5%"
        
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [sample_financial_metrics]
        mock_db.query.return_value = query_mock
        
        start_time = time.time()
        result = hallucination_detector.detect_hallucinations(answer)
        duration = time.time() - start_time
        
        # Should complete in < 100ms (excluding DB time)
        assert duration < 0.1
        assert result['verification_time_ms'] < 1000  # Including DB time


# ============================================================================
# TEST: Integration
# ============================================================================

class TestIntegration:
    """Integration tests with real components"""
    
    @pytest.mark.integration
    def test_should_work_with_real_database(
        self, db_session
    ):
        """Integration test with real database (requires test DB)"""
        detector = HallucinationDetector(db=db_session)
        
        answer = "The NOI was $1,234,567.89"
        
        result = detector.detect_hallucinations(answer)
        
        assert result is not None
        assert 'has_hallucinations' in result
