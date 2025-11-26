from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.api.v1 import health, users, tasks, storage, ocr, pdf, extraction, properties, chart_of_accounts, documents, validations, metrics, review, reports, auth, exports, reconciliation, anomalies, alerts, rbac, public_api, property_research, tenant_recommendations, nlq, risk_alerts, workflow_locks, statistical_anomalies, variance_analysis, bulk_import, document_summary, pdf_viewer, concordance, anomaly_thresholds
from app.db.database import engine, Base
from app.db.init_views import create_database_views

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# Create database tables
Base.metadata.create_all(bind=engine)

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
app.include_router(validations.router, prefix=settings.API_V1_STR, tags=["validations"])
app.include_router(metrics.router, prefix=settings.API_V1_STR, tags=["metrics"])
app.include_router(pdf_viewer.router, prefix=settings.API_V1_STR, tags=["pdf-viewer"])
app.include_router(review.router, prefix=settings.API_V1_STR, tags=["review"])
app.include_router(reports.router, prefix=settings.API_V1_STR, tags=["reports"])
app.include_router(exports.router, prefix=settings.API_V1_STR, tags=["exports"])
app.include_router(reconciliation.router, prefix=settings.API_V1_STR, tags=["reconciliation"])
app.include_router(anomalies.router, prefix=settings.API_V1_STR + "/anomalies", tags=["anomalies"])
app.include_router(alerts.router, prefix=settings.API_V1_STR + "/alerts", tags=["alerts"])
app.include_router(rbac.router, prefix=settings.API_V1_STR + "/rbac", tags=["rbac"])
app.include_router(public_api.router, prefix=settings.API_V1_STR + "/public", tags=["public-api"])

# Next-level AI features
app.include_router(property_research.router, prefix=settings.API_V1_STR, tags=["property-research"])
app.include_router(tenant_recommendations.router, prefix=settings.API_V1_STR, tags=["tenant-recommendations"])
app.include_router(nlq.router, prefix=settings.API_V1_STR, tags=["natural-language-query"])

# Risk management
app.include_router(risk_alerts.router, prefix=settings.API_V1_STR, tags=["risk-alerts"])
app.include_router(workflow_locks.router, prefix=settings.API_V1_STR, tags=["workflow-locks"])
app.include_router(statistical_anomalies.router, prefix=settings.API_V1_STR, tags=["statistical-anomalies"])
app.include_router(variance_analysis.router, prefix=settings.API_V1_STR, tags=["variance-analysis"])

# Data import
app.include_router(bulk_import.router, prefix=settings.API_V1_STR, tags=["bulk-import"])

# Document summarization
app.include_router(document_summary.router, prefix=settings.API_V1_STR, tags=["document-summary"])

# Concordance tables
app.include_router(concordance.router, prefix=settings.API_V1_STR, tags=["concordance"])

# Anomaly thresholds
app.include_router(anomaly_thresholds.router, prefix=settings.API_V1_STR + "/anomaly-thresholds", tags=["anomaly-thresholds"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to REIMS API",
        "docs": "/docs",
        "openapi": f"{settings.API_V1_STR}/openapi.json"
    }

