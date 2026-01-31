from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.db.database import get_db
from app.api.dependencies import get_current_user, get_current_organization, require_org_role
from app.models.organization import Organization
from app.models.chart_of_accounts import ChartOfAccounts
from app.schemas.chart_of_accounts import (
    ChartOfAccountsResponse,
    ChartOfAccountsListResponse,
    ChartOfAccountsCreate,
    ChartOfAccountsUpdate
)

router = APIRouter(prefix="/chart-of-accounts", tags=["chart-of-accounts"])


@router.get("/", response_model=List[ChartOfAccountsResponse])
async def list_chart_of_accounts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    account_type: Optional[str] = Query(None, description="Filter by account type (asset, liability, equity, income, expense)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory"),
    document_type: Optional[str] = Query(None, description="Filter by document type (balance_sheet, income_statement, cash_flow, rent_roll)"),
    is_calculated: Optional[bool] = Query(None, description="Filter by calculated fields"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by account code or name"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """List chart of accounts. Requires org context (template is global)."""
    
    Filters:
    - account_type: Filter by type (asset, liability, equity, income, expense)
    - category: Filter by category
    - subcategory: Filter by subcategory
    - document_type: Filter by document type
    - is_calculated: Filter calculated/total fields
    - is_active: Filter active accounts (default: True)
    - search: Search account code or name
    
    Pagination:
    - skip: Number of records to skip (default: 0)
    - limit: Maximum records to return (default: 100, max: 500)
    """
    query = db.query(ChartOfAccounts)
    
    # Apply filters
    if account_type:
        query = query.filter(ChartOfAccounts.account_type == account_type)
    
    if category:
        query = query.filter(ChartOfAccounts.category == category)
    
    if subcategory:
        query = query.filter(ChartOfAccounts.subcategory == subcategory)
    
    if document_type:
        # Use LIKE to work with both PostgreSQL ARRAY and SQLite TEXT
        # For PostgreSQL ARRAY, cast to text; for SQLite TEXT, search JSON string
        from sqlalchemy import cast, Text as TextType
        query = query.filter(
            cast(ChartOfAccounts.document_types, TextType).like(f'%{document_type}%')
        )
    
    if is_calculated is not None:
        query = query.filter(ChartOfAccounts.is_calculated == is_calculated)
    
    if is_active is not None:
        query = query.filter(ChartOfAccounts.is_active == is_active)
    
    # Search by account code or name
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                ChartOfAccounts.account_code.ilike(search_pattern),
                ChartOfAccounts.account_name.ilike(search_pattern)
            )
        )
    
    # Order by display_order, then by account_code
    query = query.order_by(
        ChartOfAccounts.display_order.nullslast(),
        ChartOfAccounts.account_code
    )
    
    # Apply pagination
    accounts = query.offset(skip).limit(limit).all()
    
    return accounts


@router.get("/summary")
async def get_chart_of_accounts_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get summary statistics of chart of accounts
    
    Returns count by account type and category
    """
    from sqlalchemy import func
    
    # Count by account type
    type_counts = db.query(
        ChartOfAccounts.account_type,
        func.count(ChartOfAccounts.id).label('count')
    ).group_by(ChartOfAccounts.account_type).all()
    
    # Count calculated fields
    calculated_count = db.query(ChartOfAccounts).filter(
        ChartOfAccounts.is_calculated == True
    ).count()
    
    # Total count
    total_count = db.query(ChartOfAccounts).count()
    
    # Active count
    active_count = db.query(ChartOfAccounts).filter(
        ChartOfAccounts.is_active == True
    ).count()
    
    return {
        "total_accounts": total_count,
        "active_accounts": active_count,
        "calculated_accounts": calculated_count,
        "by_type": {item[0]: item[1] for item in type_counts},
    }


@router.get("/{account_code}", response_model=ChartOfAccountsResponse)
async def get_account_by_code(
    account_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get a specific account by account code
    """
    account = db.query(ChartOfAccounts).filter(
        ChartOfAccounts.account_code == account_code
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with code {account_code} not found"
        )
    
    return account


@router.get("/{account_code}/children", response_model=List[ChartOfAccountsResponse])
async def get_account_children(
    account_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get all child accounts of a parent account
    """
    # Verify parent exists
    parent = db.query(ChartOfAccounts).filter(
        ChartOfAccounts.account_code == account_code
    ).first()
    
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent account with code {account_code} not found"
        )
    
    # Get children
    children = db.query(ChartOfAccounts).filter(
        ChartOfAccounts.parent_account_code == account_code
    ).order_by(ChartOfAccounts.display_order).all()
    
    return children


@router.post("/", response_model=ChartOfAccountsResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: ChartOfAccountsCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_org_role("admin")),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Create a new chart of accounts entry
    """
    # Check if account code already exists
    existing = db.query(ChartOfAccounts).filter(
        ChartOfAccounts.account_code == account_data.account_code
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account with code {account_data.account_code} already exists"
        )
    
    # Create account
    db_account = ChartOfAccounts(**account_data.model_dump())
    db.add(db_account)
    from app.services.audit_service import log_action
    log_action(db, "chart_of_accounts.created", current_user.id, current_org.id, "chart_of_accounts", account_data.account_code, f"Created account {account_data.account_code}")
    db.commit()
    db.refresh(db_account)
    
    return db_account


@router.put("/{account_code}", response_model=ChartOfAccountsResponse)
async def update_account(
    account_code: str,
    account_data: ChartOfAccountsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_org_role("admin")),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Update an existing chart of accounts entry
    """
    account = db.query(ChartOfAccounts).filter(
        ChartOfAccounts.account_code == account_code
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with code {account_code} not found"
        )
    
    # Update fields
    for field, value in account_data.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    from app.services.audit_service import log_action
    log_action(db, "chart_of_accounts.updated", current_user.id, current_org.id, "chart_of_accounts", account_code, f"Updated account {account_code}")
    db.commit()
    db.refresh(account)
    
    return account


@router.delete("/{account_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_org_role("admin")),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Delete a chart of accounts entry
    """
    account = db.query(ChartOfAccounts).filter(
        ChartOfAccounts.account_code == account_code
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with code {account_code} not found"
        )
    from app.services.audit_service import log_action
    log_action(db, "chart_of_accounts.deleted", current_user.id, current_org.id, "chart_of_accounts", account_code, f"Deleted account {account_code}")
    db.delete(account)
    db.commit()
    
    return None

