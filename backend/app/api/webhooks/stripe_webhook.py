
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
    if event['type'] in [
        'customer.subscription.updated',
        'customer.subscription.deleted',
        'customer.subscription.created',
    ]:
        subscription = event['data']['object']
        customer_id = subscription.get('customer', '')
        status_ = subscription.get('status', '')
        # Map Stripe status to our enum: trialing, active, past_due, canceled, unpaid
        if status_ in ('trialing', 'active'):
            mapped_status = status_
        elif status_ in ('canceled', 'unpaid'):
            mapped_status = status_
        elif status_ == 'past_due':
            mapped_status = 'past_due'
        else:
            mapped_status = status_ or 'active'
        org = db.query(Organization).filter(
            Organization.stripe_customer_id == str(customer_id)
        ).first()
        if org:
            logger.info(f"Updating subscription for Org {org.id} to {mapped_status}")
            org.subscription_status = mapped_status
            db.commit()
        else:
            logger.warning(f"Received webhook for unknown customer {customer_id}")

    # P2: Invoice events - sync payment status
    elif event['type'] in ['invoice.paid', 'invoice.payment_failed', 'invoice.payment_action_required']:
        invoice = event['data']['object']
        customer_id = invoice.get('customer')
        if not customer_id:
            return {"status": "success"}
        org = db.query(Organization).filter(
            Organization.stripe_customer_id == str(customer_id)
        ).first()
        if event['type'] == 'invoice.payment_failed' and org:
            # Past due when payment fails
            logger.info(f"Payment failed for Org {org.id}, marking past_due")
            org.subscription_status = 'past_due'
            db.commit()
        elif event['type'] == 'invoice.paid' and org:
            # Restore active when payment succeeds
            if org.subscription_status == 'past_due':
                logger.info(f"Payment received for Org {org.id}, restoring active")
                org.subscription_status = 'active'
                db.commit()

    return {"status": "success"}
