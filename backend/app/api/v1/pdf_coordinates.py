"""
PDF Coordinate Prediction API

Endpoints for ML-based PDF field coordinate prediction and highlighting.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.services.pdf_field_locator import PDFFieldLocator
from app.services.layoutlm_coordinator import LayoutLMCoordinator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdf-coordinates", tags=["PDF Coordinates"])


# Request/Response Models
class FieldCoordinates(BaseModel):
    """Field coordinate information."""
    x: float
    y: float
    width: float
    height: float
    page: int
    confidence: float
    method: str


class LocateFieldRequest(BaseModel):
    """Request to locate a field in PDF."""
    pdf_path: str = Field(..., description="Path to PDF file")
    field_name: str = Field(..., description="Name of field to locate")
    page_number: Optional[int] = Field(None, description="Specific page number (1-indexed)")
    use_cache: bool = Field(True, description="Use cached coordinates if available")


class LocateFieldResponse(BaseModel):
    """Response with field coordinates."""
    field_name: str
    located: bool
    coordinates: Optional[FieldCoordinates] = None
    message: Optional[str] = None


class LocateMultipleFieldsRequest(BaseModel):
    """Request to locate multiple fields."""
    pdf_path: str
    field_names: List[str] = Field(..., description="List of field names to locate")
    page_number: Optional[int] = None


class HighlightAnomalyRequest(BaseModel):
    """Request to highlight an anomalous field."""
    pdf_path: str
    field_name: str
    anomaly_value: float
    expected_value: Optional[float] = None
    page_number: Optional[int] = None


class HighlightInfo(BaseModel):
    """Anomaly highlighting information."""
    field_name: str
    located: bool
    page: Optional[int] = None
    coordinates: Optional[FieldCoordinates] = None
    anomaly_value: float
    expected_value: Optional[float] = None
    highlight_color: Optional[str] = None
    error: Optional[str] = None


# Endpoints

@router.post("/locate-field", response_model=LocateFieldResponse)
async def locate_field(
    request: LocateFieldRequest,
    db: Session = Depends(get_db)
):
    """
    Locate a field in a PDF document using ML-based coordinate prediction.

    Uses LayoutLM for intelligent field localization with fallback to OCR-based search.
    Results are cached for faster subsequent requests.
    """
    try:
        locator = PDFFieldLocator(db)

        coordinates = locator.locate_field(
            pdf_path=request.pdf_path,
            field_name=request.field_name,
            page_number=request.page_number,
            use_cache=request.use_cache
        )

        if coordinates:
            return LocateFieldResponse(
                field_name=request.field_name,
                located=True,
                coordinates=FieldCoordinates(**coordinates)
            )
        else:
            return LocateFieldResponse(
                field_name=request.field_name,
                located=False,
                message=f"Field '{request.field_name}' not found in PDF"
            )

    except Exception as e:
        logger.error(f"Error locating field: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/locate-multiple-fields")
async def locate_multiple_fields(
    request: LocateMultipleFieldsRequest,
    db: Session = Depends(get_db)
):
    """
    Locate multiple fields in a PDF document.

    Efficiently locates multiple fields in parallel, with caching support.
    """
    try:
        locator = PDFFieldLocator(db)

        results = locator.locate_multiple_fields(
            pdf_path=request.pdf_path,
            field_names=request.field_names,
            page_number=request.page_number
        )

        response = {}
        for field_name, coordinates in results.items():
            if coordinates:
                response[field_name] = {
                    'located': True,
                    'coordinates': FieldCoordinates(**coordinates).dict()
                }
            else:
                response[field_name] = {
                    'located': False,
                    'message': f"Field '{field_name}' not found"
                }

        return response

    except Exception as e:
        logger.error(f"Error locating multiple fields: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/highlight-anomaly", response_model=HighlightInfo)
async def highlight_anomaly_field(
    request: HighlightAnomalyRequest,
    db: Session = Depends(get_db)
):
    """
    Locate and prepare highlighting information for an anomalous field.

    Returns coordinates and color coding based on anomaly severity.
    Color codes:
    - Red (#FF0000): Critical (≥50% deviation)
    - Orange (#FFA500): Medium (10-25% deviation)
    - Yellow (#FFFF00): Low (<10% deviation)
    """
    try:
        locator = PDFFieldLocator(db)

        highlight_info = locator.highlight_anomaly_field(
            pdf_path=request.pdf_path,
            field_name=request.field_name,
            anomaly_value=request.anomaly_value,
            expected_value=request.expected_value,
            page_number=request.page_number
        )

        # Convert to response model
        if highlight_info.get('located'):
            coords = highlight_info['coordinates']
            return HighlightInfo(
                field_name=highlight_info['field_name'],
                located=True,
                page=highlight_info['page'],
                coordinates=FieldCoordinates(
                    x=coords['x'],
                    y=coords['y'],
                    width=coords['width'],
                    height=coords['height'],
                    page=highlight_info['page'],
                    confidence=highlight_info['confidence'],
                    method=highlight_info['method']
                ),
                anomaly_value=highlight_info['anomaly_value'],
                expected_value=highlight_info.get('expected_value'),
                highlight_color=highlight_info['highlight_color']
            )
        else:
            return HighlightInfo(
                field_name=highlight_info['field_name'],
                located=False,
                anomaly_value=request.anomaly_value,
                expected_value=request.expected_value,
                error=highlight_info.get('error', 'Field not found')
            )

    except Exception as e:
        logger.error(f"Error highlighting anomaly: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/page-dimensions")
async def get_pdf_page_dimensions(
    pdf_path: str = Query(..., description="Path to PDF file"),
    page_number: int = Query(1, description="Page number (1-indexed)"),
    db: Session = Depends(get_db)
):
    """
    Get dimensions of a PDF page.

    Useful for calculating relative positions for highlights.
    """
    try:
        locator = PDFFieldLocator(db)

        dimensions = locator.get_pdf_page_dimensions(pdf_path, page_number)

        return dimensions

    except Exception as e:
        logger.error(f"Error getting page dimensions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cached-coordinates")
async def get_cached_coordinates(
    pdf_path: str = Query(..., description="Path to PDF file"),
    field_name: str = Query(..., description="Field name"),
    page_number: int = Query(..., description="Page number"),
    db: Session = Depends(get_db)
):
    """
    Retrieve cached field coordinates.

    Returns cached coordinates if available, None otherwise.
    """
    try:
        coordinator = LayoutLMCoordinator(db)

        coordinates = coordinator.get_cached_coordinates(
            pdf_path=pdf_path,
            field_name=field_name,
            page_number=page_number
        )

        if coordinates:
            coordinates['page'] = page_number
            return {
                'cached': True,
                'coordinates': FieldCoordinates(**coordinates).dict()
            }
        else:
            return {
                'cached': False,
                'message': 'No cached coordinates found'
            }

    except Exception as e:
        logger.error(f"Error retrieving cached coordinates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-field-value")
async def extract_field_value(
    pdf_path: str = Body(..., embed=True),
    field_name: str = Body(..., embed=True),
    page_number: Optional[int] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """
    Extract the value of a field from PDF.

    Locates the field and extracts the text value near it.
    """
    try:
        locator = PDFFieldLocator(db)

        value = locator.extract_field_value(
            pdf_path=pdf_path,
            field_name=field_name,
            page_number=page_number
        )

        if value:
            return {
                'extracted': True,
                'field_name': field_name,
                'value': value
            }
        else:
            return {
                'extracted': False,
                'field_name': field_name,
                'message': 'Could not extract value'
            }

    except Exception as e:
        logger.error(f"Error extracting field value: {e}")
        raise HTTPException(status_code=500, detail=str(e))
