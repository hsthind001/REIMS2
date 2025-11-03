from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
from app.db.redis_client import get_redis
import redis

router = APIRouter()


@router.get("/health")
async def health_check(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    Health check endpoint to verify API, Database, and Redis connections
    """
    health_status = {
        "status": "healthy",
        "api": "ok",
        "database": "disconnected",
        "redis": "disconnected"
    }
    
    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"
    
    # Check Redis connection
    try:
        redis_client.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["redis"] = f"error: {str(e)}"
    
    return health_status

