
from fastapi import HTTPException, status, Depends
from app.models.organization import Organization
from app.api.dependencies import get_current_organization
import logging

logger = logging.getLogger(__name__)

def require_active_subscription(
    current_org: Organization = Depends(get_current_organization)
) -> Organization:
    """
    Dependency to ensure the organization has an active subscription.
    Blocks access if status is 'canceled', 'unpaid', or 'past_due'.
    Allowed: 'active', 'trialing'.
    """
    allowed_statuses = ["active", "trialing"]
    
    if current_org.subscription_status not in allowed_statuses:
        logger.warning(f"Blocked access for Org {current_org.id} (Status: {current_org.subscription_status})")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Subscription is {current_org.subscription_status}. Please update your billing."
        )
        
    return current_org

def require_feature(feature_key: str):
    """
    Factory for feature-flag based checks (placeholder for future plan tiers).
    Usage: @router.get("/", dependencies=[Depends(require_feature("advanced_reports"))])
    """
    def _dependency(current_org: Organization = Depends(get_current_organization)):
        # Placeholder logic: In future, check Plan capabilities
        # if feature_key not in current_org.plan.features: raise 403
        return current_org
    return _dependency
