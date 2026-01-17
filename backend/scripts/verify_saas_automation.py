
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import logging
from datetime import datetime

# Add backend key path
sys.path.append('backend')

# MOCK STRIPE BEFORE IMPORTS
sys.modules['stripe'] = MagicMock()

from app.schemas.onboarding import OnboardingRequest
from app.models.organization import Organization
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_saas")

class TestSaaSAutomation(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = MagicMock()
        
    def test_onboarding_flow(self):
        """Test the registration endpoint logic"""
        from app.api.v1.endpoints.onboarding import register_organization
        
        logger.info("Testing Onboarding API...")
        
        # Mock Request
        req_data = OnboardingRequest(
            organization_name="Test SaaS Org",
            email="admin@saas.com",
            password="StrongPassword123!",
            username="saas_admin"
        )
        
        # Mock DB queries
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock DB add/commit
        self.mock_db.add = MagicMock()
        self.mock_db.commit = MagicMock()
        self.mock_db.refresh = MagicMock()
        
        # Patch dependencies
        with patch('app.api.v1.endpoints.onboarding.settings') as mock_settings:
            mock_settings.SECRET_KEY = "secret"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.STRIPE_API_KEY = "sk_test_mock"
            mock_settings.ALGORITHM = "HS256"
            
            response = register_organization(req_data, self.mock_db)
            
            self.assertEqual(response["organization"].name, "Test SaaS Org")
            self.assertTrue(response["user"].email == "admin@saas.com")
            # JWT Service returns a string token
            self.assertTrue(isinstance(response["access_token"], str))
            self.assertTrue(len(response["access_token"]) > 0)
            logger.info("✅ Onboarding API verified.")

    def test_feature_gating_middleware(self):
        """Test require_active_subscription"""
        from app.middleware.feature_gating import require_active_subscription
        from fastapi import HTTPException
        
        logger.info("Testing Feature Gating...")
        
        # Case 1: Active
        org_active = MagicMock(spec=Organization)
        org_active.subscription_status = 'active'
        self.assertEqual(require_active_subscription(org_active), org_active)
        
        # Case 2: Past Due (Should Raise)
        org_bad = MagicMock(spec=Organization)
        org_bad.subscription_status = 'past_due'
        
        with self.assertRaises(HTTPException) as cm:
            require_active_subscription(org_bad)
        
        self.assertEqual(cm.exception.status_code, 402)
        logger.info("✅ Feature Gating verified (Blocked past_due).")

class AsyncTestSaaS(unittest.IsolatedAsyncioTestCase):
     def setUp(self):
        self.mock_db = MagicMock()
        
     async def test_stripe_webhook_async(self):
        logger.info("Testing Stripe Webhook (Async)...")
        # Ensure we re-import or use the mocked module
        from app.api.webhooks.stripe_webhook import stripe_webhook
        import stripe # This is the mock
        
        mock_request = AsyncMock()
        mock_request.body.return_value = b'payload'
        
        mock_event = {
            'type': 'customer.subscription.updated',
            'data': {
                'object': {
                    'customer': 'cus_123',
                    'status': 'past_due'
                }
            }
        }
        stripe.Webhook.construct_event.return_value = mock_event
        
        mock_org = MagicMock()
        mock_org.subscription_status = 'active'
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_org
        
        with patch('app.api.webhooks.stripe_webhook.settings') as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
            
            await stripe_webhook(mock_request, "sig", self.mock_db)
            
            self.assertEqual(mock_org.subscription_status, 'past_due')
            logger.info("✅ Webhook verified.")

if __name__ == "__main__":
    unittest.main()
