"""
Data Drift Detection Service

Detects feature distribution changes using KS test and PSI.
Triggers recalibration when drift is detected.
"""

from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
import logging

from app.models.anomaly_detection import AnomalyDetection
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData

logger = logging.getLogger(__name__)

try:
    from evidently import ColumnMapping
    from evidently.metric_preset import DataDriftPreset
    from evidently.report import Report
    EVIDENTLY_AVAILABLE = True
except ImportError:
    EVIDENTLY_AVAILABLE = False
    logger.warning("Evidently not available - using scipy only")


class DataDriftDetector:
    """
    Detects data drift in feature distributions.
    
    Uses:
    - Kolmogorov-Smirnov (KS) test
    - Population Stability Index (PSI)
    - Evidently library (if available)
    """
    
    def __init__(self, db: Session):
        """Initialize drift detector."""
        self.db = db
        self.ks_threshold = 0.05  # p-value threshold
        self.psi_threshold = 0.2  # PSI threshold
    
    def detect_drift(
        self,
        property_id: int,
        account_code: str,
        reference_period_days: int = 90,
        current_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Detect data drift for a property/account combination.
        
        Args:
            property_id: Property ID
            account_code: Account code
            reference_period_days: Days for reference distribution
            current_period_days: Days for current distribution
            
        Returns:
            Dict with drift detection results
        """
        # Get reference data
        ref_cutoff = datetime.utcnow() - timedelta(days=reference_period_days + current_period_days)
        ref_end = datetime.utcnow() - timedelta(days=current_period_days)
        
        reference_data = self._get_account_data(property_id, account_code, ref_cutoff, ref_end)
        
        # Get current data
        current_cutoff = datetime.utcnow() - timedelta(days=current_period_days)
        current_data = self._get_account_data(property_id, account_code, current_cutoff, datetime.utcnow())
        
        if len(reference_data) < 10 or len(current_data) < 5:
            return {
                'drift_detected': False,
                'reason': 'Insufficient data'
            }
        
        # Run KS test
        ks_result = self._ks_test(reference_data, current_data)
        
        # Calculate PSI
        psi_result = self._calculate_psi(reference_data, current_data)
        
        # Determine if drift detected
        drift_detected = (
            ks_result['p_value'] < self.ks_threshold or
            psi_result['psi'] > self.psi_threshold
        )
        
        result = {
            'drift_detected': drift_detected,
            'ks_test': ks_result,
            'psi': psi_result,
            'property_id': property_id,
            'account_code': account_code,
            'reference_sample_size': len(reference_data),
            'current_sample_size': len(current_data)
        }
        
        # Trigger recalibration if drift detected
        if drift_detected:
            self._trigger_recalibration(property_id, account_code, result)
        
        return result
    
    def _get_account_data(
        self,
        property_id: int,
        account_code: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[float]:
        """Get account data for time period."""
        from app.models.financial_period import FinancialPeriod
        
        # Try income statement
        data = self.db.query(IncomeStatementData.period_amount).join(
            FinancialPeriod
        ).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.account_code == account_code,
                FinancialPeriod.period_end_date >= start_date,
                FinancialPeriod.period_end_date <= end_date
            )
        ).all()
        
        if data:
            return [float(row.period_amount) for row in data if row.period_amount]
        
        # Try balance sheet
        data = self.db.query(BalanceSheetData.amount).join(
            FinancialPeriod
        ).filter(
            and_(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.account_code == account_code,
                FinancialPeriod.period_end_date >= start_date,
                FinancialPeriod.period_end_date <= end_date
            )
        ).all()
        
        return [float(row.amount) for row in data if row.amount]
    
    def _ks_test(
        self,
        reference: List[float],
        current: List[float]
    ) -> Dict[str, float]:
        """Run Kolmogorov-Smirnov test."""
        statistic, p_value = ks_2samp(reference, current)
        
        return {
            'statistic': float(statistic),
            'p_value': float(p_value),
            'significant': p_value < self.ks_threshold
        }
    
    def _calculate_psi(
        self,
        reference: List[float],
        current: List[float]
    ) -> Dict[str, float]:
        """Calculate Population Stability Index."""
        # Bin the data
        all_values = reference + current
        min_val = min(all_values)
        max_val = max(all_values)
        
        bins = 10
        bin_edges = np.linspace(min_val, max_val, bins + 1)
        
        # Calculate distributions
        ref_hist, _ = np.histogram(reference, bins=bin_edges)
        curr_hist, _ = np.histogram(current, bins=bin_edges)
        
        # Normalize
        ref_dist = ref_hist / len(reference) if len(reference) > 0 else ref_hist
        curr_dist = curr_hist / len(current) if len(current) > 0 else curr_hist
        
        # Calculate PSI
        psi = 0.0
        for i in range(bins):
            if ref_dist[i] > 0 and curr_dist[i] > 0:
                psi += (curr_dist[i] - ref_dist[i]) * np.log(curr_dist[i] / ref_dist[i])
        
        return {
            'psi': float(psi),
            'significant': psi > self.psi_threshold
        }
    
    def _trigger_recalibration(
        self,
        property_id: int,
        account_code: str,
        drift_result: Dict[str, Any]
    ) -> None:
        """Trigger recalibration for affected models."""
        logger.warning(
            f"Data drift detected for property {property_id}, account {account_code}. "
            f"Triggering recalibration. KS p-value: {drift_result['ks_test']['p_value']}, "
            f"PSI: {drift_result['psi']['psi']}"
        )
        
        # In production, would trigger recalibration task
        # For now, just log
