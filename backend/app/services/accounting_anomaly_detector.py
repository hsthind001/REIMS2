"""
Advanced Accounting Anomaly Detector

Detects:
- Unusual account reclassifications
- Month-end close anomalies
- Currency mismatches
- Benford's Law violations
- Duplicate patterns
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import hashlib
import logging

from app.models.anomaly_detection import AnomalyDetection, AnomalyCategory
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData

logger = logging.getLogger(__name__)

try:
    import benfordslaw
    BENFORDS_AVAILABLE = True
except ImportError:
    BENFORDS_AVAILABLE = False
    logger.warning("benfordslaw not available - Benford's Law checks disabled")


class AccountingAnomalyDetector:
    """
    Detects accounting-specific anomalies.
    """
    
    def __init__(self, db: Session):
        """Initialize accounting detector."""
        self.db = db
    
    def detect_accounting_anomalies(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """
        Detect all accounting anomalies for a period.
        
        Args:
            property_id: Property ID
            period_id: Period ID
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # 1. Account reclassifications
        anomalies.extend(self._detect_reclassifications(property_id, period_id))
        
        # 2. Month-end close anomalies
        anomalies.extend(self._detect_month_end_anomalies(property_id, period_id))
        
        # 3. Currency mismatches
        anomalies.extend(self._detect_currency_mismatches(property_id, period_id))
        
        # 4. Benford's Law violations
        if BENFORDS_AVAILABLE:
            anomalies.extend(self._detect_benford_violations(property_id, period_id))
        
        # 5. Duplicate patterns
        anomalies.extend(self._detect_duplicates(property_id, period_id))
        
        return anomalies
    
    def _detect_reclassifications(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """Detect unusual account reclassifications."""
        # Get previous period
        from app.models.financial_period import FinancialPeriod
        current_period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.id == period_id
        ).first()
        
        if not current_period:
            return []
        
        prev_period = self.db.query(FinancialPeriod).filter(
            and_(
                FinancialPeriod.property_id == property_id,
                FinancialPeriod.period_end_date < current_period.period_end_date
            )
        ).order_by(FinancialPeriod.period_end_date.desc()).first()
        
        if not prev_period:
            return []
        
        # Compare account codes between periods
        current_accounts = set(
            row.account_code for row in
            self.db.query(IncomeStatementData.account_code).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id
            ).distinct().all()
        )
        
        prev_accounts = set(
            row.account_code for row in
            self.db.query(IncomeStatementData.account_code).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == prev_period.id
            ).distinct().all()
        )
        
        # Find new or removed accounts
        new_accounts = current_accounts - prev_accounts
        removed_accounts = prev_accounts - current_accounts
        
        anomalies = []
        if new_accounts:
            anomalies.append({
                'anomaly_type': 'account_reclassification',
                'severity': 'medium',
                'message': f"New accounts detected: {', '.join(new_accounts)}",
                'details': {'new_accounts': list(new_accounts)}
            })
        
        if removed_accounts:
            anomalies.append({
                'anomaly_type': 'account_reclassification',
                'severity': 'medium',
                'message': f"Removed accounts detected: {', '.join(removed_accounts)}",
                'details': {'removed_accounts': list(removed_accounts)}
            })
        
        return anomalies
    
    def _detect_month_end_anomalies(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """
        Detect month-end close anomalies.
        
        Checks for:
        - Large transactions on last day of period
        - Missing expected provision accounts
        - Unusual last-day posting patterns
        """
        from app.models.financial_period import FinancialPeriod
        from app.models.income_statement_header import IncomeStatementHeader
        
        period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.id == period_id
        ).first()
        
        if not period:
            return []
        
        anomalies = []
        
        # 1. Check for large transactions on last day of period
        # Use period_end_date to identify last-day transactions
        if period.period_end_date:
            # Get header to check report_generation_date
            header = self.db.query(IncomeStatementHeader).filter(
                IncomeStatementHeader.period_id == period_id
            ).first()
            
            if header and header.report_generation_date:
                # Check if report was generated on or very close to period end
                days_diff = (header.report_generation_date.date() - period.period_end_date).days
                
                # If report generated within 3 days of period end, check for large last-day entries
                if 0 <= days_diff <= 3:
                    # Get large transactions (threshold: $10,000)
                    large_transactions = self.db.query(IncomeStatementData).filter(
                        and_(
                            IncomeStatementData.property_id == property_id,
                            IncomeStatementData.period_id == period_id,
                            func.abs(IncomeStatementData.period_amount) >= 10000
                        )
                    ).all()
                    
                    if large_transactions:
                        anomalies.append({
                            'anomaly_type': 'large_last_day_transaction',
                            'severity': 'medium',
                            'message': f"Large transactions detected near period end: {len(large_transactions)} transactions >= $10,000",
                            'details': {
                                'transaction_count': len(large_transactions),
                                'period_end_date': period.period_end_date.isoformat() if period.period_end_date else None,
                                'report_date': header.report_generation_date.isoformat() if header.report_generation_date else None,
                                'days_from_period_end': days_diff
                            }
                        })
        
        # 2. Check for missing expected provision accounts
        provision_anomalies = self._check_provision_accounts(property_id, period_id)
        anomalies.extend(provision_anomalies)
        
        return anomalies
    
    def _check_provision_accounts(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """
        Check for expected provision accounts.
        
        Expected provision accounts typically include:
        - Accrued liabilities (2xxx series, especially 21xx-22xx)
        - Accrued expenses
        - Accrued interest
        - Accrued taxes
        """
        anomalies = []
        
        # Expected provision account code patterns
        expected_provision_patterns = [
            '21%',  # Accrued liabilities
            '22%',  # Accrued expenses
            '2197%',  # Current portion of long-term debt (may have provisions)
        ]
        
        # Get all account codes for this period
        existing_accounts = set(
            row.account_code for row in
            self.db.query(IncomeStatementData.account_code).filter(
                and_(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.period_id == period_id
                )
            ).distinct().all()
        )
        
        # Also check balance sheet for provision accounts
        from app.models.balance_sheet_data import BalanceSheetData
        balance_sheet_accounts = set(
            row.account_code for row in
            self.db.query(BalanceSheetData.account_code).filter(
                and_(
                    BalanceSheetData.property_id == property_id,
                    BalanceSheetData.period_id == period_id
                )
            ).distinct().all()
        )
        
        all_accounts = existing_accounts.union(balance_sheet_accounts)
        
        # Check if any expected provision accounts are missing
        missing_provisions = []
        for pattern in expected_provision_patterns:
            # Check if any account matches the pattern
            matching_accounts = [
                acc for acc in all_accounts
                if acc and acc.startswith(pattern.replace('%', ''))
            ]
            
            if not matching_accounts:
                missing_provisions.append(pattern)
        
        # If we have historical data, check if provisions were present in previous periods
        from app.models.financial_period import FinancialPeriod
        current_period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.id == period_id
        ).first()
        
        if current_period and missing_provisions:
            # Check previous period for comparison
            prev_period = self.db.query(FinancialPeriod).filter(
                and_(
                    FinancialPeriod.property_id == property_id,
                    FinancialPeriod.period_end_date < current_period.period_end_date
                )
            ).order_by(FinancialPeriod.period_end_date.desc()).first()
            
            if prev_period:
                prev_accounts = set(
                    row.account_code for row in
                    self.db.query(IncomeStatementData.account_code).filter(
                        and_(
                            IncomeStatementData.property_id == property_id,
                            IncomeStatementData.period_id == prev_period.id
                        )
                    ).distinct().all()
                )
                
                # Check if provisions existed in previous period but are missing now
                prev_had_provisions = any(
                    any(acc.startswith(p.replace('%', '')) for acc in prev_accounts if acc)
                    for p in expected_provision_patterns
                )
                
                if prev_had_provisions:
                    anomalies.append({
                        'anomaly_type': 'missing_provision_accounts',
                        'severity': 'high',
                        'message': f"Expected provision accounts missing: {', '.join(missing_provisions)}",
                        'details': {
                            'missing_patterns': missing_provisions,
                            'previous_period_had_provisions': True
                        }
                    })
        
        return anomalies
    
    def _detect_currency_mismatches(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """
        Detect currency and FX mismatches.
        
        Checks for:
        - Transactions with unexpected currencies
        - Currency inconsistencies within the same period
        - FX conversion anomalies
        """
        anomalies = []
        
        # Get property to check expected currency
        from app.models.property import Property
        property_obj = self.db.query(Property).filter(
            Property.id == property_id
        ).first()
        
        if not property_obj:
            return []
        
        # Expected currency (default to USD if not specified)
        # Note: Property model may not have currency field, so we'll use a default
        expected_currency = getattr(property_obj, 'currency', 'USD') or 'USD'
        
        # Check if financial data models have currency fields
        # Since models may not have explicit currency fields, we'll check for:
        # 1. Currency indicators in account codes or descriptions
        # 2. Amount patterns that suggest currency conversion issues
        
        # Get all transactions for the period
        transactions = self.db.query(IncomeStatementData).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id
            )
        ).all()
        
        # Check for currency indicators in descriptions
        currency_keywords = {
            'USD': ['USD', 'US$', 'dollar', 'dollars'],
            'CAD': ['CAD', 'CA$', 'canadian', 'canada'],
            'EUR': ['EUR', '€', 'euro', 'euros'],
            'GBP': ['GBP', '£', 'pound', 'pounds', 'sterling']
        }
        
        currency_mismatches = []
        for trans in transactions:
            if not trans.description:
                continue
            
            desc_upper = trans.description.upper()
            
            # Check for currency indicators in description
            detected_currencies = []
            for currency, keywords in currency_keywords.items():
                if any(keyword.upper() in desc_upper for keyword in keywords):
                    detected_currencies.append(currency)
            
            # If currency detected and doesn't match expected
            if detected_currencies and expected_currency not in detected_currencies:
                currency_mismatches.append({
                    'account_code': trans.account_code,
                    'account_name': trans.account_name,
                    'amount': float(trans.period_amount) if trans.period_amount else 0.0,
                    'description': trans.description,
                    'detected_currency': detected_currencies[0],
                    'expected_currency': expected_currency
                })
        
        if currency_mismatches:
            anomalies.append({
                'anomaly_type': 'currency_mismatch',
                'severity': 'medium',
                'message': f"Currency mismatches detected: {len(currency_mismatches)} transactions",
                'details': {
                    'expected_currency': expected_currency,
                    'mismatches': currency_mismatches[:10]  # First 10
                }
            })
        
        # Check for FX conversion anomalies (round numbers that suggest conversion)
        # Large round numbers might indicate currency conversion issues
        fx_anomalies = []
        for trans in transactions:
            if trans.period_amount:
                amount = abs(float(trans.period_amount))
                # Check for suspicious round numbers (exactly divisible by 1000, 10000, etc.)
                if amount >= 1000 and (amount % 1000 == 0 or amount % 10000 == 0):
                    # Check if description suggests FX conversion
                    desc = (trans.description or '').upper()
                    if any(keyword in desc for keyword in ['FX', 'EXCHANGE', 'CONVERT', 'RATE']):
                        fx_anomalies.append({
                            'account_code': trans.account_code,
                            'amount': amount,
                            'description': trans.description
                        })
        
        if fx_anomalies:
            anomalies.append({
                'anomaly_type': 'fx_conversion_anomaly',
                'severity': 'low',
                'message': f"Potential FX conversion anomalies: {len(fx_anomalies)} transactions",
                'details': {'anomalies': fx_anomalies[:10]}
            })
        
        return anomalies
    
    def _detect_benford_violations(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """Detect Benford's Law violations."""
        # Get high-risk account values (CAPEX, large invoices)
        high_risk_accounts = ['CAPEX', 'Capital Expenditures', 'Major Repairs']
        
        values = []
        for account in high_risk_accounts:
            data = self.db.query(IncomeStatementData.period_amount).filter(
                and_(
                    IncomeStatementData.property_id == property_id,
                    IncomeStatementData.period_id == period_id,
                    IncomeStatementData.account_code.like(f'%{account}%')
                )
            ).all()
            
            values.extend([abs(float(row.period_amount)) for row in data if row.period_amount and abs(float(row.period_amount)) >= 1000])
        
        if len(values) < 20:
            return []
        
        try:
            bl = benfordslaw.positive()
            results = bl.fit(values)
            
            # Check for significant deviations
            violations = []
            for digit, expected, observed in zip(results['percentage'], results['expected'], results['observed']):
                if abs(observed - expected) > 0.05:  # 5% deviation
                    violations.append({
                        'digit': digit,
                        'expected': expected,
                        'observed': observed,
                        'deviation': abs(observed - expected)
                    })
            
            if violations:
                return [{
                    'anomaly_type': 'benford_law_violation',
                    'severity': 'medium',
                    'message': f"Benford's Law violation detected in high-risk accounts",
                    'details': {'violations': violations}
                }]
        except Exception as e:
            logger.error(f"Benford's Law check error: {e}")
        
        return []
    
    def _detect_duplicates(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """Detect duplicate patterns using hashing."""
        # Get all transactions
        transactions = self.db.query(
            IncomeStatementData.account_code,
            IncomeStatementData.period_amount,
            IncomeStatementData.description
        ).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id
            )
        ).all()
        
        # Hash transactions
        hashes = {}
        duplicates = []
        
        for trans in transactions:
            # Create hash from account, amount, description
            hash_key = hashlib.md5(
                f"{trans.account_code}|{trans.period_amount}|{trans.description}".encode()
            ).hexdigest()
            
            if hash_key in hashes:
                duplicates.append({
                    'account_code': trans.account_code,
                    'amount': float(trans.period_amount) if trans.period_amount else 0.0,
                    'description': trans.description
                })
            else:
                hashes[hash_key] = trans
        
        if duplicates:
            return [{
                'anomaly_type': 'duplicate_transaction',
                'severity': 'high',
                'message': f"Duplicate transactions detected: {len(duplicates)} instances",
                'details': {'duplicates': duplicates[:10]}  # First 10
            }]
        
        return []
