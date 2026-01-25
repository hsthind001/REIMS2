"""
API v2 Documents Endpoints

Enhanced document management with standardized responses and improved validation.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.db.database import get_db
from app.api.dependencies import get_current_user, get_current_organization, require_role, UserRole
from app.models.user import User
from app.models import DocumentUpload, Property, FinancialPeriod
from app.models.organization import Organization
from app.schemas.base import (
    SuccessResponse,
    ErrorResponse,
    ErrorDetail,
    ErrorCode,
    PaginatedResponse,
    PaginationMeta,
    DeleteResponse,
    TaskResponse,
)
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentListItem,
    DocumentTypeEnum,
)
from app.core.constants import FileUploadLimits, BatchProcessingLimits

router = APIRouter(prefix="/documents", tags=["documents-v2"])


@router.get(
    "/",
    response_model=PaginatedResponse[DocumentListItem],
    summary="List documents with pagination",
    description="Get paginated list of documents with filtering options."
)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        BatchProcessingLimits.QUERY_PAGE_SIZE_DEFAULT,
        ge=1,
        le=BatchProcessingLimits.QUERY_PAGE_SIZE_MAX,
        description="Items per page"
    ),
    property_code: Optional[str] = Query(None, description="Filter by property code"),
    document_type: Optional[DocumentTypeEnum] = Query(None, description="Filter by document type"),
    extraction_status: Optional[str] = Query(None, description="Filter by extraction status"),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    List documents with standardized pagination.

    Returns documents the user has access to, with optional filtering.
    """
    # Build query
    query = db.query(DocumentUpload).join(
        Property, DocumentUpload.property_id == Property.id
    ).filter(
        DocumentUpload.is_active == True,
        Property.organization_id == current_org.id
    )

    # Apply filters
    if property_code:
        property_obj = db.query(Property).filter(
            Property.property_code == property_code,
            Property.organization_id == current_org.id
        ).first()
        if property_obj:
            query = query.filter(DocumentUpload.property_id == property_obj.id)

    if document_type:
        query = query.filter(DocumentUpload.document_type == document_type.value)

    if extraction_status:
        query = query.filter(DocumentUpload.extraction_status == extraction_status)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    documents = query.order_by(DocumentUpload.upload_date.desc()).offset(offset).limit(page_size).all()

    # Convert to response items
    items = []
    for doc in documents:
        # Get property and period info
        property_obj = db.query(Property).filter(Property.id == doc.property_id).first()
        period_obj = db.query(FinancialPeriod).filter(FinancialPeriod.id == doc.period_id).first()

        items.append(DocumentListItem(
            id=doc.id,
            property_code=property_obj.property_code if property_obj else None,
            period_year=period_obj.year if period_obj else None,
            period_month=period_obj.month if period_obj else None,
            document_type=doc.document_type,
            file_name=doc.file_name,
            upload_date=doc.upload_date,
            extraction_status=doc.extraction_status,
            extraction_confidence=doc.extraction_confidence,
            version=doc.version,
            is_active=doc.is_active
        ))

    # Build response
    pagination = PaginationMeta.from_query(total=total, page=page, page_size=page_size)

    return PaginatedResponse(
        data=items,
        pagination=pagination,
        message=f"Found {total} documents"
    )


@router.get(
    "/{document_id}",
    response_model=SuccessResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"}
    },
    summary="Get document details"
)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific document.
    """
    document = db.query(DocumentUpload).join(
        Property, DocumentUpload.property_id == Property.id
    ).filter(
        DocumentUpload.id == document_id,
        DocumentUpload.is_active == True,
        Property.organization_id == current_org.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Document with ID {document_id} not found",
                "details": {"document_id": document_id}
            }
        )

    # Get related data
    property_obj = db.query(Property).filter(
        Property.id == document.property_id,
        Property.organization_id == current_org.id
    ).first()
    period_obj = db.query(FinancialPeriod).filter(FinancialPeriod.id == document.period_id).first()

    return SuccessResponse(
        message="Document retrieved successfully",
        data={
            "id": document.id,
            "property_code": property_obj.property_code if property_obj else None,
            "property_name": property_obj.property_name if property_obj else None,
            "period_year": period_obj.year if period_obj else None,
            "period_month": period_obj.month if period_obj else None,
            "document_type": document.document_type,
            "file_name": document.file_name,
            "file_path": document.file_path,
            "file_size_bytes": document.file_size_bytes,
            "upload_date": document.upload_date.isoformat() if document.upload_date else None,
            "extraction_status": document.extraction_status,
            "extraction_confidence": document.extraction_confidence,
            "version": document.version,
            "is_active": document.is_active,
            "notes": document.notes
        }
    )


@router.delete(
    "/{document_id}",
    response_model=DeleteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"}
    },
    summary="Delete a document"
)
async def delete_document(
    document_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SUPERUSER)),
    current_org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Delete a document (soft delete - marks as inactive).

    Requires ADMIN or SUPERUSER role.
    """
    document = db.query(DocumentUpload).join(
        Property, DocumentUpload.property_id == Property.id
    ).filter(
        DocumentUpload.id == document_id,
        DocumentUpload.is_active == True,
        Property.organization_id == current_org.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": ErrorCode.NOT_FOUND.value,
                "message": f"Document with ID {document_id} not found"
            }
        )

    # Soft delete
    document.is_active = False
    document.notes = f"Deleted by user {current_user.id} at {datetime.utcnow().isoformat()}"
    db.commit()

    return DeleteResponse(
        message="Document deleted successfully",
        deleted_id=document_id
    )
