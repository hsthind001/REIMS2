"""
Document Upload API - Complete workflow for financial document management
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query, Depends, Form, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func
from typing import Optional, List
from decimal import Decimal

from app.db.database import get_db
from app.db.minio_client import get_file_url, delete_file
from app.api.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.services.document_service import DocumentService
from app.services.pdf_generator_service import PDFGeneratorService
from app.tasks.extraction_tasks import extract_document
from fastapi.responses import StreamingResponse
from app.models.document_upload import DocumentUpload
from app.models.escrow_document_link import EscrowDocumentLink
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.financial_metrics import FinancialMetrics
from app.models.validation_result import ValidationResult
from app.models.validation_rule import ValidationRule
from app.models.extraction_log import ExtractionLog
from app.schemas.document import (
    DocumentTypeEnum,
    ExtractionStatusEnum,
    DocumentUploadResponse,
    DocumentUploadDetail,
    DocumentListResponse,
    DocumentListItem,
    ExtractedDataResponse,
    BalanceSheetDataItem,
    IncomeStatementDataItem,
    CashFlowDataItem,
    RentRollDataItem,
    FinancialMetricsData,
    ValidationResultItem,
    DocumentDownloadResponse,
    EscrowLinkCreate,
    EscrowLinkResponse,
    EscrowLinkListResponse,
)

# Import rate limiter from main app
from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance for this router
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


def _get_upload_for_org(db: Session, upload_id: int, organization_id: int) -> Optional[DocumentUpload]:
    return (
        db.query(DocumentUpload)
        .join(Property, DocumentUpload.property_id == Property.id)
        .filter(
            DocumentUpload.id == upload_id,
            Property.organization_id == organization_id
        )
        .first()
    )


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")  # Rate limit: 10 uploads per minute per IP
async def upload_document(
    request: Request,  # Required for rate limiter
    property_code: str = Form(..., description="Property code (e.g., WEND001)"),
    period_year: int = Form(..., ge=2000, le=2100, description="Financial period year"),
    period_month: int = Form(..., ge=1, le=12, description="Financial period month (1-12)"),
    document_type: DocumentTypeEnum = Form(..., description="Type of financial document"),
    file: UploadFile = File(..., description="PDF file to upload"),
    force_overwrite: bool = Form(False, description="Force overwrite if file exists"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Upload financial document and trigger extraction
    
    **Workflow:**
    1. Validate property exists
    2. Create/get financial period
    3. Check for duplicate (by file hash)
    4. If duplicate found: AUTO-DELETE old upload and replace with new one
    5. Upload file to MinIO
    6. Create document_uploads record
    7. Trigger Celery task for extraction
    8. Return upload_id and task_id
    
    **Duplicate Handling (Auto-Replace):**
    - Uses MD5 hash of file content to detect duplicates
    - If duplicate found: Automatically deletes old upload (including all related financial data)
    - Old file removed from MinIO
    - New file uploaded and extracted
    - Prevents failed uploads from blocking new attempts
    
    **Returns:**
    - upload_id: Unique identifier for tracking
    - task_id: Celery task ID for extraction status
    - file_path: Storage path in MinIO
    """
    # Validate file type (MIME type check)
    if not file.content_type or file.content_type != "application/pdf":
        # Capture issue for learning
        try:
            from app.services.issue_capture_service import IssueCaptureService
            capture_service = IssueCaptureService(db)
            capture_service.capture_frontend_error(
                error_message=f"Invalid file type: {file.content_type}. Expected application/pdf",
                api_endpoint="/documents/upload",
                context={
                    "filename": file.filename,
                    "content_type": file.content_type
                }
            )
        except Exception:
            pass  # Don't fail upload if issue capture fails

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF (application/pdf)"
        )

    # Validate file size (max 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50MB limit"
        )

    # SECURITY: Validate PDF magic bytes to prevent file spoofing
    # PDF files must start with %PDF (magic bytes: 0x25 0x50 0x44 0x46)
    PDF_MAGIC_BYTES = b'%PDF'
    file_header = file.file.read(8)  # Read first 8 bytes for signature
    file.file.seek(0)  # Reset to beginning

    if not file_header.startswith(PDF_MAGIC_BYTES):
        # Capture issue for learning
        try:
            from app.services.issue_capture_service import IssueCaptureService
            capture_service = IssueCaptureService(db)
            capture_service.capture_frontend_error(
                error_message="File content does not match PDF format (invalid magic bytes)",
                api_endpoint="/documents/upload",
                context={
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "magic_bytes_hex": file_header[:4].hex() if file_header else "empty"
                }
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF file: file content does not match PDF format"
        )
    
    try:
        # Create document service
        doc_service = DocumentService(db, organization_id=current_org.id)
        
        # Upload document
        result = await doc_service.upload_document(
            property_code=property_code,
            period_year=period_year,
            period_month=period_month,
            document_type=document_type.value,
            file=file,
            uploaded_by=None,  # TODO: Get from auth context
            force_overwrite=force_overwrite
        )
        
        # Check for property mismatch
        if result.get("property_mismatch"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "property_mismatch",
                    "message": result["message"],
                    "selected_property_code": result["selected_property_code"],
                    "selected_property_name": result["selected_property_name"],
                    "detected_property_code": result["detected_property_code"],
                    "detected_property_name": result["detected_property_name"],
                    "confidence": result["confidence"],
                    "matches_found": result.get("matches_found", [])
                }
            )
        
        # Check for document type mismatch
        if result.get("type_mismatch"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "document_type_mismatch",
                    "message": result["message"],
                    "selected_type": result["selected_type"],
                    "detected_type": result["detected_type"],
                    "confidence": result["confidence"],
                    "keywords_found": result.get("keywords_found", [])
                }
            )
        
        # Check for year mismatch
        if result.get("year_mismatch"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "year_mismatch",
                    "message": result["message"],
                    "selected_year": result["selected_year"],
                    "detected_year": result["detected_year"],
                    "period_text": result.get("period_text", ""),
                    "confidence": result["confidence"]
                }
            )
        
        # Check for month/period mismatch
        if result.get("period_mismatch"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "period_mismatch",
                    "message": result["message"],
                    "selected_month": result["selected_month"],
                    "detected_month": result["detected_month"],
                    "selected_month_name": result["selected_month_name"],
                    "detected_month_name": result["detected_month_name"],
                    "period_text": result.get("period_text", ""),
                    "confidence": result["confidence"]
                }
            )
        
        # Check if file already exists (and not forcing overwrite)
        if result.get("file_exists"):
            return DocumentUploadResponse(
                upload_id=None,
                task_id=None,
                message=result["message"],
                file_path=None,
                extraction_status=None,
                file_exists=True,
                existing_file=result.get("existing_file")
            )
        
        # Check if duplicate (by hash)
        if result.get("is_duplicate"):
            return DocumentUploadResponse(
                upload_id=result["upload_id"],
                task_id="N/A",
                message="Duplicate file already exists - no extraction triggered",
                file_path=result["file_path"],
                extraction_status="completed"
            )
        
        # Trigger Celery extraction task with error handling
        try:
            task = extract_document.delay(result["upload_id"])
            task_id = task.id
            extraction_status = "pending"
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to queue extraction for upload_id={result['upload_id']}: {e}")
            # Don't fail the upload - file is in MinIO, extraction will be recovered
            task_id = None
            extraction_status = "pending"  # Background task will pick it up
        
        return DocumentUploadResponse(
            upload_id=result["upload_id"],
            task_id=task_id,
            message=result["message"],
            file_path=result["file_path"],
            extraction_status=extraction_status
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/documents/bulk-upload", status_code=status.HTTP_201_CREATED)
async def bulk_upload_documents(
    property_code: str = Form(..., description="Property code (e.g., WEND001)"),
    year: int = Form(..., ge=2000, le=2100, description="Year for all documents"),
    files: List[UploadFile] = File(..., description="Multiple files to upload (PDF, CSV, Excel, DOC)"),
    duplicate_strategy: str = Form("skip", description="How to handle duplicates: 'skip' (default), 'replace', or 'version'"),
    uploaded_by: Optional[int] = Form(None, description="User ID (optional)"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Bulk upload multiple documents for a year with intelligent duplicate handling.

    **Features:**
    - Auto-detects document type from filename
    - Auto-detects month from filename (defaults to January if not found)
    - Supports PDF, CSV, Excel (.xlsx, .xls), DOC (.doc, .docx)
    - Intelligently organizes files in MinIO buckets
    - Queues extraction tasks automatically
    - Smart duplicate handling with user control

    **Duplicate Handling Strategies:**
    - **skip** (default): Skip files where documents already exist for that property/period/type
    - **replace**: Replace existing documents with new uploads (deletes old data)
    - **version**: Create new version and keep both (future feature)

    **Filename Patterns:**
    - Document type: *balance*sheet*, *income*statement*, *cash*flow*, *rent*roll*
    - Month: Numeric (1-12), month name (January-December), quarter (Q1-Q4)

    **Returns:**
    - Results per file with status (success/skipped/replaced/failed)
    - Summary counts and duplicate statistics
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    if len(files) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 files allowed per bulk upload"
        )
    
    try:
        # Create document service
        doc_service = DocumentService(db, organization_id=current_org.id)

        # Bulk upload documents with duplicate strategy
        result = await doc_service.bulk_upload_documents(
            property_code=property_code,
            year=year,
            files=files,
            uploaded_by=uploaded_by,
            duplicate_strategy=duplicate_strategy
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Bulk upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk upload failed: {str(e)}"
        )


@router.get("/documents/queue-status")
async def get_queue_status(db: Session = Depends(get_db)):
    """Get Celery queue status and pending extractions"""
    from celery import current_app
    from app.models.document_upload import DocumentUpload
    
    try:
        # Get Celery inspect object
        inspect = current_app.control.inspect()
        
        # Get active, scheduled, and reserved tasks
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}
        
        # Count extraction tasks across all workers
        extraction_tasks = 0
        for worker_tasks_dict in [active, scheduled, reserved]:
            if worker_tasks_dict:
                for worker_name, tasks in worker_tasks_dict.items():
                    if tasks:
                        extraction_tasks += len([
                            t for t in tasks 
                            if 'extract_document' in t.get('name', '') or 
                               'extract_document' in str(t.get('task', ''))
                        ])
        
        # Get worker stats
        stats = inspect.stats() or {}
        workers_available = len(stats)
        
        # Count pending uploads
        pending_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == 'pending'
        ).count()
        
        return {
            "queue_depth": extraction_tasks,
            "workers_available": workers_available,
            "pending_uploads": pending_uploads,
            "workers": list(stats.keys()) if stats else []
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get queue status: {e}")
        # Return safe defaults if Celery is unavailable
        pending_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == 'pending'
        ).count()
        return {
            "queue_depth": 0,
            "workers_available": 0,
            "pending_uploads": pending_uploads,
            "workers": [],
            "error": "Celery unavailable"
        }


