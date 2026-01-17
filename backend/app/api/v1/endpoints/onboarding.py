
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.onboarding import OnboardingRequest, OnboardingResponse
from app.models.user import User
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.core.security import get_password_hash
from app.core.jwt_auth import get_jwt_service
from app.core.config import settings
from datetime import timedelta
import logging

# Import Stripe if available (mock/placeholder for now)
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register-org", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED)
def register_organization(
    request: OnboardingRequest,
    db: Session = Depends(get_db)
):
    """
    Self-Service Onboarding:
    Creates a new Organization, a new Admin User, and links them.
    Also handles Stripe Customer creation (placeholder).
    """
    
    # 1. Validation: Check if user exists
    existing_user = db.query(User).filter(
        (User.email == request.email) | (User.username == request.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
        
    # 2. Validation: Check if Organization name collision (optional, usually slugs)
    # Simple slugify for demo
    slug = request.organization_name.lower().replace(" ", "-")
    existing_org = db.query(Organization).filter(Organization.slug == slug).first()
    if existing_org:
         # Append random suffix in real world, or fail
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name is already taken"
        )

    try:
        # 3. Create Organization
        new_org = Organization(
            name=request.organization_name,
            slug=slug,
            subscription_status="active", # Default to active trial?
            stripe_customer_id=None # To be filled
        )
        db.add(new_org)
        db.flush() # Get ID
        
        # 4. Create User
        new_user = User(
            email=request.email,
            username=request.username,
            hashed_password=get_password_hash(request.password),
            is_active=True,
            is_superuser=False
        )
        db.add(new_user)
        db.flush() # Get ID
        
        # 5. Link User to Org as OWNER/ADMIN
        member_link = OrganizationMember(
            user_id=new_user.id,
            organization_id=new_org.id,
            role=OrganizationRole.OWNER.value
        )
        db.add(member_link)
        
        # 6. Stripe Integration (Mock)
        if STRIPE_AVAILABLE and settings.STRIPE_API_KEY:
            try:
                # stripe.api_key = settings.STRIPE_API_KEY
                # customer = stripe.Customer.create(email=request.email, name=request.organization_name)
                # new_org.stripe_customer_id = customer.id
                pass
            except Exception as e:
                logger.error(f"Stripe creation failed: {e}")
                # Don't fail the whole registration, just log
        
        db.commit()
        db.refresh(new_org)
        db.refresh(new_user)
        
        # 7. Generate Token
        jwt_service = get_jwt_service()
        # Note: create_access_token in JWTAuthService takes (user_id, username, email, roles...)
        # We need to adapt the call signature
        access_token = jwt_service.create_access_token(
            user_id=new_user.id, 
            username=new_user.username,
            email=new_user.email,
            roles=[OrganizationRole.OWNER.value]
        )
        
        return {
            "organization": new_org,
            "user": new_user,
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Onboarding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )
