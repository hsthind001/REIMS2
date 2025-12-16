#!/usr/bin/env python3
"""
Startup Validation Script

Validates that all critical imports and dependencies are available
before the application starts. This helps catch errors early.
"""
import sys
import traceback

def validate_imports():
    """Validate all critical imports"""
    errors = []
    warnings = []
    
    # Core dependencies
    try:
        import fastapi
        print("✅ FastAPI imported successfully")
    except ImportError as e:
        errors.append(f"FastAPI: {e}")
    
    try:
        import structlog
        print(f"✅ structlog imported successfully (version: {structlog.__version__})")
    except ImportError as e:
        errors.append(f"structlog: {e}")
    
    try:
        import sqlalchemy
        print(f"✅ SQLAlchemy imported successfully (version: {sqlalchemy.__version__})")
    except ImportError as e:
        errors.append(f"SQLAlchemy: {e}")
    
    # Application imports
    try:
        from app.core.config import settings
        print("✅ Configuration loaded successfully")
    except Exception as e:
        errors.append(f"Configuration: {e}")
        traceback.print_exc()
    
    try:
        from app.db.database import engine, Base
        print("✅ Database connection configured")
    except Exception as e:
        warnings.append(f"Database configuration: {e} (may be OK if DB not ready)")
    
    try:
        from app.main import app
        print("✅ Main application imported successfully")
    except Exception as e:
        errors.append(f"Main application: {e}")
        traceback.print_exc()
    
    # Report results
    if warnings:
        print("\n⚠️  Warnings (non-critical):")
        for warning in warnings:
            print(f"   - {warning}")
    
    if errors:
        print("\n❌ Errors found:")
        for error in errors:
            print(f"   - {error}")
        print("\n⚠️  Application may fail to start. Please fix the errors above.")
        return False
    else:
        print("\n✅ All critical imports validated successfully!")
        return True

if __name__ == "__main__":
    success = validate_imports()
    sys.exit(0 if success else 1)

