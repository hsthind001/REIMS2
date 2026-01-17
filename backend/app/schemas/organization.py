from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class OrganizationRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class OrganizationBase(BaseModel):
    name: str
    slug: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationResponse(OrganizationBase):
    id: int
    subscription_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class OrganizationMemberResponse(BaseModel):
    id: int
    organization_id: int
    role: str
    organization: OrganizationResponse
    
    class Config:
        from_attributes = True
