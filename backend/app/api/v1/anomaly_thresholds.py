"""
API endpoints for managing anomaly detection thresholds
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.schemas.anomaly_threshold import (
    AnomalyThresholdCreate,
    AnomalyThresholdUpdate,
    AnomalyThresholdResponse,
    AnomalyThresholdListResponse,
    DefaultThresholdResponse,
    DefaultThresholdUpdate
)
from app.services.anomaly_threshold_service import AnomalyThresholdService

router = APIRouter()


@router.get("/", response_model=AnomalyThresholdListResponse)
async def list_thresholds(
    include_inactive: bool = False,
    document_type: str = None,  # Filter by document type: income_statement, balance_sheet, cash_flow
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    List all anomaly thresholds
    
    Args:
        include_inactive: Include inactive thresholds
        document_type: Filter by document type (income_statement, balance_sheet, cash_flow)
    
    Returns:
        List of all thresholds
    """
    service = AnomalyThresholdService(db)
    
    if document_type:
        # Get accounts with thresholds filtered by document type
        document_types = [document_type] if document_type else None
        accounts = service.get_all_accounts_with_thresholds(document_types=document_types)
        
        # Convert to threshold responses
        thresholds = []
        for account in accounts:
            if account["is_custom"]:
                threshold = service.get_threshold(account["account_code"])
                if threshold:
                    thresholds.append(threshold)
        
        return AnomalyThresholdListResponse(
            thresholds=[AnomalyThresholdResponse.model_validate(t) for t in thresholds],
            total=len(thresholds)
        )
    else:
        thresholds = service.list_all_thresholds(include_inactive=include_inactive)
        return AnomalyThresholdListResponse(
            thresholds=[AnomalyThresholdResponse.model_validate(t) for t in thresholds],
            total=len(thresholds)
        )


@router.get("/accounts", response_model=List[dict])
async def get_all_accounts_with_thresholds(
    document_type: str = None,  # Filter by document type
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get all accounts from chart_of_accounts with their threshold information.
    This is used to populate the Value Setup table.
    
    Returns accounts from Income Statement, Balance Sheet, and Cash Flow documents.
    """
    service = AnomalyThresholdService(db)
    
    document_types = None
    if document_type:
        document_types = [document_type]
    else:
        # Default: include all relevant document types
        document_types = ["income_statement", "balance_sheet", "cash_flow"]
    
    accounts = service.get_all_accounts_with_thresholds(document_types=document_types)
    return accounts


@router.get("/{account_code}", response_model=AnomalyThresholdResponse)
async def get_threshold(
    account_code: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get threshold for a specific account code"""
    service = AnomalyThresholdService(db)
    threshold = service.get_threshold(account_code)
    
    if not threshold:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threshold not found for account_code: {account_code}"
        )
    
    return AnomalyThresholdResponse.model_validate(threshold)


@router.post("/", response_model=AnomalyThresholdResponse, status_code=status.HTTP_201_CREATED)
async def create_threshold(
    threshold_data: AnomalyThresholdCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new threshold"""
    service = AnomalyThresholdService(db)
    
    # Check if threshold already exists
    existing = service.get_threshold(threshold_data.account_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Threshold already exists for account_code: {threshold_data.account_code}. Use PUT to update."
        )
    
    threshold = service.get_or_create_threshold(
        account_code=threshold_data.account_code,
        account_name=threshold_data.account_name,
        threshold_value=threshold_data.threshold_value
    )
    
    return AnomalyThresholdResponse.model_validate(threshold)


@router.put("/{account_code}", response_model=AnomalyThresholdResponse)
async def update_threshold(
    account_code: str,
    threshold_data: AnomalyThresholdUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update an existing threshold"""
    service = AnomalyThresholdService(db)
    
    try:
        threshold = service.update_threshold(
            account_code=account_code,
            account_name=threshold_data.account_name,
            threshold_value=threshold_data.threshold_value,
            is_active=threshold_data.is_active
        )
        return AnomalyThresholdResponse.model_validate(threshold)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{account_code}", response_model=AnomalyThresholdResponse)
async def create_or_update_threshold(
    account_code: str,
    threshold_data: AnomalyThresholdCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create or update a threshold (upsert operation).
    If threshold exists, updates it; otherwise creates a new one.
    """
    service = AnomalyThresholdService(db)
    
    existing = service.get_threshold(account_code)
    if existing:
        # Update existing
        threshold = service.update_threshold(
            account_code=account_code,
            account_name=threshold_data.account_name,
            threshold_value=threshold_data.threshold_value,
            is_active=threshold_data.is_active
        )
    else:
        # Create new
        threshold = service.get_or_create_threshold(
            account_code=threshold_data.account_code,
            account_name=threshold_data.account_name,
            threshold_value=threshold_data.threshold_value
        )
    
    return AnomalyThresholdResponse.model_validate(threshold)




@router.delete("/{account_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_threshold(
    account_code: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete (deactivate) a threshold"""
    service = AnomalyThresholdService(db)
    success = service.delete_threshold(account_code)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threshold not found for account_code: {account_code}"
        )


@router.get("/default/threshold", response_model=DefaultThresholdResponse)
async def get_default_threshold(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get the global default threshold value"""
    service = AnomalyThresholdService(db)
    default_value = service.get_default_threshold()
    
    return DefaultThresholdResponse(
        default_threshold=default_value,
        description="Default absolute value threshold for anomaly detection. Used when no custom threshold is set for an account."
    )


@router.put("/default/threshold", response_model=DefaultThresholdResponse)
async def set_default_threshold(
    threshold_data: DefaultThresholdUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Set the global default threshold value"""
    service = AnomalyThresholdService(db)
    config = service.set_default_threshold(threshold_data.default_threshold)
    
    return DefaultThresholdResponse(
        default_threshold=Decimal(config.config_value),
        description="Default absolute value threshold for anomaly detection. Used when no custom threshold is set for an account."
    )