@router.get("/documents/monitoring-status")
async def get_monitoring_status(db: Session = Depends(get_db)):
    """
    Get comprehensive monitoring status for bulk uploads.
    Returns queue status, recent uploads, failed uploads, stuck uploads, and service status.
    """
    from sqlalchemy import text
    from app.models.document_upload import DocumentUpload
    from celery import current_app
    
    try:
        # Queue status
        inspect = current_app.control.inspect()
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}
        stats = inspect.stats() or {}
        
        # Count extraction tasks
        extraction_tasks = 0
        for worker_tasks_dict in [active, scheduled, reserved]:
            if worker_tasks_dict:
                for worker_name, tasks in worker_tasks_dict.items():
                    if tasks:
                        extraction_tasks += len([
                            t for t in tasks 
                            if 'extract_document' in t.get('name', '') or 
                               'extract_document' in str(t.get('task', ''))
                        ])
        
        workers_available = len(stats)
        pending_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == 'pending'
        ).count()
        
        # Recent uploads (last 5 minutes)
        recent_uploads = db.execute(
            text("""
                SELECT id, file_name, document_type, extraction_status, 
                       EXTRACT(EPOCH FROM (NOW() - upload_date))/60 as minutes_ago,
                       extraction_task_id
                FROM document_uploads 
                WHERE upload_date > NOW() - INTERVAL '5 minutes'
                ORDER BY upload_date DESC
                LIMIT 10
            """)
        ).fetchall()
        
        # Failed uploads (last hour)
        failed_uploads = db.execute(
            text("""
                SELECT id, file_name, extraction_status, 
                       LEFT(notes, 200) as error_summary,
                       EXTRACT(EPOCH FROM (NOW() - upload_date))/60 as minutes_ago
                FROM document_uploads 
                WHERE extraction_status = 'failed' 
                  AND upload_date > NOW() - INTERVAL '1 hour'
                ORDER BY upload_date DESC
                LIMIT 5
            """)
        ).fetchall()
        
        # Stuck uploads (pending > 10 minutes)
        stuck_uploads = db.execute(
            text("""
                SELECT id, file_name, extraction_status, 
                       EXTRACT(EPOCH FROM (NOW() - upload_date))/60 as minutes_pending
                FROM document_uploads 
                WHERE extraction_status = 'pending' 
                  AND upload_date < NOW() - INTERVAL '10 minutes'
                ORDER BY upload_date ASC
                LIMIT 5
            """)
        ).fetchall()
        
        # Upload summary by status (last hour)
        upload_summary = db.execute(
            text("""
                SELECT extraction_status, COUNT(*) as count
                FROM document_uploads
                WHERE upload_date > NOW() - INTERVAL '1 hour'
                GROUP BY extraction_status
                ORDER BY count DESC
            """)
        ).fetchall()
        
        return {
            "queue_status": {
                "queue_depth": extraction_tasks,
                "workers_available": workers_available,
                "pending_uploads": pending_uploads,
                "workers": list(stats.keys()) if stats else []
            },
            "recent_uploads": [
                {
                    "id": row[0],
                    "file_name": row[1],
                    "document_type": row[2],
                    "extraction_status": row[3],
                    "minutes_ago": float(row[4]) if row[4] else 0,
                    "extraction_task_id": row[5]
                }
                for row in recent_uploads
            ],
            "failed_uploads": [
                {
                    "id": row[0],
                    "file_name": row[1],
                    "extraction_status": row[2],
                    "error_summary": row[3],
                    "minutes_ago": float(row[4]) if row[4] else 0
                }
                for row in failed_uploads
            ],
            "stuck_uploads": [
                {
                    "id": row[0],
                    "file_name": row[1],
                    "extraction_status": row[2],
                    "minutes_pending": float(row[3]) if row[3] else 0
                }
                for row in stuck_uploads
            ],
            "upload_summary": [
                {
                    "status": row[0],
                    "count": row[1]
                }
                for row in upload_summary
            ],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get monitoring status: {e}")
        # Return safe defaults
        pending_uploads = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == 'pending'
        ).count()
        return {
            "queue_status": {
                "queue_depth": 0,
                "workers_available": 0,
                "pending_uploads": pending_uploads,
                "workers": [],
                "error": "Monitoring unavailable"
            },
            "recent_uploads": [],
            "failed_uploads": [],
            "stuck_uploads": [],
            "upload_summary": [],
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/documents/uploads", response_model=DocumentListResponse)
async def list_uploads(
    property_code: Optional[str] = Query(None, description="Filter by property code"),
    document_type: Optional[DocumentTypeEnum] = Query(None, description="Filter by document type"),
    extraction_status: Optional[ExtractionStatusEnum] = Query(None, description="Filter by extraction status"),
    period_year: Optional[int] = Query(None, description="Filter by period year"),
    period_month: Optional[int] = Query(None, description="Filter by period month"),
    is_active: Optional[bool] = Query(True, description="Filter by active status (default: True, only current versions)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    List all uploaded documents with filters
    
    **Filters:**
    - property_code: Filter by specific property
    - document_type: Filter by document type
    - extraction_status: Filter by extraction status
    - period_year/period_month: Filter by financial period
    - is_active: Filter by active status (default: True, shows only current versions)
    
    **Pagination:**
    - skip: Number of records to skip
    - limit: Maximum records to return (max 500)
    
    **Returns:**
    - Paginated list of document uploads with metadata (only active versions by default)
    """
    try:
        # Build query with outer joins to ensure documents are returned even if Property/Period don't exist
        query = db.query(
            DocumentUpload,
            Property.property_code,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            ExtractionLog.confidence_score
        ).outerjoin(
            Property, DocumentUpload.property_id == Property.id
        ).outerjoin(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).outerjoin(
            ExtractionLog, DocumentUpload.extraction_id == ExtractionLog.id
        )
        
        # Apply filters
        query = query.filter(Property.organization_id == current_org.id)

        if property_code:
            query = query.filter(Property.property_code == property_code)
        
        if document_type:
            query = query.filter(DocumentUpload.document_type == document_type.value)
        
        if extraction_status:
            query = query.filter(DocumentUpload.extraction_status == extraction_status.value)
        
        if period_year:
            query = query.filter(FinancialPeriod.period_year == period_year)
        
        if period_month:
            query = query.filter(FinancialPeriod.period_month == period_month)
        
        # Filter by active status (default: only show current versions)
        if is_active is not None:
            query = query.filter(DocumentUpload.is_active == is_active)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        results = query.order_by(DocumentUpload.upload_date.desc()).offset(skip).limit(limit).all()
        
        # Build response items
        items = []
        for upload, prop_code, year, month, confidence in results:
            items.append(DocumentListItem(
                id=upload.id,
                property_code=prop_code,
                period_year=year,
                period_month=month,
                document_type=upload.document_type,
                file_name=upload.file_name,
                upload_date=upload.upload_date,
                extraction_status=upload.extraction_status,
                extraction_confidence=float(confidence) if confidence else None,
                version=upload.version,
                is_active=upload.is_active
            ))
        
        return DocumentListResponse(
            total=total,
            skip=skip,
            limit=limit,
            items=items
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list uploads: {str(e)}"
        )


@router.get("/documents/uploads/{upload_id}", response_model=DocumentUploadDetail)
async def get_upload_status(
    upload_id: int,
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get extraction status and details for an upload
    
    **Returns:**
    - Complete upload record with extraction status
    - Extraction quality metrics (if available)
    - Property and period information
    """
    try:
        # Query with joins
        result = db.query(
            DocumentUpload,
            Property.property_code,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            ExtractionLog.confidence_score,
            ExtractionLog.quality_level,
            ExtractionLog.needs_review
        ).join(
            Property, DocumentUpload.property_id == Property.id
        ).join(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).outerjoin(
            ExtractionLog, DocumentUpload.extraction_id == ExtractionLog.id
        ).filter(
            DocumentUpload.id == upload_id,
            Property.organization_id == current_org.id
        ).first()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        upload, prop_code, year, month, confidence, quality, needs_review = result
        
        return DocumentUploadDetail(
            id=upload.id,
            property_id=upload.property_id,
            period_id=upload.period_id,
            property_code=prop_code,
            period_year=year,
            period_month=month,
            document_type=upload.document_type,
            file_name=upload.file_name,
            file_path=upload.file_path,
            file_hash=upload.file_hash,
            file_size_bytes=upload.file_size_bytes,
            upload_date=upload.upload_date,
            uploaded_by=upload.uploaded_by,
            extraction_status=upload.extraction_status,
            extraction_started_at=upload.extraction_started_at,
            extraction_completed_at=upload.extraction_completed_at,
            extraction_id=upload.extraction_id,
            extraction_confidence=float(confidence) if confidence else None,
            extraction_quality=quality,
            needs_review=needs_review,
            version=upload.version,
            is_active=upload.is_active,
            notes=upload.notes
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get upload status: {str(e)}"
        )


@router.get("/documents/uploads/{upload_id}/data", response_model=ExtractedDataResponse)
async def get_extracted_data(
    upload_id: int,
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get extracted financial data from upload
    
    **Returns:**
    - Balance sheet data (if applicable)
    - Income statement data (if applicable)
    - Cash flow data (if applicable)
    - Rent roll data (if applicable)
    - Financial metrics (if calculated)
    - Validation results (if available)
    """
    try:
        # Get upload with property and period info
        upload_query = db.query(
            DocumentUpload,
            Property.property_code,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month,
            ExtractionLog.confidence_score
        ).join(
            Property, DocumentUpload.property_id == Property.id
        ).join(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).outerjoin(
            ExtractionLog, DocumentUpload.extraction_id == ExtractionLog.id
        ).filter(
            DocumentUpload.id == upload_id,
            Property.organization_id == current_org.id
        ).first()
        
        if not upload_query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        upload, prop_code, year, month, confidence = upload_query
        
        # Initialize response
        response = ExtractedDataResponse(
            upload_id=upload.id,
            property_code=prop_code,
            period_year=year,
            period_month=month,
            document_type=upload.document_type,
            extraction_status=upload.extraction_status,
            extraction_confidence=float(confidence) if confidence else None,
            balance_sheet_data=[],
            income_statement_data=[],
            cash_flow_data=[],
            rent_roll_data=[],
            financial_metrics=None,
            validation_results=[],
            validation_passed=True,
            validation_summary={}
        )
        
        # Get financial data based on document type
        if upload.document_type == "balance_sheet":
            bs_items = db.query(BalanceSheetData).filter(
                BalanceSheetData.upload_id == upload_id
            ).all()
            
            response.balance_sheet_data = [
                BalanceSheetDataItem(
                    account_code=item.account_code,
                    account_name=item.account_name,
                    amount=float(item.amount),
                    extraction_confidence=float(item.extraction_confidence) if item.extraction_confidence else None,
                    needs_review=item.needs_review
                )
                for item in bs_items
            ]
        
        elif upload.document_type == "income_statement":
            is_items = db.query(IncomeStatementData).filter(
                IncomeStatementData.upload_id == upload_id
            ).all()
            
            response.income_statement_data = [
                IncomeStatementDataItem(
                    account_code=item.account_code,
                    account_name=item.account_name,
                    period_amount=float(item.period_amount),
                    ytd_amount=float(item.ytd_amount) if item.ytd_amount else None,
                    period_percentage=float(item.period_percentage) if item.period_percentage else None,
                    ytd_percentage=float(item.ytd_percentage) if item.ytd_percentage else None,
                    extraction_confidence=float(item.extraction_confidence) if item.extraction_confidence else None,
                    needs_review=item.needs_review
                )
                for item in is_items
            ]
        
        elif upload.document_type == "cash_flow":
            cf_items = db.query(CashFlowData).filter(
                CashFlowData.upload_id == upload_id
            ).all()
            
            response.cash_flow_data = [
                CashFlowDataItem(
                    account_code=item.account_code,
                    account_name=item.account_name,
                    period_amount=float(item.period_amount),
                    cash_flow_category=item.cash_flow_category,
                    is_inflow=item.is_inflow,
                    extraction_confidence=float(item.extraction_confidence) if item.extraction_confidence else None,
                    needs_review=item.needs_review
                )
                for item in cf_items
            ]
        
        elif upload.document_type == "rent_roll":
            rr_items = db.query(RentRollData).filter(
                RentRollData.upload_id == upload_id
            ).all()
            
            response.rent_roll_data = [
                RentRollDataItem(
                    unit_number=item.unit_number,
                    tenant_name=item.tenant_name,
                    lease_start_date=item.lease_start_date,
                    lease_end_date=item.lease_end_date,
                    unit_area_sqft=float(item.unit_area_sqft) if item.unit_area_sqft else None,
                    monthly_rent=float(item.monthly_rent) if item.monthly_rent else None,
                    annual_rent=float(item.annual_rent) if item.annual_rent else None,
                    occupancy_status=item.occupancy_status,
                    extraction_confidence=float(item.extraction_confidence) if item.extraction_confidence else None,
                    needs_review=item.needs_review
                )
                for item in rr_items
            ]
        
        # Get financial metrics (if available)
        metrics = db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == upload.property_id,
            FinancialMetrics.period_id == upload.period_id
        ).first()
        
        if metrics:
            response.financial_metrics = FinancialMetricsData(
                total_assets=float(metrics.total_assets) if metrics.total_assets else None,
                total_liabilities=float(metrics.total_liabilities) if metrics.total_liabilities else None,
                total_equity=float(metrics.total_equity) if metrics.total_equity else None,
                total_revenue=float(metrics.total_revenue) if metrics.total_revenue else None,
                total_expenses=float(metrics.total_expenses) if metrics.total_expenses else None,
                net_operating_income=float(metrics.net_operating_income) if metrics.net_operating_income else None,
                net_income=float(metrics.net_income) if metrics.net_income else None,
                occupancy_rate=float(metrics.occupancy_rate) if metrics.occupancy_rate else None,
                debt_service_coverage_ratio=float(metrics.debt_service_coverage_ratio) if metrics.debt_service_coverage_ratio else None
            )
        
        # Get validation results
        validation_results = db.query(
            ValidationResult,
            ValidationRule.rule_name
        ).join(
            ValidationRule, ValidationResult.rule_id == ValidationRule.id
        ).filter(
            ValidationResult.upload_id == upload_id
        ).all()
        
        if validation_results:
            response.validation_results = [
                ValidationResultItem(
                    rule_id=vr.rule_id,
                    rule_name=rule_name,
                    passed=vr.passed,
                    expected_value=float(vr.expected_value) if vr.expected_value else None,
                    actual_value=float(vr.actual_value) if vr.actual_value else None,
                    difference=float(vr.difference) if vr.difference else None,
                    difference_percentage=float(vr.difference_percentage) if vr.difference_percentage else None,
                    error_message=vr.error_message,
                    severity=vr.severity
                )
                for vr, rule_name in validation_results
            ]
            
            # Calculate validation summary
            total_checks = len(validation_results)
            passed_checks = sum(1 for vr, _ in validation_results if vr.passed)
            failed_checks = total_checks - passed_checks
            
            response.validation_passed = failed_checks == 0
            response.validation_summary = {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": failed_checks
            }
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get extracted data: {str(e)}"
        )


@router.get("/documents/uploads/{upload_id}/download", response_model=DocumentDownloadResponse)
async def get_download_url(
    upload_id: int,
    expires_in_seconds: int = Query(3600, ge=60, le=86400, description="URL expiry time in seconds (1 hour default, max 24 hours)"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get presigned download URL for uploaded document
    
    **Returns:**
    - Presigned URL valid for specified duration (default 1 hour)
    - File metadata
    
    **Note:** URL expires after specified time for security
    """
    try:
        # Get upload record
        upload = _get_upload_for_org(db, upload_id, current_org.id)
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        # Generate presigned URL
        download_url = get_file_url(
            object_name=upload.file_path,
            expires_seconds=expires_in_seconds
        )
        
        if not download_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL"
            )
        
        return DocumentDownloadResponse(
            upload_id=upload.id,
            file_name=upload.file_name,
            file_size_bytes=upload.file_size_bytes,
            download_url=download_url,
            expires_in_seconds=expires_in_seconds
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get download URL: {str(e)}"
        )


@router.post("/documents/uploads/reprocess-failed", status_code=status.HTTP_200_OK)
async def reprocess_failed_uploads(
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Reprocess all failed document uploads
    
    **Operation:**
    - Finds all documents with extraction_status = 'failed' or containing 'failed'
    - Resets their status to 'pending'
    - Queues them for extraction again
    - Returns count of queued documents
    
    **Returns:**
    - Count of failed documents queued for reprocessing
    """
    try:
        # Find all failed uploads
        from sqlalchemy import or_
        failed_uploads = db.query(DocumentUpload).join(
            Property, DocumentUpload.property_id == Property.id
        ).filter(
            Property.organization_id == current_org.id,
            or_(
                DocumentUpload.extraction_status == 'failed',
                DocumentUpload.extraction_status.like('%failed%')
            )
        ).all()
        
        queued_count = 0
        
        for upload in failed_uploads:
            try:
                # Reset status to pending
                upload.extraction_status = 'pending'
                upload.extraction_task_id = None
                upload.extraction_started_at = None
                upload.extraction_completed_at = None
                db.flush()
                
                # Queue extraction task
                task = extract_document.delay(upload.id)
                upload.extraction_task_id = task.id
                db.commit()
                
                queued_count += 1
            except Exception as e:
                db.rollback()
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to reprocess upload_id={upload.id}: {str(e)}")
        
        return {
            "message": f"Successfully queued {queued_count} failed document(s) for reprocessing",
            "queued_count": queued_count,
            "total_failed": len(failed_uploads)
        }
    
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to reprocess failed uploads: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reprocess failed uploads: {str(e)}"
        )


@router.post("/documents/uploads/{upload_id}/reprocess", status_code=status.HTTP_200_OK)
async def reprocess_single_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Reprocess a single document upload

    **Operation:**
    - Deletes existing extracted data for the upload
    - Resets extraction status to 'pending'
    - Queues document for extraction again

    **Parameters:**
    - upload_id: The ID of the document upload to reprocess

    **Returns:**
    - Success message with task ID
    """
    try:
        # Get the upload
        upload = _get_upload_for_org(db, upload_id, current_org.id)

        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload with ID {upload_id} not found"
            )

        # Delete existing extracted data based on document type
        from app.models.balance_sheet_data import BalanceSheetData
        from app.models.income_statement_data import IncomeStatementData
        from app.models.cash_flow_data import CashFlowData
        from app.models.rent_roll_data import RentRollData
        from app.models.mortgage_statement_data import MortgageStatementData

        if upload.document_type == 'balance_sheet':
            db.query(BalanceSheetData).filter(BalanceSheetData.upload_id == upload_id).delete()
        elif upload.document_type == 'income_statement':
            db.query(IncomeStatementData).filter(IncomeStatementData.upload_id == upload_id).delete()
        elif upload.document_type == 'cash_flow':
            db.query(CashFlowData).filter(CashFlowData.upload_id == upload_id).delete()
        elif upload.document_type == 'rent_roll':
            db.query(RentRollData).filter(RentRollData.upload_id == upload_id).delete()
        elif upload.document_type == 'mortgage_statement':
            db.query(MortgageStatementData).filter(MortgageStatementData.upload_id == upload_id).delete()

        # Reset extraction status
        upload.extraction_status = 'pending'
        upload.extraction_task_id = None
        upload.extraction_started_at = None
        upload.extraction_completed_at = None
        db.flush()

        # Queue extraction task
        task = extract_document.delay(upload.id)
        upload.extraction_task_id = task.id
        db.commit()

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Reprocessing upload_id={upload_id}, task_id={task.id}")

        return {
            "message": f"Successfully queued document '{upload.file_name}' for reprocessing",
            "upload_id": upload.id,
            "task_id": task.id,
            "document_type": upload.document_type
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to reprocess upload_id={upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reprocess upload: {str(e)}"
        )


@router.delete("/documents/uploads/delete-all-history", status_code=status.HTTP_200_OK)
@limiter.limit("1/minute")  # Rate limit: 1 destructive operation per minute per IP
async def delete_all_upload_history(
    request: Request,  # Required for rate limiter
    db: Session = Depends(get_db)
):
    """
    Delete all document upload history from the database
    
    **Warning:** This operation:
    - Deletes ALL document upload records from the database
    - Deletes associated extracted financial data (via cascade)
    - Deletes files from MinIO storage
    - This action CANNOT be undone
    
    **Use Cases:**
    - Clean up old upload history
    - Reset system for testing
    - Remove all document records
    
    **Returns:**
    - Count of deleted records
    """
    import logging
    from sqlalchemy import text
    
    logger = logging.getLogger(__name__)
    
    try:
        # Step 1: Delete orphaned anomaly_detections records (where document_id is null)
        # These orphaned records violate the NOT NULL constraint and prevent cascade deletion
        logger.info("Cleaning up orphaned anomaly_detections records...")
        orphaned_count = db.execute(
            text("DELETE FROM anomaly_detections WHERE document_id IS NULL")
        ).rowcount
        if orphaned_count > 0:
            logger.info(f"Deleted {orphaned_count} orphaned anomaly_detections records")

        # Step 2: Delete document uploads in batches to prevent memory exhaustion
        # PERFORMANCE FIX: Process in batches instead of loading all records at once
        BATCH_SIZE = 100
        deleted_count = 0
        batch_number = 0

        while True:
            batch_number += 1
            # Fetch a batch of uploads (limit prevents loading entire table into memory)
            batch = db.query(DocumentUpload).limit(BATCH_SIZE).all()

            if not batch:
                break  # No more records to delete

            logger.info(f"Processing batch {batch_number} with {len(batch)} records...")

            # Step 3: Delete files from MinIO and database records for this batch
            for upload in batch:
                # Delete file from MinIO if file_path exists
                if upload.file_path:
                    try:
                        delete_file(upload.file_path)
                    except Exception as e:
                        # Log error but continue deletion
                        logger.warning(f"Failed to delete file from MinIO: {upload.file_path}, error: {str(e)}")

                # Delete database record (cascade will handle related data)
                db.delete(upload)

            # Commit this batch to free memory and ensure progress is saved
            db.commit()
            deleted_count += len(batch)
            logger.info(f"Batch {batch_number} committed. Total deleted so far: {deleted_count}")

        return {
            "message": f"Successfully deleted {deleted_count} document upload records",
            "deleted_count": deleted_count,
            "orphaned_anomalies_deleted": orphaned_count,
            "batches_processed": batch_number - 1
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete upload history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete upload history: {str(e)}"
        )


@router.delete("/documents/anomalies-warnings-alerts/delete-all", status_code=status.HTTP_200_OK)
@limiter.limit("1/minute")  # Rate limit: 1 destructive operation per minute per IP
async def delete_all_anomalies_warnings_alerts(
    request: Request,  # Required for rate limiter
    db: Session = Depends(get_db)
):
    """
    Delete all anomalies, warnings, and alerts data from the database
    
    **Warning:** This operation:
    - Deletes ALL anomaly detection records
    - Deletes ALL alerts (from alerts table)
    - Deletes ALL committee alerts
    - Deletes ALL alert history
    - Deletes ALL alert suppressions and snoozes
    - Deletes ALL alert suppression rules
    - **KEEPS** alert_rules (rule definitions are preserved)
    - This action CANNOT be undone
    
    **Use Cases:**
    - Clean up old anomaly/alert data before re-uploading documents
    - Reset system for testing with new anomaly detection implementation
    - Remove all generated alerts/anomalies to regenerate with updated logic
    
    **Returns:**
    - Count of deleted records for each table
    """
    import logging
    from sqlalchemy import text
    
    logger = logging.getLogger(__name__)
    
    try:
        deletion_counts = {}
        
        # Step 1: Delete alert_history (must be first due to foreign key to committee_alerts)
        logger.info("Deleting alert_history records...")
        deletion_counts['alert_history'] = db.execute(
            text("DELETE FROM alert_history")
        ).rowcount
        logger.info(f"Deleted {deletion_counts['alert_history']} alert_history records")
        
        # Step 2: Delete alert_snoozes
        logger.info("Deleting alert_snoozes records...")
        deletion_counts['alert_snoozes'] = db.execute(
            text("DELETE FROM alert_snoozes")
        ).rowcount
        logger.info(f"Deleted {deletion_counts['alert_snoozes']} alert_snoozes records")
        
        # Step 3: Delete alert_suppressions
        logger.info("Deleting alert_suppressions records...")
        deletion_counts['alert_suppressions'] = db.execute(
            text("DELETE FROM alert_suppressions")
        ).rowcount
        logger.info(f"Deleted {deletion_counts['alert_suppressions']} alert_suppressions records")
        
        # Step 4: Delete alert_suppression_rules
        logger.info("Deleting alert_suppression_rules records...")
        deletion_counts['alert_suppression_rules'] = db.execute(
            text("DELETE FROM alert_suppression_rules")
        ).rowcount
        logger.info(f"Deleted {deletion_counts['alert_suppression_rules']} alert_suppression_rules records")
        
        # Step 5: Delete committee_alerts
        logger.info("Deleting committee_alerts records...")
        deletion_counts['committee_alerts'] = db.execute(
            text("DELETE FROM committee_alerts")
        ).rowcount
        logger.info(f"Deleted {deletion_counts['committee_alerts']} committee_alerts records")
        
        # Step 6: Delete alerts (from alerts table)
        logger.info("Deleting alerts records...")
        deletion_counts['alerts'] = db.execute(
            text("DELETE FROM alerts")
        ).rowcount
        logger.info(f"Deleted {deletion_counts['alerts']} alerts records")
        
        # Step 7: Delete anomaly_detections (including orphaned records)
        logger.info("Deleting anomaly_detections records...")
        deletion_counts['anomaly_detections'] = db.execute(
            text("DELETE FROM anomaly_detections")
        ).rowcount
        logger.info(f"Deleted {deletion_counts['anomaly_detections']} anomaly_detections records")
        
        # Step 8: Delete related feedback/explanation records if they exist
        # Check if tables exist before deleting
        try:
            logger.info("Deleting anomaly_feedback records...")
            deletion_counts['anomaly_feedback'] = db.execute(
                text("DELETE FROM anomaly_feedback")
            ).rowcount
            logger.info(f"Deleted {deletion_counts['anomaly_feedback']} anomaly_feedback records")
        except Exception as e:
            logger.warning(f"anomaly_feedback table may not exist: {str(e)}")
            deletion_counts['anomaly_feedback'] = 0
        
        try:
            logger.info("Deleting anomaly_explanations records...")
            deletion_counts['anomaly_explanations'] = db.execute(
                text("DELETE FROM anomaly_explanations")
            ).rowcount
            logger.info(f"Deleted {deletion_counts['anomaly_explanations']} anomaly_explanations records")
        except Exception as e:
            logger.warning(f"anomaly_explanations table may not exist: {str(e)}")
            deletion_counts['anomaly_explanations'] = 0
        
        # Commit all deletions
        db.commit()
        
        total_deleted = sum(deletion_counts.values())
        
        return {
            "message": f"Successfully deleted all anomalies, warnings, and alerts data. Total records deleted: {total_deleted}",
            "total_deleted": total_deleted,
            "deletion_counts": deletion_counts,
            "note": "alert_rules (rule definitions) were preserved and not deleted"
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete anomalies/warnings/alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete anomalies/warnings/alerts: {str(e)}"
        )


@router.post("/documents/anomalies-warnings-alerts/delete-filtered", status_code=status.HTTP_200_OK)
async def delete_filtered_anomalies_warnings_alerts(
    property_ids: Optional[List[int]] = Query(None, description="List of property IDs (required)"),
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Filter by period year (optional)"),
    document_type: Optional[DocumentTypeEnum] = Query(None, description="Filter by document type (optional)"),
    period_id: Optional[int] = Query(None, description="Filter by specific period ID (optional)"),
    db: Session = Depends(get_db)
):
    """
    Delete anomalies, warnings, and alerts data with intelligent filtering
    
    **Filters:**
    - **property_ids** (required): List of property IDs to filter by
    - **year** (optional): Filter by financial period year
    - **document_type** (optional): Filter by document type (balance_sheet, income_statement, etc.)
    - **period_id** (optional): Filter by specific financial period ID
    
    **Warning:** This operation:
    - Deletes anomaly detection records matching filters
    - Deletes alerts (from alerts table) matching filters
    - Deletes committee alerts matching filters
    - Deletes alert history for matching alerts
    - Deletes alert suppressions/snoozes for matching alerts
    - **KEEPS** alert_rules (rule definitions are preserved)
    - This action CANNOT be undone
    
    **Returns:**
    - Count of deleted records for each table
    - Preview of what will be deleted (before deletion)
    """
    import logging
    from sqlalchemy import text, and_, or_
    from app.models.document_upload import DocumentUpload
    from app.models.financial_period import FinancialPeriod
    
    logger = logging.getLogger(__name__)
    
    try:
        # Validate required filters
        if not property_ids or len(property_ids) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="property_ids is required and must contain at least one property ID"
            )
        
        # Build query to find matching document_uploads
        query = db.query(DocumentUpload.id).join(
            FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
        ).filter(
            DocumentUpload.property_id.in_(property_ids)
        )
        
        # Apply optional filters
        if year:
            query = query.filter(FinancialPeriod.period_year == year)
        
        if document_type:
            query = query.filter(DocumentUpload.document_type == document_type.value)
        
        if period_id:
            query = query.filter(DocumentUpload.period_id == period_id)
        
        # Get matching document upload IDs
        matching_upload_ids = [row[0] for row in query.all()]
        
        if not matching_upload_ids:
            return {
                "message": "No documents found matching the specified filters",
                "total_deleted": 0,
                "deletion_counts": {},
                "matching_documents": 0,
                "filters_applied": {
                    "property_ids": property_ids,
                    "year": year,
                    "document_type": document_type.value if document_type else None,
                    "period_id": period_id
                }
            }
        
        logger.info(f"Found {len(matching_upload_ids)} documents matching filters. Upload IDs: {matching_upload_ids[:10]}...")
        
        deletion_counts = {}
        
        # Step 1: Delete alert_history for matching committee_alerts
        logger.info("Deleting alert_history records...")
        from app.models.alert_history import AlertHistory
        from app.models.committee_alert import CommitteeAlert
        
        committee_alert_ids = db.query(CommitteeAlert.id).filter(
            CommitteeAlert.property_id.in_(property_ids)
        )
        if period_id:
            committee_alert_ids = committee_alert_ids.filter(CommitteeAlert.financial_period_id == period_id)
        
        committee_alert_ids_list = [row[0] for row in committee_alert_ids.all()]
        if committee_alert_ids_list:
            deletion_counts['alert_history'] = db.query(AlertHistory).filter(
                AlertHistory.alert_id.in_(committee_alert_ids_list)
            ).delete(synchronize_session=False)
        else:
            deletion_counts['alert_history'] = 0
        logger.info(f"Deleted {deletion_counts['alert_history']} alert_history records")
        
        # Step 2: Delete alert_snoozes for matching alerts
        logger.info("Deleting alert_snoozes records...")
        from app.models.alert_suppression import AlertSnooze
        from app.models.alert_rule import AlertRule
        from app.models.anomaly_detection import AnomalyDetection
        
        alert_ids_to_delete = []
        if matching_upload_ids:
            # Get alert IDs from alerts table
            alert_ids_from_alerts = db.execute(
                text("SELECT id FROM alerts WHERE document_id = ANY(:upload_ids)"),
                {"upload_ids": matching_upload_ids}
            ).fetchall()
            alert_ids_to_delete.extend([row[0] for row in alert_ids_from_alerts])
        
        # Add committee alert IDs
        alert_ids_to_delete.extend(committee_alert_ids_list)
        
        if alert_ids_to_delete:
            deletion_counts['alert_snoozes'] = db.query(AlertSnooze).filter(
                AlertSnooze.alert_id.in_(alert_ids_to_delete)
            ).delete(synchronize_session=False)
        else:
            deletion_counts['alert_snoozes'] = 0
        logger.info(f"Deleted {deletion_counts['alert_snoozes']} alert_snoozes records")
        
        # Step 3: Delete alert_suppressions for matching alerts
        logger.info("Deleting alert_suppressions records...")
        from app.models.alert_suppression import AlertSuppression
        
        if alert_ids_to_delete:
            deletion_counts['alert_suppressions'] = db.query(AlertSuppression).filter(
                AlertSuppression.alert_id.in_(alert_ids_to_delete)
            ).delete(synchronize_session=False)
        else:
            deletion_counts['alert_suppressions'] = 0
        logger.info(f"Deleted {deletion_counts['alert_suppressions']} alert_suppressions records")
        
        # Step 4: Delete committee_alerts
        logger.info("Deleting committee_alerts records...")
        committee_query = db.query(CommitteeAlert).filter(
            CommitteeAlert.property_id.in_(property_ids)
        )
        if period_id:
            committee_query = committee_query.filter(CommitteeAlert.financial_period_id == period_id)
        deletion_counts['committee_alerts'] = committee_query.delete(synchronize_session=False)
        logger.info(f"Deleted {deletion_counts['committee_alerts']} committee_alerts records")
        
        # Step 5: Delete alerts (from alerts table) for matching documents
        logger.info("Deleting alerts records...")
        if matching_upload_ids:
            # Use raw SQL for alerts table (no model exists)
            # Use IN clause with tuple unpacking for PostgreSQL
            placeholders = ','.join([':id' + str(i) for i in range(len(matching_upload_ids))])
            params = {f'id{i}': upload_id for i, upload_id in enumerate(matching_upload_ids)}
            deletion_counts['alerts'] = db.execute(
                text(f"DELETE FROM alerts WHERE document_id IN ({placeholders})"),
                params
            ).rowcount
        else:
            deletion_counts['alerts'] = 0
        logger.info(f"Deleted {deletion_counts['alerts']} alerts records")
        
        # Step 6: Delete anomaly_detections for matching documents
        logger.info("Deleting anomaly_detections records...")
        if matching_upload_ids:
            deletion_counts['anomaly_detections'] = db.query(AnomalyDetection).filter(
                AnomalyDetection.document_id.in_(matching_upload_ids)
            ).delete(synchronize_session=False)
        else:
            deletion_counts['anomaly_detections'] = 0
        logger.info(f"Deleted {deletion_counts['anomaly_detections']} anomaly_detections records")
        
        # Step 7: Delete related feedback/explanation records
        try:
            logger.info("Deleting anomaly_feedback records...")
            from app.models.anomaly_feedback import AnomalyFeedback
            if matching_upload_ids:
                # Get anomaly detection IDs first
                anomaly_ids = db.query(AnomalyDetection.id).filter(
                    AnomalyDetection.document_id.in_(matching_upload_ids)
                ).all()
                anomaly_ids_list = [row[0] for row in anomaly_ids]
                if anomaly_ids_list:
                    deletion_counts['anomaly_feedback'] = db.query(AnomalyFeedback).filter(
                        AnomalyFeedback.anomaly_detection_id.in_(anomaly_ids_list)
                    ).delete(synchronize_session=False)
                else:
                    deletion_counts['anomaly_feedback'] = 0
            else:
                deletion_counts['anomaly_feedback'] = 0
            logger.info(f"Deleted {deletion_counts['anomaly_feedback']} anomaly_feedback records")
        except Exception as e:
            logger.warning(f"anomaly_feedback table may not exist: {str(e)}")
            deletion_counts['anomaly_feedback'] = 0
        
        try:
            logger.info("Deleting anomaly_explanations records...")
            from app.models.anomaly_explanation import AnomalyExplanation
            if matching_upload_ids:
                # Get anomaly detection IDs first
                anomaly_ids = db.query(AnomalyDetection.id).filter(
                    AnomalyDetection.document_id.in_(matching_upload_ids)
                ).all()
                anomaly_ids_list = [row[0] for row in anomaly_ids]
                if anomaly_ids_list:
                    deletion_counts['anomaly_explanations'] = db.query(AnomalyExplanation).filter(
                        AnomalyExplanation.anomaly_detection_id.in_(anomaly_ids_list)
                    ).delete(synchronize_session=False)
                else:
                    deletion_counts['anomaly_explanations'] = 0
            else:
                deletion_counts['anomaly_explanations'] = 0
            logger.info(f"Deleted {deletion_counts['anomaly_explanations']} anomaly_explanations records")
        except Exception as e:
            logger.warning(f"anomaly_explanations table may not exist: {str(e)}")
            deletion_counts['anomaly_explanations'] = 0
        
        # Commit all deletions
        db.commit()
        
        total_deleted = sum(deletion_counts.values())
        
        return {
            "message": f"Successfully deleted anomalies, warnings, and alerts data. Total records deleted: {total_deleted}",
            "total_deleted": total_deleted,
            "deletion_counts": deletion_counts,
            "matching_documents": len(matching_upload_ids),
            "filters_applied": {
                "property_ids": property_ids,
                "year": year,
                "document_type": document_type.value if document_type else None,
                "period_id": period_id
            },
            "note": "alert_rules (rule definitions) were preserved and not deleted"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete filtered anomalies/warnings/alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete filtered anomalies/warnings/alerts: {str(e)}"
        )


@router.get("/documents/anomalies-warnings-alerts/preview", status_code=status.HTTP_200_OK)
async def preview_filtered_anomalies_warnings_alerts(
    property_ids: Optional[List[int]] = Query(None, description="List of property IDs (required)"),
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Filter by period year (optional)"),
    document_type: Optional[DocumentTypeEnum] = Query(None, description="Filter by document type (optional)"),
    period_id: Optional[int] = Query(None, description="Filter by specific period ID (optional)"),
    db: Session = Depends(get_db)
):
    """
    Preview what will be deleted before actually deleting
    
    Returns counts of records that would be deleted without actually deleting them.
    """
    from sqlalchemy import text
    from app.models.document_upload import DocumentUpload
    from app.models.financial_period import FinancialPeriod
    
    if not property_ids or len(property_ids) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="property_ids is required and must contain at least one property ID"
        )
    
    # Build query to find matching document_uploads
    query = db.query(DocumentUpload.id).join(
        FinancialPeriod, DocumentUpload.period_id == FinancialPeriod.id
    ).filter(
        DocumentUpload.property_id.in_(property_ids)
    )
    
    if year:
        query = query.filter(FinancialPeriod.period_year == year)
    
    if document_type:
        query = query.filter(DocumentUpload.document_type == document_type.value)
    
    if period_id:
        query = query.filter(DocumentUpload.period_id == period_id)
    
    matching_upload_ids = [row[0] for row in query.all()]
    
    from app.models.anomaly_detection import AnomalyDetection
    from app.models.committee_alert import CommitteeAlert
    
    preview_counts = {}
    
    if matching_upload_ids:
        # Count anomaly_detections
        preview_counts['anomaly_detections'] = db.query(AnomalyDetection).filter(
            AnomalyDetection.document_id.in_(matching_upload_ids)
        ).count()
        
        # Count alerts (using raw SQL since no model exists)
        if matching_upload_ids:
            placeholders = ','.join([':id' + str(i) for i in range(len(matching_upload_ids))])
            params = {f'id{i}': upload_id for i, upload_id in enumerate(matching_upload_ids)}
            preview_counts['alerts'] = db.execute(
                text(f"SELECT COUNT(*) FROM alerts WHERE document_id IN ({placeholders})"),
                params
            ).scalar()
        else:
            preview_counts['alerts'] = 0
        
        # Count committee_alerts
        committee_query = db.query(CommitteeAlert).filter(
            CommitteeAlert.property_id.in_(property_ids)
        )
        if period_id:
            committee_query = committee_query.filter(CommitteeAlert.financial_period_id == period_id)
        preview_counts['committee_alerts'] = committee_query.count()
    else:
        preview_counts = {
            'anomaly_detections': 0,
            'alerts': 0,
            'committee_alerts': 0
        }
    
    total_preview = sum(preview_counts.values())
    
    return {
        "message": f"Preview: {total_preview} records would be deleted",
        "total_preview": total_preview,
        "preview_counts": preview_counts,
        "matching_documents": len(matching_upload_ids),
        "filters_applied": {
            "property_ids": property_ids,
            "year": year,
            "document_type": document_type.value if document_type else None,
            "period_id": period_id
        }
    }


@router.post("/documents/uploads/{upload_id}/re-extract")
async def re_run_extraction(
    upload_id: int,
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Re-run extraction for an existing document upload.
    
    Useful when:
    - Extraction completed but inserted 0 records
    - Extraction logic was improved after initial processing
    - Data needs to be re-extracted with updated patterns
    
    Returns:
    - Task ID for the extraction
    - Updated extraction status
    """
    upload = _get_upload_for_org(db, upload_id, current_org.id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Reset extraction status
    upload.extraction_status = 'pending'
    upload.extraction_started_at = None
    upload.extraction_completed_at = None
    upload.extraction_task_id = None
    db.commit()
    
    # Trigger extraction
    try:
        task = extract_document.delay(upload_id)
        upload.extraction_task_id = task.id
        db.commit()
        
        return {
            "success": True,
            "upload_id": upload_id,
            "task_id": task.id,
            "message": "Extraction re-queued successfully"
        }
    except Exception as e:
        upload.extraction_status = 'failed'
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to queue extraction: {str(e)}")


@router.post("/documents/re-extract-failed")
async def re_extract_failed_uploads(
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    property_id: Optional[int] = Query(None, description="Filter by property"),
    period_id: Optional[int] = Query(None, description="Filter by period"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Re-run extraction for uploads that completed but have no data records.
    
    This identifies uploads where extraction_status='completed' but no data
    was inserted into the corresponding data table.
    """
    from app.models.mortgage_statement_data import MortgageStatementData
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Build query for completed uploads
    query = db.query(DocumentUpload).join(
        Property, DocumentUpload.property_id == Property.id
    ).filter(
        DocumentUpload.extraction_status == 'completed',
        Property.organization_id == current_org.id
    )
    
    if document_type:
        query = query.filter(DocumentUpload.document_type == document_type)
    if property_id:
        query = query.filter(DocumentUpload.property_id == property_id)
    if period_id:
        query = query.filter(DocumentUpload.period_id == period_id)
    
    uploads = query.all()
    
    # Check which uploads have no data records
    failed_uploads = []
    data_model_map = {
        'mortgage_statement': MortgageStatementData,
        'balance_sheet': BalanceSheetData,
        'income_statement': IncomeStatementData,
        'cash_flow': CashFlowData,
        'rent_roll': RentRollData
    }
    
    for upload in uploads:
        DataModel = data_model_map.get(upload.document_type)
        if not DataModel:
            continue
        
        # Check if data exists
        data_count = db.query(sql_func.count(DataModel.id)).filter(
            DataModel.upload_id == upload.id
        ).scalar()
        
        if data_count == 0:
            failed_uploads.append(upload)
    
    # Re-queue extractions
    re_queued = []
    for upload in failed_uploads:
        upload.extraction_status = 'pending'
        upload.extraction_task_id = None
        try:
            task = extract_document.delay(upload.id)
            upload.extraction_task_id = task.id
            re_queued.append({
                "upload_id": upload.id,
                "file_name": upload.file_name,
                "task_id": task.id
            })
        except Exception as e:
            upload.extraction_status = 'failed'
            logger.error(f"Failed to re-queue extraction for upload {upload.id}: {e}")
    
    db.commit()
    
    return {
        "success": True,
        "total_checked": len(uploads),
        "failed_extractions": len(failed_uploads),
        "re_queued": len(re_queued),
        "uploads": re_queued
    }


@router.get("/documents/uploads/{upload_id}/regenerate-pdf")
async def regenerate_income_statement_pdf(
    upload_id: int,
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Regenerate income statement PDF from database data
    
    Creates a new PDF matching the original format using extracted data from the database.
    This allows you to verify that extracted values match the original PDF.
    
    **Supported Document Types:**
    - income_statement
    
    **Returns:**
    - PDF file matching original format
    
    **Example Usage:**
    1. Upload ESP 2023 Income Statement
    2. Extract data (already done)
    3. Call this endpoint to regenerate PDF
    4. Compare original vs regenerated PDF to verify extraction accuracy
    """
    try:
        # Get upload record
        upload = _get_upload_for_org(db, upload_id, current_org.id)
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        if upload.document_type != "income_statement":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This endpoint only supports income statements. Document type: {upload.document_type}"
            )
        
        # Generate PDF
        generator = PDFGeneratorService()
        pdf_bytes = generator.generate_income_statement_pdf(upload_id, db)
        
        # Generate filename
        filename = upload.file_name or f"income_statement_{upload_id}.pdf"
        # Add "regenerated_" prefix
        if not filename.startswith("regenerated_"):
            filename = f"regenerated_{filename}"
        
        # Return PDF as streaming response
        return StreamingResponse(
            pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate PDF: {str(e)}"
        )


@router.post("/documents/uploads/{upload_id}/correct-period")
async def correct_upload_period(
    upload_id: int,
    correct_month: int = Body(..., ge=1, le=12, description="Correct month (1-12)"),
    correct_year: int = Body(..., ge=2000, le=2100, description="Correct year"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization)
):
    """
    User confirms or corrects the detected period for an upload.
    This feeds into the self-learning pattern recognition system.

    Args:
        upload_id: Document upload ID
        correct_month: Correct month (1-12)
        correct_year: Correct year (2000-2100)

    Returns:
        {
            "success": bool,
            "was_correct": bool,
            "old_period": {"month": int, "year": int},
            "new_period": {"month": int, "year": int},
            "period_moved": bool,
            "message": str
        }
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Get upload
        upload = _get_upload_for_org(db, upload_id, current_org.id)
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        # Get current period
        current_period = db.query(FinancialPeriod).filter(
            FinancialPeriod.id == upload.period_id
        ).first()

        if not current_period:
            raise HTTPException(status_code=404, detail="Period not found")

        # Check if correction is needed
        was_correct = (
            current_period.period_month == correct_month and
            current_period.period_year == correct_year
        )

        old_period = {
            "month": current_period.period_month,
            "year": current_period.period_year
        }

        new_period = {
            "month": correct_month,
            "year": correct_year
        }

        # Update learning system FIRST (before moving data)
        try:
            from app.services.filename_pattern_learning_service import FilenamePatternLearningService
            learning_service = FilenamePatternLearningService(db)

            learning_service.learn_from_upload(
                filename=upload.file_name,
                detected_month=correct_month,
                detected_year=correct_year,
                property_id=upload.property_id,
                document_type=upload.document_type,
                detection_method='user_correction',
                was_correct=was_correct
            )

            logger.info(f"Pattern learning updated for upload {upload_id}: was_correct={was_correct}")

        except Exception as e:
            logger.error(f"Failed to update pattern learning: {e}")
            # Continue even if learning fails

        # Move upload to correct period if needed
        period_moved = False
        if not was_correct:
            # Get or create correct period
            from app.services.document_service import DocumentService
            doc_service = DocumentService(db, organization_id=current_org.id)

            correct_period = doc_service.get_or_create_period(
                upload.property_id,
                correct_year,
                correct_month
            )

            # Move upload to correct period
            old_period_id = upload.period_id
            upload.period_id = correct_period.id
            upload.notes = (upload.notes or "") + f"\nPeriod corrected by user from {old_period['month']}/{old_period['year']} to {correct_month}/{correct_year} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            db.commit()
            period_moved = True

            logger.info(f"Upload {upload_id} moved from period {old_period_id} to {correct_period.id}")

            message = f"Period corrected from {old_period['month']}/{old_period['year']} to {correct_month}/{correct_year}"
        else:
            message = "Period was already correct - no changes made"

        return {
            "success": True,
            "was_correct": was_correct,
            "old_period": old_period,
            "new_period": new_period,
            "period_moved": period_moved,
            "message": message
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to correct period for upload {upload_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to correct period: {str(e)}"
        )


@router.get("/documents/pattern-learning/statistics")
async def get_pattern_learning_statistics(
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    db: Session = Depends(get_db)
):
    """
    Get statistics about the self-learning pattern recognition system.

    Returns:
        {
            "total_patterns": int,
            "average_success_rate": float,
            "total_uploads_learned": int,
            "patterns": [
                {
                    "pattern": str,
                    "pattern_type": str,
                    "example": str,
                    "success_rate": float,
                    "times_seen": int,
                    "document_type": str
                },
                ...
            ]
        }
    """
    try:
        from app.services.filename_pattern_learning_service import FilenamePatternLearningService

        learning_service = FilenamePatternLearningService(db)
        stats = learning_service.get_pattern_statistics(
            property_id=property_id,
            document_type=document_type
        )

        return stats

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get pattern statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pattern statistics: {str(e)}"
        )


@router.get("/documents/availability-matrix")
def get_document_availability_matrix(
    property_id: int = Query(..., description="Property ID"),
    year: int = Query(..., description="Year to fetch document availability for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get document availability matrix for a property for the entire year.

    Returns a matrix showing which documents are available for each month,
    and identifies the latest period where all required documents are available.

    Required documents: balance_sheet, income_statement, cash_flow, rent_roll, mortgage_statement
    """
    try:
        from app.models.mortgage_statement_data import MortgageStatementData
        from datetime import datetime

        # Get all periods for the property and year
        periods = db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id,
            FinancialPeriod.period_year == year
        ).order_by(
            FinancialPeriod.period_month.asc()
        ).all()

        if not periods:
            return {
                "property_id": property_id,
                "year": year,
                "months": [],
                "latest_complete_period": None
            }

        # Required document types
        required_doc_types = ['balance_sheet', 'income_statement', 'cash_flow', 'rent_roll', 'mortgage_statement']

        matrix = []
        latest_complete_period = None

        for period in periods:
            # Get all uploaded documents for this period
            uploaded_docs = db.query(DocumentUpload).filter(
                DocumentUpload.property_id == property_id,
                DocumentUpload.period_id == period.id,
                DocumentUpload.extraction_status == 'completed'
            ).all()

            # Create a set of available document types
            available_types = {doc.document_type for doc in uploaded_docs}

            # Check for mortgage statement data (alternative to uploaded mortgage doc)
            has_mortgage_data = db.query(MortgageStatementData).filter(
                MortgageStatementData.property_id == property_id,
                MortgageStatementData.period_id == period.id
            ).first() is not None

            if has_mortgage_data:
                available_types.add('mortgage_statement')

            # Build document status for each required type
            doc_status = {}
            for doc_type in required_doc_types:
                doc_status[doc_type] = doc_type in available_types

            # Check if all required documents are available
            all_available = all(doc_status.values())

            month_data = {
                "period_id": period.id,
                "month": period.period_month,
                "month_name": datetime(year, period.period_month, 1).strftime('%B'),
                "documents": doc_status,
                "all_available": all_available,
                "uploaded_count": len(uploaded_docs)
            }

            matrix.append(month_data)

            # Track the latest complete period
            if all_available:
                latest_complete_period = {
                    "period_id": period.id,
                    "month": period.period_month,
                    "month_name": datetime(year, period.period_month, 1).strftime('%B'),
                    "year": year
                }

        return {
            "property_id": property_id,
            "year": year,
            "months": matrix,
            "latest_complete_period": latest_complete_period,
            "required_documents": required_doc_types
        }

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get document availability matrix: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document availability matrix: {str(e)}"
        )


# ---------- FA-MORT-4: Escrow document links ----------

@router.get("/documents/escrow-links", response_model=EscrowLinkListResponse)
def list_escrow_document_links(
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    period_id: Optional[int] = Query(None, description="Filter by financial period ID"),
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization),
):
    """
    List escrow document links (FA-MORT-4). Optionally filter by property_id and/or period_id.
    Only returns links for properties in the current organization.
    """
    query = (
        db.query(EscrowDocumentLink)
        .join(Property, EscrowDocumentLink.property_id == Property.id)
        .filter(Property.organization_id == current_org.id)
    )
    if property_id is not None:
        query = query.filter(EscrowDocumentLink.property_id == property_id)
    if period_id is not None:
        query = query.filter(EscrowDocumentLink.period_id == period_id)
    links = query.order_by(EscrowDocumentLink.created_at.desc()).all()
    return EscrowLinkListResponse(
        links=[EscrowLinkResponse(
            id=l.id,
            property_id=l.property_id,
            period_id=l.period_id,
            document_upload_id=l.document_upload_id,
            escrow_type=l.escrow_type,
            created_at=l.created_at,
        ) for l in links],
        total=len(links),
    )


@router.post("/documents/escrow-links", response_model=EscrowLinkResponse, status_code=status.HTTP_201_CREATED)
def create_escrow_document_link(
    body: EscrowLinkCreate,
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Link a document upload to escrow activity for a property/period/type (FA-MORT-4).
    The document_upload must belong to the same property_id and period_id.
    """
    # Ensure property is in org
    prop = (
        db.query(Property)
        .filter(Property.id == body.property_id, Property.organization_id == current_org.id)
        .first()
    )
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found or not in organization")
    # Ensure upload exists and matches property/period
    upload = (
        db.query(DocumentUpload)
        .join(Property, DocumentUpload.property_id == Property.id)
        .filter(
            DocumentUpload.id == body.document_upload_id,
            DocumentUpload.property_id == body.property_id,
            DocumentUpload.period_id == body.period_id,
            Property.organization_id == current_org.id,
            DocumentUpload.is_active.is_(True),
        )
        .first()
    )
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document upload not found or does not match property/period, or is inactive",
        )
    link = EscrowDocumentLink(
        property_id=body.property_id,
        period_id=body.period_id,
        document_upload_id=body.document_upload_id,
        escrow_type=body.escrow_type.value,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return EscrowLinkResponse(
        id=link.id,
        property_id=link.property_id,
        period_id=link.period_id,
        document_upload_id=link.document_upload_id,
        escrow_type=link.escrow_type,
        created_at=link.created_at,
    )


@router.delete("/documents/escrow-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_escrow_document_link(
    link_id: int,
    db: Session = Depends(get_db),
    current_org: Organization = Depends(get_current_organization),
):
    """Remove an escrow document link (FA-MORT-4). Only links for org properties can be deleted."""
    link = (
        db.query(EscrowDocumentLink)
        .join(Property, EscrowDocumentLink.property_id == Property.id)
        .filter(EscrowDocumentLink.id == link_id, Property.organization_id == current_org.id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow link not found")
    db.delete(link)
    db.commit()
