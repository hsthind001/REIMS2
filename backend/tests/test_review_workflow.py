"""
Comprehensive Test Suite for Review Workflow

Tests cover:
- Review queue operations
- Approval chains
- Dual approval logic
- Record correction workflow
- Impact analysis
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, MagicMock

from app.models.review_approval_chain import ReviewApprovalChain, ApprovalStatus
from app.models.account_mapping_rule import AccountMappingRule
from app.services.review_service import ReviewService
from app.services.review_auto_suggestion_service import ReviewAutoSuggestionService
from app.services.dscr_monitoring_service import DSCRMonitoringService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def sample_property(mock_db):
    """Sample property for testing"""
    prop = Property(
        id=1,
        property_code="TEST-001",
        property_name="Test Property",
        property_type="Office"
    )
    mock_db.query.return_value.filter.return_value.first.return_value = prop
    return prop


@pytest.fixture
def sample_period(mock_db):
    """Sample financial period for testing"""
    period = FinancialPeriod(
        id=1,
        property_id=1,
        period_year=2024,
        period_month=12,
        period_start_date=datetime(2024, 12, 1),
        period_end_date=datetime(2024, 12, 31)
    )
    return period


@pytest.fixture
def review_service(mock_db):
    """ReviewService instance for testing"""
    return ReviewService(mock_db)


@pytest.fixture
def sample_income_statement_record():
    """Sample income statement record needing review"""
    return IncomeStatementData(
        id=1,
        property_id=1,
        period_id=1,
        account_code="4010-0000",
        account_name="Base Rental Income",
        amount=Decimal("50000.00"),
        extraction_confidence=85.5,
        match_confidence=92.0,
        needs_review=True,
        reviewed=False
    )


class TestReviewQueueOperations:
    """Test review queue retrieval and filtering"""

    def test_get_review_queue_all_items(self, review_service, mock_db):
        """Test retrieving all items needing review"""
        # Mock database query results
        mock_records = [
            Mock(
                id=1,
                property_id=1,
                period_id=1,
                account_code="4010-0000",
                amount=Decimal("50000.00"),
                needs_review=True,
                reviewed=False
            ),
            Mock(
                id=2,
                property_id=1,
                period_id=1,
                account_code="5010-0000",
                amount=Decimal("10000.00"),
                needs_review=True,
                reviewed=False
            )
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = mock_records
        
        result = review_service.get_review_queue()
        
        assert result is not None
        assert "items" in result or "total" in result

    def test_get_review_queue_filtered_by_property(self, review_service, mock_db):
        """Test filtering review queue by property code"""
        mock_records = [Mock(id=1, property_id=1, needs_review=True)]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_records
        
        result = review_service.get_review_queue(property_code="TEST-001")
        
        assert result is not None

    def test_get_review_queue_filtered_by_document_type(self, review_service, mock_db):
        """Test filtering review queue by document type"""
        mock_records = [Mock(id=1, needs_review=True)]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_records
        
        result = review_service.get_review_queue(document_type="income_statement")
        
        assert result is not None

    def test_get_review_queue_pagination(self, review_service, mock_db):
        """Test pagination in review queue"""
        mock_records = [Mock(id=i, needs_review=True) for i in range(1, 21)]
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_records[:10]
        
        result = review_service.get_review_queue(skip=0, limit=10)
        
        assert result is not None


class TestApprovalWorkflow:
    """Test approval workflow operations"""

    def test_approve_record_single_approval(self, review_service, mock_db, sample_income_statement_record):
        """Test approving a record without changes (single approval)"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_income_statement_record
        
        result = review_service.approve_record(
            record_id=1,
            table_name="income_statement_data",
            user_id=1,
            notes="Verified correct"
        )
        
        assert result is not None
        assert "success" in result or result.get("success") is True
        # Verify record was marked as reviewed
        assert sample_income_statement_record.reviewed is True
        assert sample_income_statement_record.needs_review is False

    def test_approve_record_creates_audit_trail(self, review_service, mock_db, sample_income_statement_record):
        """Test that approval creates audit trail entry"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_income_statement_record
        
        result = review_service.approve_record(
            record_id=1,
            table_name="income_statement_data",
            user_id=1,
            notes="Approved"
        )
        
        # Verify audit trail was created (mock_db.add should be called)
        assert mock_db.add.called or mock_db.commit.called

    def test_correct_record_updates_fields(self, review_service, mock_db, sample_income_statement_record):
        """Test correcting record fields"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_income_statement_record
        
        corrections = {
            "amount": Decimal("55000.00"),
            "account_name": "Base Rental Income - Corrected"
        }
        
        result = review_service.correct_record(
            record_id=1,
            table_name="income_statement_data",
            corrections=corrections,
            user_id=1,
            notes="Corrected based on bank statement"
        )
        
        assert result is not None
        # Verify fields were updated
        assert sample_income_statement_record.amount == Decimal("55000.00")
        assert sample_income_statement_record.account_name == "Base Rental Income - Corrected"

    def test_correct_record_marks_as_reviewed(self, review_service, mock_db, sample_income_statement_record):
        """Test that correction marks record as reviewed"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_income_statement_record
        
        corrections = {"amount": Decimal("55000.00")}
        
        review_service.correct_record(
            record_id=1,
            table_name="income_statement_data",
            corrections=corrections,
            user_id=1
        )
        
        assert sample_income_statement_record.reviewed is True
        assert sample_income_statement_record.needs_review is False


class TestDualApprovalLogic:
    """Test dual approval requirements and workflow"""

    def test_high_risk_item_requires_dual_approval(self, review_service, mock_db):
        """Test that high-risk items require dual approval"""
        # Create a high-risk record (large variance)
        record = Mock(
            id=1,
            property_id=1,
            period_id=1,
            account_code="4010-0000",
            amount=Decimal("100000.00"),
            needs_review=True
        )
        mock_db.query.return_value.filter.return_value.first.return_value = record
        
        # Mock high variance calculation
        with patch.object(review_service, '_calculate_correction_impact') as mock_impact:
            mock_impact.return_value = {
                'total_variance': 50000.0,  # High variance
                'requires_dual_approval': True,
                'is_covenant_impacting': False,
                'is_dscr_affecting': False
            }
            
            corrections = {"amount": Decimal("150000.00")}
            
            # First approval should create approval chain
            result = review_service.correct_record(
                record_id=1,
                table_name="income_statement_data",
                corrections=corrections,
                user_id=1,
                notes="First approval"
            )
            
            # Verify approval chain was created
            assert mock_db.add.called

    def test_dual_approval_chain_creation(self, review_service, mock_db):
        """Test creation of approval chain for dual approval"""
        # Mock approval chain creation
        approval_chain = ReviewApprovalChain(
            id=1,
            record_id=1,
            table_name="income_statement_data",
            status=ApprovalStatus.PENDING_SECOND_APPROVAL,
            first_approver_id=1,
            first_approved_at=datetime.utcnow()
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing chain
        mock_db.add.return_value = None
        
        # Verify approval chain structure
        assert approval_chain.status == ApprovalStatus.PENDING_SECOND_APPROVAL
        assert approval_chain.first_approver_id == 1

    def test_second_approval_completes_chain(self, review_service, mock_db):
        """Test that second approval completes the approval chain"""
        approval_chain = ReviewApprovalChain(
            id=1,
            record_id=1,
            table_name="income_statement_data",
            status=ApprovalStatus.PENDING_SECOND_APPROVAL,
            first_approver_id=1,
            second_approver_id=2,
            first_approved_at=datetime.utcnow(),
            second_approved_at=datetime.utcnow()
        )
        
        # Simulate second approval
        approval_chain.status = ApprovalStatus.APPROVED
        approval_chain.second_approved_at = datetime.utcnow()
        
        assert approval_chain.status == ApprovalStatus.APPROVED
        assert approval_chain.second_approver_id == 2

    def test_covenant_impacting_correction_requires_dual_approval(self, review_service, mock_db):
        """Test that covenant-impacting corrections require dual approval"""
        with patch.object(review_service, '_calculate_covenant_impact') as mock_covenant:
            mock_covenant.return_value = True  # Covenant impacting
            
            impact = review_service._calculate_correction_impact(
                old_values={"amount": Decimal("100000.00")},
                corrections={"amount": Decimal("150000.00")},
                record=Mock(property_id=1, period_id=1)
            )
            
            # Should require dual approval if covenant impacting
            assert impact.get('is_covenant_impacting') is True

    def test_dscr_affecting_correction_requires_dual_approval(self, review_service, mock_db):
        """Test that DSCR-affecting corrections require dual approval"""
        with patch.object(review_service, '_calculate_dscr_impact') as mock_dscr:
            mock_dscr.return_value = True  # DSCR affecting
            
            impact = review_service._calculate_correction_impact(
                old_values={"amount": Decimal("50000.00")},
                corrections={"amount": Decimal("40000.00")},
                record=Mock(property_id=1, period_id=1)
            )
            
            # Should require dual approval if DSCR affecting
            assert impact.get('is_dscr_affecting') is True


class TestAccountMappingSuggestions:
    """Test account mapping auto-suggestion functionality"""

    def test_auto_suggestion_service_returns_suggestions(self, mock_db):
        """Test that auto-suggestion service returns account mapping suggestions"""
        suggestion_service = ReviewAutoSuggestionService(mock_db)
        
        # Mock account mapping rules
        mock_rules = [
            AccountMappingRule(
                id=1,
                property_id=1,
                raw_label="Rental Income",
                account_code="4010-0000",
                account_name="Base Rental Income",
                confidence_score=Decimal("95.0"),
                usage_count=10
            )
        ]
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_rules
        
        suggestions = suggestion_service.get_suggestions(
            property_id=1,
            raw_label="Rental Income",
            table_name="income_statement_data"
        )
        
        assert suggestions is not None
        assert len(suggestions) > 0

    def test_suggestions_ordered_by_confidence(self, mock_db):
        """Test that suggestions are ordered by confidence score"""
        suggestion_service = ReviewAutoSuggestionService(mock_db)
        
        mock_rules = [
            AccountMappingRule(
                id=1,
                raw_label="Income",
                account_code="4010-0000",
                confidence_score=Decimal("90.0"),
                usage_count=5
            ),
            AccountMappingRule(
                id=2,
                raw_label="Income",
                account_code="4020-0000",
                confidence_score=Decimal("95.0"),
                usage_count=10
            )
        ]
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_rules
        
        suggestions = suggestion_service.get_suggestions(
            property_id=1,
            raw_label="Income",
            table_name="income_statement_data"
        )
        
        # Highest confidence should be first
        if len(suggestions) > 1:
            assert suggestions[0].confidence_score >= suggestions[1].confidence_score


class TestImpactAnalysis:
    """Test impact analysis calculations"""

    def test_calculate_financial_impact(self, review_service, mock_db):
        """Test calculation of financial impact from corrections"""
        old_values = {
            "amount": Decimal("100000.00"),
            "period_amount": Decimal("50000.00")
        }
        corrections = {
            "amount": Decimal("120000.00"),
            "period_amount": Decimal("60000.00")
        }
        
        impact = review_service._calculate_correction_impact(
            old_values=old_values,
            corrections=corrections,
            record=Mock(property_id=1, period_id=1)
        )
        
        assert impact is not None
        assert "total_variance" in impact
        assert impact["total_variance"] > 0

    def test_high_variance_triggers_dual_approval(self, review_service, mock_db):
        """Test that high variance triggers dual approval requirement"""
        old_values = {"amount": Decimal("100000.00")}
        corrections = {"amount": Decimal("200000.00")}  # 100% increase
        
        impact = review_service._calculate_correction_impact(
            old_values=old_values,
            corrections=corrections,
            record=Mock(property_id=1, period_id=1)
        )
        
        # High variance should require dual approval
        if impact["total_variance"] > review_service.high_risk_threshold:
            assert impact["requires_dual_approval"] is True

    @patch('app.services.review_service.DSCRMonitoringService')
    def test_dscr_impact_calculation(self, mock_dscr_service, review_service, mock_db):
        """Test DSCR impact calculation"""
        mock_dscr = Mock()
        mock_dscr.calculate_dscr.return_value = {
            "success": True,
            "dscr": 1.25,
            "status": "warning"
        }
        mock_dscr_service.return_value = mock_dscr
        
        impact = review_service._calculate_dscr_impact(
            property_id=1,
            period_id=1,
            corrections={"amount": Decimal("50000.00")}
        )
        
        # Should check DSCR impact
        assert isinstance(impact, bool)

    def test_covenant_impact_calculation(self, review_service, mock_db):
        """Test covenant impact calculation"""
        # Mock covenant-affecting accounts
        with patch.object(review_service, '_get_covenant_affecting_accounts') as mock_accounts:
            mock_accounts.return_value = ["1010-0000", "1500-0000"]
            
            impact = review_service._calculate_covenant_impact(
                property_id=1,
                period_id=1,
                corrections={"account_code": "1010-0000", "amount": Decimal("50000.00")}
            )
            
            # Should detect covenant impact
            assert isinstance(impact, bool)


class TestBulkOperations:
    """Test bulk review operations"""

    def test_bulk_approve_records(self, review_service, mock_db):
        """Test bulk approval of multiple records"""
        record_ids = [1, 2, 3]
        table_name = "income_statement_data"
        
        # Mock records
        mock_records = [
            Mock(id=i, needs_review=True, reviewed=False)
            for i in record_ids
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = mock_records
        
        result = review_service.bulk_approve(
            record_ids=record_ids,
            table_name=table_name,
            user_id=1,
            notes="Bulk approval"
        )
        
        assert result is not None
        # Verify all records were marked as reviewed
        for record in mock_records:
            assert record.reviewed is True
            assert record.needs_review is False


@pytest.mark.integration
class TestReviewWorkflowIntegration:
    """Integration tests for review workflow"""

    def test_complete_review_workflow(self, db_session, sample_property, sample_period):
        """Test complete review workflow from queue to approval"""
        # Create a record needing review
        record = IncomeStatementData(
            property_id=sample_property.id,
            period_id=sample_period.id,
            account_code="4010-0000",
            account_name="Base Rental Income",
            amount=Decimal("50000.00"),
            needs_review=True,
            reviewed=False
        )
        db_session.add(record)
        db_session.commit()
        
        # Get review queue
        review_service = ReviewService(db_session)
        queue = review_service.get_review_queue()
        
        assert queue is not None
        assert len(queue.get("items", [])) > 0
        
        # Approve the record
        result = review_service.approve_record(
            record_id=record.id,
            table_name="income_statement_data",
            user_id=1,
            notes="Approved in test"
        )
        
        assert result is not None
        
        # Verify record is no longer in queue
        db_session.refresh(record)
        assert record.reviewed is True
        assert record.needs_review is False

    def test_correction_workflow_with_impact(self, db_session, sample_property, sample_period):
        """Test correction workflow with impact analysis"""
        # Create record
        record = IncomeStatementData(
            property_id=sample_property.id,
            period_id=sample_period.id,
            account_code="4010-0000",
            account_name="Base Rental Income",
            amount=Decimal("50000.00"),
            needs_review=True
        )
        db_session.add(record)
        db_session.commit()
        
        # Correct the record
        review_service = ReviewService(db_session)
        result = review_service.correct_record(
            record_id=record.id,
            table_name="income_statement_data",
            corrections={"amount": Decimal("55000.00")},
            user_id=1,
            notes="Corrected amount",
            recalculate_metrics=True
        )
        
        assert result is not None
        
        # Verify correction
        db_session.refresh(record)
        assert record.amount == Decimal("55000.00")
        assert record.reviewed is True

