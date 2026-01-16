from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Create database engine with optimized connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,           # Number of connections to keep open
    max_overflow=30,        # Additional connections when pool is full
    pool_timeout=30,        # Seconds to wait for available connection
    pool_recycle=1800,      # Recycle connections after 30 minutes
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


# Dependency to get database session with proper transaction handling
def get_db():
    """
    FastAPI dependency that provides a database session.

    Transaction handling:
    - On successful request: commits are handled by the endpoint
    - On exception: automatically rolls back to prevent partial commits
    - Always closes the session to return connection to pool
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Rollback on any exception to prevent partial commits
        db.rollback()
        raise
    finally:
        db.close()


def get_db_with_autocommit():
    """
    Database session that auto-commits on success.
    Use for simple CRUD operations that don't need explicit transaction control.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

