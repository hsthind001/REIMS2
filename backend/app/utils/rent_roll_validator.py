"""
Rent Roll Validation System - Template v2.0

Implements 20+ validation rules with quality scoring and auto-approve criteria
Based on Rent_Roll_Extraction_Template_v2.0 specification
"""
from typing import Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class ValidationFlag:
    """Validation flag with severity level"""
    severity: str  # CRITICAL, WARNING, INFO
    record_id: Optional[int] = None
    unit_number: Optional[str] = None
    field: Optional[str] = None
    message: str = ""
    expected: Optional[str] = None
    actual: Optional[str] = None


class RentRollValidator:
    """
    Comprehensive validation for rent roll data
    
    Implements Template v2.0 validation rules:
    - Financial calculations (annual = monthly × 12)
    - Rent per SF validations
    - Date sequence logic
    - Security deposit ranges
    - Edge case detection
    """
    
    def __init__(self):
        self.flags: List[ValidationFlag] = []
    
    def validate_records(self, records: List[Dict], report_date: Optional[str] = None) -> List[ValidationFlag]:
        """
        Validate all records and return validation flags
        
        Args:
            records: List of rent roll records
            report_date: Report date in YYYY-MM-DD format
            
        Returns:
            List of validation flags
        """
        self.flags = []
        self.report_date = datetime.strptime(report_date, '%Y-%m-%d').date() if report_date else None
        
        for idx, record in enumerate(records, 1):
            record_id = record.get('id', idx)
            unit_number = record.get('unit_number', '')
            
            # Skip validation for gross rent rows (they have different rules)
            if record.get('is_gross_rent_row'):
                self._validate_gross_rent_row(record, record_id, unit_number)
                continue
            
            # Skip validation for vacant units (many fields legitimately NULL)
            if record.get('is_vacant') or record.get('occupancy_status') == 'vacant':
                self._validate_vacant_unit(record, record_id, unit_number)
                continue
            
            # Validate active leases
            self._validate_financial_calculations(record, record_id, unit_number)
            self._validate_rent_per_sf(record, record_id, unit_number)
            self._validate_date_sequence(record, record_id, unit_number)
            self._validate_term_calculation(record, record_id, unit_number)
            self._validate_tenancy_calculation(record, record_id, unit_number)
            self._validate_area(record, record_id, unit_number)
            self._validate_security_deposit(record, record_id, unit_number)
            self._validate_non_negative_values(record, record_id, unit_number)
            self._detect_edge_cases(record, record_id, unit_number)
        
        return self.flags
    
    def _validate_financial_calculations(self, record: Dict, record_id: int, unit_number: str):
        """Validate: Annual Rent = Monthly Rent × 12 (±2% tolerance)"""
        monthly = record.get('monthly_rent')
        annual = record.get('annual_rent')
        
        if monthly is not None and annual is not None and monthly > 0:
            calculated_annual = float(monthly) * 12
            actual_annual = float(annual)
            diff_pct = abs(calculated_annual - actual_annual) / actual_annual * 100 if actual_annual > 0 else 0
            
            if diff_pct > 2.0:
                self.flags.append(ValidationFlag(
                    severity='CRITICAL',
                    record_id=record_id,
                    unit_number=unit_number,
                    field='annual_rent',
                    message=f'Annual rent mismatch: {diff_pct:.1f}% difference',
                    expected=f'${calculated_annual:,.2f}',
                    actual=f'${actual_annual:,.2f}'
                ))
    
    def _validate_rent_per_sf(self, record: Dict, record_id: int, unit_number: str):
        """Validate: Rent per SF = Monthly Rent / Area (±$0.05 tolerance)"""
        monthly = record.get('monthly_rent')
        area = record.get('unit_area_sqft')
        rent_per_sf = record.get('monthly_rent_per_sqft')
        
        if monthly is not None and area is not None and area > 0 and rent_per_sf is not None:
            calculated_per_sf = float(monthly) / float(area)
            actual_per_sf = float(rent_per_sf)
            diff = abs(calculated_per_sf - actual_per_sf)
            
            if diff > 0.05:
                self.flags.append(ValidationFlag(
                    severity='WARNING',
                    record_id=record_id,
                    unit_number=unit_number,
                    field='monthly_rent_per_sqft',
                    message=f'Rent per SF mismatch: ${diff:.3f} difference',
                    expected=f'${calculated_per_sf:.2f}',
                    actual=f'${actual_per_sf:.2f}'
                ))
    
    def _validate_date_sequence(self, record: Dict, record_id: int, unit_number: str):
        """Validate: Lease From < Report Date ≤ Lease To (for active leases)"""
        lease_from = record.get('lease_start_date')
        lease_to = record.get('lease_end_date')
        
        # Convert to date objects if strings
        if isinstance(lease_from, str):
            lease_from = datetime.strptime(lease_from, '%Y-%m-%d').date()
        if isinstance(lease_to, str):
            lease_to = datetime.strptime(lease_to, '%Y-%m-%d').date()
        
        # Validate From < To
        if lease_from and lease_to:
            if lease_to < lease_from:
                self.flags.append(ValidationFlag(
                    severity='CRITICAL',
                    record_id=record_id,
                    unit_number=unit_number,
                    field='lease_end_date',
                    message=f'Lease end date ({lease_to}) before start date ({lease_from})'
                ))
        
        # Check for expired leases
        if lease_to and self.report_date:
            if lease_to < self.report_date:
                self.flags.append(ValidationFlag(
                    severity='WARNING',
                    record_id=record_id,
                    unit_number=unit_number,
                    field='lease_end_date',
                    message=f'Lease expired on {lease_to} but tenant still listed (possible holdover)'
                ))
    
    def _validate_term_calculation(self, record: Dict, record_id: int, unit_number: str):
        """Validate: Term months ≈ months between Lease From and Lease To (±2 months)"""
        lease_from = record.get('lease_start_date')
        lease_to = record.get('lease_end_date')
        term_months = record.get('lease_term_months')
        
        if not (lease_from and lease_to and term_months):
            return
        
        # Convert to date objects
        if isinstance(lease_from, str):
            lease_from = datetime.strptime(lease_from, '%Y-%m-%d').date()
        if isinstance(lease_to, str):
            lease_to = datetime.strptime(lease_to, '%Y-%m-%d').date()
        
        # Calculate months difference
        months_diff = (lease_to.year - lease_from.year) * 12 + (lease_to.month - lease_from.month)
        
        # Allow ±2 months tolerance
        if abs(months_diff - term_months) > 2:
            self.flags.append(ValidationFlag(
                severity='WARNING',
                record_id=record_id,
                unit_number=unit_number,
                field='lease_term_months',
                message=f'Term months mismatch: calculated {months_diff}, reported {term_months}'
            ))
    
    def _validate_tenancy_calculation(self, record: Dict, record_id: int, unit_number: str):
        """Validate: Tenancy Years ≈ years from Lease From to Report Date"""
        lease_from = record.get('lease_start_date')
        tenancy_years = record.get('tenancy_years')
        
        if not (lease_from and tenancy_years and self.report_date):
            return
        
        # Convert to date
        if isinstance(lease_from, str):
            lease_from = datetime.strptime(lease_from, '%Y-%m-%d').date()
        
        # Calculate years
        days_diff = (self.report_date - lease_from).days
        calculated_years = days_diff / 365.25
        
        # Allow ±0.5 year tolerance
        if abs(calculated_years - float(tenancy_years)) > 0.5:
            self.flags.append(ValidationFlag(
                severity='INFO',
                record_id=record_id,
                unit_number=unit_number,
                field='tenancy_years',
                message=f'Tenancy years mismatch: calculated {calculated_years:.2f}, reported {tenancy_years}'
            ))
    
    def _validate_area(self, record: Dict, record_id: int, unit_number: str):
        """Validate: Area is reasonable (0-100,000 SF for retail)"""
        area = record.get('unit_area_sqft')
        
        if area is None:
            return
        
        area_float = float(area)
        
        # Must be non-negative
        if area_float < 0:
            self.flags.append(ValidationFlag(
                severity='CRITICAL',
                record_id=record_id,
                unit_number=unit_number,
                field='unit_area_sqft',
                message=f'Negative area: {area_float}'
            ))
        
        # Unusually large (but not critical - could be anchor tenant)
        if area_float > 100000:
            self.flags.append(ValidationFlag(
                severity='INFO',
                record_id=record_id,
                unit_number=unit_number,
                field='unit_area_sqft',
                message=f'Very large unit: {area_float:,.0f} SF (may be anchor tenant)'
            ))
    
    def _validate_security_deposit(self, record: Dict, record_id: int, unit_number: str):
        """Validate: Security deposit typically 1-3 months rent"""
        monthly = record.get('monthly_rent')
        security = record.get('security_deposit')
        lease_from = record.get('lease_start_date')
        
        if not monthly or monthly <= 0:
            return
        
        monthly_float = float(monthly)
        
        # Missing security deposit on newer leases
        if security is None or security == 0:
            # Check if lease is recent (within 5 years)
            if lease_from and self.report_date:
                if isinstance(lease_from, str):
                    lease_from = datetime.strptime(lease_from, '%Y-%m-%d').date()
                years_ago = (self.report_date - lease_from).days / 365.25
                
                if years_ago < 5:
                    self.flags.append(ValidationFlag(
                        severity='INFO',
                        record_id=record_id,
                        unit_number=unit_number,
                        field='security_deposit',
                        message=f'No security deposit on lease from {lease_from}'
                    ))
        elif security:
            security_float = float(security)
            ratio = security_float / monthly_float
            
            # Unusually high or low
            if ratio < 0.5 or ratio > 4:
                self.flags.append(ValidationFlag(
                    severity='INFO',
                    record_id=record_id,
                    unit_number=unit_number,
                    field='security_deposit',
                    message=f'Unusual security deposit: {ratio:.1f} months of rent'
                ))
    
    def _validate_non_negative_values(self, record: Dict, record_id: int, unit_number: str):
        """Validate: All financial fields must be >= 0"""
        financial_fields = [
            'monthly_rent', 'annual_rent', 'gross_rent',
            'security_deposit', 'loc_amount',
            'monthly_rent_per_sqft', 'annual_rent_per_sqft',
            'annual_recoveries_per_sf', 'annual_misc_per_sf'
        ]
        
        for field in financial_fields:
            value = record.get(field)
            if value is not None and float(value) < 0:
                self.flags.append(ValidationFlag(
                    severity='CRITICAL',
                    record_id=record_id,
                    unit_number=unit_number,
                    field=field,
                    message=f'Negative value not allowed: {value}'
                ))
    
    def _detect_edge_cases(self, record: Dict, record_id: int, unit_number: str):
        """Detect edge cases and special situations"""
        monthly = record.get('monthly_rent')
        area = record.get('unit_area_sqft')
        lease_to = record.get('lease_end_date')
        lease_from = record.get('lease_start_date')
        term_months = record.get('lease_term_months')
        monthly_per_sf = record.get('monthly_rent_per_sqft')
        
        # Future lease
        if lease_from and self.report_date:
            if isinstance(lease_from, str):
                lease_from = datetime.strptime(lease_from, '%Y-%m-%d').date()
            if lease_from > self.report_date:
                self.flags.append(ValidationFlag(
                    severity='INFO',
                    record_id=record_id,
                    unit_number=unit_number,
                    field='lease_start_date',
                    message=f'Future lease: starts {lease_from}'
                ))
        
        # Month-to-month lease
        if lease_from and not lease_to:
            self.flags.append(ValidationFlag(
                severity='INFO',
                record_id=record_id,
                unit_number=unit_number,
                field='lease_end_date',
                message='Month-to-month lease (no end date)'
            ))
        
        # Zero rent (expense-only lease)
        if monthly is not None and float(monthly) == 0:
            self.flags.append(ValidationFlag(
                severity='INFO',
                record_id=record_id,
                unit_number=unit_number,
                field='monthly_rent',
                message='Zero rent (expense-only lease or rent abatement)'
            ))
        
        # Zero area (ATM, signage, parking)
        if area is not None and float(area) == 0:
            self.flags.append(ValidationFlag(
                severity='INFO',
                record_id=record_id,
                unit_number=unit_number,
                field='unit_area_sqft',
                message='Zero area (ATM, signage, or parking lease)'
            ))
        
        # Short term lease (<12 months)
        if term_months and term_months < 12:
            self.flags.append(ValidationFlag(
                severity='WARNING',
                record_id=record_id,
                unit_number=unit_number,
                field='lease_term_months',
                message=f'Short term lease: {term_months} months'
            ))
        
        # Very long term (>20 years, except ground leases)
        if term_months and term_months > 240:
            self.flags.append(ValidationFlag(
                severity='INFO',
                record_id=record_id,
                unit_number=unit_number,
                field='lease_term_months',
                message=f'Very long term: {term_months} months ({term_months//12} years)'
            ))
        
        # Unusual rent per SF
        if monthly_per_sf:
            monthly_per_sf_float = float(monthly_per_sf)
            if monthly_per_sf_float < 0.50:
                self.flags.append(ValidationFlag(
                    severity='WARNING',
                    record_id=record_id,
                    unit_number=unit_number,
                    field='monthly_rent_per_sqft',
                    message=f'Unusually low rent: ${monthly_per_sf_float:.2f}/SF'
                ))
            elif monthly_per_sf_float > 15.00:
                self.flags.append(ValidationFlag(
                    severity='WARNING',
                    record_id=record_id,
                    unit_number=unit_number,
                    field='monthly_rent_per_sqft',
                    message=f'Unusually high rent: ${monthly_per_sf_float:.2f}/SF'
                ))
        
        # Multi-unit lease
        if ',' in unit_number or '-' in unit_number:
            # Check if it looks like a range or list
            if ',' in unit_number or (unit_number.count('-') > 1):
                self.flags.append(ValidationFlag(
                    severity='INFO',
                    record_id=record_id,
                    unit_number=unit_number,
                    field='unit_number',
                    message='Multi-unit lease'
                ))
        
        # Special unit codes
        special_codes = ['ATM', 'LAND', 'COMMON', 'SIGN']
        unit_upper = unit_number.upper()
        for code in special_codes:
            if code in unit_upper:
                self.flags.append(ValidationFlag(
                    severity='INFO',
                    record_id=record_id,
                    unit_number=unit_number,
                    field='unit_number',
                    message=f'Special unit type: {code}'
                ))
                break
    
    def _validate_gross_rent_row(self, record: Dict, record_id: int, unit_number: str):
        """Validate gross rent calculation row"""
        parent_id = record.get('parent_row_id')
        
        if not parent_id:
            self.flags.append(ValidationFlag(
                severity='WARNING',
                record_id=record_id,
                unit_number=unit_number,
                field='parent_row_id',
                message='Gross rent row missing parent link'
            ))
    
    def _validate_vacant_unit(self, record: Dict, record_id: int, unit_number: str):
        """Validate vacant unit (simpler rules)"""
        # Vacant units should have area but no financial data
        area = record.get('unit_area_sqft')
        monthly = record.get('monthly_rent')
        
        if area is None or area == 0:
            self.flags.append(ValidationFlag(
                severity='WARNING',
                record_id=record_id,
                unit_number=unit_number,
                field='unit_area_sqft',
                message='Vacant unit should have area specified'
            ))
        
        if monthly and float(monthly) > 0:
            self.flags.append(ValidationFlag(
                severity='WARNING',
                record_id=record_id,
                unit_number=unit_number,
                field='monthly_rent',
                message='Vacant unit should not have rent'
            ))
    
    def calculate_quality_score(self) -> Dict:
        """
        Calculate quality score based on validation flags
        
        Scoring:
        - 100% base score
        - -5% per CRITICAL issue
        - -1% per WARNING
        - No deduction for INFO
        
        Auto-approve criteria:
        - Score >= 99%
        - Zero CRITICAL issues
        
        Returns:
            dict with score, recommendation, and flag counts
        """
        critical_count = sum(1 for f in self.flags if f.severity == 'CRITICAL')
        warning_count = sum(1 for f in self.flags if f.severity == 'WARNING')
        info_count = sum(1 for f in self.flags if f.severity == 'INFO')
        
        # Calculate score
        score = 100.0
        score -= critical_count * 5.0  # -5% per critical
        score -= warning_count * 1.0   # -1% per warning
        score = max(0.0, min(100.0, score))
        
        # Determine recommendation
        if score >= 99.0 and critical_count == 0:
            recommendation = 'AUTO_APPROVE'
        elif score >= 98.0 and critical_count == 0:
            recommendation = 'REVIEW_WARNINGS'
        elif critical_count > 0:
            recommendation = 'REVIEW_CRITICAL'
        else:
            recommendation = 'REVIEW_REQUIRED'
        
        return {
            'quality_score': score,
            'recommendation': recommendation,
            'critical_count': critical_count,
            'warning_count': warning_count,
            'info_count': info_count,
            'total_flags': len(self.flags),
            'auto_approve': (score >= 99.0 and critical_count == 0)
        }
    
    def get_flags_by_severity(self, severity: str) -> List[ValidationFlag]:
        """Get all flags of a specific severity level"""
        return [f for f in self.flags if f.severity == severity]
    
    def get_flags_for_record(self, record_id: int) -> List[ValidationFlag]:
        """Get all flags for a specific record"""
        return [f for f in self.flags if f.record_id == record_id]

