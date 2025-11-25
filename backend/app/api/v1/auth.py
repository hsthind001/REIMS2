"""
Authentication endpoints

Session-based authentication using HTTP-only cookies
No JWT - simpler session management with Starlette middleware
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, PasswordChange
from app.core.security import get_password_hash, verify_password
from app.core.config import settings


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    
    - Validates email is unique
    - Validates username is unique  
    - Hashes password with bcrypt
    - Creates user in database
    
    Returns:
        UserResponse: Created user data (without password)
    """
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_superuser=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/login", response_model=UserResponse)
def login(
    login_data: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Login with username and password
    
    - Verifies credentials
    - Creates session cookie (HTTP-only, secure)
    - Returns user data
    
    Returns:
        UserResponse: Logged in user data
    """
    # Find user by username
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Set session cookie (Starlette session middleware handles this)
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    
    return user


@router.post("/logout")
def logout(request: Request):
    """
    Logout current user
    
    - Clears session cookie
    - Invalidates session
    
    Returns:
        dict: Success message
    """
    request.session.clear()
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(request: Request, db: Session = Depends(get_db)):
    """
    Get current logged-in user information
    
    - Reads user ID from session
    - Returns user data
    
    Returns:
        UserResponse: Current user data
    """
    user_id = request.session.get("user_id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        # Session exists but user doesn't - clear session
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Change current user's password
    
    - Verifies current password
    - Updates to new password
    - Maintains session
    
    Returns:
        dict: Success message
    """
    user_id = request.session.get("user_id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not verify_password(password_data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


# ==================== JWT/OAuth2 Endpoints (BR-006) ====================

from app.core.jwt_auth import get_jwt_service
from pydantic import BaseModel
from typing import Optional


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


@router.post("/token", response_model=TokenResponse)
def login_jwt(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with JWT token (OAuth2-compatible)
    
    Returns JWT access token and refresh token.
    Can be used alongside session-based auth.
    
    **BR-006:** JWT/OAuth2 authentication support
    
    Returns:
        TokenResponse with access_token and refresh_token
    """
    # Find user by username
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Get user roles (if RBAC is implemented)
    roles = []
    if hasattr(user, 'roles'):
        roles = [role.name for role in user.roles] if user.roles else []
    
    # Create tokens
    jwt_service = get_jwt_service()
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
        roles=roles
    )
    refresh_token = jwt_service.create_refresh_token(
        user_id=user.id,
        username=user.username
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/token/refresh", response_model=TokenResponse)
def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh JWT access token using refresh token
    
    **BR-006:** OAuth2 token refresh support
    
    Returns:
        New TokenResponse with new access_token
    """
    jwt_service = get_jwt_service()
    
    try:
        # Verify refresh token
        payload = jwt_service.verify_token(refresh_request.refresh_token)
        
        # Check token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user roles
        roles = []
        if hasattr(user, 'roles'):
            roles = [role.name for role in user.roles] if user.roles else []
        
        # Create new access token
        access_token = jwt_service.create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            roles=roles
        )
        
        # Optionally create new refresh token (rotate)
        new_refresh_token = jwt_service.create_refresh_token(
            user_id=user.id,
            username=user.username
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/token/verify")
def verify_token_endpoint(
    token: str = None,
    authorization: Optional[str] = None
):
    """
    Verify JWT token validity
    
    **BR-006:** Token verification endpoint
    
    Accepts token as query parameter or Authorization header:
    - Query: ?token=<jwt_token>
    - Header: Authorization: Bearer <jwt_token>
    """
    # Extract token from Authorization header if provided
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token not provided"
        )
    
    jwt_service = get_jwt_service()
    payload = jwt_service.verify_token(token)
    
    return {
        "valid": True,
        "user_id": int(payload.get("sub")),
        "username": payload.get("username"),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
        "expires_at": payload.get("exp")
    }

