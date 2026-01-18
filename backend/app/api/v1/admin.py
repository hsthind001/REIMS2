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
            created_at=org.created_at
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
