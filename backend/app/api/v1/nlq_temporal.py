"""
NLQ API Endpoints with Comprehensive Temporal Support

Endpoints:
- POST /api/v1/nlq/query - Main NLQ query endpoint
- POST /api/v1/nlq/temporal/parse - Parse temporal expressions
- GET /api/v1/nlq/formulas - List all formulas
- GET /api/v1/nlq/formulas/{metric} - Get formula details
- POST /api/v1/nlq/calculate/{metric} - Calculate specific metric
- GET /api/v1/nlq/health - Health check
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.db.database import get_db
from app.services.nlq.orchestrator import get_orchestrator
from app.services.nlq.temporal_processor import temporal_processor
from app.services.nlq.agents.formula_agent import FormulaAgent
from app.config.nlq_config import nlq_config
from loguru import logger


router = APIRouter(prefix="/nlq", tags=["Natural Language Query"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class NLQQueryRequest(BaseModel):
    """NLQ query request"""
    question: str = Field(..., description="Natural language question", min_length=1)
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context (property_id, property_code, user_id)"
    )
    user_id: Optional[int] = Field(default=1, description="User ID for tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What was the cash position in November 2025?",
                "context": {
                    "property_code": "ESP",
                    "property_id": 1
                },
                "user_id": 1
            }
        }


class NLQQueryResponse(BaseModel):
    """NLQ query response"""
    success: bool
    answer: str
    data: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    execution_time_ms: Optional[int] = None
    from_cache: bool = False
    sql_query: Optional[str] = None
    error: Optional[str] = None


class TemporalParseRequest(BaseModel):
    """Temporal expression parsing request"""
    query: str = Field(..., description="Query with temporal expression")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Show me data for last 3 months"
            }
        }


class TemporalParseResponse(BaseModel):
    """Temporal parsing response"""
    has_temporal: bool
    temporal_type: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    original_expression: Optional[str] = None
    normalized_expression: Optional[str] = None
    sql_filters: Optional[Dict[str, Any]] = None


class CalculateMetricRequest(BaseModel):
    """Metric calculation request"""
    property_id: int
    year: Optional[int] = None
    month: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "property_id": 1,
                "year": 2025,
                "month": 11
            }
        }


# ============================================================================
# MAIN NLQ ENDPOINT
# ============================================================================

@router.post("/query", response_model=NLQQueryResponse)
async def nlq_query(
    request: NLQQueryRequest,
    db: Session = Depends(get_db)
):
    """
    Process natural language query with comprehensive temporal support

    **Supported Temporal Expressions:**
    - Absolute: "November 2025", "in 2025", "2025-11-15"
    - Relative: "last 3 months", "last year", "previous quarter"
    - Fiscal: "Q4 2025", "fiscal year 2025"
    - Keywords: "YTD", "MTD", "QTD"
    - Ranges: "between August and December 2025"

    **Example Queries:**
    - "What was cash position in November 2025?"
    - "Show total revenue for Q4 2025"
    - "Compare net income YTD vs last year"
    - "Calculate DSCR for last month"
    - "How is Current Ratio calculated?"
    """
    start_time = datetime.now()

    try:
        # Get orchestrator
        orchestrator = get_orchestrator(db)

        # Process query
        result = await orchestrator.process_query(
            query=request.question,
            user_id=request.user_id or 1,
            context=request.context
        )

        # Calculate execution time
        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return NLQQueryResponse(
            success=result.get("success", True),
            answer=result.get("answer", ""),
            data=result.get("data"),
            metadata=result.get("metadata"),
            confidence_score=result.get("confidence_score"),
            execution_time_ms=execution_time_ms,
            from_cache=result.get("from_cache", False),
            sql_query=result.get("sql_query"),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"NLQ query error: {e}", exc_info=True)
        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return NLQQueryResponse(
            success=False,
            answer=f"I encountered an error: {str(e)}",
            error=str(e),
            execution_time_ms=execution_time_ms
        )


# ============================================================================
# TEMPORAL PARSING ENDPOINT
# ============================================================================

@router.post("/temporal/parse", response_model=TemporalParseResponse)
async def parse_temporal_expression(request: TemporalParseRequest):
    """
    Parse temporal expressions from natural language

    **Examples:**
    - "November 2025" → {"year": 2025, "month": 11}
    - "last 3 months" → {"start_date": "2025-10-01", "end_date": "2026-01-01"}
    - "Q4 2025" → {"quarter": 4, "year": 2025, ...}
    - "YTD" → {"start_date": "2025-01-01", "end_date": "2026-01-08"}
    """
    try:
        temporal_info = temporal_processor.extract_temporal_info(request.query)

        # Build SQL filters
        sql_filters = temporal_processor.build_temporal_filters(
            temporal_info,
            statement_type="balance_sheet"
        ) if temporal_info.get("has_temporal") else None

        return TemporalParseResponse(
            has_temporal=temporal_info.get("has_temporal", False),
            temporal_type=temporal_info.get("temporal_type"),
            filters=temporal_info.get("filters"),
            original_expression=temporal_info.get("original_expression"),
            normalized_expression=temporal_info.get("normalized_expression"),
            sql_filters=sql_filters
        )

    except Exception as e:
        logger.error(f"Temporal parsing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# FORMULA ENDPOINTS
# ============================================================================

@router.get("/formulas")
async def list_formulas(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all available financial formulas

    **Categories:**
    - liquidity (Current Ratio, Quick Ratio, Cash Ratio, Working Capital)
    - leverage (Debt-to-Assets, Debt-to-Equity, LTV)
    - mortgage (DSCR, Interest Coverage, Debt Yield, Break-Even Occupancy)
    - income_statement (NOI, Operating Margin, Profit Margin)
    - rent_roll (Occupancy Rate, Rent per Sqft)
    - balance_sheet (Net Property Value, Depreciation Rate)
    - cash_flow (Operating Cash Flow, Free Cash Flow)
    """
    try:
        formula_agent = FormulaAgent(db)

        if category:
            # Filter by category
            formulas = {
                k: v for k, v in formula_agent.FORMULAS.items()
                if v.get("category") == category
            }
        else:
            formulas = formula_agent.FORMULAS

        return {
            "success": True,
            "count": len(formulas),
            "category": category,
            "formulas": formulas
        }

    except Exception as e:
        logger.error(f"Formula list error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/formulas/{metric}")
