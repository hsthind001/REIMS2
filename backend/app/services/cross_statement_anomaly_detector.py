"""
Cross-Statement Anomaly Detector Service

Implements cross-statement consistency checks for financial data:
- Cash flow vs balance sheet roll-forward validation
- NOI vs revenue/opex component drill-down checks
- DSCR change explanation (NOI change vs debt service change)

Detects relationship anomalies across financial statements.
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import numpy as np
import logging

from app.models.anomaly_detection import AnomalyDetection, BaselineType, AnomalyCategory
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.cash_flow_header import CashFlowHeader
from app.models.financial_period import FinancialPeriod
from app.models.financial_metrics import FinancialMetrics
from app.models.cash_account_reconciliation import CashAccountReconciliation

logger = logging.getLogger(__name__)


class CrossStatementAnomalyDetector:
    """
    Detects anomalies by validating relationships across financial statements.
    
    Validates:
    1. Cash flow vs balance sheet roll-forward
    2. NOI vs revenue/opex component drill-down
    3. DSCR change explanation (NOI change vs debt service change)
    """
    
    def __init__(self, db: Session):
        """Initialize cross-statement anomaly detector."""
        self.db = db
        self.tolerance = 0.01  # 1% tolerance for rounding differences
    
    def detect_cross_statement_anomalies(
        self,
        property_id: int,
        period_id: int,
        previous_period_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies by checking cross-statement consistency.
        
        Args:
            property_id: Property to analyze
            period_id: Current period to analyze
            previous_period_id: Previous period for comparison (optional)
            
        Returns:
            List of detected cross-statement anomalies
        """
        anomalies = []
        
        # Check 1: Cash flow vs balance sheet roll-forward
        cash_flow_anomalies = self._check_cash_flow_roll_forward(property_id, period_id, previous_period_id)
        anomalies.extend(cash_flow_anomalies)
        
        # Check 2: NOI vs revenue/opex component drill-down
        noi_anomalies = self._check_noi_component_consistency(property_id, period_id)
        anomalies.extend(noi_anomalies)
        
        # Check 3: DSCR change explanation
        dscr_anomalies = self._check_dscr_change_explanation(property_id, period_id, previous_period_id)
        anomalies.extend(dscr_anomalies)
        
        return anomalies
    
    def _check_cash_flow_roll_forward(
        self,
        property_id: int,
        period_id: int,
        previous_period_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Validate cash flow vs balance sheet roll-forward.
        
        Rule: Ending Cash (BS) = Beginning Cash (BS) + Net Cash Flow (CF)
        """
        anomalies = []
        
        try:
            # Get current period balance sheet cash
            current_cash = self._get_balance_sheet_cash(property_id, period_id)
            
            # Get previous period balance sheet cash (beginning balance)
            if previous_period_id:
                beginning_cash = self._get_balance_sheet_cash(property_id, previous_period_id)
            else:
                # Try to get from cash account reconciliation
                beginning_cash = self._get_beginning_cash_from_reconciliation(property_id, period_id)
            
            # Get net cash flow from cash flow statement
            net_cash_flow = self._get_net_cash_flow(property_id, period_id)
            
            if current_cash is None or beginning_cash is None or net_cash_flow is None:
                logger.warning("Missing data for cash flow roll-forward check")
                return []
            
            # Calculate expected ending cash
            expected_ending_cash = beginning_cash + net_cash_flow
            difference = abs(current_cash - expected_ending_cash)
            difference_pct = (difference / abs(beginning_cash) * 100) if beginning_cash != 0 else 0
            
            # Check if difference exceeds tolerance
            if difference > 100 or difference_pct > self.tolerance * 100:  # $100 or 1% threshold
                anomaly = {
                    'type': 'cash_flow_roll_forward',
                    'severity': 'high' if difference > 1000 or difference_pct > 5 else 'medium',
                    'property_id': property_id,
                    'period_id': period_id,
                    'check_type': 'cash_flow_roll_forward',
                    'beginning_cash': beginning_cash,
                    'net_cash_flow': net_cash_flow,
                    'expected_ending_cash': expected_ending_cash,
                    'actual_ending_cash': current_cash,
                    'difference': difference,
                    'difference_percentage': difference_pct,
                    'baseline_type': 'mean',
                    'anomaly_category': 'accounting',
                    'pattern_type': 'structure',
                    'detected_at': datetime.utcnow()
                }
                anomalies.append(anomaly)
        
        except Exception as e:
            logger.error(f"Error in cash flow roll-forward check: {e}")
        
        return anomalies
    
    def _check_noi_component_consistency(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """
        Validate NOI vs revenue/opex component drill-down.
        
        Rule: NOI (CF) = Total Revenue (IS) - Total Operating Expenses (IS)
        Also checks: NOI components match between CF and IS
        """
        anomalies = []
        
        try:
            # Get NOI from cash flow statement
            cf_noi = self._get_cash_flow_noi(property_id, period_id)
            
            # Get revenue and expenses from income statement
            is_revenue = self._get_income_statement_revenue(property_id, period_id)
            is_expenses = self._get_income_statement_operating_expenses(property_id, period_id)
            
            if cf_noi is None or is_revenue is None or is_expenses is None:
                logger.warning("Missing data for NOI component consistency check")
                return []
            
            # Calculate expected NOI
            expected_noi = is_revenue - is_expenses
            difference = abs(cf_noi - expected_noi)
            difference_pct = (difference / abs(expected_noi) * 100) if expected_noi != 0 else 0
            
            # Check if difference exceeds tolerance
            if difference > 100 or difference_pct > self.tolerance * 100:
                anomaly = {
                    'type': 'noi_component_mismatch',
                    'severity': 'high' if difference > 1000 or difference_pct > 5 else 'medium',
                    'property_id': property_id,
                    'period_id': period_id,
                    'check_type': 'noi_component_consistency',
                    'cf_noi': cf_noi,
                    'is_revenue': is_revenue,
                    'is_expenses': is_expenses,
                    'expected_noi': expected_noi,
                    'difference': difference,
                    'difference_percentage': difference_pct,
                    'baseline_type': 'mean',
                    'anomaly_category': 'accounting',
                    'pattern_type': 'structure',
                    'detected_at': datetime.utcnow()
                }
                anomalies.append(anomaly)
            
            # Check revenue component breakdown
            revenue_components = self._get_revenue_components(property_id, period_id)
            if revenue_components:
                total_components = sum(revenue_components.values())
                if abs(total_components - is_revenue) > 100:
                    anomaly = {
                        'type': 'revenue_component_mismatch',
                        'severity': 'medium',
                        'property_id': property_id,
                        'period_id': period_id,
                        'check_type': 'revenue_component_breakdown',
                        'total_revenue': is_revenue,
                        'component_sum': total_components,
                        'difference': abs(total_components - is_revenue),
                        'baseline_type': 'mean',
                        'anomaly_category': 'accounting',
                        'pattern_type': 'structure',
                        'detected_at': datetime.utcnow()
                    }
                    anomalies.append(anomaly)
        
        except Exception as e:
            logger.error(f"Error in NOI component consistency check: {e}")
        
        return anomalies
    
    def _check_dscr_change_explanation(
        self,
        property_id: int,
        period_id: int,
        previous_period_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Validate DSCR change explanation.
        
        Rule: DSCR change should be explained by:
        - NOI change (numerator)
        - Debt service change (denominator)
        
        Flags if DSCR change is unexplained by these factors.
        """
        anomalies = []
        
        if not previous_period_id:
            return anomalies
        
        try:
            # Get DSCR for both periods
            current_dscr = self._get_dscr(property_id, period_id)
            previous_dscr = self._get_dscr(property_id, previous_period_id)
            
            if current_dscr is None or previous_dscr is None:
                return anomalies
            
            dscr_change = current_dscr - previous_dscr
            dscr_change_pct = (dscr_change / previous_dscr * 100) if previous_dscr != 0 else 0
            
            # Get NOI and debt service for both periods
            current_noi = self._get_noi(property_id, period_id)
            previous_noi = self._get_noi(property_id, previous_period_id)
            
            current_debt_service = self._get_debt_service(property_id, period_id)
            previous_debt_service = self._get_debt_service(property_id, previous_period_id)
            
            if current_noi is None or previous_noi is None or current_debt_service is None or previous_debt_service is None:
                return anomalies
            
            # Calculate expected DSCR change
            # DSCR = NOI / Debt Service
            # Change in DSCR = (NOI_new / DS_new) - (NOI_old / DS_old)
            expected_dscr = (current_noi / current_debt_service) if current_debt_service != 0 else 0
            expected_dscr_change = expected_dscr - previous_dscr
            
            # Check if actual DSCR change matches expected
            difference = abs(dscr_change - expected_dscr_change)
            
            # If DSCR changed significantly but explanation doesn't match
            if abs(dscr_change) > 0.1 and difference > 0.05:  # DSCR changed by >0.1 but explanation off by >0.05
                noi_change = current_noi - previous_noi
                ds_change = current_debt_service - previous_debt_service
                
                anomaly = {
                    'type': 'dscr_change_unexplained',
                    'severity': 'high' if abs(dscr_change) > 0.2 else 'medium',
                    'property_id': property_id,
                    'period_id': period_id,
                    'check_type': 'dscr_change_explanation',
                    'current_dscr': current_dscr,
                    'previous_dscr': previous_dscr,
                    'dscr_change': dscr_change,
                    'current_noi': current_noi,
                    'previous_noi': previous_noi,
                    'noi_change': noi_change,
                    'current_debt_service': current_debt_service,
                    'previous_debt_service': previous_debt_service,
                    'debt_service_change': ds_change,
                    'expected_dscr_change': expected_dscr_change,
                    'difference': difference,
                    'baseline_type': 'mean',
                    'anomaly_category': 'covenant',
                    'pattern_type': 'trend',
                    'detected_at': datetime.utcnow()
                }
                anomalies.append(anomaly)
        
        except Exception as e:
            logger.error(f"Error in DSCR change explanation check: {e}")
        
        return anomalies
    
    def _get_balance_sheet_cash(self, property_id: int, period_id: int) -> Optional[float]:
        """Get total cash from balance sheet."""
        # Sum all cash accounts (typically 0122-0125 range)
        cash_total = self.db.query(func.sum(BalanceSheetData.amount)).filter(
            BalanceSheetData.property_id == property_id,
            BalanceSheetData.period_id == period_id,
            BalanceSheetData.account_code.like('012%')  # Cash accounts
        ).scalar()
        
        return float(cash_total) if cash_total else None
    
    def _get_beginning_cash_from_reconciliation(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[float]:
        """Get beginning cash from cash account reconciliation."""
        reconciliation = self.db.query(CashAccountReconciliation).filter(
            CashAccountReconciliation.property_id == property_id,
            CashAccountReconciliation.period_id == period_id
        ).first()
        
        if reconciliation:
            return float(reconciliation.beginning_balance)
        return None
    
    def _get_net_cash_flow(self, property_id: int, period_id: int) -> Optional[float]:
        """Get net cash flow from cash flow statement."""
        header = self.db.query(CashFlowHeader).filter(
            CashFlowHeader.property_id == property_id,
            CashFlowHeader.period_id == period_id
        ).first()
        
        if header and header.net_cash_flow:
            return float(header.net_cash_flow)
        return None
    
    def _get_cash_flow_noi(self, property_id: int, period_id: int) -> Optional[float]:
        """Get NOI from cash flow statement."""
        # NOI is typically in PERFORMANCE_METRICS section
        noi_data = self.db.query(CashFlowData).filter(
            CashFlowData.property_id == property_id,
            CashFlowData.period_id == period_id,
            CashFlowData.line_section == 'PERFORMANCE_METRICS',
            CashFlowData.line_subcategory.like('%NOI%')
        ).first()
        
        if noi_data:
            return float(noi_data.period_amount)
        
        # Fallback: calculate from header
        header = self.db.query(CashFlowHeader).filter(
            CashFlowHeader.property_id == property_id,
            CashFlowHeader.period_id == period_id
        ).first()
        
        if header and header.net_operating_income:
            return float(header.net_operating_income)
        return None
    
    def _get_income_statement_revenue(self, property_id: int, period_id: int) -> Optional[float]:
        """Get total revenue from income statement."""
        metrics = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == period_id
        ).first()
        
        if metrics and metrics.total_revenue:
            return float(metrics.total_revenue)
        return None
    
    def _get_income_statement_operating_expenses(
        self,
        property_id: int,
        period_id: int
    ) -> Optional[float]:
        """Get total operating expenses from income statement."""
        metrics = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == period_id
        ).first()
        
        if metrics and metrics.total_expenses:
            return float(metrics.total_expenses)
        return None
    
    def _get_revenue_components(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, float]:
        """Get revenue component breakdown."""
        components = {}
        
        # Get revenue line items from income statement
        revenue_items = self.db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code.like('4%')  # Revenue accounts typically start with 4
        ).all()
        
        for item in revenue_items:
            if item.period_amount:
                components[item.account_code] = float(item.period_amount)
        
        return components
    
    def _get_dscr(self, property_id: int, period_id: int) -> Optional[float]:
        """Get DSCR from financial metrics."""
        metrics = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == period_id
        ).first()
        
        if metrics:
            # Calculate DSCR if not directly stored
            if metrics.net_operating_income and metrics.total_debt:
                # Approximate debt service as interest portion (simplified)
                # In production, get actual debt service from mortgage statements
                return float(metrics.net_operating_income / metrics.total_debt * 12) if metrics.total_debt != 0 else None
        return None
    
    def _get_noi(self, property_id: int, period_id: int) -> Optional[float]:
        """Get NOI from financial metrics."""
        metrics = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == period_id
        ).first()
        
        if metrics and metrics.net_operating_income:
            return float(metrics.net_operating_income)
        return None
    
    def _get_debt_service(self, property_id: int, period_id: int) -> Optional[float]:
        """Get debt service (principal + interest) for the period."""
        # Try to get from mortgage payment history
        from app.models.mortgage_payment_history import MortgagePaymentHistory
        
        payments = self.db.query(func.sum(MortgagePaymentHistory.principal_payment + MortgagePaymentHistory.interest_payment)).filter(
            MortgagePaymentHistory.property_id == property_id,
            MortgagePaymentHistory.period_id == period_id
        ).scalar()
        
        if payments:
            return float(payments)
        
        # Fallback: estimate from metrics (simplified)
        metrics = self.db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == period_id
        ).first()
        
        if metrics and metrics.total_debt:
            # Rough estimate: assume 5% annual interest rate
            return float(metrics.total_debt * 0.05 / 12)  # Monthly debt service
        return None
    
    def save_anomaly_to_db(
        self,
        anomaly: Dict[str, Any],
        document_id: Optional[int] = None
    ) -> Optional[AnomalyDetection]:
        """
        Save cross-statement anomaly to database.
        
        Args:
            anomaly: Anomaly dictionary from detect_cross_statement_anomalies
            document_id: Optional document ID to associate with
            
        Returns:
            Created AnomalyDetection record
        """
        if document_id is None:
            # Try to get document_id from period
            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == anomaly['period_id']
            ).first()
            if period:
                # Get most recent document for this period
                from app.models.document_upload import DocumentUpload
                doc = self.db.query(DocumentUpload).filter(
                    DocumentUpload.property_id == anomaly['property_id'],
                    DocumentUpload.period_id == anomaly['period_id']
                ).order_by(DocumentUpload.upload_date.desc()).first()
                if doc:
                    document_id = doc.id
        
        if document_id is None:
            logger.warning(f"Could not determine document_id for cross-statement anomaly")
            return None
        
        try:
            anomaly_record = AnomalyDetection(
                document_id=document_id,
                field_name=anomaly.get('check_type', 'cross_statement'),
                field_value=str(anomaly.get('actual_ending_cash') or anomaly.get('cf_noi') or anomaly.get('current_dscr', '')),
                expected_value=str(anomaly.get('expected_ending_cash') or anomaly.get('expected_noi') or anomaly.get('expected_dscr_change', '')),
                z_score=Decimal(str(anomaly.get('difference', 0) / 1000.0)),  # Normalized
                percentage_change=Decimal(str(anomaly.get('difference_percentage', 0))),
                anomaly_type='cross_statement',
                severity=anomaly['severity'],
                confidence=Decimal('0.90'),  # High confidence for cross-statement checks
                baseline_type=BaselineType.MEAN,
                anomaly_category=AnomalyCategory.ACCOUNTING,
                pattern_type=anomaly.get('pattern_type', 'structure'),
                metadata_json={
                    'check_type': anomaly.get('check_type'),
                    'anomaly_type': anomaly.get('type'),
                    'difference': anomaly.get('difference'),
                    'difference_percentage': anomaly.get('difference_percentage'),
                    **{k: v for k, v in anomaly.items() if k not in ['type', 'severity', 'property_id', 'period_id', 'detected_at']}
                }
            )
            
            self.db.add(anomaly_record)
            self.db.commit()
            self.db.refresh(anomaly_record)
            
            logger.info(f"Saved cross-statement anomaly: {anomaly_record.id} for check {anomaly.get('check_type')}")
            return anomaly_record
            
        except Exception as e:
            logger.error(f"Error saving cross-statement anomaly: {e}")
            self.db.rollback()
            return None
