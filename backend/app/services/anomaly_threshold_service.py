"""
Anomaly Threshold Service

Manages percentage-based thresholds for anomaly detection per account code.
Thresholds are stored as decimals (e.g., 0.01 = 1%).
Provides methods to get, create, update, and delete thresholds, as well as
manage the global default threshold.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, and_
import statistics
import numpy as np
from app.models.anomaly_threshold import AnomalyThreshold, SystemConfig
from app.models.chart_of_accounts import ChartOfAccounts
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData
from app.models.financial_period import FinancialPeriod
import logging

logger = logging.getLogger(__name__)


class AnomalyThresholdService:
    """Service for managing anomaly detection thresholds"""
    
    DEFAULT_THRESHOLD_KEY = "anomaly_threshold_default"
    SYSTEM_FALLBACK_THRESHOLD = Decimal("0.01")  # Fallback if no default set (1% = 0.01)
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_threshold(self, account_code: str) -> Optional[AnomalyThreshold]:
        """Get threshold for a specific account code"""
        return self.db.query(AnomalyThreshold).filter(
            AnomalyThreshold.account_code == account_code,
            AnomalyThreshold.is_active == True
        ).first()
    
    def get_threshold_value(
        self,
        account_code: str,
        property_id: Optional[int] = None,
        use_adaptive: bool = True
    ) -> Decimal:
        """
        Get threshold value for an account code.
        
        Enhanced with adaptive thresholds based on volatility.
        
        Args:
            account_code: Account code
            property_id: Optional property ID for property-specific thresholds
            use_adaptive: Whether to apply volatility-based adaptive adjustment
        
        Returns:
            Threshold value (as Decimal)
        """
        # Get base threshold (custom or default)
        threshold = self.get_threshold(account_code)
        base_threshold = self._validate_threshold_value(
            threshold.threshold_value if threshold else self.get_default_threshold()
        )
        
        # Apply adaptive adjustment if enabled
        if use_adaptive and property_id:
            adaptive_result = self._calculate_adaptive_threshold(
                property_id,
                account_code,
                base_threshold
            )
            if adaptive_result.get('adjusted_threshold'):
                return adaptive_result['adjusted_threshold']
        
        return base_threshold
    
    def _calculate_adaptive_threshold(
        self,
        property_id: int,
        account_code: str,
        base_threshold: Decimal
    ) -> Dict[str, Any]:
        """
        Calculate adaptive threshold based on account volatility.
        
        High volatility accounts get higher thresholds automatically.
        
        Args:
            property_id: Property ID
            account_code: Account code
            base_threshold: Base threshold value
        
        Returns:
            Dict with adjusted_threshold and adjustment details
        """
        try:
            # Get historical values for this account
            historical_values = self._get_historical_values(property_id, account_code, lookback_months=24)
            
            if len(historical_values) < 6:
                # Not enough data for volatility calculation
                return {
                    'adjusted_threshold': base_threshold,
                    'volatility': None,
                    'adjustment_factor': 1.0
                }
            
            # Calculate volatility (coefficient of variation)
            values_array = np.array(historical_values)
            mean_val = np.mean(values_array)
            std_val = np.std(values_array)
            
            if mean_val == 0:
                return {
                    'adjusted_threshold': base_threshold,
                    'volatility': None,
                    'adjustment_factor': 1.0
                }
            
            coefficient_of_variation = std_val / abs(mean_val)
            
            # Adjust threshold based on volatility
            # High volatility (CV > 0.5) -> increase threshold by up to 2x
            # Medium volatility (CV 0.2-0.5) -> increase by up to 1.5x
            # Low volatility (CV < 0.2) -> use base threshold
            
            if coefficient_of_variation > 0.5:
                adjustment_factor = min(2.0, 1.0 + coefficient_of_variation)
            elif coefficient_of_variation > 0.2:
                adjustment_factor = 1.0 + (coefficient_of_variation - 0.2) * 1.67  # Scale to 1.5x max
            else:
                adjustment_factor = 1.0
            
            adjusted_threshold = Decimal(str(float(base_threshold) * adjustment_factor))
            
            return {
                'adjusted_threshold': adjusted_threshold,
                'volatility': float(coefficient_of_variation),
                'adjustment_factor': float(adjustment_factor),
                'base_threshold': base_threshold,
                'historical_count': len(historical_values)
            }
        
        except Exception as e:
            logger.warning(f"Error calculating adaptive threshold: {e}")
            return {
                'adjusted_threshold': base_threshold,
                'volatility': None,
                'adjustment_factor': 1.0
            }
    
    def _get_historical_values(
        self,
        property_id: int,
        account_code: str,
        lookback_months: int = 24
    ) -> List[float]:
        """Get historical values for an account code."""
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_months * 30)
        
        values = []
        
        # Try income statement first
        income_data = self.db.query(IncomeStatementData).join(FinancialPeriod).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.account_code == account_code,
                FinancialPeriod.period_end_date >= cutoff_date
            )
        ).order_by(FinancialPeriod.period_end_date).all()
        
        if income_data:
            for record in income_data:
                if record.amount is not None:
                    values.append(float(record.amount))
            return values
        
        # Try balance sheet
        balance_data = self.db.query(BalanceSheetData).join(FinancialPeriod).filter(
            and_(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.account_code == account_code,
                FinancialPeriod.period_end_date >= cutoff_date
            )
        ).order_by(FinancialPeriod.period_end_date).all()
        
        if balance_data:
            for record in balance_data:
                if record.amount is not None:
                    values.append(float(record.amount))
        
        return values
    
    def get_account_category_threshold(
        self,
        account_code: str,
        account_category: Optional[str] = None
    ) -> Decimal:
        """
        Get threshold based on account category intelligence.
        
        Different account categories have different natural variability:
        - Revenue: Lower variability (default threshold)
        - Operating Expenses: Medium variability (1.5x threshold)
        - Maintenance: High variability (2x threshold)
        - One-time items: Very high variability (3x threshold)
        """
        # Determine category from account code if not provided
        if not account_category:
            account_category = self._infer_account_category(account_code)
        
        # Category-based multipliers
        category_multipliers = {
            'revenue': 1.0,
            'income': 1.0,
            'operating_expense': 1.5,
            'expense': 1.5,
            'maintenance': 2.0,
            'repair': 2.0,
            'one_time': 3.0,
            'asset': 1.2,
            'liability': 1.2,
            'equity': 1.0
        }
        
        # Find matching category
        multiplier = 1.0
        for cat, mult in category_multipliers.items():
            if cat in account_category.lower():
                multiplier = mult
                break
        
        base_threshold = self.get_default_threshold()
        adjusted_threshold = Decimal(str(float(base_threshold) * multiplier))
        
        return adjusted_threshold
    
    def _infer_account_category(self, account_code: str) -> str:
        """Infer account category from account code."""
        # Account code patterns (simplified)
        code_prefix = account_code.split('-')[0] if '-' in account_code else account_code[:4]
        
        try:
            code_num = int(code_prefix)
            
            # Chart of accounts ranges (simplified)
            if 4000 <= code_num < 5000:
                return 'revenue'
            elif 5000 <= code_num < 6000:
                if 5020 <= code_num < 5040:
                    return 'maintenance'
                else:
                    return 'operating_expense'
            elif 1000 <= code_num < 2000:
                return 'asset'
            elif 2000 <= code_num < 3000:
                return 'liability'
            elif 3000 <= code_num < 4000:
                return 'equity'
        except ValueError:
            pass
        
        return 'unknown'
    
    def get_or_create_threshold(
        self,
        account_code: str,
        account_name: Optional[str] = None,
        threshold_value: Optional[Decimal] = None
    ) -> AnomalyThreshold:
        """
        Get existing threshold or create a new one.
        If account_name is not provided, looks it up from chart_of_accounts.
        If threshold_value is not provided, uses default threshold.
        """
        threshold = self.get_threshold(account_code)
        
        if threshold:
            # Update account_name if provided and different
            if account_name and threshold.account_name != account_name:
                threshold.account_name = account_name
                self.db.commit()
            return threshold
        
        # Look up account_name from chart_of_accounts if not provided
        if not account_name:
            account = self.db.query(ChartOfAccounts).filter(
                ChartOfAccounts.account_code == account_code
            ).first()
            if account:
                account_name = account.account_name
            else:
                account_name = account_code  # Fallback to account_code
        
        # Use default threshold if not provided
        if threshold_value is None:
            threshold_value = self.get_default_threshold()
        threshold_value = self._validate_threshold_value(threshold_value)
        
        # Create new threshold
        threshold = AnomalyThreshold(
            account_code=account_code,
            account_name=account_name,
            threshold_value=threshold_value,
            is_active=True
        )
        self.db.add(threshold)
        self.db.commit()
        self.db.refresh(threshold)
        
        return threshold
    
    def update_threshold(
        self,
        account_code: str,
        account_name: Optional[str] = None,
        threshold_value: Optional[Decimal] = None,
        is_active: Optional[bool] = None
    ) -> AnomalyThreshold:
        """Update an existing threshold"""
        threshold = self.db.query(AnomalyThreshold).filter(
            AnomalyThreshold.account_code == account_code
        ).first()
        
        if not threshold:
            raise ValueError(f"Threshold not found for account_code: {account_code}")
        
        if account_name is not None:
            threshold.account_name = account_name
        if threshold_value is not None:
            threshold.threshold_value = self._validate_threshold_value(threshold_value)
        if is_active is not None:
            threshold.is_active = is_active
        
        self.db.commit()
        self.db.refresh(threshold)
        
        return threshold
    
    def delete_threshold(self, account_code: str) -> bool:
        """Delete a threshold (soft delete by setting is_active=False)"""
        threshold = self.get_threshold(account_code)
        if threshold:
            threshold.is_active = False
            self.db.commit()
            return True
        return False
    
    def list_all_thresholds(self, include_inactive: bool = False) -> List[AnomalyThreshold]:
        """List all thresholds, optionally including inactive ones"""
        query = self.db.query(AnomalyThreshold)
        if not include_inactive:
            query = query.filter(AnomalyThreshold.is_active == True)
        return query.order_by(AnomalyThreshold.account_code).all()
    
    def get_default_threshold(self) -> Decimal:
        """Get the global default threshold value"""
        config = self.db.query(SystemConfig).filter(
            SystemConfig.config_key == self.DEFAULT_THRESHOLD_KEY
        ).first()
        
        if config:
            try:
                return Decimal(config.config_value)
            except (ValueError, TypeError):
                return self.SYSTEM_FALLBACK_THRESHOLD
        
        return self.SYSTEM_FALLBACK_THRESHOLD
    
    def set_default_threshold(self, threshold_value: Decimal) -> SystemConfig:
        """Set the global default threshold value"""
        threshold_value = self._validate_threshold_value(threshold_value)
        config = self.db.query(SystemConfig).filter(
            SystemConfig.config_key == self.DEFAULT_THRESHOLD_KEY
        ).first()
        
        if config:
            config.config_value = str(threshold_value)
        else:
            config = SystemConfig(
                config_key=self.DEFAULT_THRESHOLD_KEY,
                config_value=str(threshold_value),
                description="Default percentage threshold for anomaly detection (1% = 0.01)"
            )
            self.db.add(config)
        
        self.db.commit()
        self.db.refresh(config)
        
        return config

    def _validate_threshold_value(self, value: Decimal) -> Decimal:
        """
        Ensure threshold values are within sensible bounds.
        Thresholds are stored as decimals (e.g., 0.01 = 1%). Clamp to [0, 1].
        """
        try:
            val = Decimal(str(value))
        except Exception:
            return self.SYSTEM_FALLBACK_THRESHOLD

        if val < Decimal('0'):
            val = Decimal('0')
        if val > Decimal('1'):
            val = Decimal('1')
        return val
    
    def get_all_accounts_with_thresholds(
        self,
        document_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all accounts from chart_of_accounts AND actual data tables with their thresholds.
        Optionally filter by document types (income_statement, balance_sheet, cash_flow, rent_roll, mortgage_statement).
        Returns list of dicts with account info and threshold if exists.
        
        This method combines:
        1. Accounts from chart_of_accounts (template/master list)
        2. Accounts from actual data tables (income_statement_data, balance_sheet_data, cash_flow_data, mortgage_statement_data)
        """
        from sqlalchemy import distinct, func
        from app.models.income_statement_data import IncomeStatementData
        from app.models.balance_sheet_data import BalanceSheetData
        from app.models.cash_flow_data import CashFlowData
        from app.models.mortgage_statement_data import MortgageStatementData
        from app.models.rent_roll_data import RentRollData
        
        # Get all active thresholds
        thresholds = {
            t.account_code: t
            for t in self.db.query(AnomalyThreshold).filter(
                AnomalyThreshold.is_active == True
            ).all()
        }
        
        default_threshold = self.get_default_threshold()
        
        # Collect accounts from multiple sources
        account_map = {}  # account_code -> account info
        
        # 1. Get accounts from chart_of_accounts (if document_types filter matches)
        query = self.db.query(ChartOfAccounts).filter(
            ChartOfAccounts.is_active == True
        )
        
        if document_types:
            from sqlalchemy import cast, Text as TextType, or_
            conditions = []
            for doc_type in document_types:
                conditions.append(
                    cast(ChartOfAccounts.document_types, TextType).like(f'%{doc_type}%')
                )
            if conditions:
                query = query.filter(or_(*conditions))
        
        chart_accounts = query.all()
        for account in chart_accounts:
            account_map[account.account_code] = {
                "account_code": account.account_code,
                "account_name": account.account_name,
                "account_type": account.account_type,
                "threshold_value": float(thresholds[account.account_code].threshold_value) if account.account_code in thresholds else None,
                "is_custom": account.account_code in thresholds,
                "default_threshold": float(default_threshold)
            }
        
        # 2. Get accounts from actual data tables (to include accounts that exist in data but not in chart_of_accounts)
        if not document_types or 'income_statement' in document_types:
            income_accounts = self.db.query(
                distinct(IncomeStatementData.account_code).label('account_code'),
                func.max(IncomeStatementData.account_name).label('account_name')
            ).group_by(IncomeStatementData.account_code).all()
            
            for acc in income_accounts:
                if acc.account_code and acc.account_code not in account_map:
                    account_map[acc.account_code] = {
                        "account_code": acc.account_code,
                        "account_name": acc.account_name or acc.account_code,
                        "account_type": "expense",  # Default, could be improved
                        "threshold_value": float(thresholds[acc.account_code].threshold_value) if acc.account_code in thresholds else None,
                        "is_custom": acc.account_code in thresholds,
                        "default_threshold": float(default_threshold)
                    }
        
        if not document_types or 'balance_sheet' in document_types:
            balance_accounts = self.db.query(
                distinct(BalanceSheetData.account_code).label('account_code'),
                func.max(BalanceSheetData.account_name).label('account_name')
            ).group_by(BalanceSheetData.account_code).all()
            
            for acc in balance_accounts:
                if acc.account_code and acc.account_code not in account_map:
                    account_map[acc.account_code] = {
                        "account_code": acc.account_code,
                        "account_name": acc.account_name or acc.account_code,
                        "account_type": "asset",  # Default, could be improved
                        "threshold_value": float(thresholds[acc.account_code].threshold_value) if acc.account_code in thresholds else None,
                        "is_custom": acc.account_code in thresholds,
                        "default_threshold": float(default_threshold)
                    }
        
        if not document_types or 'cash_flow' in document_types:
            # For cash flow, we need to handle "UNMATCHED" accounts specially
            # Get distinct combinations of account_code and account_name
            cash_flow_accounts = self.db.query(
                CashFlowData.account_code,
                CashFlowData.account_name
            ).distinct(CashFlowData.account_code, CashFlowData.account_name).all()
            
            for acc in cash_flow_accounts:
                # For UNMATCHED accounts, use account_name as the identifier (since they don't have real codes)
                # For matched accounts, use account_code as the identifier
                if acc.account_code and acc.account_code.upper() == 'UNMATCHED':
                    # Use account_name as both the key and the display code for UNMATCHED accounts
                    # This allows each account name to have its own threshold
                    identifier = acc.account_name
                    display_code = acc.account_name
                else:
                    identifier = acc.account_code
                    display_code = acc.account_code
                
                if identifier not in account_map:
                    # Check if there's a threshold for this identifier
                    threshold_val = None
                    is_custom = False
                    if identifier in thresholds:
                        threshold_val = float(thresholds[identifier].threshold_value)
                        is_custom = True
                    
                    account_map[identifier] = {
                        "account_code": display_code,  # For UNMATCHED: account_name, for others: account_code
                        "account_name": acc.account_name,
                        "account_type": "expense",  # Default, could be improved
                        "threshold_value": threshold_val,
                        "is_custom": is_custom,
                        "default_threshold": float(default_threshold)
                    }
        
        if not document_types or 'mortgage_statement' in document_types:
            mortgage_accounts = self.db.query(
                distinct(MortgageStatementData.loan_number).label('loan_number')
            ).filter(MortgageStatementData.loan_number.isnot(None)).all()

            for acc in mortgage_accounts:
                code = acc.loan_number
                if code and code not in account_map:
                    threshold_val = None
                    is_custom = False
                    if code in thresholds:
                        threshold_val = float(thresholds[code].threshold_value)
                        is_custom = True
                    account_map[code] = {
                        "account_code": code,
                        "account_name": f"Loan {code} Principal Balance",
                        "account_type": "liability",
                        "threshold_value": threshold_val,
                        "is_custom": is_custom,
                        "default_threshold": float(default_threshold)
                    }

        if not document_types or 'rent_roll' in document_types:
            # Use unit_number as the identifier; if missing, fall back to tenant_name
            rent_roll_accounts = self.db.query(
                distinct(RentRollData.unit_number).label('unit_number'),
                func.max(RentRollData.tenant_name).label('tenant_name')
            ).group_by(RentRollData.unit_number).all()

            for acc in rent_roll_accounts:
                identifier = acc.unit_number or acc.tenant_name
                if not identifier:
                    continue
                if identifier not in account_map:
                    threshold_val = None
                    is_custom = False
                    if identifier in thresholds:
                        threshold_val = float(thresholds[identifier].threshold_value)
                        is_custom = True

                    display_name = acc.tenant_name or acc.unit_number
                    if acc.unit_number and acc.tenant_name:
                        display_name = f"{acc.unit_number} - {acc.tenant_name}"

                    account_map[identifier] = {
                        "account_code": identifier,
                        "account_name": display_name,
                        "account_type": "rent_roll",
                        "threshold_value": threshold_val,
                        "is_custom": is_custom,
                        "default_threshold": float(default_threshold)
                    }
        
        # Convert to list and sort by account_code
        result = list(account_map.values())
        result.sort(key=lambda x: x["account_code"])
        
        return result
