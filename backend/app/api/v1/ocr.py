from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.utils.ocr import (
    extract_text_from_image,
    extract_text_with_boxes,
    extract_text_from_pdf,
    get_supported_languages,
    get_tesseract_version
)

router = APIRouter()


# Response models
class OCRTextResponse(BaseModel):
    text: str
    language: str
    confidence: float
    word_count: int
    char_count: int
    success: bool
    error: Optional[str] = None


class OCRBoxesResponse(BaseModel):
    words: List[Dict]
    total_words: int
    image_width: int
    image_height: int
    success: bool
    error: Optional[str] = None


class PDFOCRResponse(BaseModel):
    text: str
    pages: List[Dict]
    total_pages: int
    avg_confidence: float
    success: bool
    error: Optional[str] = None


class LanguagesResponse(BaseModel):
    languages: List[str]
    count: int


class VersionResponse(BaseModel):
    tesseract_version: str
    pytesseract_installed: bool


@router.post("/ocr/image", response_model=OCRTextResponse)
async def ocr_image(
    file: UploadFile = File(...),
    lang: str = Query("eng", description="Language code (eng, fra, deu, etc.)"),
    config: str = Query("", description="Tesseract config options")
):
    """
    Extract text from an image file
    
    Supported formats: JPG, PNG, TIFF, BMP, GIF
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    try:
        # Read image data
        image_data = await file.read()
        
        # Extract text
        result = extract_text_from_image(image_data, lang=lang, config=config)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "OCR failed")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}"
        )


@router.post("/ocr/image/boxes", response_model=OCRBoxesResponse)
async def ocr_image_with_boxes(
    file: UploadFile = File(...),
    lang: str = Query("eng", description="Language code")
):
    """
    Extract text from image with bounding box coordinates
    
    Returns word-level bounding boxes for each detected text element
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    try:
        image_data = await file.read()
        result = extract_text_with_boxes(image_data, lang=lang)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "OCR failed")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}"
        )


@router.post("/ocr/pdf", response_model=PDFOCRResponse)
async def ocr_pdf(
    file: UploadFile = File(...),
    lang: str = Query("eng", description="Language code"),
    dpi: int = Query(300, description="DPI for PDF conversion", ge=72, le=600)
):
    """
    Extract text from a PDF file
    
    Converts PDF pages to images and performs OCR on each page
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        pdf_data = await file.read()
        result = extract_text_from_pdf(pdf_data, lang=lang, dpi=dpi)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "OCR failed")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )


@router.get("/ocr/languages", response_model=LanguagesResponse)
async def list_languages():
    """
    Get list of supported OCR languages
    """
    try:
        languages = get_supported_languages()
        return {
            "languages": languages,
            "count": len(languages)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting languages: {str(e)}"
        )


@router.get("/ocr/version", response_model=VersionResponse)
async def get_version():
    """
    Get Tesseract OCR version information
    """
    try:
        version = get_tesseract_version()
        return {
            "tesseract_version": str(version),
            "pytesseract_installed": True
        }
    except Exception as e:
        return {
            "tesseract_version": "Unknown",
            "pytesseract_installed": False
        }


@router.get("/ocr/health")
async def ocr_health():
    """
    Check OCR service health
    """
    try:
        version = get_tesseract_version()
        languages = get_supported_languages()
        
        return {
            "status": "healthy",
            "tesseract_version": str(version),
            "available_languages": len(languages),
            "default_language": "eng"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

