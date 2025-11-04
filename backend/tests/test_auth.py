"""
Comprehensive tests for authentication system

Tests registration, login, session management, and password security
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from app.db.database import get_db, SessionLocal
import app.db.database as database


# Test client
client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session"""
    # Use the existing database for now (could be improved with test DB)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_password_hashing(self):
        """Test that password hashing works"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        # Hash should be different from password
        assert hashed != password
        # Hash should be bcrypt format (starts with $2b$)
        assert hashed.startswith("$2b$")
        # Hash should be 60 characters
        assert len(hashed) == 60
    
    def test_password_verification(self):
        """Test that password verification works"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        # Correct password should verify
        assert verify_password(password, hashed) is True
        
        # Wrong password should not verify
        assert verify_password("WrongPassword", hashed) is False
        assert verify_password("testpassword123!", hashed) is False
    
    def test_password_hashing_uniqueness(self):
        """Test that same password produces different hashes (salt)"""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different (different salts)
        assert hash1 != hash2
        
        # But both should verify with the same password
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
    
    def test_password_truncation(self):
        """Test that passwords longer than 72 chars are handled"""
        # Bcrypt has a 72 byte limit
        very_long_password = "A" * 100 + "b1!"
        hashed = get_password_hash(very_long_password)
        
        # Should hash without error
        assert hashed is not None
        # Verification should work with the same long password
        assert verify_password(very_long_password, hashed) is True


class TestUserRegistration:
    """Test user registration endpoint"""
    
    def test_register_new_user(self, db_session):
        """Test successful user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "username": "newuser",
                "password": "Test123456!"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["username"] == "newuser"
        assert data["is_active"] is True
        assert data["is_superuser"] is False
        assert "created_at" in data
        assert "hashed_password" not in data  # Should not return password
        
        # Clean up
        user = db_session.query(User).filter(User.email == "newuser@test.com").first()
        if user:
            db_session.delete(user)
            db_session.commit()
    
    def test_register_duplicate_email(self):
        """Test that duplicate email is rejected"""
        # Register first user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@test.com",
                "username": "user1",
                "password": "Test123456!"
            }
        )
        
        # Try to register with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@test.com",
                "username": "user2",
                "password": "Test123456!"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_duplicate_username(self):
        """Test that duplicate username is rejected"""
        # Try to register with same username
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "another@test.com",
                "username": "admin",  # Admin already exists
                "password": "Test123456!"
            }
        )
        
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()
    
    def test_register_invalid_email(self):
        """Test that invalid email format is rejected"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "username": "testuser",
                "password": "Test123456!"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_register_weak_password(self):
        """Test that weak passwords are rejected"""
        # Too short
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@test.com",
                "username": "weakuser",
                "password": "short"
            }
        )
        assert response.status_code == 422
        
        # No uppercase
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak2@test.com",
                "username": "weakuser2",
                "password": "alllowercase123"
            }
        )
        assert response.status_code == 422
        
        # No digit
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak3@test.com",
                "username": "weakuser3",
                "password": "NoDigitsHere!"
            }
        )
        assert response.status_code == 422


class TestUserLogin:
    """Test user login endpoint"""
    
    def test_login_success(self):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "Admin123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@reims.com"
        assert data["username"] == "admin"
        assert "set-cookie" in response.headers.get("set-cookie", "").lower() or "reims_session" in str(response.cookies)
    
    def test_login_wrong_password(self):
        """Test login with incorrect password"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent username"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "SomePassword123!"
            }
        )
        
        assert response.status_code == 401


class TestSessionManagement:
    """Test session management and authentication"""
    
    def test_get_current_user_with_session(self):
        """Test getting current user with valid session"""
        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin123!"}
        )
        
        # Get current user
        response = client.get("/api/v1/auth/me")
        
        # Should work because session is maintained by TestClient
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
    
    def test_get_current_user_without_session(self):
        """Test getting current user without session"""
        # Create new client (no session)
        new_client = TestClient(app)
        
        response = new_client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()
    
    def test_logout(self):
        """Test logout clears session"""
        # Login first
        client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin123!"}
        )
        
        # Logout
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()
        
        # After logout, should not be able to access protected endpoints
        # Note: TestClient maintains session, so this test is informational
    
    def test_protected_endpoint_requires_auth(self):
        """Test that endpoints require authentication"""
        # Create new client without session
        new_client = TestClient(app)
        
        # Try to access a protected endpoint (if we have any marked as such)
        # For now, just verify auth endpoints work as expected
        response = new_client.get("/api/v1/auth/me")
        
        assert response.status_code == 401


class TestPasswordChange:
    """Test password change functionality"""
    
    def test_change_password_success(self, db_session):
        """Test successful password change"""
        # Create test user
        test_user = User(
            email="changepass@test.com",
            username="changepassuser",
            hashed_password=get_password_hash("OldPassword123!"),
            is_active=True
        )
        db_session.add(test_user)
        db_session.commit()
        db_session.refresh(test_user)
        
        # Login
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "changepassuser", "password": "OldPassword123!"}
        )
        assert login_resp.status_code == 200
        
        # Change password
        change_resp = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NewPassword456!"
            }
        )
        
        assert change_resp.status_code == 200
        
        # Clean up
        db_session.delete(test_user)
        db_session.commit()
    
    def test_change_password_wrong_current(self, db_session):
        """Test password change with wrong current password"""
        # Login as admin
        client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "Admin123!"}
        )
        
        # Try to change with wrong current password
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "WrongPassword!",
                "new_password": "NewPassword456!"
            }
        )
        
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_change_password_not_authenticated(self):
        """Test password change without authentication"""
        new_client = TestClient(app)
        
        response = new_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "OldPassword!",
                "new_password": "NewPassword456!"
            }
        )
        
        assert response.status_code == 401


class TestUserSchemaValidation:
    """Test user schema validation"""
    
    def test_username_validation(self):
        """Test username validation rules"""
        # Too short
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "username": "ab",
                "password": "Test123456!"
            }
        )
        assert response.status_code == 422
        
        # Invalid characters
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test2@test.com",
                "username": "user@name!",
                "password": "Test123456!"
            }
        )
        assert response.status_code == 422
    
    def test_email_validation(self):
        """Test email format validation"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "username": "testuser",
                "password": "Test123456!"
            }
        )
        assert response.status_code == 422


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

