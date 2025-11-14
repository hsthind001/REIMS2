"""
Report Audit Model - M3 Auditor results
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.database import Base


class ReportAudit(Base):
    """
    Report Audits - M3 Auditor verification results

    Tracks quality, issues, and approval status of generated reports
    """
    __tablename__ = "report_audits"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, nullable=True, comment="Reference to generated report")
    report_type = Column(String(100), nullable=False, index=True, comment="Type of report audited")
    audit_date = Column(DateTime, server_default=func.now())

    # Audit results
    issues_found = Column(JSONB, nullable=True, comment="Array of issues detected")
    factual_accuracy = Column(Numeric(5, 4), nullable=True, comment="Factual accuracy score (0-1)")
    citation_coverage = Column(Numeric(5, 4), nullable=True, comment="Citation coverage score (0-1)")
    hallucination_score = Column(Numeric(5, 4), nullable=True, comment="Hallucination detection score (0-1, lower is better)")
    overall_quality = Column(String(10), nullable=True, index=True, comment="Overall quality grade (A+, A, B, etc.)")

    # Audit metadata
    audited_by = Column(String(100), default='M3-Auditor', comment="Who/what audited the report")
    approved = Column(Boolean, default=False, comment="Whether report is approved")
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Relationships
    approver = relationship("User", foreign_keys=[approved_by])

    def __repr__(self):
        return f"<ReportAudit(id={self.id}, type={self.report_type}, quality={self.overall_quality}, approved={self.approved})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'report_id': self.report_id,
            'report_type': self.report_type,
            'audit_date': self.audit_date.isoformat() if self.audit_date else None,
            'issues_found': self.issues_found,
            'factual_accuracy': float(self.factual_accuracy) if self.factual_accuracy else None,
            'citation_coverage': float(self.citation_coverage) if self.citation_coverage else None,
            'hallucination_score': float(self.hallucination_score) if self.hallucination_score else None,
            'overall_quality': self.overall_quality,
            'audited_by': self.audited_by,
            'approved': self.approved,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None
        }

    @property
    def needs_revision(self):
        """Check if report needs revision"""
        if not self.factual_accuracy:
            return True
        return self.factual_accuracy < 0.90 or (self.issues_found and len(self.issues_found) > 5)

    @property
    def issue_count_by_severity(self):
        """Get count of issues by severity"""
        if not self.issues_found:
            return {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}

        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for issue in self.issues_found:
            severity = issue.get('severity', 'low')
            if severity in counts:
                counts[severity] += 1

        return counts

    def approve(self, user_id: int):
        """Approve the report"""
        self.approved = True
        self.approved_by = user_id
        self.approved_at = func.now()
