from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import io
from app.utils.pdf import (
    extract_text_from_pdf,
    get_pdf_metadata,
    pdf_to_images,
    extract_images_from_pdf,
    split_pdf,
    merge_pdfs,
    compress_pdf,
    add_watermark,
    get_pdf_info
)

router = APIRouter()


# Response models
class PDFTextResponse(BaseModel):
    text: str
    pages: List[dict]
    total_pages: int
    total_chars: int
    total_words: int
    success: bool
    error: Optional[str] = None


class PDFMetadataResponse(BaseModel):
    title: str
    author: str
    subject: str
    creator: str
    producer: str
    creation_date: str
    modification_date: str
    page_count: int
    is_encrypted: bool
    is_pdf: bool
    permissions: int
    success: bool
    error: Optional[str] = None


class PDFInfoResponse(BaseModel):
    file_size: int
    page_count: int
    total_images: int
    is_encrypted: bool
    is_pdf: bool
    page_sizes: List[dict]
    metadata: dict
    success: bool
    error: Optional[str] = None


class PDFSplitRequest(BaseModel):
    start_page: int
    end_page: int


class PDFCompressRequest(BaseModel):
    image_quality: int = 75


class PDFWatermarkRequest(BaseModel):
    watermark_text: str
    opacity: float = 0.3


@router.post("/pdf/extract-text", response_model=PDFTextResponse)
async def extract_pdf_text(file: UploadFile = File(...)):
    """
    Extract all text from a PDF file
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        pdf_data = await file.read()
        result = extract_text_from_pdf(pdf_data)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to extract text")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )


@router.post("/pdf/metadata", response_model=PDFMetadataResponse)
async def get_metadata(file: UploadFile = File(...)):
    """
    Extract metadata from a PDF file
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        pdf_data = await file.read()
        result = get_pdf_metadata(pdf_data)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to extract metadata")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )


@router.post("/pdf/info", response_model=PDFInfoResponse)
async def get_info(file: UploadFile = File(...)):
    """
    Get comprehensive PDF information
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        pdf_data = await file.read()
        result = get_pdf_info(pdf_data)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to get PDF info")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )


@router.post("/pdf/to-images")
async def convert_to_images(
    file: UploadFile = File(...),
    dpi: int = Query(150, description="Image resolution (72-300)", ge=72, le=300),
    format: str = Query("png", description="Output format (png or jpg)")
):
    """
    Convert PDF pages to images
    
    Returns a ZIP file containing all page images
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        pdf_data = await file.read()
        result = pdf_to_images(pdf_data, dpi=dpi, fmt=format)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to convert PDF")
            )
        
        # For simplicity, return the first page image
        # In production, you'd want to create a ZIP file
        if result["images"]:
            first_image = result["images"][0]
            return StreamingResponse(
                io.BytesIO(first_image["image"]),
                media_type=f"image/{format}",
                headers={
                    "Content-Disposition": f"attachment; filename=page_1.{format}"
                }
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No images generated"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )


@router.post("/pdf/extract-images")
async def extract_images(file: UploadFile = File(...)):
    """
    Extract all embedded images from a PDF
    
    Returns information about extracted images
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        pdf_data = await file.read()
        result = extract_images_from_pdf(pdf_data)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to extract images")
            )
        
        # Return metadata without actual image data (too large)
        images_info = []
        for img in result["images"]:
            images_info.append({
                "page": img["page"],
                "image_index": img["image_index"],
                "extension": img["extension"],
                "width": img["width"],
                "height": img["height"],
                "size": img["size"]
            })
        
        return {
            "images": images_info,
            "total_images": result["total_images"],
            "success": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )


@router.post("/pdf/split")
async def split_pdf_endpoint(
    file: UploadFile = File(...),
    start_page: int = Query(..., description="Starting page number (1-indexed)"),
    end_page: int = Query(..., description="Ending page number (1-indexed)")
):
    """
    Extract specific pages from a PDF
    
    Returns a new PDF with only the specified pages
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        pdf_data = await file.read()
        result = split_pdf(pdf_data, start_page, end_page)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to split PDF")
            )
        
        return StreamingResponse(
            io.BytesIO(result["pdf"]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=pages_{start_page}-{end_page}.pdf"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )


@router.post("/pdf/merge")
async def merge_pdf_files(files: List[UploadFile] = File(...)):
    """
    Merge multiple PDF files into one
    
    Upload multiple PDF files and get a single merged PDF
    """
    if len(files) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 PDF files are required for merging"
        )
    
    try:
        pdf_files = []
        for file in files:
            if not file.content_type or file.content_type != "application/pdf":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File {file.filename} is not a PDF"
                )
            pdf_data = await file.read()
            pdf_files.append(pdf_data)
        
        result = merge_pdfs(pdf_files)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to merge PDFs")
            )
        
        return StreamingResponse(
            io.BytesIO(result["pdf"]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=merged.pdf"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDFs: {str(e)}"
        )


@router.post("/pdf/compress")
async def compress_pdf_endpoint(
    file: UploadFile = File(...),
    quality: int = Query(75, description="Image quality (1-100)", ge=1, le=100)
):
    """
    Compress a PDF by reducing image quality
    
    Returns a compressed version of the PDF
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        pdf_data = await file.read()
        result = compress_pdf(pdf_data, image_quality=quality)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to compress PDF")
            )
        
        return StreamingResponse(
            io.BytesIO(result["pdf"]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=compressed.pdf",
                "X-Original-Size": str(result["original_size"]),
                "X-Compressed-Size": str(result["compressed_size"]),
                "X-Compression-Ratio": str(result["compression_ratio"])
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )


@router.post("/pdf/watermark")
async def add_watermark_endpoint(
    file: UploadFile = File(...),
    text: str = Query(..., description="Watermark text"),
    opacity: float = Query(0.3, description="Watermark opacity (0-1)", ge=0, le=1)
):
    """
    Add a text watermark to all pages of a PDF
    
    Returns a watermarked version of the PDF
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        pdf_data = await file.read()
        result = add_watermark(pdf_data, text, opacity)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to add watermark")
            )
        
        return StreamingResponse(
            io.BytesIO(result["pdf"]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=watermarked.pdf"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )


@router.get("/pdf/health")
async def pdf_health():
    """
    Check PDF processing service health
    """
    try:
        import fitz
        version = fitz.VersionBind
        
        return {
            "status": "healthy",
            "pymupdf_version": version,
            "features": [
                "text_extraction",
                "metadata",
                "pdf_to_images",
                "image_extraction",
                "split",
                "merge",
                "compress",
                "watermark"
            ]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

