"""
Integrated Natural Language Query API Endpoints

Uses IntegratedNLQService which combines SemanticCacheService and NLQService.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from app.db.database import get_db
from app.services.nlq_service_integrated import IntegratedNLQService
from app.api.dependencies import get_current_user, get_current_organization
from app.models.user import User
from app.models.organization import Organization

router = APIRouter(prefix="/nlq", tags=["natural_language_query"])
logger = logging.getLogger(__name__)


class NLQueryRequest(BaseModel):
    question: str
    context: Optional[dict] = None
    conversation_id: Optional[str] = None


@router.post("/query")
def natural_language_query(
    request: NLQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Process natural language query with integrated caching
    
    Uses IntegratedNLQService which:
    1. Checks semantic cache first (Component A)
    2. If cache miss, processes query with NLQ service (Component B)
    3. Updates cache with new query result
    
    Examples:
    - "What was the NOI for Eastern Shore Plaza in Q3 2024?"
    - "Show me occupancy trends over the last 2 years"
    - "Which properties have the highest operating expense ratio?"
    
    Returns answer with data, citations, and cache metadata
    """
    logger.info(f"Integrated NLQ query received from user {current_user.id}: {request.question}")
    user_id = current_user.id

    service = IntegratedNLQService(db, organization_id=current_org.id)

    try:
        # Process query with integrated caching
        result = service.query(
            question=request.question,
            user_id=user_id,
            context=request.context
        )

        if not result.get('success', False):
            logger.warning(f"NLQ query failed: {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": result.get('error', 'Unable to process query'),
                "question": request.question,
                "answer": f"❌ Error: {result.get('error', 'Unable to process your query. Please try rephrasing or check if the required data is available.')}",
                "data": result.get('data', {}),
                "confidence": 0,
                "suggested_follow_ups": [],
                "from_cache": False
            }

        return result

    except Exception as e:
        logger.error(f"Integrated NLQ failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "question": request.question,
            "answer": f"❌ Error: {str(e)}",
            "data": {},
            "confidence": 0,
            "suggested_follow_ups": [],
            "from_cache": False
        }


@router.get("/cache/stats")
def get_cache_statistics(
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get cache statistics for monitoring
    
    Returns:
        Dict with cache hit/miss rates and Component A statistics
    """
    service = IntegratedNLQService(db, organization_id=current_org.id)
    stats = service.get_cache_statistics(hours=hours)
    return stats


@router.get("/health")
def get_service_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org: Organization = Depends(get_current_organization)
):
    """
    Get health status of integrated service components
    
    Returns:
        Dict with health status of Component A, Component B, and integration
    """
    service = IntegratedNLQService(db, organization_id=current_org.id)
    health = service.get_health_status()
    return health
