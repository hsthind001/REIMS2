from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query, Depends, Body
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
import hashlib
from app.utils.extraction_engine import MultiEngineExtractor
from app.services.model_scoring_service import ScoringFactors
from app.db.database import get_db
from app.models.extraction_log import ExtractionLog
from app.models.document_upload import DocumentUpload
from app.db.minio_client import download_file
from app.core.config import settings

router = APIRouter()

# Initialize extractor
extractor = MultiEngineExtractor()


# Response models
class ExtractionResponse(BaseModel):
    text: str
    total_pages: int
    total_words: int
    total_chars: int
    confidence_score: float
    quality_level: str
    document_type: str
    needs_review: bool
    processing_time_seconds: float
    engines_used: List[str]
    validation_summary: dict
    extraction_id: Optional[int] = None


class ComparisonResponse(BaseModel):
    primary_extraction: dict
    all_extractions: List[dict]
    consensus: dict
    validation: dict
    confidence_score: float
    quality_level: str


class QualityReportResponse(BaseModel):
    extraction_id: int
    filename: str
    confidence_score: float
    quality_level: str
    passed_checks: int
    total_checks: int
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    needs_review: bool


@router.post("/extract/analyze", response_model=ExtractionResponse)
async def analyze_pdf(
    file: UploadFile = File(...),
    strategy: str = Query("auto", description="Extraction strategy: auto, fast, accurate, multi_engine"),
    lang: str = Query("eng", description="Language for OCR"),
    store_results: bool = Query(True, description="Store extraction results in database"),
    db: Session = Depends(get_db)
):
    """
    Analyze and extract PDF with quality validation
    
    This is the primary endpoint for production-grade extraction with full validation
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        # Read PDF
        pdf_data = await file.read()
        
        # Calculate file hash
        file_hash = hashlib.sha256(pdf_data).hexdigest()
        
        # Extract with validation
        result = extractor.extract_with_validation(
            pdf_data,
            strategy=strategy,
            lang=lang
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Extraction failed")
            )
        
        extraction = result["extraction"]
        validation = result["validation"]
        classification = result["classification"]
        
        # Store in database if requested
        extraction_id = None
        if store_results:
            log_entry = ExtractionLog(
                filename=file.filename,
                file_size=len(pdf_data),
                file_hash=file_hash,
                document_type=classification.get("document_type", "unknown"),
                total_pages=extraction.get("total_pages", 0),
                strategy_used=strategy,
                engines_used=extraction.get("engines_used", [extraction.get("engine")]),
                primary_engine=extraction.get("engine", "unknown"),
                confidence_score=validation["confidence_score"],
                quality_level=validation["overall_quality"],
                passed_checks=validation["passed_checks"],
                total_checks=validation["total_checks"],
                processing_time_seconds=result["processing_time_seconds"],
                validation_issues=validation["issues"],
                validation_warnings=validation["warnings"],
                recommendations=validation.get("recommendations", []),
                text_preview=extraction.get("text", "")[:500],
                total_words=extraction.get("total_words", 0),
                total_chars=extraction.get("total_chars", 0),
                tables_found=0,  # TODO: Add table counting
                images_found=0,  # TODO: Add image counting
                needs_review=result["needs_review"],
                metadata=classification.get("characteristics", {})
            )
            
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            extraction_id = log_entry.id
        
        # Build response
        return {
            "text": extraction.get("text", ""),
            "total_pages": extraction.get("total_pages", 0),
            "total_words": extraction.get("total_words", 0),
            "total_chars": extraction.get("total_chars", 0),
            "confidence_score": validation["confidence_score"],
            "quality_level": validation["overall_quality"],
            "document_type": classification.get("document_type", "unknown"),
            "needs_review": result["needs_review"],
            "processing_time_seconds": result["processing_time_seconds"],
            "engines_used": extraction.get("engines_used", [extraction.get("engine")]),
            "validation_summary": {
                "passed_checks": validation["passed_checks"],
                "total_checks": validation["total_checks"],
                "issues": validation["issues"],
                "warnings": validation["warnings"],
                "recommendations": validation.get("recommendations", [])
            },
            "extraction_id": extraction_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing PDF: {str(e)}"
        )


@router.post("/extract/compare", response_model=ComparisonResponse)
async def compare_extractions(
    file: UploadFile = File(...),
    engines: List[str] = Query(["pymupdf", "pdfplumber"], description="Engines to compare"),
    lang: str = Query("eng", description="Language for OCR")
):
    """
    Extract with multiple engines and compare results
    
    Returns side-by-side comparison with consensus analysis
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        pdf_data = await file.read()
        
        # Extract with consensus
        result = extractor.extract_with_consensus(
            pdf_data,
            engines=engines,
            lang=lang
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Comparison failed")
            )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error comparing extractions: {str(e)}"
        )


