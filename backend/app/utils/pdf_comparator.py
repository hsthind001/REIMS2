"""
PDF to Database Comparison Utilities

Provides utilities for comparing extracted PDF data with database records
to identify differences, validate totals, and ensure data quality.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher


def compare_amounts(
    pdf_value: Optional[Decimal],
    db_value: Optional[Decimal],
    tolerance: Decimal = Decimal('0.01')
) -> Tuple[str, Optional[Decimal], Optional[Decimal]]:
    """
    Compare two amounts with tolerance
    
    Args:
        pdf_value: Amount from PDF extraction
        db_value: Amount from database
        tolerance: Absolute tolerance for exact match (default $0.01)
        
    Returns:
        Tuple of (match_status, difference, difference_percent)
        match_status: 'exact', 'tolerance', 'mismatch', 'missing_pdf', 'missing_db'
    """
    # Handle missing values
    if pdf_value is None and db_value is None:
        return ('exact', Decimal('0'), Decimal('0'))
    
    if pdf_value is None:
        return ('missing_pdf', None, None)
    
    if db_value is None:
        return ('missing_db', None, None)
    
    # Calculate absolute difference
    difference = abs(pdf_value - db_value)
    
    # Check exact match within tolerance
    if difference <= tolerance:
        return ('exact', difference, Decimal('0'))
    
    # Calculate percentage difference
    base_value = max(abs(pdf_value), abs(db_value))
    if base_value == 0:
        # Both are zero (within tolerance), already handled above
        return ('exact', difference, Decimal('0'))
    
    difference_percent = (difference / base_value) * Decimal('100')
    
    # Check if within 1% tolerance
    if difference_percent <= Decimal('1.0'):
        return ('tolerance', difference, difference_percent)
    
    # Significant mismatch
    return ('mismatch', difference, difference_percent)


def compare_account_names(
    pdf_name: str,
    db_name: str,
    threshold: float = 0.85
) -> Tuple[bool, float]:
    """
    Fuzzy string matching for account names
    
    Args:
        pdf_name: Account name from PDF
        db_name: Account name from database
        threshold: Minimum similarity ratio (0.0-1.0)
        
    Returns:
        Tuple of (is_match, similarity_score)
    """
    if not pdf_name or not db_name:
        return (False, 0.0)
    
    # Normalize strings
    pdf_normalized = pdf_name.lower().strip()
    db_normalized = db_name.lower().strip()
    
    # Exact match
    if pdf_normalized == db_normalized:
        return (True, 1.0)
    
    # Calculate similarity using SequenceMatcher
    similarity = SequenceMatcher(None, pdf_normalized, db_normalized).ratio()
    
    is_match = similarity >= threshold
    return (is_match, similarity)


def detect_missing_accounts(
    pdf_records: Dict[str, Dict],
    db_records: Dict[str, Dict]
) -> List[Dict]:
    """
    Find accounts in PDF that are not in database
    
    Args:
        pdf_records: Dict of {account_code: record_data} from PDF
        db_records: Dict of {account_code: record_data} from DB
        
    Returns:
        List of missing account records
    """
    missing = []
    
    for account_code, pdf_record in pdf_records.items():
        if account_code not in db_records:
            missing.append({
                'account_code': account_code,
                'account_name': pdf_record.get('account_name'),
                'amount': pdf_record.get('amount'),
                'difference_type': 'missing_in_db'
            })
    
    return missing


def detect_extra_accounts(
    pdf_records: Dict[str, Dict],
    db_records: Dict[str, Dict]
) -> List[Dict]:
    """
    Find accounts in database that are not in PDF
    
    Args:
        pdf_records: Dict of {account_code: record_data} from PDF
        db_records: Dict of {account_code: record_data} from DB
        
    Returns:
        List of extra account records
    """
    extra = []
    
    for account_code, db_record in db_records.items():
        if account_code not in pdf_records:
            extra.append({
                'account_code': account_code,
                'account_name': db_record.get('account_name'),
                'amount': db_record.get('amount'),
                'difference_type': 'missing_in_pdf'
            })
    
    return extra


def validate_totals(
    records: List[Dict],
    total_account_codes: List[str],
    tolerance: Decimal = Decimal('0.01')
) -> Dict[str, Dict]:
    """
    Ensure section totals match sum of detail items
    
    Args:
        records: List of account records with amounts
        total_account_codes: List of account codes that are totals
        tolerance: Tolerance for matching
        
    Returns:
        Dict of {account_code: {extracted_total, calculated_total, difference, valid}}
    """
    validation_results = {}
    
    # Build lookup dict
    records_dict = {r['account_code']: r for r in records}
    
    for total_code in total_account_codes:
        if total_code not in records_dict:
            continue
        
        total_record = records_dict[total_code]
        extracted_total = total_record.get('amount', Decimal('0'))
        
        # Find detail accounts that roll up to this total
        # This is a simplified version - in reality, you'd need parent_account_code
        detail_accounts = [
            r for r in records
            if r.get('parent_account_code') == total_code and not r.get('is_calculated')
        ]
        
        calculated_total = sum(
            (r.get('amount', Decimal('0')) for r in detail_accounts),
            Decimal('0')
        )
        
        difference = abs(extracted_total - calculated_total)
        is_valid = difference <= tolerance
        
        validation_results[total_code] = {
            'account_name': total_record.get('account_name'),
            'extracted_total': extracted_total,
            'calculated_total': calculated_total,
            'difference': difference,
            'valid': is_valid,
            'detail_count': len(detail_accounts)
        }
    
    return validation_results


def validate_balance_sheet_equation(
    total_assets: Decimal,
    total_liabilities: Decimal,
    total_equity: Decimal,
    tolerance: Decimal = Decimal('0.01')
) -> Dict:
    """
    Validate: Assets = Liabilities + Equity
    
    Args:
        total_assets: Total assets amount
        total_liabilities: Total liabilities amount
        total_equity: Total equity amount
        tolerance: Tolerance for equation balance
        
    Returns:
        Dict with validation result
    """
    liabilities_plus_equity = total_liabilities + total_equity
    difference = abs(total_assets - liabilities_plus_equity)
    is_balanced = difference <= tolerance
    
    return {
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'liabilities_plus_equity': liabilities_plus_equity,
        'difference': difference,
        'balanced': is_balanced,
        'equation': f"{total_assets} = {total_liabilities} + {total_equity}"
    }


def calculate_reconciliation_summary(
    pdf_records: Dict[str, Dict],
    db_records: Dict[str, Dict],
    differences: List[Dict]
) -> Dict:
    """
    Calculate summary statistics for reconciliation
    
    Args:
        pdf_records: Records from PDF
        db_records: Records from database
        differences: List of detected differences
        
    Returns:
        Summary statistics dict
    """
    # Count by match status (reconciliation uses match_status, not difference_type)
    difference_counts = {
        'exact': 0,
        'tolerance': 0,
        'mismatch': 0,
        'missing_pdf': 0,
        'missing_db': 0
    }
    
    for diff in differences:
        # Check both match_status (used by reconciliation) and difference_type (legacy)
        diff_type = diff.get('match_status') or diff.get('difference_type', 'unknown')
        if diff_type in difference_counts:
            difference_counts[diff_type] += 1
    
    total_records = len(differences) if differences else len(set(list(pdf_records.keys()) + list(db_records.keys())))
    matches = difference_counts['exact'] + difference_counts['tolerance']
    total_differences = difference_counts['mismatch'] + difference_counts['missing_pdf'] + difference_counts['missing_db']
    
    return {
        'total_records': total_records,
        'matches': matches,
        'differences': total_differences,
        'missing_in_db': difference_counts['missing_db'],
        'missing_in_pdf': difference_counts['missing_pdf'],
        'mismatches': difference_counts['mismatch'],
        'within_tolerance': difference_counts['tolerance'],
        'match_rate': (matches / total_records * 100) if total_records > 0 else 0
    }


def prioritize_differences(differences: List[Dict]) -> List[Dict]:
    """
    Prioritize differences by severity and impact
    
    Priority levels:
    1. Missing accounts (critical)
    2. Large mismatches (>10% or >$10,000)
    3. Medium mismatches (1-10% or $100-$10,000)
    4. Small mismatches (<1% or <$100)
    5. Within tolerance
    
    Args:
        differences: List of difference records
        
    Returns:
        Sorted list with priority field added
    """
    for diff in differences:
        diff_type = diff.get('difference_type')
        difference = diff.get('difference', Decimal('0')) or Decimal('0')
        difference_percent = diff.get('difference_percent', Decimal('0')) or Decimal('0')
        
        # Assign priority
        if diff_type in ['missing_db', 'missing_pdf']:
            priority = 1
            severity = 'critical'
        elif difference_percent > 10 or difference > Decimal('10000'):
            priority = 2
            severity = 'high'
        elif difference_percent > 1 or difference > Decimal('100'):
            priority = 3
            severity = 'medium'
        elif diff_type == 'mismatch':
            priority = 4
            severity = 'low'
        else:  # tolerance or exact
            priority = 5
            severity = 'info'
        
        diff['priority'] = priority
        diff['severity'] = severity
    
    # Sort by priority (ascending) and difference (descending)
    return sorted(
        differences,
        key=lambda x: (x['priority'], -(x.get('difference', Decimal('0')) or Decimal('0')))
    )

