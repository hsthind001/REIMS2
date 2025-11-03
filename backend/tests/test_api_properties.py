"""
Tests for Properties API endpoints - Sprint 1.2
Testing property_code based endpoints as per specification
"""
import pytest
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DECIMAL, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql import func

from app.main import app
from app.db.database import get_db


# Create separate base for testing to avoid importing models with PostgreSQL-specific types
TestBase = declarative_base()


class User(TestBase):
    """User model for testing"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Property(TestBase):
    """Property model for testing"""
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    property_code = Column(String(50), unique=True, nullable=False, index=True)
    property_name = Column(String(255), nullable=False)
    property_type = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    country = Column(String(50), default='USA')
    total_area_sqft = Column(DECIMAL(12, 2))
    acquisition_date = Column(Date)
    ownership_structure = Column(String(100))
    status = Column(String(50), default='active', index=True)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)


# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    TestBase.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Create system user for authentication
    system_user = User(
        username="system",
        email="system@reims.local",
        hashed_password="not_used",
        is_active=True,
        is_superuser=True
    )
    session.add(system_user)
    session.commit()
    
    yield session
    session.close()
    TestBase.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_property_data():
    """Sample property data for testing"""
    return {
        "property_code": "ESP001",
        "property_name": "Esplanade Shopping Center",
        "property_type": "Retail",
        "address": "1234 Main Street",
        "city": "Phoenix",
        "state": "AZ",
        "zip_code": "85001",
        "country": "USA",
        "total_area_sqft": "125000.50",
        "acquisition_date": "2023-01-15",
        "ownership_structure": "LLC",
        "status": "active",
        "notes": "Premium shopping center"
    }


class TestPropertiesAPI:
    """Test Properties API endpoints"""
    
    def test_create_property(self, client, sample_property_data):
        """Test POST /api/v1/properties/"""
        response = client.post("/api/v1/properties/", json=sample_property_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["property_code"] == "ESP001"
        assert data["property_name"] == "Esplanade Shopping Center"
        assert "id" in data
        assert "created_at" in data
    
    def test_create_property_invalid_code(self, client):
        """Test creating property with invalid property_code format"""
        invalid_data = {
            "property_code": "invalid",  # Should be 2-5 letters + 3 digits
            "property_name": "Test Property",
            "status": "active"
        }
        
        response = client.post("/api/v1/properties/", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    def test_create_property_invalid_status(self, client):
        """Test creating property with invalid status"""
        invalid_data = {
            "property_code": "TEST001",
            "property_name": "Test Property",
            "status": "invalid_status"
        }
        
        response = client.post("/api/v1/properties/", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    def test_create_property_negative_area(self, client):
        """Test creating property with negative area"""
        invalid_data = {
            "property_code": "TEST001",
            "property_name": "Test Property",
            "status": "active",
            "total_area_sqft": "-1000"
        }
        
        response = client.post("/api/v1/properties/", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    def test_list_properties(self, client, sample_property_data):
        """Test GET /api/v1/properties/"""
        # Create a property first
        client.post("/api/v1/properties/", json=sample_property_data)
        
        # List properties
        response = client.get("/api/v1/properties/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["property_code"] == "ESP001"
    
    def test_get_property_by_code(self, client, sample_property_data):
        """Test GET /api/v1/properties/{property_code}"""
        # Create a property
        create_response = client.post("/api/v1/properties/", json=sample_property_data)
        property_code = create_response.json()["property_code"]
        
        # Get property by code
        response = client.get(f"/api/v1/properties/{property_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["property_code"] == property_code
        assert data["property_name"] == "Esplanade Shopping Center"
    
    def test_get_property_not_found(self, client):
        """Test GET /api/v1/properties/{property_code} with non-existent code"""
        response = client.get("/api/v1/properties/NONEXIST999")
        assert response.status_code == 404
    
    def test_update_property(self, client, sample_property_data):
        """Test PUT /api/v1/properties/{property_code}"""
        # Create a property
        create_response = client.post("/api/v1/properties/", json=sample_property_data)
        property_code = create_response.json()["property_code"]
        
        # Update property
        update_data = {
            "property_name": "Updated Shopping Center",
            "status": "sold"
        }
        response = client.put(f"/api/v1/properties/{property_code}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["property_name"] == "Updated Shopping Center"
        assert data["status"] == "sold"
    
    def test_update_property_not_found(self, client):
        """Test PUT /api/v1/properties/{property_code} with non-existent code"""
        update_data = {"property_name": "Updated Name"}
        response = client.put("/api/v1/properties/NONEXIST999", json=update_data)
        assert response.status_code == 404
    
    def test_delete_property(self, client, sample_property_data):
        """Test DELETE /api/v1/properties/{property_code}"""
        # Create a property
        create_response = client.post("/api/v1/properties/", json=sample_property_data)
        property_code = create_response.json()["property_code"]
        
        # Delete property
        response = client.delete(f"/api/v1/properties/{property_code}")
        
        assert response.status_code == 204
        
        # Verify property is deleted
        get_response = client.get(f"/api/v1/properties/{property_code}")
        assert get_response.status_code == 404
    
    def test_delete_property_not_found(self, client):
        """Test DELETE /api/v1/properties/{property_code} with non-existent code"""
        response = client.delete("/api/v1/properties/NONEXIST999")
        assert response.status_code == 404
    
    def test_create_duplicate_property_code(self, client, sample_property_data):
        """Test creating property with duplicate property_code"""
        # Create first property
        client.post("/api/v1/properties/", json=sample_property_data)
        
        # Try to create duplicate
        response = client.post("/api/v1/properties/", json=sample_property_data)
        assert response.status_code == 400  # Duplicate error
        assert "already exists" in response.json()["detail"]
    
    def test_list_properties_with_status_filter(self, client, sample_property_data):
        """Test GET /api/v1/properties/ with status filter"""
        # Create properties with different statuses
        client.post("/api/v1/properties/", json=sample_property_data)
        
        sample_property_data2 = sample_property_data.copy()
        sample_property_data2["property_code"] = "ESP002"
        sample_property_data2["status"] = "sold"
        client.post("/api/v1/properties/", json=sample_property_data2)
        
        # Filter by active status
        response = client.get("/api/v1/properties/?status=active")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "active"
        
        # Filter by sold status
        response = client.get("/api/v1/properties/?status=sold")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "sold"
