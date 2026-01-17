"""
User schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional
import re


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """Username must be alphanumeric with optional underscores/hyphens"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username must be alphanumeric (underscores and hyphens allowed)')
        return v


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8, max_length=100)
    organization_name: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Basic password strength validation"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None



from typing import List
# Forward reference or import if no circular dependency
# Since organization.py doesn't import user.py, we can import it here
try:
    from app.schemas.organization import OrganizationMemberResponse
except ImportError:
    # Handle circular if structure changes later
    pass

class UserResponse(UserBase):
    """Schema for user data in responses"""
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    organization_memberships: List['OrganizationMemberResponse'] = []
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for login request"""
    username: str
    password: str


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Basic password strength validation"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
