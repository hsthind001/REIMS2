
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import dependencies
from app.services.document_intelligence_service import DocumentIntelligenceService

router = APIRouter()

@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_document(
    file_path: str,
    document_type: str = "general",
    db: Session = Depends(dependencies.get_db),
    current_user: Any = Depends(dependencies.get_current_active_user),
) -> Dict[str, Any]:
    """
    Analyze a document using advanced AI/ML models (LayoutLMv3/EasyOCR).
    
    - **file_path**: Absolute path to the file on the server (simulating internal processing loop)
    - **document_type**: Type of document (general, invoice, rent_roll)
    """
    service = DocumentIntelligenceService(db)
    try:
        result = service.analyze_document(file_path, document_type)
        if result.get("status") == "failed":
             raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
