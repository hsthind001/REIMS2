from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import settings
from app.api.v1 import health, users, tasks, storage, ocr, pdf, extraction, properties, chart_of_accounts, documents, validations, metrics, review, reports, auth, exports, reconciliation
from app.db.database import engine, Base
from app.db.init_views import create_database_views

# Create database tables
Base.metadata.create_all(bind=engine)

# Create database views
try:
    views_result = create_database_views(engine)
    if views_result["success"]:
        print(f"✅ Created {views_result['total_views']} database views")
    else:
        print(f"⚠️ View creation had errors: {views_result.get('errors', [])}")
except Exception as e:
    print(f"⚠️ Failed to create views: {e}")

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure Session Middleware (for session-based authentication)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="reims_session",
    max_age=86400 * 7,  # 7 days
    same_site="lax",
    https_only=False  # Set to True in production with HTTPS
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(review.router, prefix=settings.API_V1_STR, tags=["review"])
app.include_router(reports.router, prefix=settings.API_V1_STR, tags=["reports"])
app.include_router(exports.router, prefix=settings.API_V1_STR, tags=["exports"])
app.include_router(reconciliation.router, prefix=settings.API_V1_STR, tags=["reconciliation"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to REIMS API",
        "docs": "/docs",
        "openapi": f"{settings.API_V1_STR}/openapi.json"
    }

