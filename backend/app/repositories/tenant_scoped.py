"""
Tenant-scoped data access helpers (E2-S2).

Use these functions instead of direct session.query(Model).filter(Model.id == id)
to enforce organization isolation. All fetches validate that the resource
belongs to the given organization.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.document_upload import DocumentUpload
from app.models.financial_period import FinancialPeriod


def get_property_for_org(
    db: Session, organization_id: int, property_id: int
) -> Optional[Property]:
    """
    Get property by ID scoped to organization.
    Returns None if not found or does not belong to org.
    """
    return (
        db.query(Property)
        .filter(Property.id == property_id, Property.organization_id == organization_id)
        .first()
    )


def get_property_by_code_for_org(
    db: Session, organization_id: int, property_code: str
) -> Optional[Property]:
    """
    Get property by property_code scoped to organization.
    Returns None if not found or does not belong to org.
    """
    return (
        db.query(Property)
        .filter(
            Property.property_code == property_code,
            Property.organization_id == organization_id,
        )
        .first()
    )


def get_upload_for_org(
    db: Session, organization_id: int, upload_id: int
) -> Optional[DocumentUpload]:
    """
    Get document upload by ID scoped to organization.
    Uses organization_id when set, else joins through Property.
    Returns None if not found or does not belong to org.
    """
    from sqlalchemy import or_
    return (
        db.query(DocumentUpload)
        .outerjoin(Property, DocumentUpload.property_id == Property.id)
        .filter(
            DocumentUpload.id == upload_id,
            or_(
                DocumentUpload.organization_id == organization_id,
                (
                    (DocumentUpload.organization_id.is_(None))
                    & (Property.organization_id == organization_id)
                ),
            ),
        )
        .first()
    )


def get_upload_by_path_for_org(
    db: Session, organization_id: int, file_path: str
) -> Optional[DocumentUpload]:
    """
    Get document upload by file_path scoped to organization.
    Use for presigned URL / download - only allow access if DB record exists.
    """
    from sqlalchemy import or_
    return (
        db.query(DocumentUpload)
        .outerjoin(Property, DocumentUpload.property_id == Property.id)
        .filter(
            DocumentUpload.file_path == file_path,
            or_(
                DocumentUpload.organization_id == organization_id,
                (
                    (DocumentUpload.organization_id.is_(None))
                    & (Property.organization_id == organization_id)
                ),
            ),
        )
        .first()
    )


def get_workflow_lock_for_org(
    db: Session, organization_id: int, lock_id: int
) -> Optional["WorkflowLock"]:
    """
    Get workflow lock by ID scoped to organization (via property).
    """
    from app.models.workflow_lock import WorkflowLock
    return (
        db.query(WorkflowLock)
        .join(Property, WorkflowLock.property_id == Property.id)
        .filter(
            WorkflowLock.id == lock_id,
            Property.organization_id == organization_id,
        )
        .first()
    )


def get_reconciliation_session_for_org(
    db: Session, organization_id: int, session_id: int
) -> Optional["ReconciliationSession"]:
    """
    Get reconciliation session by ID scoped to organization.
    Joins through Property. Returns None if not found or does not belong to org.
    """
    from app.models.reconciliation_session import ReconciliationSession
    return (
        db.query(ReconciliationSession)
        .join(Property, ReconciliationSession.property_id == Property.id)
        .filter(
            ReconciliationSession.id == session_id,
            Property.organization_id == organization_id,
        )
        .first()
    )


def get_forensic_reconciliation_session_for_org(
    db: Session, organization_id: int, session_id: int
) -> Optional["ForensicReconciliationSession"]:
    """
    Get forensic reconciliation session by ID scoped to organization.
    Joins through Property. Returns None if not found or does not belong to org.
    """
    from app.models.forensic_reconciliation_session import ForensicReconciliationSession
    return (
        db.query(ForensicReconciliationSession)
        .join(Property, ForensicReconciliationSession.property_id == Property.id)
        .filter(
            ForensicReconciliationSession.id == session_id,
            Property.organization_id == organization_id,
        )
        .first()
    )


def get_forensic_match_for_org(
    db: Session, organization_id: int, match_id: int
) -> Optional["ForensicMatch"]:
    """Get forensic match by ID scoped to organization (via session -> property)."""
    from app.models.forensic_match import ForensicMatch
    from app.models.forensic_reconciliation_session import ForensicReconciliationSession
    return (
        db.query(ForensicMatch)
        .join(
            ForensicReconciliationSession,
            ForensicMatch.session_id == ForensicReconciliationSession.id,
        )
        .join(Property, ForensicReconciliationSession.property_id == Property.id)
        .filter(ForensicMatch.id == match_id, Property.organization_id == organization_id)
        .first()
    )


def get_forensic_discrepancy_for_org(
    db: Session, organization_id: int, discrepancy_id: int
) -> Optional["ForensicDiscrepancy"]:
    """Get forensic discrepancy by ID scoped to organization (via session -> property)."""
    from app.models.forensic_discrepancy import ForensicDiscrepancy
    from app.models.forensic_reconciliation_session import ForensicReconciliationSession
    return (
        db.query(ForensicDiscrepancy)
        .join(
            ForensicReconciliationSession,
            ForensicDiscrepancy.session_id == ForensicReconciliationSession.id,
        )
        .join(Property, ForensicReconciliationSession.property_id == Property.id)
        .filter(
            ForensicDiscrepancy.id == discrepancy_id,
            Property.organization_id == organization_id,
        )
        .first()
    )


def get_anomaly_for_org(
    db: Session, organization_id: int, anomaly_id: int
) -> Optional["AnomalyDetection"]:
    """
    Get anomaly by ID scoped to organization (via document -> property).
    Returns None if not found or document does not belong to org.
    """
    from app.models.anomaly_detection import AnomalyDetection

    anomaly = db.query(AnomalyDetection).filter(AnomalyDetection.id == anomaly_id).first()
    if not anomaly:
        return None
    if anomaly.document_id:
        upload = get_upload_for_org(db, organization_id, anomaly.document_id)
        return anomaly if upload else None
    # No document_id - check metadata property_id if present
    meta = anomaly.metadata_json
    if meta is None:
        meta = {}
    elif isinstance(meta, str):
        import json
        try:
            meta = json.loads(meta) if meta else {}
        except (json.JSONDecodeError, TypeError):
            meta = {}
    prop_id = meta.get("property_id")
    if prop_id is not None:
        pid = int(prop_id) if isinstance(prop_id, str) and str(prop_id).isdigit() else prop_id
        if isinstance(pid, int) and get_property_for_org(db, organization_id, pid):
            return anomaly
    return None


def get_batch_job_for_org(
    db: Session, organization_id: int, job_id: int
) -> Optional["BatchReprocessingJob"]:
    """
    Get batch reprocessing job by ID scoped to organization.
    Returns None if not found or does not belong to org.
    """
    from app.models.batch_reprocessing_job import BatchReprocessingJob

    job = db.query(BatchReprocessingJob).filter(BatchReprocessingJob.id == job_id).first()
    if not job:
        return None
    # E2-S3: Prefer organization_id when set
    if job.organization_id is not None:
        return job if job.organization_id == organization_id else None
    # Legacy jobs: verify via property_ids
    if job.property_ids:
        for pid in job.property_ids:
            if isinstance(pid, int) and get_property_for_org(db, organization_id, pid):
                return job
        return None
    # No property filter: verify via initiated_by user's org membership
    if job.initiated_by:
        from app.models.organization import OrganizationMember
        m = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == job.initiated_by,
                OrganizationMember.organization_id == organization_id,
            )
            .first()
        )
        if m:
            return job
    return None


def get_period_for_org(
    db: Session, organization_id: int, period_id: int
) -> Optional[FinancialPeriod]:
    """
    Get financial period by ID scoped to organization.
    Uses organization_id when set, else joins through Property.
    Returns None if not found or does not belong to org.
    """
    from sqlalchemy import or_
    return (
        db.query(FinancialPeriod)
        .outerjoin(Property, FinancialPeriod.property_id == Property.id)
        .filter(
            FinancialPeriod.id == period_id,
            or_(
                FinancialPeriod.organization_id == organization_id,
                (
                    (FinancialPeriod.organization_id.is_(None))
                    & (Property.organization_id == organization_id)
                ),
            ),
        )
        .first()
    )
