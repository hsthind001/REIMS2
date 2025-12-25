"""
Extraction Self-Learning System API

Endpoints for monitoring and managing the intelligent self-learning extraction system.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.extraction_learning_pattern import ExtractionLearningPattern
from app.models.adaptive_confidence_threshold import AdaptiveConfidenceThreshold
from app.services.self_learning_extraction_service import SelfLearningExtractionService

router = APIRouter()


# ==================== RESPONSE MODELS ====================

class LearningPatternResponse(BaseModel):
    id: int
    account_code: str
    account_name: str
    document_type: str
    total_occurrences: int
    approved_count: int
    rejected_count: int
    auto_approved_count: int
    reliability_score: float
    pattern_strength: float
    is_trustworthy: bool
    auto_approve_threshold: Optional[float]
    first_seen_at: datetime
    last_updated_at: datetime

    class Config:
        from_attributes = True


class AdaptiveThresholdResponse(BaseModel):
    id: int
    account_code: str
    account_name: str
    current_threshold: float
    original_threshold: float
    total_extractions: int
    successful_extractions: int
    historical_accuracy: float
    complexity_score: float
    is_simple_account: bool
    is_complex_account: bool
    adjustment_count: int

    class Config:
        from_attributes = True


class SelfLearningStatsResponse(BaseModel):
    total_patterns_learned: int
    trustworthy_patterns: int
    auto_approve_ready: int
    total_adaptive_thresholds: int
    adjusted_thresholds: int
    total_auto_approvals: int
    system_maturity: float
    estimated_review_reduction: float


class ReviewFeedbackRequest(BaseModel):
    account_code: str
    account_name: str
    document_type: str
    confidence: float
    approved: bool
    property_id: Optional[int] = None


# ==================== ENDPOINTS ====================

@router.get("/stats", response_model=SelfLearningStatsResponse)
async def get_self_learning_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overall statistics about the self-learning extraction system"""
    service = SelfLearningExtractionService(db)
    stats = service.get_learning_statistics()
    return stats


@router.get("/patterns", response_model=List[LearningPatternResponse])
async def list_learning_patterns(
    trustworthy_only: bool = Query(False),
    document_type: Optional[str] = Query(None),
    min_occurrences: int = Query(0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all learned patterns"""
    query = db.query(ExtractionLearningPattern)

    if trustworthy_only:
        query = query.filter(ExtractionLearningPattern.is_trustworthy == True)

    if document_type:
        query = query.filter(ExtractionLearningPattern.document_type == document_type)

    if min_occurrences > 0:
        query = query.filter(ExtractionLearningPattern.total_occurrences >= min_occurrences)

    patterns = query.order_by(
        desc(ExtractionLearningPattern.reliability_score)
    ).limit(limit).all()

    return patterns


@router.get("/insights")
async def get_learning_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get actionable insights from the self-learning system"""
    # Get trustworthy patterns ready for auto-approval
    auto_approve_ready = db.query(ExtractionLearningPattern).filter(
        ExtractionLearningPattern.is_trustworthy == True
    ).order_by(desc(ExtractionLearningPattern.reliability_score)).limit(10).all()

    # Get recently adjusted thresholds
    cutoff = datetime.now() - timedelta(days=30)
    recent_adjustments = db.query(AdaptiveConfidenceThreshold).filter(
        AdaptiveConfidenceThreshold.last_adjustment_date >= cutoff
    ).order_by(desc(AdaptiveConfidenceThreshold.last_adjustment_date)).limit(10).all()

    # Calculate potential savings
    total_patterns = db.query(func.count(ExtractionLearningPattern.id)).scalar()
    trustworthy_count = db.query(func.count(ExtractionLearningPattern.id)).filter(
        ExtractionLearningPattern.is_trustworthy == True
    ).scalar()

    total_auto_approvals = db.query(
        func.sum(ExtractionLearningPattern.auto_approved_count)
    ).scalar() or 0

    return {
        "auto_approve_ready": [
            {
                "account_code": p.account_code,
                "account_name": p.account_name,
                "document_type": p.document_type,
                "reliability_score": p.reliability_score,
                "total_occurrences": p.total_occurrences
            }
            for p in auto_approve_ready
        ],
        "recent_adjustments": [
            {
                "account_code": t.account_code,
                "old_threshold": t.original_threshold,
                "new_threshold": t.current_threshold
            }
            for t in recent_adjustments
        ],
        "summary": {
            "total_patterns": total_patterns or 0,
            "trustworthy_patterns": trustworthy_count or 0,
            "auto_approvals_to_date": total_auto_approvals,
            "learning_coverage": (trustworthy_count / total_patterns * 100) if total_patterns and total_patterns > 0 else 0
        }
    }
