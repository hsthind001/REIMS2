"""
Materiality Service

Calculates materiality thresholds and risk classifications for reconciliation.
Supports property-specific, statement-specific, and account-specific configurations.
"""
import logging
from typing import Dict, Optional, Tuple
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.materiality_config import MaterialityConfig, AccountRiskClass
from app.models.property import Property
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData

logger = logging.getLogger(__name__)


class MaterialityService:
    """Service for calculating materiality thresholds and risk classifications"""
    
    def __init__(self, db: Session):
        """
        Initialize materiality service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_risk_class(
        self,
        property_id: int,
        account_code: Optional[str] = None,
        account_name: Optional[str] = None
    ) -> str:
        """
        Get risk class for an account
        
        Args:
            property_id: Property ID
            account_code: Account code (e.g., '1000-0000')
            account_name: Account name (optional)
            
        Returns:
            Risk class: 'critical', 'high', 'medium', 'low'
        """
        # Try account-specific risk class first
        if account_code:
            # Find matching risk class by pattern
            risk_classes = self.db.query(AccountRiskClass).filter(
                AccountRiskClass.is_active == True
            ).all()
            
            for risk_class in risk_classes:
                # Simple pattern matching (supports wildcards like '1*', '2*')
                pattern = risk_class.account_code_pattern.replace('*', '')
                if account_code.startswith(pattern):
                    # Check property type override if exists
                    if risk_class.property_type_override:
                        property_obj = self.db.query(Property).filter(
                            Property.id == property_id
                        ).first()
                        if property_obj and property_obj.property_type:
                            override = risk_class.property_type_override.get(property_obj.property_type)
                            if override:
                                return override.get('risk_class', risk_class.risk_class)
                    return risk_class.risk_class
        
        # Default to 'medium' if no match found
        return 'medium'
    
    def calculate_materiality_threshold(
        self,
        property_id: int,
        statement_type: str,
        account_code: Optional[str] = None,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Decimal]:
        """
        Calculate materiality threshold for a property/statement/account
        
        Args:
            property_id: Property ID
            statement_type: Statement type (balance_sheet, income_statement, etc.)
            account_code: Account code (optional, for account-specific threshold)
            amount: Current amount (optional, for relative threshold calculation)
            
        Returns:
            Dict with 'absolute_threshold' and 'relative_threshold_percent'
        """
        today = date.today()
        
        # Try to find most specific config (account > statement > property > global)
        config = None
        
        # 1. Account-specific config
        if account_code:
            config = self.db.query(MaterialityConfig).filter(
                and_(
                    or_(
                        MaterialityConfig.property_id == property_id,
                        MaterialityConfig.property_id.is_(None)
                    ),
                    MaterialityConfig.statement_type == statement_type,
                    MaterialityConfig.account_code == account_code,
                    MaterialityConfig.effective_date <= today,
                    or_(
                        MaterialityConfig.expires_at.is_(None),
                        MaterialityConfig.expires_at >= today
                    )
                )
            ).order_by(
                MaterialityConfig.property_id.desc().nullslast(),  # Property-specific first
                MaterialityConfig.effective_date.desc()
            ).first()
        
        # 2. Statement-specific config
        if not config:
            config = self.db.query(MaterialityConfig).filter(
                and_(
                    or_(
                        MaterialityConfig.property_id == property_id,
                        MaterialityConfig.property_id.is_(None)
                    ),
                    MaterialityConfig.statement_type == statement_type,
                    MaterialityConfig.account_code.is_(None),
                    MaterialityConfig.effective_date <= today,
                    or_(
                        MaterialityConfig.expires_at.is_(None),
                        MaterialityConfig.expires_at >= today
                    )
                )
            ).order_by(
                MaterialityConfig.property_id.desc().nullslast(),
                MaterialityConfig.effective_date.desc()
            ).first()
        
        # 3. Property-level default
        if not config:
            config = self.db.query(MaterialityConfig).filter(
                and_(
                    MaterialityConfig.property_id == property_id,
                    MaterialityConfig.statement_type.is_(None),
                    MaterialityConfig.account_code.is_(None),
                    MaterialityConfig.effective_date <= today,
                    or_(
                        MaterialityConfig.expires_at.is_(None),
                        MaterialityConfig.expires_at >= today
                    )
                )
            ).order_by(
                MaterialityConfig.effective_date.desc()
            ).first()
        
        # 4. Global default
        if not config:
            config = self.db.query(MaterialityConfig).filter(
                and_(
                    MaterialityConfig.property_id.is_(None),
                    MaterialityConfig.statement_type.is_(None),
                    MaterialityConfig.account_code.is_(None),
                    MaterialityConfig.effective_date <= today,
                    or_(
                        MaterialityConfig.expires_at.is_(None),
                        MaterialityConfig.expires_at >= today
                    )
                )
            ).order_by(
                MaterialityConfig.effective_date.desc()
            ).first()
        
        # Default values if no config found
        if not config:
            # Default materiality thresholds
            absolute_threshold = Decimal('1000.00')  # $1,000 default
            relative_threshold_percent = Decimal('1.0')  # 1% default
        else:
            absolute_threshold = config.absolute_threshold
            relative_threshold_percent = config.relative_threshold_percent or Decimal('1.0')
        
        return {
            'absolute_threshold': absolute_threshold,
            'relative_threshold_percent': relative_threshold_percent,
            'risk_class': config.risk_class if config else 'medium',
            'tolerance_type': config.tolerance_type if config else 'standard',
            'tolerance_absolute': config.tolerance_absolute,
            'tolerance_percent': config.tolerance_percent
        }
    
    def get_dynamic_tolerance(
        self,
        property_id: int,
        account_code: str,
        match_type: str,
        statement_type: str
    ) -> Dict[str, Decimal]:
        """
        Get dynamic tolerance based on risk class and match type
        
        Args:
            property_id: Property ID
            account_code: Account code
            match_type: Match type (exact, fuzzy, calculated, inferred)
            statement_type: Statement type
            
        Returns:
            Dict with 'absolute' and 'percent' tolerance values
        """
        # Get risk class
        risk_class = self.get_risk_class(property_id, account_code)
        
        # Get materiality config
        materiality = self.calculate_materiality_threshold(
            property_id, statement_type, account_code
        )
        
        # Base tolerances by risk class
        base_tolerances = {
            'critical': {'absolute': Decimal('0.01'), 'percent': Decimal('0.01')},  # Very strict
            'high': {'absolute': Decimal('1.00'), 'percent': Decimal('0.1')},
            'medium': {'absolute': Decimal('10.00'), 'percent': Decimal('1.0')},
            'low': {'absolute': Decimal('100.00'), 'percent': Decimal('5.0')}
        }
        
        # Adjust by tolerance_type from config
        tolerance_type = materiality.get('tolerance_type', 'standard')
        tolerance_multipliers = {
            'strict': Decimal('0.5'),
            'standard': Decimal('1.0'),
            'loose': Decimal('2.0')
        }
        
        multiplier = tolerance_multipliers.get(tolerance_type, Decimal('1.0'))
        
        base = base_tolerances.get(risk_class, base_tolerances['medium'])
        
        # Use config overrides if available
        absolute = materiality.get('tolerance_absolute')
        percent = materiality.get('tolerance_percent')
        
        if absolute is None:
            absolute = base['absolute'] * multiplier
        if percent is None:
            percent = base['percent'] * multiplier
        
        # Adjust by match type (exact matches can be stricter)
        if match_type == 'exact':
            absolute = absolute * Decimal('0.5')
        elif match_type == 'fuzzy':
            absolute = absolute * Decimal('1.5')
        
        return {
            'absolute': absolute,
            'percent': percent,
            'risk_class': risk_class
        }
    
    def is_material(
        self,
        property_id: int,
        amount: Decimal,
        account_code: Optional[str] = None,
        statement_type: Optional[str] = None
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if an amount is material
        
        Args:
            property_id: Property ID
            amount: Amount to check
            account_code: Account code (optional)
            statement_type: Statement type (optional)
            
        Returns:
            Tuple of (is_material: bool, details: dict)
        """
        if statement_type is None:
            statement_type = 'balance_sheet'  # Default
        
        materiality = self.calculate_materiality_threshold(
            property_id, statement_type, account_code, amount
        )
        
        absolute_threshold = materiality['absolute_threshold']
        relative_threshold_percent = materiality['relative_threshold_percent']
        
        # Check absolute threshold
        is_absolute_material = abs(amount) >= absolute_threshold
        
        # Check relative threshold (if we can calculate base amount)
        is_relative_material = False
        relative_base = None
        
        if relative_threshold_percent and statement_type:
            # Try to get revenue or total assets as base
            if statement_type == 'income_statement':
                # Get total revenue
                revenue = self.db.query(
                    func.sum(IncomeStatementData.period_amount)
                ).filter(
                    and_(
                        IncomeStatementData.property_id == property_id,
                        IncomeStatementData.account_code.like('4%')  # Revenue accounts
                    )
                ).scalar()
                if revenue:
                    relative_base = revenue
                    threshold_amount = revenue * (relative_threshold_percent / 100)
                    is_relative_material = abs(amount) >= threshold_amount
            elif statement_type == 'balance_sheet':
                # Get total assets
                assets = self.db.query(
                    func.sum(BalanceSheetData.amount)
                ).filter(
                    and_(
                        BalanceSheetData.property_id == property_id,
                        BalanceSheetData.account_code.like('1%')  # Asset accounts
                    )
                ).scalar()
                if assets:
                    relative_base = assets
                    threshold_amount = assets * (relative_threshold_percent / 100)
                    is_relative_material = abs(amount) >= threshold_amount
        
        is_material = is_absolute_material or is_relative_material
        
        return is_material, {
            'is_material': is_material,
            'absolute_threshold': absolute_threshold,
            'relative_threshold_percent': relative_threshold_percent,
            'relative_base': relative_base,
            'is_absolute_material': is_absolute_material,
            'is_relative_material': is_relative_material,
            'risk_class': materiality.get('risk_class', 'medium')
        }

