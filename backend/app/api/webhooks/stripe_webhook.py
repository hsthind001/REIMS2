
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.organization import Organization
from app.core.config import settings
import logging
import json

# Try importing stripe, handle if missing
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Handle Stripe Webhooks for subscription updates.
    """
    if not STRIPE_AVAILABLE:
        logger.warning("Stripe webhook received but 'stripe' library not installed.")
        return {"status": "ignored", "reason": "stripe_lib_missing"}

    if not settings.STRIPE_WEBHOOK_SECRET:
         logger.warning("Stripe webhook received but STRIPE_WEBHOOK_SECRET not set.")
         # Return 200 to stop Stripe from retrying if we haven't configured it
         return {"status": "ignored", "reason": "secret_missing"}

    payload = await request.body()
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
         logger.error(f"Stripe webhook error: {e}")
         raise HTTPException(status_code=400, detail="Webhook Error")

    # Handle Events
    if event['type'] in ['customer.subscription.updated', 'customer.subscription.deleted', 'customer.subscription.created']:
        subscription = event['data']['object']
        customer_id = subscription['customer']
        status_ = subscription['status']
        
        # Find Org
        org = db.query(Organization).filter(Organization.stripe_customer_id == customer_id).first()
        
        if org:
            logger.info(f"Updating subscription for Org {org.id} to {status_}")
            org.subscription_status = status_
            db.commit()
        else:
            logger.warning(f"Received webhook for unknown customer {customer_id}")

    return {"status": "success"}
