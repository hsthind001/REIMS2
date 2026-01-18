"""
Billing and Subscription Management API Endpoints

Provides endpoints for:
- Viewing subscription status
- Managing billing information
- Accessing invoice history
- Creating Stripe customer portal sessions
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from app.db.database import get_db
from app.models.user import User
from app.models.organization import Organization
from app.api.dependencies import get_current_user, get_current_organization
from pydantic import BaseModel

# Import Stripe if available
try:
    import stripe
    from app.core.config import settings
    if hasattr(settings, 'STRIPE_API_KEY') and settings.STRIPE_API_KEY:
        stripe.api_key = settings.STRIPE_API_KEY
        STRIPE_AVAILABLE = True
    else:
        STRIPE_AVAILABLE = False
except ImportError:
    STRIPE_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic Models
class SubscriptionResponse(BaseModel):
    id: int
    organization_name: str
    subscription_status: str
    stripe_customer_id: Optional[str]
    plan_name: str
    billing_cycle: str
    next_billing_date: Optional[str]
    amount: Optional[float]
    currency: str
    
    class Config:
        from_attributes = True


class InvoiceItem(BaseModel):
    id: str
    invoice_number: str
    amount: float
    currency: str
    status: str
    created_at: datetime
    due_date: Optional[datetime]
    pdf_url: Optional[str]


class PlanResponse(BaseModel):
    id: str
    name: str
    description: str
    price_monthly: float
    price_yearly: float
    currency: str
    features: List[str]
    is_popular: bool = False


class PortalSessionResponse(BaseModel):
    url: str


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    request: Request,
    current_org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current organization's subscription details
    """
    # Debug logging
    logger.info(f"Billing subscription request from user: {current_user.username}")
    logger.info(f"Organization: {current_org.name} (ID: {current_org.id})")
    
    # Default response with organization data
    subscription_data = {
        "id": current_org.id,
        "organization_name": current_org.name,
        "subscription_status": current_org.subscription_status or "active",
        "stripe_customer_id": current_org.stripe_customer_id,
        "plan_name": "Professional",  # Default plan
        "billing_cycle": "monthly",
        "next_billing_date": None,
        "amount": 99.00,
        "currency": "usd"
    }
    
    # If Stripe is available and customer exists, fetch real data
    if STRIPE_AVAILABLE and current_org.stripe_customer_id:
        try:
            # Get customer subscriptions
            subscriptions = stripe.Subscription.list(
                customer=current_org.stripe_customer_id,
                limit=1
            )
            
            if subscriptions.data:
                sub = subscriptions.data[0]
                subscription_data.update({
                    "subscription_status": sub.status,
                    "billing_cycle": sub.items.data[0].plan.interval if sub.items.data else "monthly",
                    "next_billing_date": datetime.fromtimestamp(sub.current_period_end).isoformat() if sub.current_period_end else None,
                    "amount": sub.items.data[0].plan.amount / 100 if sub.items.data else 0,
                    "currency": sub.currency
                })
                
        except Exception as e:
            logger.error(f"Failed to fetch Stripe subscription: {e}")
            # Continue with default data
    
    return SubscriptionResponse(**subscription_data)


@router.get("/invoices", response_model=List[InvoiceItem])
async def get_invoices(
    limit: int = 10,
    offset: int = 0,
    current_org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user)
):
    """
    Get billing invoices for the organization
    """
    invoices = []
    
    if STRIPE_AVAILABLE and current_org.stripe_customer_id:
        try:
            stripe_invoices = stripe.Invoice.list(
                customer=current_org.stripe_customer_id,
                limit=limit
            )
            
            for inv in stripe_invoices.data:
                invoices.append(InvoiceItem(
                    id=inv.id,
                    invoice_number=inv.number or inv.id,
                    amount=inv.amount_paid / 100,
                    currency=inv.currency,
                    status=inv.status,
                    created_at=datetime.fromtimestamp(inv.created),
                    due_date=datetime.fromtimestamp(inv.due_date) if inv.due_date else None,
                    pdf_url=inv.invoice_pdf
                ))
                
        except Exception as e:
            logger.error(f"Failed to fetch invoices: {e}")
            # Return empty list on error
    
    # Return mock data if no Stripe or no customer
    if not invoices:
        # Mock invoice for demonstration
        invoices = [
            InvoiceItem(
                id="inv_mock_001",
                invoice_number="INV-2026-001",
                amount=99.00,
                currency="usd",
                status="paid",
                created_at=datetime.now(),
                due_date=None,
                pdf_url=None
            )
        ]
    
    return invoices


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal_session(
    return_url: str = "http://localhost:5173/#admin",
    current_org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user)
):
    """
    Create a Stripe customer portal session for managing billing
    """
    if not STRIPE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Stripe integration not configured"
        )
    
    if not current_org.stripe_customer_id:
        raise HTTPException(
            status_code=404,
            detail="No billing account found for this organization"
        )
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=current_org.stripe_customer_id,
            return_url=return_url
        )
        
        return PortalSessionResponse(url=session.url)
        
    except Exception as e:
        logger.error(f"Failed to create portal session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create billing portal session"
        )


@router.get("/plans", response_model=List[PlanResponse])
async def get_plans(
    current_user: User = Depends(get_current_user)
):
    """
    Get available subscription plans
    """
    # Mock plans for now - in production, fetch from Stripe or database
    plans = [
        PlanResponse(
            id="plan_starter",
            name="Starter",
            description="Perfect for small portfolios",
            price_monthly=49.00,
            price_yearly=490.00,
            currency="usd",
            features=[
                "Up to 10 properties",
                "Basic financial reporting",
                "Email support",
                "1GB storage"
            ],
            is_popular=False
        ),
        PlanResponse(
            id="plan_professional",
            name="Professional",
            description="For growing real estate businesses",
            price_monthly=99.00,
            price_yearly=990.00,
            currency="usd",
            features=[
                "Up to 50 properties",
                "Advanced analytics",
                "Priority support",
                "10GB storage",
                "API access",
                "Custom reports"
            ],
            is_popular=True
        ),
        PlanResponse(
            id="plan_enterprise",
            name="Enterprise",
            description="For large-scale operations",
            price_monthly=299.00,
            price_yearly=2990.00,
            currency="usd",
            features=[
                "Unlimited properties",
                "White-label options",
                "Dedicated support",
                "Unlimited storage",
                "Custom integrations",
                "SLA guarantee",
                "Advanced security"
            ],
            is_popular=False
        )
    ]
    
    return plans
