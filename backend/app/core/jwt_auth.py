"""
JWT/OAuth2 Authentication Service

Provides JWT token-based authentication alongside existing session-based auth.
Supports both authentication methods for backward compatibility.

BR-006: Security & Compliance requirement
"""
import jwt
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, status
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class JWTAuthService:
    """
    JWT Authentication Service
    
    Provides:
    - JWT token generation
    - Token validation
    - Token refresh
    - OAuth2-compatible endpoints
    """
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    def create_access_token(
        self,
        user_id: int,
        username: str,
        email: str,
        roles: Optional[list] = None,
        additional_claims: Optional[Dict] = None
    ) -> str:
        """
        Create JWT access token
        
        Args:
            user_id: User ID
            username: Username
            email: User email
            roles: List of user roles
            additional_claims: Additional claims to include
            
        Returns:
            Encoded JWT token
        """
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": str(user_id),  # Subject (user ID)
            "username": username,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        if roles:
            payload["roles"] = roles
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def create_refresh_token(
        self,
        user_id: int,
        username: str
    ) -> str:
        """
        Create JWT refresh token (longer expiration)
        
        Args:
            user_id: User ID
            username: Username
            
        Returns:
            Encoded JWT refresh token
        """
        expire = datetime.utcnow() + timedelta(days=30)  # 30 days for refresh token
        
        payload = {
            "sub": str(user_id),
            "username": username,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_token(self, token: str) -> Dict:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException if token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def get_user_from_token(self, token: str) -> Dict:
        """
        Extract user information from token
        
        Args:
            token: JWT token string
            
        Returns:
            Dict with user_id, username, email, roles
            
        Raises:
            HTTPException 401 if 'sub' claim is missing
        """
        payload = self.verify_token(token)

        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing required 'sub' claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "user_id": int(payload["sub"]),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "roles": payload.get("roles", [])
        }


# Singleton instance
_jwt_service_instance: Optional[JWTAuthService] = None


def get_jwt_service() -> JWTAuthService:
    """Get singleton JWT service instance"""
    global _jwt_service_instance
    if _jwt_service_instance is None:
        _jwt_service_instance = JWTAuthService()
    return _jwt_service_instance

