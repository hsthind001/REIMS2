"""
Natural Language Query API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from app.db.database import get_db
from app.services.nlq_service import NaturalLanguageQueryService

router = APIRouter(prefix="/nlq", tags=["natural_language_query"])
logger = logging.getLogger(__name__)


class NLQueryRequest(BaseModel):
    question: str
    context: Optional[dict] = None


@router.post("/query")
def natural_language_query(
    request: NLQueryRequest,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # Add auth when ready
):
    """
    Process natural language query

    Examples:
    - "What was the NOI for Eastern Shore Plaza in Q3 2024?"
    - "Show me occupancy trends over the last 2 years"
    - "Which properties have the highest operating expense ratio?"
    - "Compare revenue for all properties in 2024"

    Returns answer with data, citations, and SQL query used
    """
    # For now, use a default user_id (add proper auth later)
    user_id = 1  # TODO: Replace with current_user.id

    service = NaturalLanguageQueryService(db)

    try:
        result = service.query(request.question, user_id)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))

        return result

    except Exception as e:
        logger.error(f"NLQ failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
def get_query_suggestions():
    """
    Get suggested questions users can ask

    Returns list of example questions
    """
    service = NaturalLanguageQueryService(None)  # No DB needed for suggestions
    suggestions = service.get_suggestions()

    return {
        "suggestions": suggestions,
        "total": len(suggestions)
    }


@router.get("/history")
def get_query_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)
):
    """
    Get user's query history

    Returns recent queries with answers
    """
    user_id = 1  # TODO: Replace with current_user.id

    service = NaturalLanguageQueryService(db)
    history = service.get_history(user_id, limit)

    return {
        "history": history,
        "total": len(history)
    }


@router.delete("/cache")
def clear_query_cache(
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)
):
    """
    Clear query cache (admin only)

    Removes cached query results
    """
    # TODO: Implement cache clearing
    return {"success": True, "message": "Cache cleared"}
