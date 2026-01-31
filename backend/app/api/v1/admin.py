"""
Admin API endpoints for REIMS platform owner to manage tenants
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.api.dependencies import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class TenantDetail(BaseModel):
    """Detailed information about a tenant organization"""
    id: int
    name: str
    slug: str
    subscription_status: str
    stripe_customer_id: str | None
    member_count: int
    owner_username: str | None
    owner_email: str | None
    created_at: datetime | None
    plan_id: str | None = None
    documents_limit: int | None = None
    documents_used: int | None = None
    storage_limit_gb: float | None = None
    storage_used_bytes: int | None = None

    class Config:
        from_attributes = True


class UserDetail(BaseModel):
    """Detailed information about a user"""
    id: int
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    organization_count: int
    organizations: List[str]
    created_at: datetime | None
    
    class Config:
        from_attributes = True


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure only superusers can access admin endpoints"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform administrators can access this endpoint"
        )
    return current_user


@router.get("/admin/tenants", response_model=List[TenantDetail])
def list_all_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser)
):
    """
    List all tenant organizations and their subscription status.
    
    Only accessible by superusers (platform owners).
    """
    orgs = db.query(Organization).all()
    
    tenant_list = []
    for org in orgs:
        # Count members
        member_count = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id
        ).count()
        
        # Get owner
        owner = db.query(User).join(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.role == "owner"
        ).first()
        
        # If no owner, check for admin
        if not owner:
            owner = db.query(User).join(OrganizationMember).filter(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.role == "admin"
            ).first()
        
        tenant_list.append(TenantDetail(
            id=org.id,
            name=org.name,
            slug=org.slug,
            subscription_status=org.subscription_status,
            stripe_customer_id=org.stripe_customer_id,
            member_count=member_count,
            owner_username=owner.username if owner else None,
            owner_email=owner.email if owner else None,
            created_at=org.created_at,
            plan_id=org.plan_id,
            documents_limit=org.documents_limit,
            documents_used=org.documents_used,
            storage_limit_gb=float(org.storage_limit_gb) if org.storage_limit_gb else None,
            storage_used_bytes=org.storage_used_bytes,
        ))
    
    return tenant_list


@router.get("/admin/users", response_model=List[UserDetail])
def list_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser)
):
    """
    List all users on the platform.
    
    Only accessible by superusers (platform owners).
    """
    users = db.query(User).all()
    
    user_list = []
    for user in users:
        # Get user's organizations
        orgs = db.query(Organization).join(OrganizationMember).filter(
            OrganizationMember.user_id == user.id
        ).all()
        
        user_list.append(UserDetail(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            organization_count=len(orgs),
            organizations=[org.name for org in orgs],
            created_at=user.created_at
        ))
    
    return user_list


@router.get("/admin/stats")
def get_platform_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser)
):
    """
    Get platform-wide statistics.
    
    Only accessible by superusers (platform owners).
    """
    total_orgs = db.query(Organization).count()
    total_users = db.query(User).count()
    
    # Count by subscription status
    active_subs = db.query(Organization).filter(
        Organization.subscription_status == "active"
    ).count()
    
    trial_subs = db.query(Organization).filter(
        Organization.subscription_status == "trialing"
    ).count()
    
    past_due_subs = db.query(Organization).filter(
        Organization.subscription_status == "past_due"
    ).count()
    
    canceled_subs = db.query(Organization).filter(
        Organization.subscription_status == "canceled"
    ).count()
    
    return {
        "total_organizations": total_orgs,
        "total_users": total_users,
        "subscriptions": {
            "active": active_subs,
            "trialing": trial_subs,
            "past_due": past_due_subs,
            "canceled": canceled_subs
        }
    }


@router.get("/admin/audit-log")
def get_audit_log(
    organization_id: int = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """View audit log. Superusers can filter by org or see all."""
    from app.models.audit_log import AuditLog
    from app.services.audit_service import log_action
    log_action(db, "admin.audit_log_viewed", current_user.id, organization_id, "audit_log", None, f"Viewed audit log" + (f" for org {organization_id}" if organization_id else " (all)"))
    db.commit()
    query = db.query(AuditLog)
    if organization_id is not None:
        query = query.filter(AuditLog.organization_id == organization_id)
    rows = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return [
        {
            "id": r.id,
            "action": r.action,
            "user_id": r.user_id,
            "organization_id": r.organization_id,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


class OrgPlanUpdate(BaseModel):
    plan_id: str | None = None
    documents_limit: int | None = None
    storage_limit_gb: float | None = None


@router.patch("/admin/tenants/{org_id}/plan")
def update_org_plan(
    org_id: int,
    body: OrgPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Set plan and quotas for an organization. Superuser only."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if body.plan_id is not None:
        org.plan_id = body.plan_id
    if body.documents_limit is not None:
        org.documents_limit = body.documents_limit
    if body.storage_limit_gb is not None:
        org.storage_limit_gb = body.storage_limit_gb
    from app.services.audit_service import log_action
    log_action(db, "admin.plan_updated", current_user.id, org_id, "organization", str(org_id), f"Updated plan to {body.plan_id or org.plan_id}, limits={body.documents_limit},{body.storage_limit_gb}")
    db.commit()
    db.refresh(org)
    return {
        "id": org.id,
        "plan_id": org.plan_id,
        "documents_limit": org.documents_limit,
        "storage_limit_gb": float(org.storage_limit_gb) if org.storage_limit_gb else None,
    }


@router.post("/admin/tenants/refresh-all-usage")
def refresh_all_orgs_usage_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Recalculate documents_used and storage_used_bytes for ALL orgs. Superuser only. Use after enabling quotas."""
    from app.services.quota_service import refresh_all_orgs_usage
    count = refresh_all_orgs_usage(db)
    db.commit()
    return {"message": f"Refreshed usage for {count} organizations", "orgs_updated": count}


@router.post("/admin/tenants/{org_id}/refresh-usage")
def refresh_org_usage(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """Recalculate documents_used and storage_used_bytes from actual data. Superuser only."""
    from app.services.quota_service import refresh_org_usage as do_refresh
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    do_refresh(db, org_id)
    db.commit()
    db.refresh(org)
    return {
        "id": org.id,
        "documents_used": org.documents_used,
        "storage_used_bytes": org.storage_used_bytes,
    }
