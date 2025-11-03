"""
Pytest configuration and shared fixtures
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db.database import Base

# Use Docker PostgreSQL (from docker-compose)
# Use separate test database name to avoid conflicts
TEST_DATABASE_URL = "postgresql://reims:reims@localhost:5432/reims_test"

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Apply CHECK constraints manually (since they're not in metadata)
    with test_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        try:
            # Add CHECK constraints from migration
            conn.execute(text("""
                ALTER TABLE properties 
                DROP CONSTRAINT IF EXISTS ck_properties_status;
                
                ALTER TABLE properties
                ADD CONSTRAINT ck_properties_status 
                CHECK (status IN ('active', 'sold', 'under_contract'));
                
                ALTER TABLE financial_periods
                DROP CONSTRAINT IF EXISTS ck_financial_periods_month;
                
                ALTER TABLE financial_periods
                ADD CONSTRAINT ck_financial_periods_month
                CHECK (period_month BETWEEN 1 AND 12);
                
                ALTER TABLE financial_periods
                DROP CONSTRAINT IF EXISTS ck_financial_periods_quarter;
                
                ALTER TABLE financial_periods
                ADD CONSTRAINT ck_financial_periods_quarter
                CHECK (fiscal_quarter IS NULL OR (fiscal_quarter BETWEEN 1 AND 4));
            """))
        except:
            pass  # Constraints might not exist yet
    
    # Create session
    session = TestingSessionLocal()
    
    yield session
    
    # Rollback and close
    session.rollback()
    session.close()
    
    # Drop all tables
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True, scope="session")
def create_test_database():
    """Create test database before any tests run"""
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import ProgrammingError
    
    # Connect to default postgres database to create test database
    # Use Docker PostgreSQL credentials
    admin_engine = create_engine("postgresql://reims:reims@localhost:5432/reims")
    
    with admin_engine.connect() as connection:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        
        try:
            # Drop if exists and create
            connection.execute(text("DROP DATABASE IF EXISTS reims_test"))
            connection.execute(text("CREATE DATABASE reims_test OWNER reims"))
        except ProgrammingError as e:
            # Database might not exist yet or we don't have permissions
            print(f"Warning: Could not create test database: {e}")
    
    yield
    
    # Cleanup: drop test database after all tests
    with admin_engine.connect() as connection:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        try:
            connection.execute(text("DROP DATABASE IF EXISTS reims_test"))
        except:
            pass
