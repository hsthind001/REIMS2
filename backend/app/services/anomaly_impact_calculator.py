"""
Anomaly Impact Calculator Service

Calculates financial impact metrics for anomalies:
1. Absolute dollar variance (|actual - expected|)
2. Percentage impact on parent category
3. Covenant proximity (DSCR distance to threshold)
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import numpy as np
import logging

from app.models.anomaly_detection import AnomalyDetection
from app.models.financial_metrics import FinancialMetrics
from app.models.chart_of_accounts import ChartOfAccounts

logger = logging.getLogger(__name__)


class AnomalyImpactCalculator:
    """
    Calculates financial impact metrics for anomalies.
    
    Metrics:
    - Absolute dollar variance
    - Percentage impact on parent category
    - Covenant proximity (DSCR)
    """
    
    def __init__(self, db: Session):
        """Initialize impact calculator."""
        self.db = db
        self.dscr_threshold = 1.25  # Default DSCR covenant threshold
    
    def calculate_impact(
        self,
        anomaly: AnomalyDetection,
        property_id: int,
        period_id: int
    ) -> Dict[str, Any]:
        """
        Calculate impact metrics for an anomaly.
        
        Args:
            anomaly: AnomalyDetection record
            property_id: Property ID
            period_id: Period ID
            
        Returns:
            Dict with impact metrics
        """
        impact = {}
        
        # 1. Absolute dollar variance
        impact['absolute_variance'] = self._calculate_absolute_variance(anomaly)
        
        # 2. Percentage impact on parent category
        impact['parent_category_impact'] = self._calculate_parent_category_impact(
            anomaly, property_id, period_id
        )
        
        # 3. Covenant proximity (DSCR)
        impact['dscr_proximity'] = self._calculate_dscr_proximity(
            property_id, period_id, impact['absolute_variance']
        )
        
        # Combined impact score (0-100)
        impact['impact_score'] = self._calculate_combined_impact_score(impact)
        
        return impact
    
    def _calculate_absolute_variance(self, anomaly: AnomalyDetection) -> float:
        """Calculate absolute dollar variance: |actual - expected|."""
        try:
            actual = float(anomaly.field_value) if anomaly.field_value else 0.0
            expected = float(anomaly.expected_value) if anomaly.expected_value else 0.0
            return abs(actual - expected)
        except (ValueError, TypeError):
            logger.warning(f"Could not calculate variance for anomaly {anomaly.id}")
            return 0.0
    
    def _calculate_parent_category_impact(
        self,
        anomaly: AnomalyDetection,
        property_id: int,
        period_id: int
    ) -> Dict[str, float]:
        """
        Calculate percentage impact on parent category.
        
        Example: If "Repairs & Maintenance" is $5K over expected and
        "Total Operating Expenses" is $100K, impact = 5%
        """
        try:
            account_code = anomaly.field_name
            
            # Get parent category from chart of accounts
            account = self.db.query(ChartOfAccounts).filter(
                ChartOfAccounts.account_code == account_code
            ).first()
            
            if not account or not account.parent_account_code:
                return {'impact_percentage': 0.0, 'parent_total': 0.0}
            
            parent_code = account.parent_account_code
            
            # Get parent category total
            from app.models.income_statement_data import IncomeStatementData
            from app.models.balance_sheet_data import BalanceSheetData
            
            # Try income statement first
            parent_data = self.db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id,
                IncomeStatementData.account_code == parent_code
            ).first()
            
            if not parent_data:
                # Try balance sheet
                parent_data = self.db.query(BalanceSheetData).filter(
                    BalanceSheetData.property_id == property_id,
                    BalanceSheetData.period_id == period_id,
                    BalanceSheetData.account_code == parent_code
                ).first()
            
            if not parent_data or not parent_data.period_amount:
                return {'impact_percentage': 0.0, 'parent_total': 0.0}
            
            parent_total = float(parent_data.period_amount)
            absolute_variance = self._calculate_absolute_variance(anomaly)
            
            if parent_total > 0:
                impact_percentage = (absolute_variance / parent_total) * 100
            else:
                impact_percentage = 0.0
            
            return {
                'impact_percentage': impact_percentage,
                'parent_total': parent_total,
                'parent_account_code': parent_code
            }
            
        except Exception as e:
            logger.error(f"Error calculating parent category impact: {e}")
            return {'impact_percentage': 0.0, 'parent_total': 0.0}
    
    def _calculate_dscr_proximity(
        self,
        property_id: int,
        period_id: int,
        absolute_variance: float
    ) -> Dict[str, float]:
        """
        Calculate DSCR proximity to threshold.
        
        Returns distance to threshold and impact on DSCR.
        """
        try:
            # Get current DSCR
            metrics = self.db.query(FinancialMetrics).filter(
                FinancialMetrics.property_id == property_id,
                FinancialMetrics.period_id == period_id
            ).first()
            
            if not metrics or not metrics.net_operating_income:
                return {
                    'current_dscr': None,
                    'distance_to_threshold': None,
                    'dscr_impact': 0.0
                }
            
            # Calculate DSCR (simplified - assumes debt service from metrics)
            # In production, get actual debt service from mortgage data
            noi = float(metrics.net_operating_income)
            total_debt = float(metrics.total_debt) if metrics.total_debt else 0.0
            
            if total_debt > 0:
                # Estimate monthly debt service (assume 5% annual interest)
                monthly_debt_service = (total_debt * 0.05) / 12
                annual_debt_service = monthly_debt_service * 12
                
                current_dscr = noi / annual_debt_service if annual_debt_service > 0 else 0.0
            else:
                current_dscr = None
            
            if current_dscr is None:
                return {
                    'current_dscr': None,
                    'distance_to_threshold': None,
                    'dscr_impact': 0.0
                }
            
            # Calculate distance to threshold
            distance_to_threshold = current_dscr - self.dscr_threshold
            
            # Calculate impact of variance on DSCR
            # Assuming variance affects NOI
            if annual_debt_service > 0:
                dscr_impact = absolute_variance / annual_debt_service
            else:
                dscr_impact = 0.0
            
            return {
                'current_dscr': current_dscr,
                'distance_to_threshold': distance_to_threshold,
                'dscr_impact': dscr_impact,
                'threshold': self.dscr_threshold,
                'is_breach_risk': distance_to_threshold < 0.1  # Within 0.1 of threshold
            }
            
        except Exception as e:
            logger.error(f"Error calculating DSCR proximity: {e}")
            return {
                'current_dscr': None,
                'distance_to_threshold': None,
                'dscr_impact': 0.0
            }
    
    def _calculate_combined_impact_score(self, impact: Dict[str, Any]) -> float:
        """
        Calculate combined impact score (0-100).
        
        Combines:
        - Absolute variance (normalized)
        - Parent category impact
        - DSCR proximity
        """
        score = 0.0
        
        # 1. Absolute variance component (0-40 points)
        # Normalize: $10K variance = 40 points, $1K = 4 points
        absolute_variance = impact.get('absolute_variance', 0.0)
        variance_score = min(40.0, absolute_variance / 250.0)  # $10K = 40 points
        score += variance_score
        
        # 2. Parent category impact (0-30 points)
        # 10% impact = 30 points, 1% = 3 points
        parent_impact = impact.get('parent_category_impact', {}).get('impact_percentage', 0.0)
        parent_score = min(30.0, parent_impact * 3.0)
        score += parent_score
        
        # 3. DSCR proximity (0-30 points)
        dscr_prox = impact.get('dscr_proximity', {})
        distance = dscr_prox.get('distance_to_threshold')
        if distance is not None:
            # Close to threshold = high score
            if distance < 0.1:
                dscr_score = 30.0  # Critical
            elif distance < 0.25:
                dscr_score = 20.0  # High risk
            elif distance < 0.5:
                dscr_score = 10.0  # Medium risk
            else:
                dscr_score = 0.0  # Low risk
            
            # Add impact of variance on DSCR
            dscr_impact = abs(dscr_prox.get('dscr_impact', 0.0))
            if dscr_impact > 0.1:  # Significant DSCR impact
                dscr_score += min(10.0, dscr_impact * 50.0)
            
            score += dscr_score
        
        return min(100.0, score)
    
    def update_anomaly_impact(
        self,
        anomaly_id: int,
        impact: Dict[str, Any]
    ) -> bool:
        """
        Update anomaly_detections table with calculated impact.
        
        Args:
            anomaly_id: AnomalyDetection ID
            impact: Impact metrics dict
            
        Returns:
            True if updated successfully
        """
        try:
            anomaly = self.db.query(AnomalyDetection).filter(
                AnomalyDetection.id == anomaly_id
            ).first()
            
            if anomaly:
                # Update impact_amount
                anomaly.impact_amount = Decimal(str(impact.get('absolute_variance', 0.0)))
                
                # Store additional metrics in metadata
                if not anomaly.metadata_json:
                    anomaly.metadata_json = {}
                
                anomaly.metadata_json.update({
                    'parent_category_impact': impact.get('parent_category_impact', {}),
                    'dscr_proximity': impact.get('dscr_proximity', {}),
                    'impact_score': impact.get('impact_score', 0.0)
                })
                
                self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating anomaly impact: {e}")
            self.db.rollback()
            return False
