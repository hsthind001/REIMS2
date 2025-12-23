"""
Real Estate Domain-Specific Anomaly Rules

Detects anomalies specific to real estate financial data:
- Rent roll: tenant move-outs, lease expiries, concessions, delinquency spikes
- Mortgage: interest rate resets, principal curtailments, escrow changes
- NOI: seasonality and property-type seasonality bands
- Capex: one-time vs recurring classification
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.income_statement_data import IncomeStatementData
from app.models.financial_period import FinancialPeriod
from app.models.property import Property

logger = logging.getLogger(__name__)


class RealEstateAnomalyRules:
    """Real estate domain-specific anomaly detection rules"""
    
    def __init__(self, db: Session):
        """
        Initialize real estate anomaly rules
        
        Args:
            db: Database session
        """
        self.db = db
    
    def detect_rent_roll_anomalies(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """
        Detect rent roll anomalies:
        - Tenant move-outs
        - Lease expiries
        - Concessions
        - Delinquency spikes
        - Concentration risk
        
        Args:
            property_id: Property ID
            period_id: Period ID
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Get current period rent roll
        current_rent_roll = self.db.query(RentRollData).filter(
            and_(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period_id
            )
        ).all()
        
        if not current_rent_roll:
            return anomalies
        
        # Get prior period for comparison
        current_period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.id == period_id
        ).first()
        
        if not current_period:
            return anomalies
        
        # Find prior period
        prior_period = self.db.query(FinancialPeriod).filter(
            and_(
                FinancialPeriod.property_id == property_id,
                FinancialPeriod.period_end_date < current_period.period_end_date
            )
        ).order_by(FinancialPeriod.period_end_date.desc()).first()
        
        if prior_period:
            prior_rent_roll = self.db.query(RentRollData).filter(
                and_(
                    RentRollData.property_id == property_id,
                    RentRollData.period_id == prior_period.id
                )
            ).all()
        else:
            prior_rent_roll = []
        
        # 1. Detect tenant move-outs
        current_tenants = {r.tenant_name: r for r in current_rent_roll if r.tenant_name}
        prior_tenants = {r.tenant_name: r for r in prior_rent_roll if r.tenant_name}
        
        moved_out = set(prior_tenants.keys()) - set(current_tenants.keys())
        if moved_out:
            for tenant_name in moved_out:
                tenant_data = prior_tenants[tenant_name]
                anomalies.append({
                    'type': 'tenant_move_out',
                    'field_name': f'tenant_{tenant_name}',
                    'severity': 'medium',
                    'description': f'Tenant {tenant_name} moved out',
                    'impact_amount': tenant_data.monthly_rent if tenant_data.monthly_rent else Decimal('0'),
                    'expected_value': tenant_data.monthly_rent,
                    'actual_value': Decimal('0')
                })
        
        # 2. Detect lease expiries (within 90 days)
        for record in current_rent_roll:
            if record.lease_end_date:
                days_until_expiry = (record.lease_end_date - current_period.period_end_date).days
                if 0 <= days_until_expiry <= 90:
                    anomalies.append({
                        'type': 'lease_expiring',
                        'field_name': f'lease_{record.tenant_name}',
                        'severity': 'high' if days_until_expiry <= 30 else 'medium',
                        'description': f'Lease for {record.tenant_name} expires in {days_until_expiry} days',
                        'days_until_expiry': days_until_expiry
                    })
        
        # 3. Detect concessions
        for record in current_rent_roll:
            if record.concessions and record.concessions > Decimal('0'):
                # Check if concession is unusually high (>10% of rent)
                if record.monthly_rent and record.monthly_rent > Decimal('0'):
                    concession_pct = (record.concessions / record.monthly_rent) * 100
                    if concession_pct > 10:
                        anomalies.append({
                            'type': 'high_concession',
                            'field_name': f'concession_{record.tenant_name}',
                            'severity': 'medium',
                            'description': f'High concession for {record.tenant_name}: {concession_pct:.1f}% of rent',
                            'impact_amount': record.concessions,
                            'concession_percent': float(concession_pct)
                        })
        
        # 4. Detect delinquency spikes
        current_delinquent = sum(1 for r in current_rent_roll if r.days_delinquent and r.days_delinquent > 30)
        prior_delinquent = sum(1 for r in prior_rent_roll if r.days_delinquent and r.days_delinquent > 30)
        
        if prior_delinquent > 0:
            delinquency_change = ((current_delinquent - prior_delinquent) / prior_delinquent) * 100
            if delinquency_change > 50:  # 50% increase
                anomalies.append({
                    'type': 'delinquency_spike',
                    'field_name': 'delinquency_rate',
                    'severity': 'high',
                    'description': f'Delinquency increased by {delinquency_change:.1f}% ({current_delinquent} vs {prior_delinquent} tenants)',
                    'current_delinquent': current_delinquent,
                    'prior_delinquent': prior_delinquent,
                    'change_percent': float(delinquency_change)
                })
        
        # 5. Detect concentration risk (single tenant >30% of revenue)
        total_revenue = sum(r.monthly_rent for r in current_rent_roll if r.monthly_rent)
        if total_revenue > Decimal('0'):
            for record in current_rent_roll:
                if record.monthly_rent and record.tenant_name:
                    tenant_pct = (record.monthly_rent / total_revenue) * 100
                    if tenant_pct > 30:
                        anomalies.append({
                            'type': 'concentration_risk',
                            'field_name': f'concentration_{record.tenant_name}',
                            'severity': 'high',
                            'description': f'High concentration risk: {record.tenant_name} represents {tenant_pct:.1f}% of revenue',
                            'concentration_percent': float(tenant_pct),
                            'tenant_name': record.tenant_name
                        })
        
        return anomalies
    
    def detect_mortgage_anomalies(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """
        Detect mortgage statement anomalies:
        - Interest rate resets
        - Principal curtailments
        - Escrow changes
        
        Args:
            property_id: Property ID
            period_id: Period ID
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Get current and prior mortgage statements
        current_mortgage = self.db.query(MortgageStatementData).filter(
            and_(
                MortgageStatementData.property_id == property_id,
                MortgageStatementData.period_id == period_id
            )
        ).first()
        
        if not current_mortgage:
            return anomalies
        
        # Get prior period
        current_period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.id == period_id
        ).first()
        
        if not current_period:
            return anomalies
        
        prior_period = self.db.query(FinancialPeriod).filter(
            and_(
                FinancialPeriod.property_id == property_id,
                FinancialPeriod.period_end_date < current_period.period_end_date
            )
        ).order_by(FinancialPeriod.period_end_date.desc()).first()
        
        if prior_period:
            prior_mortgage = self.db.query(MortgageStatementData).filter(
                and_(
                    MortgageStatementData.property_id == property_id,
                    MortgageStatementData.period_id == prior_period.id
                )
            ).first()
        else:
            prior_mortgage = None
        
        # 1. Detect interest rate resets
        if current_mortgage.interest_rate and prior_mortgage and prior_mortgage.interest_rate:
            rate_change = abs(current_mortgage.interest_rate - prior_mortgage.interest_rate)
            if rate_change > Decimal('0.5'):  # 0.5% change
                anomalies.append({
                    'type': 'interest_rate_reset',
                    'field_name': 'interest_rate',
                    'severity': 'high',
                    'description': f'Interest rate changed by {rate_change:.2f}% ({prior_mortgage.interest_rate}% to {current_mortgage.interest_rate}%)',
                    'prior_rate': float(prior_mortgage.interest_rate),
                    'current_rate': float(current_mortgage.interest_rate),
                    'change': float(rate_change)
                })
        
        # 2. Detect principal curtailments (unusual principal payments)
        if current_mortgage.principal_payment and prior_mortgage and prior_mortgage.principal_payment:
            principal_change = current_mortgage.principal_payment - prior_mortgage.principal_payment
            if principal_change > Decimal('1000'):  # $1000 increase
                anomalies.append({
                    'type': 'principal_curtailment',
                    'field_name': 'principal_payment',
                    'severity': 'medium',
                    'description': f'Principal payment increased by ${principal_change:,.2f}',
                    'prior_principal': float(prior_mortgage.principal_payment),
                    'current_principal': float(current_mortgage.principal_payment),
                    'change': float(principal_change)
                })
        
        # 3. Detect escrow changes (>20% change)
        if current_mortgage.escrow_balance and prior_mortgage and prior_mortgage.escrow_balance:
            escrow_change_pct = abs((current_mortgage.escrow_balance - prior_mortgage.escrow_balance) / prior_mortgage.escrow_balance) * 100
            if escrow_change_pct > 20:
                anomalies.append({
                    'type': 'escrow_change',
                    'field_name': 'escrow_balance',
                    'severity': 'medium',
                    'description': f'Escrow balance changed by {escrow_change_pct:.1f}%',
                    'prior_escrow': float(prior_mortgage.escrow_balance),
                    'current_escrow': float(current_mortgage.escrow_balance),
                    'change_percent': float(escrow_change_pct)
                })
        
        return anomalies
    
    def detect_noi_seasonality_anomalies(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """
        Detect NOI seasonality anomalies based on property type
        
        Args:
            property_id: Property ID
            period_id: Period ID
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Get property type
        property_obj = self.db.query(Property).filter(
            Property.id == property_id
        ).first()
        
        if not property_obj or not property_obj.property_type:
            return anomalies
        
        property_type = property_obj.property_type.lower()
        
        # Get current period NOI
        current_period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.id == period_id
        ).first()
        
        if not current_period:
            return anomalies
        
        # Get NOI from income statement
        current_noi = self.db.query(IncomeStatementData).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id,
                IncomeStatementData.account_code.like('9%')  # Net income accounts
            )
        ).first()
        
        if not current_noi or not current_noi.period_amount:
            return anomalies
        
        # Get historical NOI for same month (seasonal comparison)
        historical_noi = self.db.query(IncomeStatementData).join(
            FinancialPeriod
        ).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                func.extract('month', FinancialPeriod.period_end_date) == current_period.period_month,
                func.extract('year', FinancialPeriod.period_end_date) < current_period.period_year,
                IncomeStatementData.account_code.like('9%')
            )
        ).order_by(FinancialPeriod.period_end_date.desc()).limit(3).all()
        
        if len(historical_noi) >= 2:
            avg_historical = sum(float(n.period_amount) for n in historical_noi) / len(historical_noi)
            current_value = float(current_noi.period_amount)
            
            # Property-type specific seasonality bands
            if property_type in ['multifamily', 'apartment']:
                # Multifamily: expect 5-10% seasonal variation
                expected_variation = 0.10
            elif property_type in ['retail', 'shopping_center']:
                # Retail: expect 15-20% seasonal variation (holiday season)
                expected_variation = 0.20
            elif property_type in ['office']:
                # Office: expect 5% seasonal variation
                expected_variation = 0.05
            else:
                expected_variation = 0.10  # Default
            
            change_pct = abs((current_value - avg_historical) / avg_historical) * 100 if avg_historical != 0 else 0
            
            if change_pct > (expected_variation * 100 * 1.5):  # 1.5x expected variation
                anomalies.append({
                    'type': 'noi_seasonality_anomaly',
                    'field_name': 'net_operating_income',
                    'severity': 'medium',
                    'description': f'NOI {change_pct:.1f}% different from seasonal average (expected ±{expected_variation*100:.0f}%)',
                    'current_value': current_value,
                    'seasonal_average': avg_historical,
                    'change_percent': change_pct,
                    'property_type': property_type
                })
        
        return anomalies
    
    def classify_capex(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, Any]:
        """
        Classify capex as one-time vs recurring
        
        Args:
            property_id: Property ID
            period_id: Period ID
            
        Returns:
            Classification results
        """
        # Get capex from income statement or balance sheet
        # This is a simplified version - would need actual capex account codes
        capex_records = self.db.query(IncomeStatementData).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id,
                IncomeStatementData.account_code.like('6%')  # Expense accounts
            )
        ).all()
        
        # Get historical capex for comparison
        current_period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.id == period_id
        ).first()
        
        if not current_period:
            return {
                'one_time_capex': [],
                'recurring_capex': [],
                'total_one_time': Decimal('0'),
                'total_recurring': Decimal('0')
            }
        
        # Get prior periods
        prior_periods = self.db.query(FinancialPeriod).filter(
            and_(
                FinancialPeriod.property_id == property_id,
                FinancialPeriod.period_end_date < current_period.period_end_date
            )
        ).order_by(FinancialPeriod.period_end_date.desc()).limit(12).all()
        
        # Classify based on frequency
        one_time = []
        recurring = []
        
        for record in capex_records:
            # Check if this account appears in prior periods
            prior_count = 0
            for prior_period in prior_periods:
                prior_record = self.db.query(IncomeStatementData).filter(
                    and_(
                        IncomeStatementData.property_id == property_id,
                        IncomeStatementData.period_id == prior_period.id,
                        IncomeStatementData.account_code == record.account_code
                    )
                ).first()
                if prior_record and prior_record.period_amount:
                    prior_count += 1
            
            # If appears in <30% of prior periods, classify as one-time
            if prior_count < len(prior_periods) * 0.3:
                one_time.append({
                    'account_code': record.account_code,
                    'account_name': record.account_name,
                    'amount': float(record.period_amount) if record.period_amount else 0
                })
            else:
                recurring.append({
                    'account_code': record.account_code,
                    'account_name': record.account_name,
                    'amount': float(record.period_amount) if record.period_amount else 0
                })
        
        return {
            'one_time_capex': one_time,
            'recurring_capex': recurring,
            'total_one_time': sum(item['amount'] for item in one_time),
            'total_recurring': sum(item['amount'] for item in recurring)
        }

