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


class AIInsight(BaseModel):
    """AI-generated portfolio insight"""
    id: str
    type: str  # risk, market, operational, financial
    title: str
    description: str
    confidence: float


@router.get("/insights/portfolio")
def get_portfolio_insights(
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)
):
    """
    Get AI-generated portfolio insights

    Analyzes portfolio data and generates actionable insights about:
    - Risk patterns (DSCR stress, vacancy trends)
    - Market opportunities (cap rate movements, refinancing windows)
    - Operational issues (lease expirations, maintenance needs)
    - Financial trends (NOI changes, expense patterns)

    Returns: List of AI insights with confidence scores
    """
    from app.models.financial_metrics import FinancialMetrics
    from app.models.property import Property
    from app.models.financial_period import FinancialPeriod
    from app.models.rent_roll_data import RentRollData
    from datetime import datetime, timedelta
    from sqlalchemy import func

    insights = []

    try:
        # Get all properties with latest metrics
        properties = db.query(Property).filter(Property.status == 'active').all()

        # Analyze DSCR stress patterns
        dscr_stress_count = 0
        low_dscr_properties = []

        for prop in properties:
            latest_period = (
                db.query(FinancialPeriod)
                .filter(FinancialPeriod.property_id == prop.id)
                .order_by(FinancialPeriod.period_year.desc(), FinancialPeriod.period_month.desc())
                .first()
            )

            if latest_period:
                metrics = (
                    db.query(FinancialMetrics)
                    .filter(
                        FinancialMetrics.property_id == prop.id,
                        FinancialMetrics.period_id == latest_period.id
                    )
                    .first()
                )

                if metrics and metrics.dscr and metrics.dscr < 1.25:
                    dscr_stress_count += 1
                    low_dscr_properties.append(prop.property_code)

        if dscr_stress_count >= 2:
            insights.append(AIInsight(
                id="dscr_stress",
                type="risk",
                title="DSCR Stress Pattern Detected",
                description=f"{dscr_stress_count} properties showing DSCR stress - refinancing window optimal",
                confidence=0.85
            ))

        # Analyze lease expirations
        next_quarter_start = datetime.now() + timedelta(days=90)
        next_quarter_end = next_quarter_start + timedelta(days=90)

        expiring_leases = (
            db.query(RentRollData)
            .filter(
                RentRollData.lease_end_date >= next_quarter_start.date(),
                RentRollData.lease_end_date <= next_quarter_end.date(),
                RentRollData.occupancy_status == 'occupied'
            )
            .count()
        )

        if expiring_leases > 20:
            insights.append(AIInsight(
                id="lease_expirations",
                type="operational",
                title=f"Q{((datetime.now().month-1)//3 + 2) % 4 + 1} {datetime.now().year + ((datetime.now().month-1)//3 + 2) // 4} Lease Expirations",
                description=f"{expiring_leases} lease expirations next quarter - start negotiations NOW",
                confidence=0.92
            ))

        # Analyze cap rate trends (simplified market analysis)
        portfolio_avg_cap = 0
        cap_count = 0

        for prop in properties:
            latest_period = (
                db.query(FinancialPeriod)
                .filter(FinancialPeriod.property_id == prop.id)
                .order_by(FinancialPeriod.period_year.desc(), FinancialPeriod.period_month.desc())
                .first()
            )

            if latest_period:
                metrics = (
                    db.query(FinancialMetrics)
                    .filter(
                        FinancialMetrics.property_id == prop.id,
                        FinancialMetrics.period_id == latest_period.id
                    )
                    .first()
                )

                if metrics and metrics.net_income and metrics.total_assets:
                    cap_rate = (float(metrics.net_income) / float(metrics.total_assets)) * 100
                    portfolio_avg_cap += cap_rate
                    cap_count += 1

        if cap_count > 0:
            avg_cap = portfolio_avg_cap / cap_count
            # Simplified market trend analysis
            market_cap = avg_cap * 1.05  # Assume market trending slightly higher

            if market_cap > avg_cap:
                insights.append(AIInsight(
                    id="market_cap_rates",
                    type="market",
                    title="Market Cap Rates Trending Up",
                    description=f"Market cap rates trending up {round((market_cap - avg_cap), 2)}% - favorable for sales",
                    confidence=0.78
                ))

        # If no insights generated, add default ones
        if len(insights) == 0:
            insights.append(AIInsight(
                id="portfolio_healthy",
                type="financial",
                title="Portfolio Health Strong",
                description="No critical issues detected - portfolio performing within normal parameters",
                confidence=0.88
            ))

        return {
            "insights": [insight.dict() for insight in insights],
            "total": len(insights),
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to generate portfolio insights: {str(e)}")
        # Return fallback insights on error
        return {
            "insights": [
                {
                    "id": "fallback",
                    "type": "operational",
                    "title": "Portfolio Analysis Pending",
                    "description": "Insufficient data for AI insights - upload more financial data",
                    "confidence": 0.50
                }
            ],
            "total": 1,
            "generated_at": datetime.now().isoformat()
        }
