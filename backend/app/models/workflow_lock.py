"""
Workflow Lock Model
Manages workflow locks tied to governance and committee approvals
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

from app.db.database import Base


class LockReason(str, enum.Enum):
    """Workflow lock reasons"""
    DSCR_BREACH = "DSCR_BREACH"
    OCCUPANCY_THRESHOLD = "OCCUPANCY_THRESHOLD"
    COVENANT_VIOLATION = "COVENANT_VIOLATION"
    COMMITTEE_REVIEW = "COMMITTEE_REVIEW"
    FINANCIAL_ANOMALY = "FINANCIAL_ANOMALY"
    VARIANCE_BREACH = "VARIANCE_BREACH"
    MANUAL_HOLD = "MANUAL_HOLD"
    DATA_QUALITY_ISSUE = "DATA_QUALITY_ISSUE"


class LockStatus(str, enum.Enum):
    """Lock status"""
    ACTIVE = "ACTIVE"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RELEASED = "RELEASED"


class LockScope(str, enum.Enum):
    """What is locked"""
    PROPERTY_ALL = "PROPERTY_ALL"  # All operations on property
    FINANCIAL_UPDATES = "FINANCIAL_UPDATES"  # Can't update financials
    REPORTING_ONLY = "REPORTING_ONLY"  # Can't generate reports
    TRANSACTION_APPROVAL = "TRANSACTION_APPROVAL"  # Requires approval for transactions
    DATA_ENTRY = "DATA_ENTRY"  # Can't enter new data


class WorkflowLock(Base):
    """
    Workflow Lock Model

    Enforces workflow pauses and governance controls.
    Prevents actions until committee approval or resolution.
    """
    __tablename__ = "workflow_locks"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    alert_id = Column(Integer, ForeignKey("committee_alerts.id"), nullable=True, index=True)

    # Lock details
    lock_reason = Column(SQLEnum(LockReason), nullable=False)
    lock_scope = Column(SQLEnum(LockScope), nullable=False, default=LockScope.FINANCIAL_UPDATES)
    status = Column(SQLEnum(LockStatus), nullable=False, default=LockStatus.ACTIVE, index=True)

    # Description
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Committee approval
    requires_committee_approval = Column(Boolean, default=True)
    approval_committee = Column(String(100), nullable=True)  # Which committee must approve

    # Timing
    locked_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    unlocked_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    # User tracking
    locked_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    unlocked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Resolution
    resolution_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Auto-release conditions
    auto_release_conditions = Column(JSONB, nullable=True)  # Conditions for auto-unlock
    auto_released = Column(Boolean, default=False)

    # Additional metadata
    metadata = Column(JSONB, nullable=True)

    # Related data (for traceability)
    br_id = Column(String(20), nullable=True)  # Business Requirement ID

    # Relationships
    property = relationship("Property", back_populates="workflow_locks")
    alert = relationship("CommitteeAlert", back_populates="workflow_locks")
    locked_by_user = relationship("User", foreign_keys=[locked_by], backref="locks_created")
    unlocked_by_user = relationship("User", foreign_keys=[unlocked_by], backref="locks_released")
    approved_by_user = relationship("User", foreign_keys=[approved_by], backref="locks_approved")
    rejected_by_user = relationship("User", foreign_keys=[rejected_by], backref="locks_rejected")

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<WorkflowLock(id={self.id}, property_id={self.property_id}, reason={self.lock_reason}, status={self.status})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "property_id": self.property_id,
            "alert_id": self.alert_id,
            "lock_reason": self.lock_reason.value if self.lock_reason else None,
            "lock_scope": self.lock_scope.value if self.lock_scope else None,
            "status": self.status.value if self.status else None,
            "title": self.title,
            "description": self.description,
            "requires_committee_approval": self.requires_committee_approval,
            "approval_committee": self.approval_committee,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "unlocked_at": self.unlocked_at.isoformat() if self.unlocked_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "locked_by": self.locked_by,
            "unlocked_by": self.unlocked_by,
            "approved_by": self.approved_by,
            "rejected_by": self.rejected_by,
            "resolution_notes": self.resolution_notes,
            "rejection_reason": self.rejection_reason,
            "auto_release_conditions": self.auto_release_conditions,
            "auto_released": self.auto_released,
            "metadata": self.metadata,
            "br_id": self.br_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_active(self) -> bool:
        """Check if lock is currently active"""
        return self.status == LockStatus.ACTIVE

    def is_blocking(self, operation: str) -> bool:
        """Check if this lock blocks a specific operation"""
        if not self.is_active():
            return False

        operation_scope_map = {
            "financial_update": [LockScope.PROPERTY_ALL, LockScope.FINANCIAL_UPDATES],
            "report_generation": [LockScope.PROPERTY_ALL, LockScope.REPORTING_ONLY],
            "data_entry": [LockScope.PROPERTY_ALL, LockScope.DATA_ENTRY],
            "transaction": [LockScope.PROPERTY_ALL, LockScope.TRANSACTION_APPROVAL],
        }

        blocking_scopes = operation_scope_map.get(operation, [])
        return self.lock_scope in blocking_scopes

    def days_locked(self) -> int:
        """Calculate days since lock was created"""
        if self.unlocked_at:
            delta = self.unlocked_at - self.locked_at
        else:
            delta = datetime.utcnow() - self.locked_at
        return delta.days

    def can_auto_release(self) -> bool:
        """Check if lock meets auto-release conditions"""
        if not self.auto_release_conditions:
            return False

        # Check conditions (simplified - implement full logic as needed)
        # Example: {"metric": "DSCR", "threshold": 1.25, "operator": ">="}
        return False  # Implement actual condition checking
