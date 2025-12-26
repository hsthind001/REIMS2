from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
import logging
from app.api.v1 import health, users, tasks, storage, ocr, pdf, extraction, properties, chart_of_accounts, documents, validations, metrics, review, reports, auth, exports, reconciliation, anomalies, alerts, rbac, public_api, property_research, tenant_recommendations, nlq, risk_alerts, workflow_locks, statistical_anomalies, variance_analysis, bulk_import, document_summary, pdf_viewer, concordance, anomaly_thresholds, websocket, quality, financial_data, mortgage, alert_rules, financial_periods, batch_reprocessing, pdf_coordinates, model_optimization, portfolio_analytics, notifications, risk_workbench, forensic_reconciliation, self_learning, extraction_learning, market_intelligence
from app.db.database import engine, Base
from app.db.init_views import create_database_views

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize self-learning system on startup
try:
    from app.services.self_learning_engine import SelfLearningEngine
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        # Verify self-learning tables exist and are accessible
        from app.models.issue_knowledge_base import IssueKnowledgeBase
        count = db.query(IssueKnowledgeBase).count()
        print(f"✅ Self-learning system initialized (found {count} issues in knowledge base)")
    except Exception as e:
        print(f"⚠️  Self-learning system initialization warning: {e}")
    finally:
        db.close()
except Exception as e:
    print(f"⚠️  Self-learning system initialization skipped: {e}")

