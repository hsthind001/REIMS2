"""
Multivariate Anomaly Detector Service

Uses Vector Autoregression (VAR) to detect relationship anomalies across accounts.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import numpy as np
import pandas as pd
import logging

from app.models.anomaly_detection import AnomalyDetection, AnomalyCategory, PatternType
from app.models.financial_period import FinancialPeriod
from app.models.income_statement_data import IncomeStatementData

logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.vector_ar.var_model import VAR
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("statsmodels not available - VAR multivariate detection disabled")


class MultivariateAnomalyDetector:
    """
    Detects relationship anomalies using Vector Autoregression (VAR).
    
    Analyzes relationships between accounts (e.g., Repairs & Maintenance vs Tenant Complaints).
    """
    
    def __init__(self, db: Session):
        """Initialize multivariate detector."""
        self.db = db
    
    def detect_relationship_anomalies(
        self,
        property_id: int,
        account_pairs: List[tuple],
        lookback_months: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Detect relationship anomalies between account pairs.
        
        Args:
            property_id: Property ID
            account_pairs: List of (account1, account2) tuples
            lookback_months: Historical months to analyze
            
        Returns:
            List of detected relationship anomalies
        """
        if not STATSMODELS_AVAILABLE:
            return []
        
        anomalies = []
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_months * 30)
        
        for account1, account2 in account_pairs:
            try:
                # Get time series data for both accounts
                data1 = self._get_account_series(property_id, account1, cutoff_date)
                data2 = self._get_account_series(property_id, account2, cutoff_date)
                
                if len(data1) < 12 or len(data2) < 12:
                    continue
                
                # Align data by date
                df = pd.DataFrame({
                    account1: data1['values'],
                    account2: data2['values']
                }, index=data1['dates'])
                
                # Fit VAR model
                model = VAR(df)
                model_fit = model.fit(maxlags=3)
                
                # Get residuals
                residuals = model_fit.resid
                
                # Detect anomalies in residuals
                for idx, (date, row) in enumerate(residuals.iterrows()):
                    # Check if residual exceeds threshold
                    if abs(row[account1]) > 2 * residuals[account1].std() or \
                       abs(row[account2]) > 2 * residuals[account2].std():
                        
                        anomalies.append({
                            'property_id': property_id,
                            'account1': account1,
                            'account2': account2,
                            'date': date,
                            'residual1': float(row[account1]),
                            'residual2': float(row[account2]),
                            'anomaly_type': 'relationship_deviation',
                            'severity': 'high',
                            'message': f"Relationship anomaly between {account1} and {account2} detected"
                        })
            except Exception as e:
                logger.error(f"Error detecting relationship anomaly for {account1}/{account2}: {e}")
        
        return anomalies
    
    def _get_account_series(
        self,
        property_id: int,
        account_code: str,
        cutoff_date: datetime
    ) -> Dict[str, Any]:
        """Get time series data for an account."""
        data = self.db.query(
            IncomeStatementData.period_amount,
            FinancialPeriod.period_end_date
        ).join(
            FinancialPeriod
        ).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.account_code == account_code,
                FinancialPeriod.period_end_date >= cutoff_date
            )
        ).order_by(FinancialPeriod.period_end_date).all()
        
        return {
            'values': [float(row.period_amount) for row in data if row.period_amount],
            'dates': [row.period_end_date for row in data if row.period_amount]
        }
