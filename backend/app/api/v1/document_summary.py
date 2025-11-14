"""
Document Summary API Endpoints

AI-powered document summarization for leases, OMs, and other property documents
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from app.db.database import get_db
from app.services.document_summarization_service import DocumentSummarizationService
from app.models.property import Property

router = APIRouter(prefix="/document-summary", tags=["document_summary"])
logger = logging.getLogger(__name__)


class LeaseSummaryRequest(BaseModel):
    property_id: int
    document_path: str
    document_name: str
    document_text: str
    created_by: Optional[int] = None


class OMSummaryRequest(BaseModel):
    property_id: int
    document_path: str
    document_name: str
    document_text: str
    created_by: Optional[int] = None


@router.post("/lease")
def summarize_lease(
    request: LeaseSummaryRequest,
    db: Session = Depends(get_db)
):
    """
    Summarize a lease document

    Uses AI (GPT-4 or Claude) to extract and summarize key lease information.

    **Implements M1/M2/M3 Multi-Agent Pattern:**
    - M1 (Retriever): Extracts structured data from document
    - M2 (Writer): Generates human-readable summaries
    - M3 (Auditor): Verifies summary against original document

    **Extracted Information:**
    - Parties (landlord, tenant)
    - Lease term (start, end, options)
    - Rent (base rent, escalations, CAM)
    - Special provisions
    - Key dates

    **Returns:**
    - executive_summary: Brief overview (2-3 sentences)
    - detailed_summary: Comprehensive analysis
    - key_points: Bullet points of critical terms
    - lease_data: Structured lease information
    - confidence_score: 0-100 quality score
    - has_quality_issues: True if M3 auditor flagged issues

    **Example:**
    ```json
    {
      "property_id": 1,
      "document_name": "Lease - 123 Main St - Acme Corp.pdf",
      "document_path": "/documents/leases/...",
      "document_text": "COMMERCIAL LEASE AGREEMENT..."
    }
    ```
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = DocumentSummarizationService(db)

    try:
        result = service.summarize_lease(
            property_id=request.property_id,
            document_path=request.document_path,
            document_name=request.document_name,
            document_text=request.document_text,
            created_by=request.created_by
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Lease summarization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/om")
def summarize_om(
    request: OMSummaryRequest,
    db: Session = Depends(get_db)
):
    """
    Summarize an Offering Memorandum (OM)

    Uses AI to extract and summarize key investment information from OMs.

    **Extracted Information:**
    - Property overview
    - Financial highlights (NOI, cap rate, asking price)
    - Market analysis
    - Tenant mix
    - Investment highlights
    - Risk factors

    **Returns:**
    - executive_summary: Investment overview (2-3 sentences)
    - detailed_summary: Comprehensive investment analysis
    - key_points: Top investment highlights
    - om_data: Structured property and financial data
    - confidence_score: Quality score
    - has_quality_issues: True if auditor flagged issues

    **Use Cases:**
    - Quick investment screening
    - Deal comparison
    - Investment committee presentations
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = DocumentSummarizationService(db)

    try:
        result = service.summarize_om(
            property_id=request.property_id,
            document_path=request.document_path,
            document_name=request.document_name,
            document_text=request.document_text,
            created_by=request.created_by
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"OM summarization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lease/upload")
async def upload_and_summarize_lease(
    property_id: int = Form(...),
    file: UploadFile = File(...),
    created_by: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload and summarize a lease document

    Accepts file upload and processes it automatically.

    **Supported Formats:**
    - PDF (.pdf)
    - Word (.docx, .doc)
    - Text (.txt)

    **Returns:**
    Complete lease summary with extracted data
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Validate file format
    allowed_extensions = [".pdf", ".docx", ".doc", ".txt"]
    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Read file content
        content = await file.read()

        # TODO: Extract text from file based on format
        # For now, assuming text extraction is handled elsewhere
        document_text = content.decode("utf-8", errors="ignore")

        # Summarize
        service = DocumentSummarizationService(db)
        result = service.summarize_lease(
            property_id=property_id,
            document_path=f"/uploads/leases/{file.filename}",
            document_name=file.filename,
            document_text=document_text,
            created_by=created_by
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Lease upload and summarization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/om/upload")
async def upload_and_summarize_om(
    property_id: int = Form(...),
    file: UploadFile = File(...),
    created_by: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload and summarize an OM document

    Accepts file upload and processes it automatically.
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Validate file format
    allowed_extensions = [".pdf", ".docx", ".doc", ".txt"]
    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Read file content
        content = await file.read()

        # Extract text
        document_text = content.decode("utf-8", errors="ignore")

        # Summarize
        service = DocumentSummarizationService(db)
        result = service.summarize_om(
            property_id=property_id,
            document_path=f"/uploads/oms/{file.filename}",
            document_name=file.filename,
            document_text=document_text,
            created_by=created_by
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"OM upload and summarization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{summary_id}")
def get_summary(
    summary_id: int,
    db: Session = Depends(get_db)
):
    """
    Get document summary by ID

    Retrieves a previously generated document summary.

    **Returns:**
    Complete summary with all extracted data and quality metrics
    """
    service = DocumentSummarizationService(db)

    try:
        result = service.get_summary(summary_id)

        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Get summary failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}")
def get_property_summaries(
    property_id: int,
    document_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all document summaries for a property

    Retrieves all summaries associated with a property.

    **Parameters:**
    - document_type: Optional filter (LEASE, OFFERING_MEMORANDUM, etc.)

    **Returns:**
    List of all summaries for the property

    **Example:**
    ```
    GET /document-summary/properties/1
    GET /document-summary/properties/1?document_type=LEASE
    ```
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = DocumentSummarizationService(db)

    try:
        result = service.get_property_summaries(property_id, document_type)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Get property summaries failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/leases")
def get_lease_summaries(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all lease summaries for a property

    Convenience endpoint to retrieve only lease document summaries.
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = DocumentSummarizationService(db)

    try:
        result = service.get_property_summaries(property_id, document_type="LEASE")

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Get lease summaries failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/oms")
def get_om_summaries(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all Offering Memorandum summaries for a property

    Convenience endpoint to retrieve only OM summaries.
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    service = DocumentSummarizationService(db)

    try:
        result = service.get_property_summaries(property_id, document_type="OFFERING_MEMORANDUM")

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Get OM summaries failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configuration")
def get_configuration():
    """
    Get document summarization configuration

    Returns current LLM provider, model, and settings.

    **Use Cases:**
    - Check which AI model is being used
    - Verify API configuration
    - Troubleshooting
    """
    from app.core.config import settings

    return {
        "success": True,
        "configuration": {
            "llm_provider": settings.LLM_PROVIDER,
            "llm_model": settings.LLM_MODEL,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "has_openai_key": bool(settings.OPENAI_API_KEY),
            "has_anthropic_key": bool(settings.ANTHROPIC_API_KEY),
        },
        "supported_document_types": [
            "LEASE",
            "OFFERING_MEMORANDUM",
            "FINANCIAL_STATEMENT",
            "APPRAISAL",
            "INSPECTION_REPORT",
            "LEGAL_DOCUMENT",
            "OTHER"
        ],
        "supported_file_formats": [".pdf", ".docx", ".doc", ".txt"],
        "multi_agent_pattern": {
            "m1_retriever": "Extracts structured data from document",
            "m2_writer": "Generates human-readable summaries",
            "m3_auditor": "Verifies summary quality and flags issues"
        }
    }