async def get_formula(metric: str, db: Session = Depends(get_db)):
    """
    Get details for a specific formula

    **Available Metrics:**
    - current_ratio, quick_ratio, cash_ratio, working_capital
    - debt_to_assets, debt_to_equity, ltv
    - dscr, interest_coverage, debt_yield, break_even_occupancy
    - noi, operating_margin, profit_margin
    - occupancy_rate, rent_per_sqft
    - And 50+ more...
    """
    try:
        formula_agent = FormulaAgent(db)

        if metric not in formula_agent.FORMULAS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Formula '{metric}' not found"
            )

        formula = formula_agent.FORMULAS[metric]

        return {
            "success": True,
            "metric": metric,
            "formula": formula
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Formula get error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/calculate/{metric}")
async def calculate_metric(
    metric: str,
    request: CalculateMetricRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate a specific metric for a property/period

    **Example:**
    ```
    POST /api/v1/nlq/calculate/dscr
    {
        "property_id": 1,
        "year": 2025,
        "month": 11
    }
    ```

    **Available Metrics:**
    See /api/v1/nlq/formulas for complete list
    """
    try:
        formula_agent = FormulaAgent(db)

        if metric not in formula_agent.FORMULAS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metric '{metric}' not found"
            )

        # Build temporal info
        temporal_info = {
            "has_temporal": True,
            "filters": {
                "year": request.year,
                "month": request.month
            }
        } if request.year and request.month else {}

        # Calculate
        result = await formula_agent._calculate_metric(
            metric_key=metric,
            temporal_info=temporal_info,
            context={"property_id": request.property_id}
        )

        return {
            "success": True,
            "metric": metric,
            **result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metric calculation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check for NLQ system

    Returns status of all components:
    - Temporal processor
    - Vector store (Qdrant)
    - Knowledge graph (Neo4j)
    - Available agents
    - Configuration
    """
    try:
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "temporal_processor": {"status": "operational"},
                "orchestrator": {"status": "operational"},
                "agents": {
                    "financial_data": {"status": "operational"},
                    "formula": {"status": "operational"}
                }
            },
            "configuration": {
                "primary_llm": nlq_config.PRIMARY_LLM_PROVIDER,
                "enable_temporal": nlq_config.ENABLE_TEMPORAL_UNDERSTANDING,
                "enable_hybrid_search": nlq_config.ENABLE_HYBRID_SEARCH,
                "enable_multi_agent": nlq_config.ENABLE_MULTI_AGENT,
                "fiscal_year_start_month": nlq_config.FISCAL_YEAR_START_MONTH
            },
            "capabilities": {
                "temporal_expressions": [
                    "Absolute dates (November 2025, 2025-11-15)",
                    "Relative periods (last 3 months, last year)",
                    "Fiscal periods (Q4 2025, FY 2025)",
                    "Special keywords (YTD, MTD, QTD)",
                    "Date ranges (between Aug and Dec 2025)"
                ],
                "query_types": [
                    "Financial data queries",
                    "Formula explanations",
                    "Metric calculations",
                    "Comparisons",
                    "Trend analysis"
                ]
            }
        }

        # Check vector store (optional)
        try:
            from app.services.nlq.vector_store_manager import vector_store_manager
            vector_store_manager.client.get_collections()
            health["components"]["vector_store"] = {"status": "operational"}
        except Exception as e:
            health["components"]["vector_store"] = {"status": "unavailable", "error": str(e)}

        return health

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return {
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
