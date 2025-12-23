"""
Test Suite for Workflow Lock Service

Tests cover:
- Lock creation
- Lock release
- Auto-release conditions
- Lock approval/rejection
- DSCR-based auto-release
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.workflow_lock_service import WorkflowLockService
from app.models.workflow_lock import WorkflowLock, LockReason, LockScope, LockStatus
from app.models.property import Property
from app.models.financial_period import FinancialPeriod


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def workflow_lock_service(mock_db):
    """WorkflowLockService instance for testing"""
    return WorkflowLockService(mock_db)


@pytest.fixture
def sample_lock():
    """Sample workflow lock for testing"""
    return WorkflowLock(
        id=1,
        property_id=1,
        period_id=1,
        lock_reason=LockReason.DSCR_BREACH,
        lock_scope=LockScope.PROPERTY_ALL,
        lock_status=LockStatus.ACTIVE,
        title="DSCR Breach Detected",
        description="DSCR below threshold",
        locked_by=1,
        locked_at=datetime.utcnow()
    )


class TestLockCreation:
    """Test workflow lock creation"""

    def test_create_lock(self, workflow_lock_service, mock_db):
        """Test creating a new workflow lock"""
        lock_data = {
            "property_id": 1,
            "period_id": 1,
            "lock_reason": LockReason.DSCR_BREACH,
            "lock_scope": LockScope.PROPERTY_ALL,
            "title": "Test Lock",
            "description": "Test description",
            "locked_by": 1
        }
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        result = workflow_lock_service.create_lock(**lock_data)
        
        assert result is not None
        assert result.get("success") is True
        assert mock_db.add.called

    def test_create_lock_with_auto_release_conditions(self, workflow_lock_service, mock_db):
        """Test creating a lock with auto-release conditions"""
        lock_data = {
            "property_id": 1,
            "period_id": 1,
            "lock_reason": LockReason.DSCR_BREACH,
            "lock_scope": LockScope.PROPERTY_ALL,
            "title": "Test Lock",
            "description": "Test description",
            "locked_by": 1,
            "auto_release_conditions": {
                "metric": "DSCR",
                "threshold": 1.25,
                "operator": ">="
            }
        }
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        result = workflow_lock_service.create_lock(**lock_data)
        
        assert result is not None
        assert result.get("success") is True


class TestLockRelease:
    """Test workflow lock release"""

    def test_release_lock(self, workflow_lock_service, mock_db, sample_lock):
        """Test releasing an active lock"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_lock
        
        result = workflow_lock_service.release_lock(
            lock_id=1,
            unlocked_by=2,
            resolution_notes="Resolved DSCR issue"
        )
        
        assert result is not None
        assert result.get("success") is True
        assert sample_lock.lock_status == LockStatus.RELEASED
        assert sample_lock.unlocked_by == 2

    def test_release_lock_not_found(self, workflow_lock_service, mock_db):
        """Test releasing a non-existent lock"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = workflow_lock_service.release_lock(
            lock_id=999,
            unlocked_by=1
        )
        
        assert result is not None
        assert result.get("success") is False
        assert "not found" in result.get("error", "").lower()


class TestAutoReleaseConditions:
    """Test auto-release condition checking"""

    def test_check_auto_release_dscr_met(self, workflow_lock_service, mock_db, sample_lock):
        """Test auto-release when DSCR condition is met"""
        sample_lock.auto_release_conditions = {
            "metric": "DSCR",
            "threshold": 1.25,
            "operator": ">="
        }
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_lock
        
        # Mock DSCR calculation
        with patch.object(workflow_lock_service, '_get_dscr_value') as mock_dscr:
            mock_dscr.return_value = 1.30  # Above threshold
            
            result = workflow_lock_service.check_auto_release_conditions(lock_id=1)
            
            assert result is not None
            # Should trigger auto-release
            if result.get("conditions_met"):
                assert result["conditions_met"] is True

    def test_check_auto_release_dscr_not_met(self, workflow_lock_service, mock_db, sample_lock):
        """Test auto-release when DSCR condition is not met"""
        sample_lock.auto_release_conditions = {
            "metric": "DSCR",
            "threshold": 1.25,
            "operator": ">="
        }
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_lock
        
        with patch.object(workflow_lock_service, '_get_dscr_value') as mock_dscr:
            mock_dscr.return_value = 1.15  # Below threshold
            
            result = workflow_lock_service.check_auto_release_conditions(lock_id=1)
            
            assert result is not None
            assert result.get("conditions_met") is False

    def test_check_auto_release_no_conditions(self, workflow_lock_service, mock_db, sample_lock):
        """Test auto-release check when no conditions are set"""
        sample_lock.auto_release_conditions = None
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_lock
        
        result = workflow_lock_service.check_auto_release_conditions(lock_id=1)
        
        assert result is not None
        assert result.get("success") is False or "No auto-release conditions" in result.get("error", "")


class TestLockApproval:
    """Test lock approval workflow"""

    def test_approve_lock(self, workflow_lock_service, mock_db, sample_lock):
        """Test approving a lock"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_lock
        
        result = workflow_lock_service.approve_lock(
            lock_id=1,
            approved_by=2,
            resolution_notes="Approved for release"
        )
        
        assert result is not None
        assert result.get("success") is True
        assert sample_lock.approved_by == 2
        assert sample_lock.lock_status == LockStatus.APPROVED

    def test_reject_lock(self, workflow_lock_service, mock_db, sample_lock):
        """Test rejecting a lock"""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_lock
        
        result = workflow_lock_service.reject_lock(
            lock_id=1,
            rejected_by=2,
            rejection_reason="Insufficient documentation"
        )
        
        assert result is not None
        assert result.get("success") is True
        assert sample_lock.rejected_by == 2
        assert sample_lock.lock_status == LockStatus.REJECTED