# Create database views (non-blocking - app will start even if views fail)
try:
    views_result = create_database_views(engine)
    if views_result["success"]:
        print(f"✅ Created {views_result['total_views']} database views")
    else:
        print(f"⚠️ View creation had {len(views_result.get('errors', []))} errors (app will continue)")
        if views_result.get('errors'):
            for error in views_result['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
except Exception as e:
    print(f"⚠️ Failed to create views: {e} (app will continue)")

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add rate limiter to app state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global exception handler to ensure CORS headers are always sent, even on errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that ensures CORS headers are always sent,
    even when unhandled exceptions occur (500 errors).
    """
    import traceback
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    # Create error response with CORS headers
    # The CORS middleware should handle this, but we ensure it's explicit
    # Check if DEBUG is available in settings, default to False
    debug_mode = getattr(settings, 'DEBUG', False)
    response = JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if debug_mode else "An unexpected error occurred"
        }
    )
    
    # Ensure CORS headers are present
    origin = request.headers.get("origin")
    if origin and origin in settings.BACKEND_CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept, Cookie"
    
    return response

# Configure CORS (add first, executes last)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Cookie"],
    expose_headers=["Set-Cookie"],
)

# Configure Session Middleware (add second, executes first)
# IMPORTANT: Must be added AFTER CORS middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="reims_session",
    max_age=86400 * 7,  # 7 days
    same_site="lax",
    https_only=False  # Set to True in production with HTTPS
)

# Include routers
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["health"])
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["authentication"])
app.include_router(users.router, prefix=settings.API_V1_STR, tags=["users"])
app.include_router(tasks.router, prefix=settings.API_V1_STR, tags=["tasks"])
app.include_router(storage.router, prefix=settings.API_V1_STR, tags=["storage"])
app.include_router(ocr.router, prefix=settings.API_V1_STR, tags=["ocr"])
app.include_router(pdf.router, prefix=settings.API_V1_STR, tags=["pdf"])
app.include_router(extraction.router, prefix=settings.API_V1_STR, tags=["extraction"])
app.include_router(properties.router, prefix=settings.API_V1_STR, tags=["properties"])
app.include_router(chart_of_accounts.router, prefix=settings.API_V1_STR, tags=["chart-of-accounts"])
app.include_router(documents.router, prefix=settings.API_V1_STR, tags=["documents"])
app.include_router(websocket.router, prefix=settings.API_V1_STR, tags=["websocket"])
app.include_router(validations.router, prefix=settings.API_V1_STR, tags=["validations"])
app.include_router(metrics.router, prefix=settings.API_V1_STR, tags=["metrics"])
app.include_router(mortgage.router, prefix=settings.API_V1_STR + "/mortgage", tags=["mortgage"])
app.include_router(quality.router, prefix=settings.API_V1_STR, tags=["quality"])
app.include_router(pdf_viewer.router, prefix=settings.API_V1_STR, tags=["pdf-viewer"])
app.include_router(financial_data.router, prefix=settings.API_V1_STR, tags=["financial-data"])
app.include_router(review.router, prefix=settings.API_V1_STR, tags=["review"])
app.include_router(reports.router, prefix=settings.API_V1_STR, tags=["reports"])
app.include_router(exports.router, prefix=settings.API_V1_STR, tags=["exports"])
app.include_router(reconciliation.router, prefix=settings.API_V1_STR, tags=["reconciliation"])
app.include_router(forensic_reconciliation.router, prefix=settings.API_V1_STR, tags=["forensic-reconciliation"])
app.include_router(self_learning.router, prefix=settings.API_V1_STR, tags=["self-learning"])
app.include_router(extraction_learning.router, prefix=settings.API_V1_STR + "/extraction-learning", tags=["extraction-learning"])
app.include_router(anomalies.router, prefix=settings.API_V1_STR + "/anomalies", tags=["anomalies"])
app.include_router(alerts.router, prefix=settings.API_V1_STR + "/alerts", tags=["alerts"])
app.include_router(notifications.router, prefix=settings.API_V1_STR, tags=["notifications"])
app.include_router(rbac.router, prefix=settings.API_V1_STR + "/rbac", tags=["rbac"])
app.include_router(public_api.router, prefix=settings.API_V1_STR + "/public", tags=["public-api"])

# Next-level AI features
app.include_router(property_research.router, prefix=settings.API_V1_STR, tags=["property-research"])
app.include_router(tenant_recommendations.router, prefix=settings.API_V1_STR, tags=["tenant-recommendations"])
# Add alternative route for tenant recommendations
if hasattr(tenant_recommendations, 'router_alt'):
    app.include_router(tenant_recommendations.router_alt, prefix=settings.API_V1_STR, tags=["tenant-recommendations"])
app.include_router(nlq.router, prefix=settings.API_V1_STR, tags=["natural-language-query"])
app.include_router(market_intelligence.router, prefix=settings.API_V1_STR, tags=["market-intelligence"])

# Risk management
app.include_router(risk_alerts.router, prefix=settings.API_V1_STR, tags=["risk-alerts"])
app.include_router(alert_rules.router, prefix=settings.API_V1_STR, tags=["alert-rules"])
app.include_router(workflow_locks.router, prefix=settings.API_V1_STR, tags=["workflow-locks"])
app.include_router(risk_workbench.router, tags=["risk-workbench"])
app.include_router(statistical_anomalies.router, prefix=settings.API_V1_STR, tags=["statistical-anomalies"])
app.include_router(variance_analysis.router, prefix=settings.API_V1_STR, tags=["variance-analysis"])
app.include_router(financial_periods.router, prefix=settings.API_V1_STR, tags=["financial-periods"])

# Data import
app.include_router(bulk_import.router, prefix=settings.API_V1_STR, tags=["bulk-import"])

# Document summarization
app.include_router(document_summary.router, prefix=settings.API_V1_STR, tags=["document-summary"])

# Concordance tables
app.include_router(concordance.router, prefix=settings.API_V1_STR, tags=["concordance"])

# Anomaly thresholds
app.include_router(anomaly_thresholds.router, prefix=settings.API_V1_STR + "/anomaly-thresholds", tags=["anomaly-thresholds"])

# Batch reprocessing (Phase 1: Anomaly Enhancement)
app.include_router(batch_reprocessing.router, prefix=settings.API_V1_STR, tags=["batch-reprocessing"])

# PDF Coordinate Prediction (Phase 5: LayoutLM Integration)
app.include_router(pdf_coordinates.router, prefix=settings.API_V1_STR, tags=["pdf-coordinates"])

# Model Optimization (Phase 6: GPU & Incremental Learning)
app.include_router(model_optimization.router, prefix=settings.API_V1_STR, tags=["model-optimization"])

# Portfolio Analytics (Phase 7: Cross-Property Intelligence)
app.include_router(portfolio_analytics.router, prefix=settings.API_V1_STR, tags=["portfolio-analytics"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to REIMS API",
        "docs": "/docs",
        "openapi": f"{settings.API_V1_STR}/openapi.json"
    }