@router.post("/extract/validate")
async def validate_extraction(
    file: UploadFile = File(...),
    strategy: str = Query("auto", description="Extraction strategy")
):
    """
    Extract and return detailed validation report
    
    Focuses on quality metrics and validation details
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        pdf_data = await file.read()
        
        result = extractor.extract_with_validation(
            pdf_data,
            strategy=strategy
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Validation failed")
            )
        
        return {
            "validation": result["validation"],
            "classification": result["classification"],
            "extraction_summary": {
                "total_pages": result["extraction"].get("total_pages", 0),
                "total_words": result["extraction"].get("total_words", 0),
                "engine": result["extraction"].get("engine", "unknown")
            },
            "quality_score": result["confidence_score"],
            "needs_review": result["needs_review"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating PDF: {str(e)}"
        )


@router.get("/extract/logs", response_model=List[QualityReportResponse])
async def get_extraction_logs(
    skip: int = 0,
    limit: int = 100,
    min_confidence: Optional[float] = Query(None, description="Minimum confidence score"),
    needs_review: Optional[bool] = Query(None, description="Filter by review status"),
    db: Session = Depends(get_db)
):
    """
    Get extraction logs with quality metrics
    
    Useful for monitoring extraction quality over time
    """
    try:
        query = db.query(ExtractionLog)
        
        if min_confidence is not None:
            query = query.filter(ExtractionLog.confidence_score >= min_confidence)
        
        if needs_review is not None:
            query = query.filter(ExtractionLog.needs_review == needs_review)
        
        logs = query.order_by(ExtractionLog.created_at.desc()).offset(skip).limit(limit).all()
        
        results = []
        for log in logs:
            results.append({
                "extraction_id": log.id,
                "filename": log.filename,
                "confidence_score": log.confidence_score,
                "quality_level": log.quality_level,
                "passed_checks": log.passed_checks,
                "total_checks": log.total_checks,
                "issues": log.validation_issues or [],
                "warnings": log.validation_warnings or [],
                "recommendations": log.recommendations or [],
                "needs_review": log.needs_review
            })
        
        return results
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving logs: {str(e)}"
        )


@router.get("/extract/stats")
async def get_extraction_stats(db: Session = Depends(get_db)):
    """
    Get aggregate extraction quality statistics
    
    Returns overall system performance metrics
    """
    try:
        from sqlalchemy import func as sql_func
        
        # Get aggregate stats
        total_extractions = db.query(sql_func.count(ExtractionLog.id)).scalar()
        
        avg_confidence = db.query(
            sql_func.avg(ExtractionLog.confidence_score)
        ).scalar() or 0
        
        needs_review_count = db.query(sql_func.count(ExtractionLog.id)).filter(
            ExtractionLog.needs_review == True
        ).scalar()
        
        # Quality distribution
        quality_dist = db.query(
            ExtractionLog.quality_level,
            sql_func.count(ExtractionLog.id)
        ).group_by(ExtractionLog.quality_level).all()
        
        # Document type distribution
        doc_type_dist = db.query(
            ExtractionLog.document_type,
            sql_func.count(ExtractionLog.id)
        ).group_by(ExtractionLog.document_type).all()
        
        return {
            "total_extractions": total_extractions,
            "average_confidence": round(avg_confidence, 2),
            "needs_review_count": needs_review_count,
            "needs_review_percentage": round((needs_review_count / total_extractions * 100), 2) if total_extractions > 0 else 0,
            "quality_distribution": {level: count for level, count in quality_dist},
            "document_type_distribution": {dtype: count for dtype, count in doc_type_dist},
            "success": True
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stats: {str(e)}"
        )


class ModelScoreResult(BaseModel):
    """Individual model extraction result with score"""
    model: str
    score: float
    confidence: float
    success: bool
    text_length: int
    processing_time_ms: float
    page_count: Optional[int] = None
    text_quality_score: Optional[float] = None
    score_breakdown: Optional[Dict[str, float]] = None
    error: Optional[str] = None


class AllModelsScoredResponse(BaseModel):
    """Response for all models extraction with scores"""
    success: bool
    results: List[ModelScoreResult]
    best_model: Optional[str]
    best_score: float
    total_models: int
    successful_models: int
    average_score: float
    scoring_factors_used: Optional[Dict] = None


class ScoringFactorsRequest(BaseModel):
    """Client-defined scoring factors"""
    text_length_weight: Optional[float] = 0.20
    text_quality_weight: Optional[float] = 0.25
    table_detection_weight: Optional[float] = 0.15
    table_structure_weight: Optional[float] = 0.10
    processing_speed_weight: Optional[float] = 0.10
    accuracy_weight: Optional[float] = 0.15
    model_type_bonus: Optional[Dict[str, float]] = None
    min_text_length: Optional[int] = 100
    max_processing_time_ms: Optional[float] = 10000.0


@router.post("/extract/all-models-scored", response_model=AllModelsScoredResponse)
async def extract_all_models_scored(
    file: UploadFile = File(...),
    lang: str = Query("eng", description="Language for OCR"),
    scoring_factors: Optional[ScoringFactorsRequest] = Body(None, description="Custom scoring factors (optional)")
):
    """
    Extract using ALL available models and return scores (1-10) for each.
    
    **IMPORTANT:** Models do NOT calculate their own confidence. Scores are calculated
    externally based on client-defined factors.
    
    **Models Tested:**
    - PyMuPDF (rule-based)
    - PDFPlumber (rule-based)
    - Camelot (table extraction)
    - Tesseract OCR (OCR)
    - LayoutLMv3 (AI model)
    - EasyOCR (AI model)
    
    **Scoring (Client-Defined Factors):**
    - Text length weight (default: 0.20)
    - Text quality weight (default: 0.25)
    - Table detection weight (default: 0.15)
    - Table structure weight (default: 0.10)
    - Processing speed weight (default: 0.10)
    - Accuracy weight (default: 0.15)
    - Model type bonuses (optional)
    
    **Custom Scoring Factors:**
    Pass `scoring_factors` in request body to customize weights:
    ```json
    {
      "text_length_weight": 0.30,
      "text_quality_weight": 0.30,
      "table_detection_weight": 0.20,
      "processing_speed_weight": 0.20
    }
    ```
    
    **Score Calculation:**
    - Each factor contributes to final score (0.0-1.0)
    - Converted to 1-10 scale: score = 1 + (confidence * 9)
    - Higher score = better extraction quality based on YOUR criteria
    
    **Use Cases:**
    - Compare model performance on specific documents
    - Identify which model works best for your document types
    - Debug extraction issues by seeing all model outputs
    - Performance benchmarking
    
    Returns:
        AllModelsScoredResponse with scored results from all models
    """
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        # Read PDF
        pdf_data = await file.read()
        
        # Create scoring factors from request (or use defaults)
        factors = None
        if scoring_factors:
            factors = ScoringFactors(
                text_length_weight=scoring_factors.text_length_weight or 0.20,
                text_quality_weight=scoring_factors.text_quality_weight or 0.25,
                table_detection_weight=scoring_factors.table_detection_weight or 0.15,
                table_structure_weight=scoring_factors.table_structure_weight or 0.10,
                processing_speed_weight=scoring_factors.processing_speed_weight or 0.10,
                accuracy_weight=scoring_factors.accuracy_weight or 0.15,
                model_type_bonus=scoring_factors.model_type_bonus or {},
                min_text_length=scoring_factors.min_text_length or 100,
                max_processing_time_ms=scoring_factors.max_processing_time_ms or 10000.0
            )
        
        # Create extractor instance with custom scoring factors
        extractor = MultiEngineExtractor(scoring_factors=factors)
        
        # Extract with all models and get scores (scored externally, not by models)
        results = extractor.extract_with_all_models_scored(pdf_data, lang=lang)
        
        # Convert results to response model format
        model_results = []
        for r in results["results"]:
            model_results.append(ModelScoreResult(
                model=r["model"],
                score=r["score"],
                confidence=r["confidence"],
                success=r["success"],
                text_length=r["text_length"],
                processing_time_ms=r["processing_time_ms"],
                page_count=r.get("page_count"),
                text_quality_score=r.get("text_quality_score"),
                score_breakdown=r.get("score_breakdown"),
                error=r.get("error")
            ))
        
        # Get scoring factors used
        scoring_factors_used = extractor.scoring_service.factors.__dict__
        
        return AllModelsScoredResponse(
            success=True,
            results=model_results,
            best_model=results["best_model"],
            best_score=results["best_score"],
            total_models=results["total_models"],
            successful_models=results["successful_models"],
            average_score=results["average_score"],
            scoring_factors_used=scoring_factors_used
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting with all models: {str(e)}"
        )


@router.post("/extract/all-models-scored/{upload_id}", response_model=AllModelsScoredResponse)
async def rescore_existing_extraction(
    upload_id: int,
    lang: str = Query("eng", description="Language for OCR"),
    scoring_factors: Optional[ScoringFactorsRequest] = Body(None, description="Custom scoring factors (optional)"),
    db: Session = Depends(get_db)
):
    """
    Re-score an EXISTING extraction using all models (1-10 scale).
    
    This endpoint retrieves a previously uploaded PDF from storage and runs
    all extraction models on it, returning scored results for comparison.
    
    **Use Cases:**
    - Compare how different models perform on documents already in the system
    - Re-evaluate extraction quality after model updates
    - Benchmark model performance on historical documents
    - Debug extraction issues by seeing all model outputs
    
    **Parameters:**
    - `upload_id`: ID of the DocumentUpload record (from document_uploads table)
    - `lang`: Language code for OCR engines (default: "eng")
    
    **Returns:**
    - Scored results from all models (1-10 scale)
    - Best performing model identification
    - Performance metrics for each model
    
    **Note:** This retrieves the PDF from MinIO storage, so the file must exist.
    """
    try:
        # Get upload record
        upload = db.query(DocumentUpload).filter(
            DocumentUpload.id == upload_id
        ).first()
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        if not upload.file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload {upload_id} has no file path - PDF may not be stored"
            )
        
        # Download PDF from MinIO
        pdf_data = download_file(
            object_name=upload.file_path,
            bucket_name=settings.MINIO_BUCKET_NAME
        )
        
        if not pdf_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF file not found in storage: {upload.file_path}"
            )
        
        # Create scoring factors from request (or use defaults)
        factors = None
        if scoring_factors:
            factors = ScoringFactors(
                text_length_weight=scoring_factors.text_length_weight or 0.20,
                text_quality_weight=scoring_factors.text_quality_weight or 0.25,
                table_detection_weight=scoring_factors.table_detection_weight or 0.15,
                table_structure_weight=scoring_factors.table_structure_weight or 0.10,
                processing_speed_weight=scoring_factors.processing_speed_weight or 0.10,
                accuracy_weight=scoring_factors.accuracy_weight or 0.15,
                model_type_bonus=scoring_factors.model_type_bonus or {},
                min_text_length=scoring_factors.min_text_length or 100,
                max_processing_time_ms=scoring_factors.max_processing_time_ms or 10000.0
            )
        
        # Create extractor instance with custom scoring factors
        extractor = MultiEngineExtractor(scoring_factors=factors)
        
        # Extract with all models and get scores (scored externally, not by models)
        results = extractor.extract_with_all_models_scored(pdf_data, lang=lang)
        
        # Convert results to response model format
        model_results = []
        for r in results["results"]:
            model_results.append(ModelScoreResult(
                model=r["model"],
                score=r["score"],
                confidence=r["confidence"],
                success=r["success"],
                text_length=r["text_length"],
                processing_time_ms=r["processing_time_ms"],
                page_count=r.get("page_count"),
                text_quality_score=r.get("text_quality_score"),
                score_breakdown=r.get("score_breakdown"),
                error=r.get("error")
            ))
        
        # Get scoring factors used
        scoring_factors_used = extractor.scoring_service.factors.__dict__
        
        return AllModelsScoredResponse(
            success=True,
            results=model_results,
            best_model=results["best_model"],
            best_score=results["best_score"],
            total_models=results["total_models"],
            successful_models=results["successful_models"],
            average_score=results["average_score"],
            scoring_factors_used=scoring_factors_used
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error re-scoring extraction: {str(e)}"
        )

