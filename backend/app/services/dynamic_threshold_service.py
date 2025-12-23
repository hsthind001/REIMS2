"""
Dynamic Threshold Service

Adjusts DSCR thresholds based on interest rates, market conditions, and property risk profiles.
"""

from typing import Dict, Optional, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class DynamicThresholdService:
    """
    Dynamically adjusts DSCR thresholds.
    
    Factors:
    - Interest rate environment
    - Market conditions
    - Property-specific risk profiles
    """
    
    def __init__(self, db: Session):
        """Initialize dynamic threshold service."""
        self.db = db
        self.base_dscr_threshold = 1.25
    
    def calculate_dynamic_threshold(
        self,
        property_id: int,
        current_interest_rate: float,
        market_volatility: float = 0.0
    ) -> Decimal:
        """
        Calculate dynamic DSCR threshold.
        
        Args:
            property_id: Property ID
            current_interest_rate: Current interest rate (e.g., 5.0 for 5%)
            market_volatility: Market volatility index (0-1)
            
        Returns:
            Dynamic DSCR threshold
        """
        # Base threshold
        threshold = Decimal(str(self.base_dscr_threshold))
        
        # Adjust for interest rates
        # Higher rates -> higher threshold needed
        if current_interest_rate > 6.0:
            threshold += Decimal('0.10')  # Increase by 0.10
        elif current_interest_rate < 4.0:
            threshold -= Decimal('0.05')  # Decrease by 0.05
        
        # Adjust for market volatility
        if market_volatility > 0.3:
            threshold += Decimal(str(market_volatility * 0.1))
        
        # Adjust for property risk (would query property risk profile)
        property_risk = self._get_property_risk(property_id)
        if property_risk == 'high':
            threshold += Decimal('0.15')
        elif property_risk == 'low':
            threshold -= Decimal('0.05')
        
        return max(Decimal('1.0'), threshold)  # Minimum 1.0
    
    def _get_property_risk(self, property_id: int) -> str:
        """Get property risk profile (placeholder)."""
        # In production, would query property risk metrics
        return 'medium'