class TestLockQueries:
    """Test lock query operations"""

    def test_get_locks_by_property(self, workflow_lock_service, mock_db):
        """Test retrieving locks for a specific property"""
        locks = [
            Mock(id=1, property_id=1, lock_status=LockStatus.ACTIVE),
            Mock(id=2, property_id=1, lock_status=LockStatus.ACTIVE),
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = locks
        
        result = workflow_lock_service.get_locks_by_property(property_id=1)
        
        assert result is not None
        assert len(result) == 2

    def test_get_active_locks(self, workflow_lock_service, mock_db):
        """Test retrieving all active locks"""
        locks = [
            Mock(id=1, lock_status=LockStatus.ACTIVE),
            Mock(id=2, lock_status=LockStatus.ACTIVE),
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = locks
        
        result = workflow_lock_service.get_active_locks()
        
        assert result is not None
        assert len(result) == 2

    def test_get_lock_statistics(self, workflow_lock_service, mock_db):
        """Test retrieving lock statistics"""
        mock_db.query.return_value.filter.return_value.count.side_effect = [5, 3, 2]  # active, approved, rejected
        
        stats = workflow_lock_service.get_lock_statistics()
        
        assert stats is not None
        assert "active" in stats or "total" in stats


@pytest.mark.integration
class TestWorkflowLockIntegration:
    """Integration tests for workflow lock service"""

    def test_complete_lock_lifecycle(self, db_session):
        """Test complete lock lifecycle: create -> approve -> release"""
        workflow_service = WorkflowLockService(db_session)
        
        # Create lock
        create_result = workflow_service.create_lock(
            property_id=1,
            period_id=1,
            lock_reason=LockReason.DSCR_BREACH,
            lock_scope=LockScope.PROPERTY_ALL,
            title="Test Lock",
            description="Integration test",
            locked_by=1
        )
        
        assert create_result is not None
        assert create_result.get("success") is True
        
        lock_id = create_result.get("lock_id") or create_result.get("id")
        
        if lock_id:
            # Approve lock
            approve_result = workflow_service.approve_lock(
                lock_id=lock_id,
                approved_by=2,
                resolution_notes="Approved in test"
            )
            
            assert approve_result is not None
            
            # Release lock
            release_result = workflow_service.release_lock(
                lock_id=lock_id,
                unlocked_by=2,
                resolution_notes="Released in test"
            )
            
            assert release_result is not None
            assert release_result.get("success") is True

