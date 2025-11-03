from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# Base User Schema
class UserBase(BaseModel):
    email: EmailStr
    username: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


# Schema for creating a user
class UserCreate(UserBase):
    password: str


# Schema for updating a user
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


# Schema for user response
class User(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

