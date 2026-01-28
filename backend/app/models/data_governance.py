"""
Data governance models.

Defines ownership, access controls, retention policies, and DQ issue tracking
used to satisfy DATA_QUALITY_INTEGRITY_RULES governance requirements.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class DataOwner(Base):
    __tablename__ = "data_owners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    role = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    policies = relationship("DataGovernancePolicy", back_populates="owner")


class DataGovernancePolicy(Base):
    __tablename__ = "data_governance_policies"

    id = Column(Integer, primary_key=True, index=True)
    policy_type = Column(String(100), nullable=False)  # ownership, access, retention, correction, etc.
    description = Column(Text, nullable=True)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    owner_id = Column(Integer, ForeignKey("data_owners.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("DataOwner", back_populates="policies")


class DataAccessControl(Base):
    __tablename__ = "data_access_controls"

    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(100), nullable=False)  # Viewer, Editor, Approver, Admin
    permission_level = Column(String(50), nullable=False)  # view, edit, approve, admin
    document_type = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DataRetentionPolicy(Base):
    __tablename__ = "data_retention_policies"

    id = Column(Integer, primary_key=True, index=True)
    document_type = Column(String(50), nullable=False)
    retention_years = Column(Integer, nullable=False)
    legal_basis = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey("financial_periods.id", ondelete="CASCADE"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("document_uploads.id", ondelete="SET NULL"), nullable=True, index=True)
    rule_id = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), default="open")  # open, in_review, resolved
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    document = relationship("DocumentUpload", backref="data_quality_issues")
    property = relationship("Property", backref="data_quality_issues")
    period = relationship("FinancialPeriod", backref="data_quality_issues")


class DataQualityCorrection(Base):
    __tablename__ = "data_quality_corrections"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("data_quality_issues.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(Text, nullable=False)
    performed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    issue = relationship("DataQualityIssue", backref="corrections")
