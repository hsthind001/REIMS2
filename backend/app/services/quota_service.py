"""
Quota enforcement for SaaS plans (P2).
Checks document and storage limits before allowing uploads.
"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.organization import Organization
from app.models.document_upload import DocumentUpload
from app.models.property import Property


def check_document_quota(db: Session, organization_id: int) -> Tuple[bool, Optional[str]]:
    """
    Check if org can upload another document.
    Returns (allowed, error_message).
    """
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        return False, "Organization not found"
    if org.documents_limit is None:
        return True, None  # No limit
    used = org.documents_used or 0
    if used >= org.documents_limit:
        return False, f"Document limit reached ({org.documents_limit}). Upgrade plan."
    return True, None


def check_storage_quota(db: Session, organization_id: int, additional_bytes: int = 0) -> Tuple[bool, Optional[str]]:
    """Check if org has storage capacity. Returns (allowed, error_message)."""
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        return False, "Organization not found"
    if org.storage_limit_gb is None:
        return True, None
    limit_bytes = int(float(org.storage_limit_gb) * 1024 * 1024 * 1024)
    used = org.storage_used_bytes or 0
    if used + additional_bytes > limit_bytes:
        return False, f"Storage limit reached ({org.storage_limit_gb} GB). Upgrade plan."
    return True, None


def increment_document_count(db: Session, organization_id: int) -> None:
    """Increment documents_used after successful upload."""
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org and org.documents_limit is not None:
        org.documents_used = (org.documents_used or 0) + 1
        db.flush()


def increment_storage(db: Session, organization_id: int, bytes_added: int) -> None:
    """Increment storage_used_bytes after successful upload."""
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org and org.storage_limit_gb is not None:
        org.storage_used_bytes = (org.storage_used_bytes or 0) + bytes_added
        db.flush()


def decrement_document_count(db: Session, organization_id: int) -> None:
    """Decrement documents_used after document deletion."""
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org and org.documents_used and org.documents_used > 0:
        org.documents_used -= 1
        db.flush()


def decrement_storage(db: Session, organization_id: int, bytes_removed: int) -> None:
    """Decrement storage_used_bytes after document deletion."""
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org and org.storage_used_bytes and org.storage_used_bytes > 0:
        org.storage_used_bytes = max(0, org.storage_used_bytes - bytes_removed)
        db.flush()


def refresh_org_usage(db: Session, organization_id: int) -> None:
    """Recalculate documents_used and storage_used_bytes from actual data.
    Uses file_size_bytes when present; falls back to 500KB/doc estimate for nulls."""
    doc_count = (
        db.query(DocumentUpload)
        .join(Property, DocumentUpload.property_id == Property.id)
        .filter(Property.organization_id == organization_id)
        .count()
    )
    storage_sum = (
        db.query(func.coalesce(func.sum(DocumentUpload.file_size_bytes), 0))
        .join(Property, DocumentUpload.property_id == Property.id)
        .filter(Property.organization_id == organization_id)
        .scalar()
    )
    total_storage = int(storage_sum) if storage_sum else 0
    if total_storage == 0 and doc_count > 0:
        total_storage = doc_count * 500 * 1024  # 500KB fallback when file_size not set
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org:
        org.documents_used = doc_count
        org.storage_used_bytes = total_storage
        db.flush()


def refresh_all_orgs_usage(db: Session) -> int:
    """Refresh usage for all orgs. Returns count of orgs updated."""
    orgs = db.query(Organization).all()
    for org in orgs:
        refresh_org_usage(db, org.id)
    return len(orgs)
