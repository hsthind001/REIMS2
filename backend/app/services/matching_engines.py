"""
Matching Engines for Forensic Reconciliation

Implements four matching engines for cross-document financial data reconciliation:
1. ExactMatchEngine - Exact account code and amount matching
2. FuzzyMatchEngine - String similarity matching using rapidfuzz
3. CalculatedMatchEngine - Relationship-based matching (e.g., Net Income = Current Period Earnings)
4. InferredMatchEngine - ML-based suggestions and historical pattern matching

Uses open source tools:
- rapidfuzz: Fast fuzzy string matching
- networkx: Graph-based relationship mapping (optional)
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logging.warning("rapidfuzz not available. Fuzzy matching will be limited.")

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logging.warning("networkx not available. Graph-based matching will be disabled.")

logger = logging.getLogger(__name__)


class MatchResult:
    """Result object for a match"""
    
    def __init__(
        self,
        source_record_id: int,
        target_record_id: int,
        match_type: str,
        confidence_score: float,
        amount_difference: Optional[Decimal] = None,
        amount_difference_percent: Optional[float] = None,
        match_algorithm: Optional[str] = None,
        relationship_type: Optional[str] = None,
        relationship_formula: Optional[str] = None
    ):
        self.source_record_id = source_record_id
        self.target_record_id = target_record_id
        self.match_type = match_type
        self.confidence_score = confidence_score
        self.amount_difference = amount_difference
        self.amount_difference_percent = amount_difference_percent
        self.match_algorithm = match_algorithm
        self.relationship_type = relationship_type
        self.relationship_formula = relationship_formula
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'source_record_id': self.source_record_id,
            'target_record_id': self.target_record_id,
            'match_type': self.match_type,
            'confidence_score': Decimal(str(self.confidence_score)),
            'amount_difference': self.amount_difference,
            'amount_difference_percent': self.amount_difference_percent,
            'match_algorithm': self.match_algorithm,
            'relationship_type': self.relationship_type,
            'relationship_formula': self.relationship_formula
        }


class ExactMatchEngine:
    """Exact matching engine - matches on exact account code and amount within tolerance"""
    
    def __init__(self, amount_tolerance: Decimal = Decimal('0.01')):
        """
        Initialize exact match engine
        
        Args:
            amount_tolerance: Tolerance for amount matching (default $0.01)
        """
        self.amount_tolerance = amount_tolerance
    
    def find_matches(
        self,
        source_records: List[Dict[str, Any]],
        target_records: List[Dict[str, Any]],
        source_table: str,
        target_table: str
    ) -> List[MatchResult]:
        """
        Find exact matches between source and target records
        
        Args:
            source_records: List of source records with account_code, amount, etc.
            target_records: List of target records with account_code, amount, etc.
            source_table: Source table name
            target_table: Target table name
            
        Returns:
            List of MatchResult objects
        """
        matches = []
        
        # Build index of target records by account code for fast lookup
        target_index = {}
        for record in target_records:
            account_code = record.get('account_code')
            if account_code:
                if account_code not in target_index:
                    target_index[account_code] = []
                target_index[account_code].append(record)
        
        # Match source records to target records
        for source_record in source_records:
            source_account_code = source_record.get('account_code')
            source_amount = self._get_amount(source_record)
            
            if not source_account_code or source_amount is None:
                continue
            
            # Find matching target records by account code
            if source_account_code in target_index:
                for target_record in target_index[source_account_code]:
                    target_amount = self._get_amount(target_record)
                    
                    if target_amount is None:
                        continue
                    
                    # Check if amounts match within tolerance
                    amount_diff = abs(source_amount - target_amount)
                    
                    if amount_diff <= self.amount_tolerance:
                        # Exact match found
                        matches.append(MatchResult(
                            source_record_id=source_record.get('id') or source_record.get('record_id'),
                            target_record_id=target_record.get('id') or target_record.get('record_id'),
                            match_type='exact',
                            confidence_score=100.0,
                            amount_difference=amount_diff,
                            amount_difference_percent=float((amount_diff / max(abs(source_amount), abs(target_amount))) * 100) if max(abs(source_amount), abs(target_amount)) > 0 else 0.0,
                            match_algorithm='exact_match',
                            relationship_type='equality'
                        ))
        
        logger.info(f"ExactMatchEngine found {len(matches)} exact matches")
        return matches
    
    def _get_amount(self, record: Dict[str, Any]) -> Optional[Decimal]:
        """Extract amount from record (handles different field names)"""
        for field in ['amount', 'period_amount', 'ytd_amount', 'total_amount', 'value']:
            if field in record and record[field] is not None:
                try:
                    return Decimal(str(record[field]))
                except (ValueError, TypeError):
                    continue
        return None


class FuzzyMatchEngine:
    """Fuzzy matching engine using rapidfuzz for string similarity"""
    
    def __init__(
        self,
        min_confidence: float = 70.0,
        account_name_weight: float = 0.6,
        account_code_weight: float = 0.4
    ):
        """
        Initialize fuzzy match engine
        
        Args:
            min_confidence: Minimum confidence score (0-100) to consider a match
            account_name_weight: Weight for account name matching (0-1)
            account_code_weight: Weight for account code matching (0-1)
        """
        if not RAPIDFUZZ_AVAILABLE:
            raise ImportError("rapidfuzz is required for FuzzyMatchEngine")
        
        self.min_confidence = min_confidence
        self.account_name_weight = account_name_weight
        self.account_code_weight = account_code_weight
    
    def find_matches(
        self,
        source_records: List[Dict[str, Any]],
        target_records: List[Dict[str, Any]],
        source_table: str,
        target_table: str
    ) -> List[MatchResult]:
        """
        Find fuzzy matches between source and target records
        
        Args:
            source_records: List of source records
            target_records: List of target records
            source_table: Source table name
            target_table: Target table name
            
        Returns:
            List of MatchResult objects with confidence scores
        """
        matches = []
        
        # Build target index for efficient matching
        target_account_names = {}
        target_account_codes = {}
        
        for record in target_records:
            record_id = record.get('id') or record.get('record_id')
            account_name = record.get('account_name', '')
            account_code = record.get('account_code', '')
            
            if account_name:
                if account_name not in target_account_names:
                    target_account_names[account_name] = []
                target_account_names[account_name].append(record)
            
            if account_code:
                if account_code not in target_account_codes:
                    target_account_codes[account_code] = []
                target_account_codes[account_code].append(record)
        
        # Match source records
        for source_record in source_records:
            source_id = source_record.get('id') or source_record.get('record_id')
            source_account_name = source_record.get('account_name', '')
            source_account_code = source_record.get('account_code', '')
            source_amount = self._get_amount(source_record)
            
            if not source_account_name and not source_account_code:
                continue
            
            best_match = None
            best_confidence = 0.0
            
            # Try account name matching
            if source_account_name:
                # Use rapidfuzz process.extractOne for best match
                target_names_list = list(target_account_names.keys())
                if target_names_list:
                    result = process.extractOne(
                        source_account_name,
                        target_names_list,
                        scorer=fuzz.WRatio,  # Weighted ratio for better accuracy
                        score_cutoff=self.min_confidence
                    )
                    
                    if result:
                        matched_name, name_score, _ = result
                        # Check amount similarity if available
                        amount_score = 100.0
                        if source_amount is not None:
                            for target_record in target_account_names[matched_name]:
                                target_amount = self._get_amount(target_record)
                                if target_amount is not None:
                                    # Calculate amount similarity (within 1% = 100, decreases linearly)
                                    amount_diff = abs(source_amount - target_amount)
                                    max_amount = max(abs(source_amount), abs(target_amount))
                                    if max_amount > 0:
                                        amount_diff_percent = float((amount_diff / max_amount) * 100)
                                        if amount_diff_percent <= 1.0:
                                            amount_score = 100.0 - (amount_diff_percent * 50)  # Penalize up to 50 points
                                        else:
                                            amount_score = max(0, 100.0 - (amount_diff_percent * 10))
                                    
                                    # Calculate combined confidence
                                    combined_confidence = (
                                        name_score * self.account_name_weight +
                                        amount_score * (1 - self.account_name_weight)
                                    )
                                    
                                    if combined_confidence > best_confidence and combined_confidence >= self.min_confidence:
                                        best_confidence = combined_confidence
                                        best_match = target_record
                                        best_match['match_algorithm'] = 'fuzzy_string'
                                        best_match['name_score'] = name_score
                                        best_match['amount_score'] = amount_score
            
            # Try account code range matching (e.g., 2610-xxxx matches 2610-0000)
            if source_account_code and not best_match:
                code_prefix = source_account_code.split('-')[0] if '-' in source_account_code else source_account_code[:4]
                
                for code, records in target_account_codes.items():
                    target_prefix = code.split('-')[0] if '-' in code else code[:4]
                    
                    if code_prefix == target_prefix:
                        # Same account code range - check amounts
                        for target_record in records:
                            target_amount = self._get_amount(target_record)
                            if source_amount is not None and target_amount is not None:
                                amount_diff = abs(source_amount - target_amount)
                                max_amount = max(abs(source_amount), abs(target_amount))
                                
                                if max_amount > 0:
                                    amount_diff_percent = float((amount_diff / max_amount) * 100)
                                    if amount_diff_percent <= 1.0:
                                        # High confidence for same code range with similar amounts
                                        confidence = 85.0 - (amount_diff_percent * 5)
                                        
                                        if confidence > best_confidence and confidence >= self.min_confidence:
                                            best_confidence = confidence
                                            best_match = target_record
                                            best_match['match_algorithm'] = 'account_code_range'
            
            # Create match result if found
            if best_match and best_confidence >= self.min_confidence:
                target_id = best_match.get('id') or best_match.get('record_id')
                source_amount = self._get_amount(source_record)
                target_amount = self._get_amount(best_match)
                
                amount_diff = None
                amount_diff_percent = None
                
                if source_amount is not None and target_amount is not None:
                    amount_diff = abs(source_amount - target_amount)
                    max_amount = max(abs(source_amount), abs(target_amount))
                    if max_amount > 0:
                        amount_diff_percent = float((amount_diff / max_amount) * 100)
                
                matches.append(MatchResult(
                    source_record_id=source_id,
                    target_record_id=target_id,
                    match_type='fuzzy',
                    confidence_score=best_confidence,
                    amount_difference=Decimal(str(amount_diff)) if amount_diff is not None else None,
                    amount_difference_percent=amount_diff_percent,
                    match_algorithm=best_match.get('match_algorithm', 'fuzzy_string'),
                    relationship_type='equality'
                ))
        
        logger.info(f"FuzzyMatchEngine found {len(matches)} fuzzy matches")
        return matches
    
    def _get_amount(self, record: Dict[str, Any]) -> Optional[Decimal]:
        """Extract amount from record"""
        for field in ['amount', 'period_amount', 'ytd_amount', 'total_amount', 'value']:
            if field in record and record[field] is not None:
                try:
                    return Decimal(str(record[field]))
                except (ValueError, TypeError):
                    continue
        return None


class CalculatedMatchEngine:
    """Calculated matching engine for relationship-based matches"""
    
    def __init__(self):
        """Initialize calculated match engine"""
        pass
    
    def find_matches(
        self,
        source_records: List[Dict[str, Any]],
        target_records: List[Dict[str, Any]],
        source_table: str,
        target_table: str,
        relationship_formula: str
    ) -> List[MatchResult]:
        """
        Find matches based on calculated relationships
        
        Args:
            source_records: List of source records
            target_records: List of target records
            source_table: Source table name
            target_table: Target table name
            relationship_formula: Formula describing the relationship (e.g., "BS.current_period_earnings = IS.net_income")
            
        Returns:
            List of MatchResult objects
        """
        matches = []
        
        # Parse relationship formula
        # Simple parser for common patterns like "BS.account = IS.account" or "BS.account = SUM(IS.accounts)"
        if '=' in relationship_formula:
            left, right = relationship_formula.split('=', 1)
            left = left.strip()
            right = right.strip()
            
            # Extract account codes or patterns
            source_pattern = self._extract_account_pattern(left, source_table)
            target_pattern = self._extract_account_pattern(right, target_table)
            
            if source_pattern and target_pattern:
                # Find matching records
                source_matches = self._find_by_pattern(source_records, source_pattern)
                target_matches = self._find_by_pattern(target_records, target_pattern)
                
                # Calculate relationship
                if 'SUM' in right.upper():
                    # Sum relationship
                    target_value = sum([self._get_amount(r) or Decimal('0') for r in target_matches])
                    
                    for source_record in source_matches:
                        source_amount = self._get_amount(source_record)
                        if source_amount is not None:
                            amount_diff = abs(source_amount - target_value)
                            max_amount = max(abs(source_amount), abs(target_value))
                            
                            if max_amount > 0:
                                amount_diff_percent = float((amount_diff / max_amount) * 100)
                                
                                # High confidence if within 1%, medium if within 5%
                                if amount_diff_percent <= 1.0:
                                    confidence = 95.0
                                elif amount_diff_percent <= 5.0:
                                    confidence = 85.0
                                else:
                                    confidence = max(70.0, 100.0 - amount_diff_percent)
                                
                                matches.append(MatchResult(
                                    source_record_id=source_record.get('id') or source_record.get('record_id'),
                                    target_record_id=0,  # Multiple targets for sum
                                    match_type='calculated',
                                    confidence_score=confidence,
                                    amount_difference=amount_diff,
                                    amount_difference_percent=amount_diff_percent,
                                    match_algorithm='calculated_relationship',
                                    relationship_type='sum',
                                    relationship_formula=relationship_formula
                                ))
                else:
                    # Direct equality relationship
                    for source_record in source_matches:
                        source_amount = self._get_amount(source_record)
                        
                        for target_record in target_matches:
                            target_amount = self._get_amount(target_record)
                            
                            if source_amount is not None and target_amount is not None:
                                amount_diff = abs(source_amount - target_amount)
                                max_amount = max(abs(source_amount), abs(target_amount))
                                
                                if max_amount > 0:
                                    amount_diff_percent = float((amount_diff / max_amount) * 100)
                                    
                                    # High confidence for calculated relationships
                                    if amount_diff_percent <= 0.01:  # $0.01 or 0.01%
                                        confidence = 95.0
                                    elif amount_diff_percent <= 1.0:
                                        confidence = 90.0
                                    else:
                                        confidence = max(70.0, 100.0 - amount_diff_percent)
                                    
                                    matches.append(MatchResult(
                                        source_record_id=source_record.get('id') or source_record.get('record_id'),
                                        target_record_id=target_record.get('id') or target_record.get('record_id'),
                                        match_type='calculated',
                                        confidence_score=confidence,
                                        amount_difference=amount_diff,
                                        amount_diff_percent=amount_diff_percent,
                                        match_algorithm='calculated_relationship',
                                        relationship_type='equality',
                                        relationship_formula=relationship_formula
                                    ))
        
        logger.info(f"CalculatedMatchEngine found {len(matches)} calculated matches")
        return matches
    
    def _extract_account_pattern(self, expression: str, table_prefix: str) -> Optional[str]:
        """Extract account code pattern from expression"""
        # Simple pattern extraction
        # Handles patterns like "BS.3995-0000" or "IS.9090-0000"
        if '.' in expression:
            parts = expression.split('.')
            if len(parts) > 1:
                account_part = parts[-1].strip()
                return account_part
        return None
    
    def _find_by_pattern(self, records: List[Dict[str, Any]], pattern: str) -> List[Dict[str, Any]]:
        """Find records matching a pattern"""
        matches = []
        
        for record in records:
            account_code = record.get('account_code', '')
            
            # Exact match
            if account_code == pattern:
                matches.append(record)
            # Prefix match (e.g., "3995" matches "3995-0000")
            elif pattern and account_code.startswith(pattern.split('-')[0]):
                matches.append(record)
        
        return matches
    
    def _get_amount(self, record: Dict[str, Any]) -> Optional[Decimal]:
        """Extract amount from record"""
        for field in ['amount', 'period_amount', 'ytd_amount', 'total_amount', 'value']:
            if field in record and record[field] is not None:
                try:
                    return Decimal(str(record[field]))
                except (ValueError, TypeError):
                    continue
        return None


class InferredMatchEngine:
    """Inferred matching engine using ML and historical patterns"""
    
    def __init__(self, min_confidence: float = 50.0):
        """
        Initialize inferred match engine
        
        Args:
            min_confidence: Minimum confidence score for inferred matches
        """
        self.min_confidence = min_confidence
        self.historical_patterns = {}  # Cache for historical matching patterns
    
    def find_matches(
        self,
        source_records: List[Dict[str, Any]],
        target_records: List[Dict[str, Any]],
        source_table: str,
        target_table: str,
        historical_matches: Optional[List[Dict[str, Any]]] = None
    ) -> List[MatchResult]:
        """
        Find inferred matches using historical patterns and context
        
        Args:
            source_records: List of source records
            target_records: List of target records
            source_table: Source table name
            target_table: Target table name
            historical_matches: Optional list of historical matches for pattern learning
            
        Returns:
            List of MatchResult objects
        """
        matches = []
        
        # Use historical patterns if available
        if historical_matches:
            # Learn patterns from historical data
            patterns = self._learn_patterns(historical_matches)
            
            # Apply patterns to current records
            for source_record in source_records:
                source_account_code = source_record.get('account_code')
                source_account_name = source_record.get('account_name', '')
                
                if source_account_code in patterns:
                    # Found historical pattern
                    pattern = patterns[source_account_code]
                    target_account_code = pattern.get('target_account_code')
                    
                    # Find matching target record
                    for target_record in target_records:
                        if target_record.get('account_code') == target_account_code:
                            source_amount = self._get_amount(source_record)
                            target_amount = self._get_amount(target_record)
                            
                            if source_amount is not None and target_amount is not None:
                                # Calculate confidence based on historical accuracy
                                historical_accuracy = pattern.get('accuracy', 0.7)
                                amount_similarity = self._calculate_amount_similarity(source_amount, target_amount)
                                
                                confidence = float(historical_accuracy * 100 * amount_similarity)
                                
                                if confidence >= self.min_confidence:
                                    amount_diff = abs(source_amount - target_amount)
                                    max_amount = max(abs(source_amount), abs(target_amount))
                                    amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
                                    
                                    matches.append(MatchResult(
                                        source_record_id=source_record.get('id') or source_record.get('record_id'),
                                        target_record_id=target_record.get('id') or target_record.get('record_id'),
                                        match_type='inferred',
                                        confidence_score=confidence,
                                        amount_difference=amount_diff,
                                        amount_difference_percent=amount_diff_percent,
                                        match_algorithm='historical_pattern',
                                        relationship_type='inferred'
                                    ))
        
        # Fallback: Use context-aware matching
        if not matches:
            matches = self._context_aware_matching(source_records, target_records)
        
        logger.info(f"InferredMatchEngine found {len(matches)} inferred matches")
        return matches
    
    def _learn_patterns(self, historical_matches: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Learn matching patterns from historical data"""
        patterns = {}
        
        for match in historical_matches:
            source_code = match.get('source_account_code')
            target_code = match.get('target_account_code')
            confidence = match.get('confidence_score', 0) / 100.0  # Normalize to 0-1
            
            if source_code and target_code:
                if source_code not in patterns:
                    patterns[source_code] = {
                        'target_account_code': target_code,
                        'count': 0,
                        'total_confidence': 0.0
                    }
                
                patterns[source_code]['count'] += 1
                patterns[source_code]['total_confidence'] += confidence
        
        # Calculate average accuracy
        for source_code, pattern in patterns.items():
            pattern['accuracy'] = pattern['total_confidence'] / pattern['count'] if pattern['count'] > 0 else 0.0
        
        return patterns
    
    def _context_aware_matching(
        self,
        source_records: List[Dict[str, Any]],
        target_records: List[Dict[str, Any]]
    ) -> List[MatchResult]:
        """Context-aware matching when no historical patterns available"""
        matches = []
        
        # Simple context matching: match by similar amounts and account categories
        for source_record in source_records:
            source_amount = self._get_amount(source_record)
            source_category = self._extract_category(source_record.get('account_code', ''))
            
            if source_amount is None:
                continue
            
            best_match = None
            best_confidence = 0.0
            
            for target_record in target_records:
                target_amount = self._get_amount(target_record)
                target_category = self._extract_category(target_record.get('account_code', ''))
                
                if target_amount is None:
                    continue
                
                # Check category match
                category_match = (source_category == target_category) if source_category and target_category else False
                
                # Calculate amount similarity
                amount_similarity = self._calculate_amount_similarity(source_amount, target_amount)
                
                # Combined confidence
                if category_match:
                    confidence = amount_similarity * 70.0  # Base confidence for category match
                else:
                    confidence = amount_similarity * 50.0  # Lower confidence without category match
                
                if confidence > best_confidence and confidence >= self.min_confidence:
                    best_confidence = confidence
                    best_match = target_record
            
            if best_match:
                source_amount = self._get_amount(source_record)
                target_amount = self._get_amount(best_match)
                amount_diff = abs(source_amount - target_amount)
                max_amount = max(abs(source_amount), abs(target_amount))
                amount_diff_percent = float((amount_diff / max_amount) * 100) if max_amount > 0 else 0.0
                
                matches.append(MatchResult(
                    source_record_id=source_record.get('id') or source_record.get('record_id'),
                    target_record_id=best_match.get('id') or best_match.get('record_id'),
                    match_type='inferred',
                    confidence_score=best_confidence,
                    amount_difference=amount_diff,
                    amount_difference_percent=amount_diff_percent,
                    match_algorithm='context_aware',
                    relationship_type='inferred'
                ))
        
        return matches
    
    def _extract_category(self, account_code: str) -> Optional[str]:
        """Extract account category from account code"""
        if not account_code:
            return None
        
        # Extract first 4 digits (e.g., "2610" from "2610-0000")
        if '-' in account_code:
            prefix = account_code.split('-')[0]
        else:
            prefix = account_code[:4]
        
        # Map to category
        category_map = {
            '0000': 'assets',
            '0100': 'current_assets',
            '1000': 'property_equipment',
            '2000': 'liabilities',
            '2600': 'long_term_debt',
            '3000': 'equity',
            '4000': 'income',
            '5000': 'expenses',
            '6000': 'operating_expenses',
            '6500': 'interest_expense',
            '9000': 'net_income'
        }
        
        return category_map.get(prefix[:4], None)
    
    def _calculate_amount_similarity(self, amount1: Decimal, amount2: Decimal) -> float:
        """Calculate similarity between two amounts (0-1)"""
        if amount1 == amount2:
            return 1.0
        
        max_amount = max(abs(amount1), abs(amount2))
        if max_amount == 0:
            return 1.0
        
        diff = abs(amount1 - amount2)
        diff_percent = float((diff / max_amount) * 100)
        
        # Similarity decreases as difference increases
        if diff_percent <= 1.0:
            return 1.0
        elif diff_percent <= 5.0:
            return 0.9 - ((diff_percent - 1.0) / 4.0 * 0.3)
        elif diff_percent <= 10.0:
            return 0.6 - ((diff_percent - 5.0) / 5.0 * 0.3)
        else:
            return max(0.0, 0.3 - ((diff_percent - 10.0) / 90.0 * 0.3))
    
    def _get_amount(self, record: Dict[str, Any]) -> Optional[Decimal]:
        """Extract amount from record"""
        for field in ['amount', 'period_amount', 'ytd_amount', 'total_amount', 'value']:
            if field in record and record[field] is not None:
                try:
                    return Decimal(str(record[field]))
                except (ValueError, TypeError):
                    continue
        return None


class ConfidenceScorer:
    """Calculate confidence scores for matches"""
    
    @staticmethod
    def calculate_confidence(
        account_match_score: float,
        amount_match_score: float,
        date_match_score: float = 100.0,
        context_match_score: float = 100.0,
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate overall confidence score
        
        Args:
            account_match_score: Account matching score (0-100)
            amount_match_score: Amount matching score (0-100)
            date_match_score: Date matching score (0-100)
            context_match_score: Context matching score (0-100)
            weights: Optional custom weights (default: account=0.4, amount=0.4, date=0.1, context=0.1)
            
        Returns:
            Overall confidence score (0-100)
        """
        if weights is None:
            weights = {
                'account': 0.4,
                'amount': 0.4,
                'date': 0.1,
                'context': 0.1
            }
        
        confidence = (
            account_match_score * weights['account'] +
            amount_match_score * weights['amount'] +
            date_match_score * weights['date'] +
            context_match_score * weights['context']
        )
        
        return round(confidence, 2)

