"""
PDF Viewer API - Endpoints for PDF viewing with highlighting support
"""
from fastapi import APIRouter, HTTPException, status, Query, Path, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import io

from app.db.database import get_db
from app.db.minio_client import get_file_url, download_file
from app.api.dependencies import get_current_user_hybrid, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.repositories.tenant_scoped import get_upload_for_org


router = APIRouter()


class PDFViewerResponse(BaseModel):
    """PDF viewer data with highlight information"""
    upload_id: int
    file_name: str
    pdf_url: str
    page_number: Optional[int] = None
    highlight_coords: Optional[dict] = None
    has_highlight: bool = False


@router.get("/pdf-viewer/{upload_id}/stream")
async def stream_pdf(
    upload_id: int = Path(..., description="Document upload ID"),
    page: Optional[int] = Query(None, description="Page number to highlight (1-indexed)"),
    x0: Optional[float] = Query(None, description="X0 coordinate for highlight"),
    y0: Optional[float] = Query(None, description="Y0 coordinate for highlight"),
    x1: Optional[float] = Query(None, description="X1 coordinate for highlight"),
    y1: Optional[float] = Query(None, description="Y1 coordinate for highlight"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Stream PDF file directly through backend to avoid CORS issues
    
    Optionally adds a red circle annotation at specified coordinates.
    This works even in iframe viewers since the annotation is embedded in the PDF.
    
    Query params (all optional):
    - page: Page number (1-indexed)
    - x0, y0, x1, y1: Bounding box coordinates for highlighting
    """
    try:
        upload = get_upload_for_org(db, current_org.id, upload_id)
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document upload {upload_id} not found"
            )

        # Download PDF from MinIO
        try:
            pdf_data = download_file(upload.file_path)
        except Exception as e:
            print(f"Error downloading PDF from MinIO: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF file not found in storage: {upload.file_path}. Error: {str(e)}"
            )
        
        if not pdf_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF file not found in storage: {upload.file_path}"
            )
        
        # If coordinates are provided, add red circle annotation to PDF
        if page is not None and x0 is not None and y0 is not None and x1 is not None and y1 is not None:
            try:
                import fitz  # PyMuPDF
                
                # Open PDF from bytes
                doc = fitz.open(stream=io.BytesIO(pdf_data), filetype="pdf")
                page_idx = page - 1
                
                if 0 <= page_idx < len(doc):
                    pdf_page = doc[page_idx]
                    
                    # Calculate center and radius for circle
                    center_x = (x0 + x1) / 2
                    center_y = (y0 + y1) / 2
                    radius = max((x1 - x0) / 2, (y1 - y0) / 2) + 5  # Add 5pt padding
                    
                    # Create red circle annotation
                    circle_rect = fitz.Rect(
                        center_x - radius,
                        center_y - radius,
                        center_x + radius,
                        center_y + radius
                    )
                    
                    # Add circle annotation with red border
                    annot = pdf_page.add_circle_annot(circle_rect)
                    annot.set_border(width=3.0)  # 3pt border
                    annot.set_colors(stroke=(1, 0, 0))  # Red color (RGB)
                    annot.update()
                    
                    # Convert back to bytes
                    pdf_data = doc.tobytes()
                    doc.close()
                    
                    print(f"✅ Added red circle annotation at page {page}, center=({center_x:.2f}, {center_y:.2f}), radius={radius:.2f}")
                else:
                    doc.close()
            except Exception as e:
                import traceback
                print(f"⚠️ Warning: Could not add annotation to PDF: {e}")
                print(traceback.format_exc())
                # Continue with original PDF if annotation fails
        
        # Stream the PDF with CORS headers
        return StreamingResponse(
            io.BytesIO(pdf_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{upload.file_name}"',
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(len(pdf_data)),
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Accept-Ranges": "bytes"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stream PDF: {str(e)}"
        )


@router.get("/pdf-viewer/{upload_id}", response_model=PDFViewerResponse)
async def get_pdf_viewer_data(
    upload_id: int = Path(..., description="Document upload ID"),
    highlight_page: Optional[int] = Query(None, description="Page number to highlight"),
    highlight_x0: Optional[float] = Query(None, description="Left coordinate for highlight"),
    highlight_y0: Optional[float] = Query(None, description="Top coordinate for highlight"),
    highlight_x1: Optional[float] = Query(None, description="Right coordinate for highlight"),
    highlight_y1: Optional[float] = Query(None, description="Bottom coordinate for highlight"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get PDF viewer data with optional highlight coordinates
    
    Returns a backend-proxied URL and highlight information for PDF viewing.
    Uses the /stream endpoint to avoid CORS issues.
    
    Query params (all optional):
    - highlight_page: Page number where highlight should appear
    - highlight_x0, highlight_y0, highlight_x1, highlight_y1: Bounding box coordinates
    
    Returns:
    - pdf_url: Backend-proxied URL to access the PDF (no CORS issues)
    - highlight_coords: Coordinates for highlighting (if provided)
    - has_highlight: Whether highlight coordinates are available
    """
    try:
        upload = get_upload_for_org(db, current_org.id, upload_id)
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document upload {upload_id} not found"
            )

        # Use backend-proxied URL instead of presigned URL to avoid CORS issues
        from app.core.config import settings
        import os
        from fastapi import Request
        
        # Get the request to determine the base URL
        # For localhost development, use localhost:8000
        # In production, this would be the actual domain
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        pdf_url = f"{backend_url}{settings.API_V1_STR}/pdf-viewer/{upload_id}/stream"
        
        # Build highlight coordinates if provided
        highlight_coords = None
        has_highlight = False
        
        if highlight_page and highlight_x0 is not None and highlight_y0 is not None and highlight_x1 is not None and highlight_y1 is not None:
            highlight_coords = {
                "page": highlight_page,
                "x0": highlight_x0,
                "y0": highlight_y0,
                "x1": highlight_x1,
                "y1": highlight_y1
            }
            has_highlight = True
        
        return PDFViewerResponse(
            upload_id=upload.id,
            file_name=upload.file_name,
            pdf_url=pdf_url,
            page_number=highlight_page,
            highlight_coords=highlight_coords,
            has_highlight=has_highlight
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get PDF viewer data: {str(e)}"
        )

