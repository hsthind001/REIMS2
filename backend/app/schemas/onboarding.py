
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.schemas.user import UserCreate
from app.schemas.organization import OrganizationResponse
from app.schemas.user import UserResponse

class OnboardingRequest(BaseModel):
    """
    Request model for full SaaS onboarding (Org + User).
    """
    organization_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    username: str = Field(..., min_length=3)
    username: str = Field(..., min_length=3)
    
    # Optional payment info for future use
    payment_method_id: Optional[str] = None
    plan_id: Optional[str] = None

class OnboardingResponse(BaseModel):
    """
    Response model returning everything created.
    """
    organization: OrganizationResponse
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
