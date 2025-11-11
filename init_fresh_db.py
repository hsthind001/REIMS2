#!/usr/bin/env python3
"""
Manual database initialization script
Creates all tables and seeds initial data
"""
import sys
import os

# Add backend to path
sys.path.insert(0, '/home/gurpyar/Documents/R/REIMS2/backend')

from sqlalchemy import create_engine, text
from app.models.base import Base
from app.core.config import settings

def init_database():
    """Initialize database with all tables"""
    print("🚀 Starting manual database initialization...")
    
    # Create engine
    engine = create_engine(str(settings.DATABASE_URL))
    
    try:
        # Create all tables from models
        print("📦 Creating all tables from SQLAlchemy models...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # Mark migrations as complete by creating alembic_version table
        print("📝 Marking migrations as complete...")
        with engine.connect() as conn:
            # Check if alembic_version exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                )
            """))
            exists = result.scalar()
            
            if not exists:
                conn.execute(text("""
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL,
                        CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                    )
                """))
                conn.commit()
            
            # Set to the latest migration version
            conn.execute(text("DELETE FROM alembic_version"))
            conn.execute(text("INSERT INTO alembic_version VALUES ('20251107_0200_cf_add_standardized_fields')"))
            conn.commit()
            print("✅ Alembic version table updated!")
        
        print("🎉 Database initialization complete!")
        return 0
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(init_database())

