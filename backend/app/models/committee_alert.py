"""
Committee Alert Model
Tracks risk alerts that require committee review/approval
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

from app.db.database import Base


class AlertType(str, enum.Enum):
    """Alert types"""
    DSCR_BREACH = "DSCR_BREACH"
    OCCUPANCY_WARNING = "OCCUPANCY_WARNING"
    OCCUPANCY_CRITICAL = "OCCUPANCY_CRITICAL"
    LTV_BREACH = "LTV_BREACH"
    COVENANT_VIOLATION = "COVENANT_VIOLATION"
    VARIANCE_BREACH = "VARIANCE_BREACH"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    FINANCIAL_THRESHOLD = "FINANCIAL_THRESHOLD"
    # New alert types
    DEBT_YIELD_BREACH = "DEBT_YIELD_BREACH"
    INTEREST_COVERAGE_BREACH = "INTEREST_COVERAGE_BREACH"
    BREAK_EVEN_OCCUPANCY_BREACH = "BREAK_EVEN_OCCUPANCY_BREACH"
    CASH_FLOW_NEGATIVE = "CASH_FLOW_NEGATIVE"
    REVENUE_DECLINE = "REVENUE_DECLINE"
    EXPENSE_SPIKE = "EXPENSE_SPIKE"
    LIQUIDITY_WARNING = "LIQUIDITY_WARNING"
    DEBT_TO_EQUITY_BREACH = "DEBT_TO_EQUITY_BREACH"
    CAPEX_THRESHOLD = "CAPEX_THRESHOLD"
    RENT_COLLECTION_RATE = "RENT_COLLECTION_RATE"


class AlertSeverity(str, enum.Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    URGENT = "URGENT"


class AlertStatus(str, enum.Enum):
    """Alert status"""
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class CommitteeType(str, enum.Enum):
    """Committee types"""
    FINANCE_SUBCOMMITTEE = "FINANCE_SUBCOMMITTEE"
    OCCUPANCY_SUBCOMMITTEE = "OCCUPANCY_SUBCOMMITTEE"
    RISK_COMMITTEE = "RISK_COMMITTEE"
    EXECUTIVE_COMMITTEE = "EXECUTIVE_COMMITTEE"


class CommitteeAlert(Base):
    """
    Committee Alert Model

    Tracks alerts that require committee review and approval.
    Linked to workflow locks for governance enforcement.
    """
    __tablename__ = "committee_alerts"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    financial_period_id = Column(Integer, ForeignKey("financial_periods.id"), nullable=True)

    # Alert details
    alert_type = Column(SQLEnum(AlertType), nullable=False, index=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, default=AlertSeverity.WARNING)
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE, index=True)

    # Title and description
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    # Threshold information
    threshold_value = Column(Numeric(15, 4), nullable=True)
    actual_value = Column(Numeric(15, 4), nullable=True)
    threshold_unit = Column(String(50), nullable=True)  # e.g., "ratio", "percentage", "dollars"

    # Committee assignment
    assigned_committee = Column(SQLEnum(CommitteeType), nullable=False)
    requires_approval = Column(Boolean, default=True)

    # Timing
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)

    # User tracking
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    dismissed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Resolution details
    resolution_notes = Column(Text, nullable=True)
    dismissal_reason = Column(Text, nullable=True)

    # Additional metadata
    # Note: Database column is 'metadata', but SQLAlchemy reserves 'metadata' attribute
    # Use explicit column name mapping
    alert_metadata = Column('metadata', JSONB, nullable=True)  # Store alert-specific data

    # Related data (for traceability)
    related_metric = Column(String(100), nullable=True)  # e.g., "DSCR", "Occupancy Rate"
    br_id = Column(String(20), nullable=True)  # Business Requirement ID
    
    # Enhanced fields (from Phase 9 migration)
    priority_score = Column(Numeric(10, 4), nullable=True)
    correlation_group_id = Column(Integer, nullable=True)
    escalation_level = Column(Integer, nullable=True, default=0)
    escalated_at = Column(DateTime, nullable=True)
    resolution_template_id = Column(Integer, nullable=True)
    related_alert_ids = Column(JSONB, nullable=True)  # Array of related alert IDs
    alert_tags = Column(JSONB, nullable=True)  # Custom tags for filtering/grouping
    performance_impact = Column(String(100), nullable=True)  # Estimated impact description

    # Relationships
    property = relationship("Property", back_populates="committee_alerts")
    financial_period = relationship("FinancialPeriod", backref="committee_alerts")
    acknowledged_user = relationship("User", foreign_keys=[acknowledged_by], backref="acknowledged_alerts")
    resolved_user = relationship("User", foreign_keys=[resolved_by], backref="resolved_alerts")
    dismissed_user = relationship("User", foreign_keys=[dismissed_by], backref="dismissed_alerts")
    workflow_locks = relationship("WorkflowLock", back_populates="alert", cascade="all, delete-orphan")

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CommitteeAlert(id={self.id}, type={self.alert_type}, severity={self.severity}, status={self.status})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "property_id": self.property_id,
            "financial_period_id": self.financial_period_id,
            "alert_type": self.alert_type.value if self.alert_type else None,
            "severity": self.severity.value if self.severity else None,
            "status": self.status.value if self.status else None,
            "title": self.title,
            "description": self.description,
            "threshold_value": float(self.threshold_value) if self.threshold_value else None,
            "actual_value": float(self.actual_value) if self.actual_value else None,
            "threshold_unit": self.threshold_unit,
            "assigned_committee": self.assigned_committee.value if self.assigned_committee else None,
            "requires_approval": self.requires_approval,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "dismissed_at": self.dismissed_at.isoformat() if self.dismissed_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_by": self.resolved_by,
            "dismissed_by": self.dismissed_by,
            "resolution_notes": self.resolution_notes,
            "dismissal_reason": self.dismissal_reason,
            "alert_metadata": self.alert_metadata,  # Column name is 'metadata' in DB
            "related_metric": self.related_metric,
            "br_id": self.br_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_active(self) -> bool:
        """Check if alert is still active"""
        return self.status == AlertStatus.ACTIVE

    def is_critical(self) -> bool:
        """Check if alert is critical or urgent"""
        return self.severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT]

    def days_open(self) -> int:
        """Calculate days since alert was triggered"""
        if self.resolved_at:
            delta = self.resolved_at - self.triggered_at
        elif self.dismissed_at:
            delta = self.dismissed_at - self.triggered_at
        else:
            delta = datetime.utcnow() - self.triggered_at
        return delta.days
