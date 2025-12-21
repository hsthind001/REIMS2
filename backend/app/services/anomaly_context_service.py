"""
Anomaly Context Service

Provides context-aware anomaly detection by considering:
- Property lifecycle stages
- Cross-account relationships
- Business rules and known transition periods
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class AnomalyContextService:
    """
    Provides context for anomaly detection to reduce false positives.
    
    Methods:
    - Property lifecycle awareness
    - Cross-account validation
    - Business rule integration
    """
    
    def __init__(self, db: Session):
        """Initialize context service."""
        self.db = db
    
    def should_suppress_anomaly(
        self,
        property_id: int,
        account_code: str,
        anomaly: Dict[str, Any],
        current_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Determine if an anomaly should be suppressed based on context.
        
        Args:
            property_id: Property ID
            account_code: Account code with anomaly
            anomaly: Anomaly detection result
            current_date: Current period date
        
        Returns:
            Dict with 'should_suppress' (bool) and 'reason' (str)
        """
        # Check property lifecycle
        lifecycle_check = self._check_property_lifecycle(property_id, current_date)
        if lifecycle_check.get('should_suppress'):
            return {
                'should_suppress': True,
                'reason': lifecycle_check.get('reason', 'Property lifecycle transition'),
                'context': lifecycle_check
            }
        
        # Check cross-account relationships
        cross_account_check = self._check_cross_account_validation(
            property_id,
            account_code,
            anomaly
        )
        if cross_account_check.get('should_suppress'):
            return {
                'should_suppress': True,
                'reason': cross_account_check.get('reason', 'Cross-account validation'),
                'context': cross_account_check
            }
        
        # Check business rules
        business_rule_check = self._check_business_rules(
            property_id,
            account_code,
            anomaly
        )
        if business_rule_check.get('should_suppress'):
            return {
                'should_suppress': True,
                'reason': business_rule_check.get('reason', 'Business rule'),
                'context': business_rule_check
            }
        
        return {
            'should_suppress': False,
            'reason': None
        }
    
    def _check_property_lifecycle(
        self,
        property_id: int,
        current_date: Optional[datetime]
    ) -> Dict[str, Any]:
        """
        Check if property is in a transition period that might cause expected anomalies.
        
        Examples:
        - Recent renovation
        - Lease expirations
        - Property acquisition/disposition
        - Major tenant move-in/out
        """
        from app.models.property import Property
        
        property_obj = self.db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            return {'should_suppress': False}
        
        # Check for recent renovations (if renovation_date field exists)
        # This would require adding renovation_date to Property model
        # For now, we'll use a placeholder approach
        
        # Check property age
        if property_obj.acquisition_date:
            age_years = (current_date - property_obj.acquisition_date).days / 365.25 if current_date else 0
            
            # New properties (< 1 year) may have more volatility
            if age_years < 1:
                return {
                    'should_suppress': False,  # Don't suppress, but note context
                    'reason': 'New property - higher volatility expected',
                    'property_age_years': age_years
                }
        
        # Check for known transition periods (would need additional tables)
        # For now, return no suppression
        return {'should_suppress': False}
    
    def _check_cross_account_validation(
        self,
        property_id: int,
        account_code: str,
        anomaly: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate anomaly against related accounts.
        
        If related accounts show similar patterns, it might be a legitimate change
        rather than an anomaly.
        
        Examples:
        - Revenue drop should correlate with expense adjustments
        - Maintenance expense spike might correlate with repair revenue
        """
        # Define account relationships
        account_relationships = {
            # Revenue accounts
            '4010': ['5010', '5020'],  # Revenue -> Operating expenses
            '4020': ['5010'],  # Other revenue -> Operating expenses
            
            # Expense accounts
            '5010': ['4010'],  # Operating expenses -> Revenue
            '5020': ['4010'],  # Maintenance -> Revenue
            
            # Balance sheet relationships
            '1010': ['2010'],  # Cash -> Accounts payable
            '2010': ['1010'],  # Accounts payable -> Cash
        }
        
        # Extract account category (first 4 digits)
        account_category = account_code.split('-')[0] if '-' in account_code else account_code[:4]
        
        related_categories = account_relationships.get(account_category, [])
        
        if not related_categories:
            return {'should_suppress': False}
        
        # Check if related accounts also show anomalies
        # This would require querying recent anomalies for related accounts
        # For now, return no suppression (would need anomaly history)
        
        return {'should_suppress': False}
    
    def _check_business_rules(
        self,
        property_id: int,
        account_code: str,
        anomaly: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply business rules to validate anomalies.
        
        Examples:
        - Maintenance expenses are naturally more variable
        - Year-end adjustments are expected
        - Certain accounts have known seasonal patterns
        """
        # Account-specific rules
        account_category = account_code.split('-')[0] if '-' in account_code else account_code[:4]
        
        # Maintenance and repair accounts are more variable
        if account_category in ['5020', '5030']:  # Maintenance, Repairs
            if anomaly.get('severity') == 'medium':
                return {
                    'should_suppress': True,
                    'reason': 'Maintenance accounts have higher natural variability',
                    'account_category': account_category
                }
        
        # Year-end adjustments (December)
        if datetime.now().month == 12:
            if account_category in ['4010', '5010']:  # Revenue, Expenses
                if anomaly.get('severity') == 'medium':
                    return {
                        'should_suppress': True,
                        'reason': 'Year-end adjustments expected',
                        'month': 12
                    }
        
        return {'should_suppress': False}
    
    def get_expected_value_adjustment(
        self,
        property_id: int,
        account_code: str,
        base_expected_value: float,
        current_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get adjusted expected value based on property context.
        
        Args:
            property_id: Property ID
            account_code: Account code
            base_expected_value: Base expected value from forecasting
            current_date: Current period date
        
        Returns:
            Dict with adjusted_expected_value and adjustment_factor
        """
        adjustment_factor = 1.0
        adjustments = []
        
        # Property lifecycle adjustments
        lifecycle_adj = self._get_lifecycle_adjustment(property_id, account_code, current_date)
        if lifecycle_adj.get('factor') != 1.0:
            adjustment_factor *= lifecycle_adj['factor']
            adjustments.append(lifecycle_adj)
        
        adjusted_value = base_expected_value * adjustment_factor
        
        return {
            'adjusted_expected_value': adjusted_value,
            'base_expected_value': base_expected_value,
            'adjustment_factor': adjustment_factor,
            'adjustments': adjustments
        }
    
    def _get_lifecycle_adjustment(
        self,
        property_id: int,
        account_code: str,
        current_date: Optional[datetime]
    ) -> Dict[str, Any]:
        """Get adjustment factor based on property lifecycle stage."""
        from app.models.property import Property
        
        property_obj = self.db.query(Property).filter(Property.id == property_id).first()
        if not property_obj:
            return {'factor': 1.0}
        
        # New property adjustments
        if property_obj.acquisition_date and current_date:
            age_months = (current_date - property_obj.acquisition_date).days / 30.0
            
            # New properties (< 6 months) may have lower expected values initially
            if age_months < 6:
                return {
                    'factor': 0.8,  # 20% reduction for new properties
                    'reason': 'New property - lower baseline expected',
                    'age_months': age_months
                }
        
        return {'factor': 1.0}

