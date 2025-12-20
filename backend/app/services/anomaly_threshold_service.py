"""
Anomaly Threshold Service

Manages percentage-based thresholds for anomaly detection per account code.
Thresholds are stored as decimals (e.g., 0.01 = 1%).
Provides methods to get, create, update, and delete thresholds, as well as
manage the global default threshold.
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.anomaly_threshold import AnomalyThreshold, SystemConfig
from app.models.chart_of_accounts import ChartOfAccounts


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
    
    def get_threshold_value(self, account_code: str) -> Decimal:
        """
        Get threshold value for an account code.
        Returns custom threshold if exists, otherwise returns default threshold.
        """
        threshold = self.get_threshold(account_code)
        if threshold:
            return threshold.threshold_value
        
        return self.get_default_threshold()
    
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
            threshold.threshold_value = threshold_value
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
    
    def get_all_accounts_with_thresholds(
        self,
        document_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all accounts from chart_of_accounts AND actual data tables with their thresholds.
        Optionally filter by document types (income_statement, balance_sheet, cash_flow).
        Returns list of dicts with account info and threshold if exists.
        
        This method combines:
        1. Accounts from chart_of_accounts (template/master list)
        2. Accounts from actual data tables (income_statement_data, balance_sheet_data, cash_flow_data)
        """
        from sqlalchemy import distinct, func
        from app.models.income_statement_data import IncomeStatementData
        from app.models.balance_sheet_data import BalanceSheetData
        from app.models.cash_flow_data import CashFlowData
        
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
        
        # Convert to list and sort by account_code
        result = list(account_map.values())
        result.sort(key=lambda x: x["account_code"])
        
        return result

