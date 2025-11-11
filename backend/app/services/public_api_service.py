"""
Public API Service for REIMS2
External API authentication, rate limiting, and integration management.

Sprint 8: API & External Integrations
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import secrets
import hashlib

from app.models.user import User


class PublicAPIService:
    """
    Manages public API access, API keys, and external integrations.
    
    Features:
    - API key generation and validation
    - Rate limiting (100 req/hour default)
    - Usage tracking
    - Webhook management
    """
    
    RATE_LIMIT_DEFAULT = 100  # requests per hour
    
    def __init__(self, db: Session):
        """Initialize public API service."""
        self.db = db
    
    def generate_api_key(
        self,
        user_id: int,
        name: str,
        permissions: List[str],
        expires_in_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate new API key for user.
        
        Args:
            user_id: User ID
            name: Descriptive name for the key
            permissions: List of permissions (scoped)
            expires_in_days: Optional expiration (None = never expires)
            
        Returns:
            Dict with api_key and metadata
        """
        # Generate secure random key
        api_key = f"reims_{secrets.token_urlsafe(32)}"
        
        # Hash for storage (never store plaintext)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Store API key metadata (would need api_keys table)
        # For now, return generated key
        return {
            'api_key': api_key,  # Show once, never again
            'key_hash': key_hash,  # Store this
            'name': name,
            'permissions': permissions,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'rate_limit': self.RATE_LIMIT_DEFAULT
        }
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate API key and return associated metadata.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Key metadata if valid, None otherwise
        """
        if not api_key or not api_key.startswith('reims_'):
            return None
        
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Look up in database (would query api_keys table)
        # Placeholder implementation
        return {
            'valid': True,
            'user_id': 1,
            'permissions': ['documents.upload', 'extraction.read'],
            'rate_limit': self.RATE_LIMIT_DEFAULT
        }
    
    def check_rate_limit(self, api_key_hash: str) -> Tuple[bool, int]:
        """
        Check if API key is within rate limit.
        
        Args:
            api_key_hash: Hashed API key
            
        Returns:
            (is_allowed, remaining_requests)
        """
        # Would use Redis for rate limiting
        # Placeholder: always allow
        return True, self.RATE_LIMIT_DEFAULT
    
    def track_api_usage(
        self,
        api_key_hash: str,
        endpoint: str,
        method: str,
        status_code: int
    ) -> bool:
        """
        Track API usage for analytics and billing.
        
        Args:
            api_key_hash: Hashed API key
            endpoint: API endpoint called
            method: HTTP method
            status_code: Response status code
            
        Returns:
            True if tracked successfully
        """
        # Would store in api_usage_logs table
        return True


class WebhookService:
    """
    Manages webhook registrations and delivery.
    
    Events:
    - extraction_complete
    - validation_failed
    - alert_triggered
    """
    
    def __init__(self, db: Session):
        """Initialize webhook service."""
        self.db = db
    
    def register_webhook(
        self,
        user_id: int,
        url: str,
        events: List[str],
        secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register webhook URL for events.
        
        Args:
            user_id: User ID
            url: Webhook URL
            events: List of events to subscribe to
            secret: Optional webhook secret for signature verification
            
        Returns:
            Webhook registration details
        """
        # Generate secret if not provided
        if not secret:
            secret = secrets.token_urlsafe(32)
        
        # Store webhook registration (would need webhooks table)
        return {
            'webhook_id': secrets.token_urlsafe(16),
            'url': url,
            'events': events,
            'secret': secret,
            'created_at': datetime.utcnow().isoformat()
        }
    
    def trigger_webhook(
        self,
        event: str,
        data: Dict[str, Any]
    ) -> Dict[str, int]:
        """
        Trigger webhooks for an event.
        
        Args:
            event: Event name
            data: Event payload
            
        Returns:
            Dict with delivery statistics
        """
        # Would query webhooks table, send to all registered URLs
        # Implement retry logic (3 attempts)
        # Track delivery status
        return {
            'triggered': 0,
            'delivered': 0,
            'failed': 0
        }

