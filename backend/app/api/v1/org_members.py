"""
Org-level member management (P2 Admin Control Plane).
Org admins/owners can list, add, remove members and update roles.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.db.database import get_db
from app.models.user import User
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.api.dependencies import get_current_organization, require_org_role
from app.services.audit_service import log_action

router = APIRouter(prefix="/organization/members", tags=["org-members"])


class MemberResponse(BaseModel):
    id: int
    user_id: int
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True


class MemberAddRequest(BaseModel):
    user_id: int
    role: str = "viewer"  # owner, admin, editor, viewer


class MemberUpdateRequest(BaseModel):
    role: str


@router.get("/", response_model=List[MemberResponse])
async def list_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_role("admin")),
    current_org: Organization = Depends(get_current_organization),
):
    """List all members of the current organization."""
    rows = (
        db.query(OrganizationMember, User)
        .join(User, OrganizationMember.user_id == User.id)
        .filter(OrganizationMember.organization_id == current_org.id)
        .all()
    )
    return [
        MemberResponse(
            id=mem.id,
            user_id=mem.user_id,
            username=usr.username,
            email=usr.email or "",
            role=mem.role or "viewer",
        )
        for mem, usr in rows
    ]


@router.post("/", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    body: MemberAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_role("admin")),
    current_org: Organization = Depends(get_current_organization),
):
    """Add a user to the organization. Requires org admin or owner."""
    if body.role not in ("owner", "admin", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")
    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == current_org.id,
            OrganizationMember.user_id == body.user_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User already a member")
    m = OrganizationMember(
        organization_id=current_org.id,
        user_id=body.user_id,
        role=body.role,
    )
    db.add(m)
    log_action(db, "member.added", current_user.id, current_org.id, "organization_member", str(body.user_id), f"Added user {user.username} as {body.role}")
    db.commit()
    db.refresh(m)
    return MemberResponse(
        id=m.id,
        user_id=m.user_id,
        username=user.username,
        email=user.email or "",
        role=m.role,
    )


@router.patch("/{member_id}", response_model=MemberResponse)
async def update_member_role(
    member_id: int,
    body: MemberUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_role("admin")),
    current_org: Organization = Depends(get_current_organization),
):
    """Update a member's role. Cannot demote the last owner."""
    if body.role not in ("owner", "admin", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")
    m = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == current_org.id,
        )
        .first()
    )
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    if m.role == "owner" and body.role != "owner":
        owners = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == current_org.id,
                OrganizationMember.role == "owner",
            )
            .count()
        )
        if owners <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot demote the last owner. Transfer ownership first.",
            )
    m.role = body.role
    log_action(db, "member.role_updated", current_user.id, current_org.id, "organization_member", str(member_id), f"Role changed to {body.role}")
    db.commit()
    db.refresh(m)
    user = db.query(User).filter(User.id == m.user_id).first()
    return MemberResponse(
        id=m.id,
        user_id=m.user_id,
        username=user.username if user else "",
        email=user.email if user else "",
        role=m.role,
    )


@router.get("/audit", response_model=List[dict])
async def get_org_audit_log(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_role("admin")),
    current_org: Organization = Depends(get_current_organization),
):
    """View audit log for the current organization."""
    from app.models.audit_log import AuditLog
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == current_org.id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "action": r.action,
            "user_id": r.user_id,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_role("admin")),
    current_org: Organization = Depends(get_current_organization),
):
    """Remove a member from the organization. Cannot remove the last owner."""
    m = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == current_org.id,
        )
        .first()
    )
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    if m.role == "owner":
        owners = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == current_org.id,
                OrganizationMember.role == "owner",
            )
            .count()
        )
        if owners <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the last owner.",
            )
    user_id_removed = m.user_id
    db.delete(m)
    log_action(db, "member.removed", current_user.id, current_org.id, "organization_member", str(member_id), f"Removed user_id={user_id_removed}")
    db.commit()
