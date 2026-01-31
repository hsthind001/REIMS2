"""
JWT Authentication Tests (E1-S1)

Unit tests for JWT token validation: valid token, expired token,
invalid signature, malformed token, missing sub → 401.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

import jwt
from fastapi import HTTPException

from app.core.jwt_auth import JWTAuthService, get_jwt_service


# Test secret key (32+ chars for validation)
TEST_SECRET = "test-secret-key-for-jwt-validation-min-32-chars"
TEST_ALGORITHM = "HS256"


@pytest.fixture
def jwt_service():
    """Create JWT service with test config."""
    with patch("app.core.jwt_auth.settings") as mock_settings:
        mock_settings.SECRET_KEY = TEST_SECRET
        mock_settings.ALGORITHM = TEST_ALGORITHM
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        yield JWTAuthService()


class TestJWTValidToken:
    """Test valid token validation."""

    def test_verify_valid_token_returns_payload(self, jwt_service):
        """Valid token should return decoded payload."""
        token = jwt_service.create_access_token(
            user_id=42,
            username="testuser",
            email="test@example.com",
            roles=["analyst"],
        )
        payload = jwt_service.verify_token(token)
        assert payload["sub"] == "42"
        assert payload["username"] == "testuser"
        assert payload["email"] == "test@example.com"
        assert payload["roles"] == ["analyst"]
        assert "exp" in payload
        assert "iat" in payload

    def test_get_user_from_token_returns_user_info(self, jwt_service):
        """get_user_from_token should return user dict."""
        token = jwt_service.create_access_token(
            user_id=99,
            username="analyst",
            email="analyst@example.com",
        )
        user_info = jwt_service.get_user_from_token(token)
        assert user_info["user_id"] == 99
        assert user_info["username"] == "analyst"
        assert user_info["email"] == "analyst@example.com"
        assert user_info["roles"] == []


class TestJWTExpiredToken:
    """Test expired token returns 401."""

    def test_expired_token_raises_401(self, jwt_service):
        """Expired token should raise HTTPException 401."""
        # Create token with exp in the past
        payload = {
            "sub": "1",
            "username": "user",
            "email": "user@test.com",
            "exp": datetime.utcnow() - timedelta(minutes=5),
            "iat": datetime.utcnow() - timedelta(hours=1),
            "type": "access",
        }
        token = jwt.encode(
            payload,
            TEST_SECRET,
            algorithm=TEST_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            jwt_service.verify_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()


class TestJWTInvalidSignature:
    """Test invalid signature returns 401."""

    def test_invalid_signature_raises_401(self, jwt_service):
        """Token signed with wrong secret should raise 401."""
        # Sign with different secret
        payload = {
            "sub": "1",
            "username": "user",
            "email": "user@test.com",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "type": "access",
        }
        token = jwt.encode(
            payload,
            "wrong-secret-key-for-testing-invalid-signature",
            algorithm=TEST_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            jwt_service.verify_token(token)
        assert exc_info.value.status_code == 401
        assert "WWW-Authenticate" in exc_info.value.headers


class TestJWTMalformedToken:
    """Test malformed token returns 401."""

    def test_malformed_token_raises_401(self, jwt_service):
        """Malformed token string should raise 401."""
        malformed_tokens = [
            "garbage",  # no segments
            "",  # empty
            "a.b",  # not enough segments
        ]
        for token in malformed_tokens:
            with pytest.raises(HTTPException) as exc_info:
                jwt_service.verify_token(token)
            assert exc_info.value.status_code == 401


class TestJWTMissingSub:
    """Test token with missing sub claim returns 401."""

    def test_missing_sub_raises_401(self, jwt_service):
        """Token without 'sub' claim should raise 401 when extracting user."""
        payload = {
            "username": "user",
            "email": "user@test.com",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "type": "access",
        }
        # No 'sub' in payload
        token = jwt.encode(
            payload,
            TEST_SECRET,
            algorithm=TEST_ALGORITHM,
        )
        # verify_token succeeds (sub not required by JWT spec), but get_user_from_token raises 401
        with pytest.raises(HTTPException) as exc_info:
            jwt_service.get_user_from_token(token)
        assert exc_info.value.status_code == 401
