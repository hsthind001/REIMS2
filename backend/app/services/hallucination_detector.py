"""
Hallucination Detection Service

Detects and verifies numeric claims in LLM-generated answers against source data.
Flags unverified claims for manual review and reduces confidence scores.
"""
import logging
import re
import time
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.config.hallucination_config import hallucination_config
from app.models.financial_metrics import FinancialMetrics
from app.models.income_statement_data import IncomeStatementData
from app.models.balance_sheet_data import BalanceSheetData
from app.models.cash_flow_data import CashFlowData
from app.models.document_chunk import DocumentChunk
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)


class Claim:
    """
    Represents an extracted numeric claim from LLM-generated text.
    
    A claim is a numeric assertion (currency, percentage, date, or ratio) that
    has been extracted from an answer and needs to be verified against source data.
    
    Attributes:
        claim_type: Type of claim ('currency', 'percentage', 'date', 'ratio')
        value: Numeric value of the claim
        original_text: Original text from which claim was extracted
        context: Surrounding text context (optional)
        verified: Whether claim has been verified against source data
        verification_source: Source of verification ('database' or 'documents')
        verification_score: Confidence score of verification (0-1)
        tolerance_applied: Tolerance percentage used for verification
    """
    
    def __init__(
        self,
        claim_type: str,
        value: float,
        original_text: str,
        context: Optional[str] = None
    ):
        """
        Initialize a claim.
        
        Args:
            claim_type: Type of claim ('currency', 'percentage', 'date', 'ratio')
            value: Numeric value of the claim
            original_text: Original text from which claim was extracted
            context: Surrounding text context (optional)
        """
        self.claim_type = claim_type  # 'currency', 'percentage', 'date', 'ratio'
        self.value = value
        self.original_text = original_text
        self.context = context
        self.verified = False
        self.verification_source = None
        self.verification_score = 0.0
        self.tolerance_applied = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert claim to dictionary representation.
        
        Returns:
            Dictionary containing all claim attributes
            
        Example:
            >>> claim = Claim('currency', 1234567.89, '$1,234,567.89')
            >>> claim_dict = claim.to_dict()
            >>> print(claim_dict['claim_type'])
            'currency'
        """
        return {
            'claim_type': self.claim_type,
            'value': self.value,
            'original_text': self.original_text,
            'context': self.context,
            'verified': self.verified,
            'verification_source': self.verification_source,
            'verification_score': self.verification_score,
            'tolerance_applied': self.tolerance_applied
        }


class HallucinationDetector:
    """
    Detects hallucinations in LLM-generated answers by verifying numeric claims
    
    Extracts numeric claims (currency, percentages, dates, ratios) and verifies
    them against source data (database and documents).
    """
    
    def __init__(self, db: Session):
        """
        Initialize hallucination detector
        
        Args:
            db: Database session for verifying claims
        """
        self.db = db
        
        # Compile regex patterns for claim extraction
        self._compile_patterns()
    
    def _compile_patterns(self):
        """
        Compile regex patterns for claim extraction.
        
        Compiles patterns for currency, percentage, date, and ratio claims.
        Patterns are compiled once during initialization for performance.
        """
        # Currency patterns: $1,234,567.89, $1.2M, $1.5 million
        self.currency_patterns = [
            re.compile(r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:million|million|M|K|k)?', re.IGNORECASE),
            re.compile(r'\$(\d+\.?\d*)\s*(?:million|M|K|k)', re.IGNORECASE),
            re.compile(r'(\d+\.?\d*)\s*(?:million|M|K|k)\s*(?:dollars|USD)?', re.IGNORECASE)
        ]
        
        # Percentage patterns: 85%, 12.5 percent
        self.percentage_patterns = [
            re.compile(r'(\d+\.?\d*)\s*%'),
            re.compile(r'(\d+\.?\d*)\s+percent', re.IGNORECASE),
            re.compile(r'(\d+\.?\d*)\s+percentage', re.IGNORECASE)
        ]
        
        # Date patterns: Q3 2024, December 2024, 2024-12-01
        self.date_patterns = [
            re.compile(r'Q([1-4])\s+(\d{4})', re.IGNORECASE),
            re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', re.IGNORECASE),
            re.compile(r'(\d{4})-(\d{2})-(\d{2})'),
            re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})')
        ]
        
        # Ratio patterns: DSCR 1.25, 1.25x
        self.ratio_patterns = [
            re.compile(r'(?:DSCR|dscr|debt.*service.*coverage|coverage.*ratio)\s*[:\s]*(\d+\.?\d*)', re.IGNORECASE),
            re.compile(r'(\d+\.?\d*)\s*x\s*(?:coverage|ratio)', re.IGNORECASE),
            re.compile(r'ratio\s+of\s+(\d+\.?\d*)', re.IGNORECASE)
        ]
    
    def detect_hallucinations(
        self,
        answer: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Detect hallucinations in LLM answer by verifying numeric claims
        
        Args:
            answer: LLM-generated answer text
            sources: List of source documents/chunks used (optional)
            property_id: Property ID for context (optional)
            period_id: Period ID for context (optional)
        
        Returns:
            Dict with detection results, flagged claims, and adjusted confidence
        """
        if not answer or not answer.strip():
            return {
                'has_hallucinations': False,
                'claims': [],
                'flagged_claims': [],
                'verification_time_ms': 0.0,
                'confidence_adjustment': 0.0
            }
        
        start_time = time.time()
        
        try:
            # Extract numeric claims
            claims = self._extract_claims(answer)
            
            if not claims:
                # No numeric claims found
                return {
                    'has_hallucinations': False,
                    'claims': [],
                    'flagged_claims': [],
                    'verification_time_ms': (time.time() - start_time) * 1000,
                    'confidence_adjustment': 0.0
                }
            
            # Verify each claim
            flagged_claims = []
            for claim in claims:
                verified = self._verify_claim(
                    claim=claim,
                    sources=sources,
                    property_id=property_id,
                    period_id=period_id
                )
                
                if not verified:
                    flagged_claims.append(claim)
                    if hallucination_config.LOG_UNVERIFIED_CLAIMS:
                        logger.warning(
                            f"Unverified claim detected: {claim.original_text} "
                            f"(type: {claim.claim_type}, value: {claim.value})"
                        )
            
            verification_time_ms = (time.time() - start_time) * 1000
            
            # Calculate confidence adjustment
            confidence_adjustment = 0.0
            if flagged_claims:
                # Reduce confidence by penalty percentage
                confidence_adjustment = -hallucination_config.CONFIDENCE_PENALTY_PERCENT / 100.0
            
            has_hallucinations = len(flagged_claims) > 0
            
            result = {
                'has_hallucinations': has_hallucinations,
                'claims': [c.to_dict() for c in claims],
                'flagged_claims': [c.to_dict() for c in flagged_claims],
                'verification_time_ms': verification_time_ms,
                'confidence_adjustment': confidence_adjustment,
                'total_claims': len(claims),
                'verified_claims': len(claims) - len(flagged_claims),
                'unverified_claims': len(flagged_claims)
            }
            
            if has_hallucinations:
                logger.warning(
                    f"Hallucinations detected: {len(flagged_claims)}/{len(claims)} claims unverified "
                    f"(verification time: {verification_time_ms:.2f}ms)"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Hallucination detection failed: {e}", exc_info=True)
            return {
                'has_hallucinations': False,
                'claims': [],
                'flagged_claims': [],
                'verification_time_ms': (time.time() - start_time) * 1000,
                'confidence_adjustment': 0.0,
                'error': str(e)
            }
    
    def _extract_claims(self, text: str) -> List[Claim]:
        """
        Extract numeric claims from text.
        
        Extracts currency, percentage, date, and ratio claims using compiled
        regex patterns. Each claim includes the original text and context.
        
        Args:
            text: Answer text to extract claims from
        
        Returns:
            List of extracted Claim objects
            
        Example:
            >>> detector._extract_claims("The NOI was $1,234,567.89 and occupancy was 85.5%")
            [Claim(claim_type='currency', value=1234567.89, ...), Claim(claim_type='percentage', value=85.5, ...)]
        """
        claims = []
        
        # Extract currency claims
        if hallucination_config.VERIFY_CURRENCY:
            for pattern in self.currency_patterns:
                for match in pattern.finditer(text):
                    value_str = match.group(1)
                    suffix = match.group(0).upper()
                    value = self._parse_currency_value(value_str, suffix)
                    if value:
                        claims.append(Claim(
                            claim_type='currency',
                            value=value,
                            original_text=match.group(0),
                            context=self._get_context(text, match.start(), match.end())
                        ))
        
        # Extract percentage claims
        if hallucination_config.VERIFY_PERCENTAGES:
            for pattern in self.percentage_patterns:
                for match in pattern.finditer(text):
                    value_str = match.group(1)
                    try:
                        value = float(value_str)
                        claims.append(Claim(
                            claim_type='percentage',
                            value=value,
                            original_text=match.group(0),
                            context=self._get_context(text, match.start(), match.end())
                        ))
                    except ValueError:
                        continue
        
        # Extract date claims
        if hallucination_config.VERIFY_DATES:
            for pattern in self.date_patterns:
                for match in pattern.finditer(text):
                    # Parse date based on pattern
                    date_value = self._parse_date_value(match)
                    if date_value:
                        claims.append(Claim(
                            claim_type='date',
                            value=date_value,
                            original_text=match.group(0),
                            context=self._get_context(text, match.start(), match.end())
                        ))
        
        # Extract ratio claims
        if hallucination_config.VERIFY_RATIOS:
            for pattern in self.ratio_patterns:
                for match in pattern.finditer(text):
                    value_str = match.group(1)
                    try:
                        value = float(value_str)
                        claims.append(Claim(
                            claim_type='ratio',
                            value=value,
                            original_text=match.group(0),
                            context=self._get_context(text, match.start(), match.end())
                        ))
                    except ValueError:
                        continue
        
        return claims
    
    def _parse_currency_value(self, value_str: str, suffix: str) -> Optional[float]:
        """
        Parse currency value, handling M (million) and K (thousand) suffixes.
        
        Args:
            value_str: Numeric string (may include commas)
            suffix: Suffix string (may contain 'M', 'K', 'million', etc.)
        
        Returns:
            Parsed float value, or None if parsing fails
            
        Example:
            >>> detector._parse_currency_value("1.5", "$1.5M")
            1500000.0
            >>> detector._parse_currency_value("500", "$500K")
            500000.0
        """
        try:
            # Remove commas
            value_str = value_str.replace(',', '')
            base_value = float(value_str)
            
            # Apply multiplier based on suffix
            if 'M' in suffix.upper() or 'MILLION' in suffix.upper():
                return base_value * 1000000
            elif 'K' in suffix.upper() or 'THOUSAND' in suffix.upper():
                return base_value * 1000
            else:
                return base_value
        except (ValueError, AttributeError):
            return None
    
    def _parse_date_value(self, match: re.Match) -> Optional[float]:
        """
        Parse date value to numeric representation.
        
        Converts dates to numeric format for comparison:
        - Quarters: Q3 2024 -> 2024.3
        - Months: December 2024 -> 2024.12
        - Dates: 2024-12-01 -> 2024.1201
        
        Args:
            match: Regex match object with date groups
        
        Returns:
            Numeric representation of date, or None if parsing fails
        """
        try:
            groups = match.groups()
            
            # Q3 2024 format
            if len(groups) == 2 and groups[0].isdigit() and int(groups[0]) in [1, 2, 3, 4]:
                quarter = int(groups[0])
                year = int(groups[1])
                # Represent as year.quarter (e.g., 2024.3)
                return float(year) + (quarter / 10.0)
            
            # Month Year format
            elif len(groups) == 2:
                month_names = {
                    'january': 1, 'february': 2, 'march': 3, 'april': 4,
                    'may': 5, 'june': 6, 'july': 7, 'august': 8,
                    'september': 9, 'october': 10, 'november': 11, 'december': 12
                }
                month_name = groups[0].lower()
                if month_name in month_names:
                    month = month_names[month_name]
                    year = int(groups[1])
                    # Represent as year.month (e.g., 2024.12)
                    return float(year) + (month / 100.0)
            
            # YYYY-MM-DD format
            elif len(groups) == 3 and len(groups[0]) == 4:
                year = int(groups[0])
                month = int(groups[1])
                day = int(groups[2])
                # Represent as year.monthday (e.g., 2024.1201)
                return float(year) + (month / 100.0) + (day / 10000.0)
            
            # MM/DD/YYYY format
            elif len(groups) == 3:
                month = int(groups[0])
                day = int(groups[1])
                year = int(groups[2])
                # Represent as year.monthday
                return float(year) + (month / 100.0) + (day / 10000.0)
            
            return None
        except (ValueError, AttributeError, IndexError):
            return None
    
    def _get_context(self, text: str, start: int, end: int, context_window: int = 50) -> str:
        """
        Get context around a match position.
        
        Extracts surrounding text to provide context for extracted claims.
        
        Args:
            text: Full text string
            start: Start position of match
            end: End position of match
            context_window: Number of characters to include before/after (default: 50)
        
        Returns:
            Context string with surrounding text
        """
        context_start = max(0, start - context_window)
        context_end = min(len(text), end + context_window)
        return text[context_start:context_end]
    
    def _verify_claim(
        self,
        claim: Claim,
        sources: Optional[List[Dict[str, Any]]] = None,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> bool:
        """
        Verify a claim against source data.
        
        Attempts to verify claim against database first, then against source
        documents if database verification fails or is disabled.
        
        Args:
            claim: Claim to verify
            sources: Source documents/chunks (optional)
            property_id: Property ID for context (optional)
            period_id: Period ID for context (optional)
        
        Returns:
            True if claim is verified, False otherwise
            
        Raises:
            SQLAlchemyError: If database query fails
        """
        # Verify against database
        if hallucination_config.VERIFY_AGAINST_DATABASE:
            if self._verify_against_database(claim, property_id, period_id):
                claim.verified = True
                claim.verification_source = 'database'
                return True
        
        # Verify against source documents
        if hallucination_config.VERIFY_AGAINST_DOCUMENTS and sources:
            if self._verify_against_documents(claim, sources):
                claim.verified = True
                claim.verification_source = 'documents'
                return True
        
        return False
    
    def _verify_against_database(
        self,
        claim: Claim,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> bool:
        """Verify claim against database records"""
        try:
            if claim.claim_type == 'currency':
                return self._verify_currency_in_db(claim, property_id, period_id)
            elif claim.claim_type == 'percentage':
                return self._verify_percentage_in_db(claim, property_id, period_id)
            elif claim.claim_type == 'ratio':
                return self._verify_ratio_in_db(claim, property_id, period_id)
            elif claim.claim_type == 'date':
                return self._verify_date_in_db(claim, property_id, period_id)
        except Exception as e:
            logger.error(f"Error verifying claim against database: {e}", exc_info=True)
            return False
        
        return False
    
    def _verify_currency_in_db(
        self,
        claim: Claim,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> bool:
        """Verify currency claim against database"""
        tolerance = hallucination_config.CURRENCY_TOLERANCE_PERCENT / 100.0
        min_value = claim.value * (1 - tolerance)
        max_value = claim.value * (1 + tolerance)
        
        # Check FinancialMetrics
        query = self.db.query(FinancialMetrics)
        if property_id:
            query = query.filter(FinancialMetrics.property_id == property_id)
        if period_id:
            query = query.filter(FinancialMetrics.period_id == period_id)
        
        metrics = query.all()
        for metric in metrics:
            # Check various currency fields
            currency_fields = [
                'net_operating_income', 'total_revenue', 'total_expenses',
                'net_income', 'total_assets', 'total_liabilities',
                'operating_expenses', 'property_income'
            ]
            
            for field in currency_fields:
                value = getattr(metric, field, None)
                if value and isinstance(value, (int, float, Decimal)):
                    numeric_value = float(value)
                    if min_value <= numeric_value <= max_value:
                        claim.verification_score = 1.0 - abs(numeric_value - claim.value) / claim.value
                        claim.tolerance_applied = tolerance
                        return True
        
        # Check IncomeStatementData
        query = self.db.query(IncomeStatementData)
        if property_id:
            query = query.filter(IncomeStatementData.property_id == property_id)
        if period_id:
            query = query.filter(IncomeStatementData.period_id == period_id)
        
        income_data = query.all()
        for data in income_data:
            value = getattr(data, 'amount', None)
            if value and isinstance(value, (int, float, Decimal)):
                numeric_value = float(value)
                if min_value <= numeric_value <= max_value:
                    claim.verification_score = 1.0 - abs(numeric_value - claim.value) / claim.value
                    claim.tolerance_applied = tolerance
                    return True
        
        return False
    
    def _verify_percentage_in_db(
        self,
        claim: Claim,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> bool:
        """Verify percentage claim against database"""
        tolerance = hallucination_config.PERCENTAGE_TOLERANCE_PERCENT / 100.0
        min_value = claim.value * (1 - tolerance)
        max_value = claim.value * (1 + tolerance)
        
        # Check FinancialMetrics for percentage fields
        query = self.db.query(FinancialMetrics)
        if property_id:
            query = query.filter(FinancialMetrics.property_id == property_id)
        if period_id:
            query = query.filter(FinancialMetrics.period_id == period_id)
        
        metrics = query.all()
        for metric in metrics:
            # Check percentage fields
            percentage_fields = [
                'occupancy_rate', 'expense_ratio', 'debt_to_equity_ratio',
                'cap_rate', 'return_on_investment'
            ]
            
            for field in percentage_fields:
                value = getattr(metric, field, None)
                if value and isinstance(value, (int, float, Decimal)):
                    numeric_value = float(value)
                    if min_value <= numeric_value <= max_value:
                        claim.verification_score = 1.0 - abs(numeric_value - claim.value) / claim.value
                        claim.tolerance_applied = tolerance
                        return True
        
        return False
    
    def _verify_ratio_in_db(
        self,
        claim: Claim,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> bool:
        """Verify ratio claim (e.g., DSCR) against database"""
        tolerance = hallucination_config.RATIO_TOLERANCE_PERCENT / 100.0
        min_value = claim.value * (1 - tolerance)
        max_value = claim.value * (1 + tolerance)
        
        # Check FinancialMetrics for DSCR
        query = self.db.query(FinancialMetrics)
        if property_id:
            query = query.filter(FinancialMetrics.property_id == property_id)
        if period_id:
            query = query.filter(FinancialMetrics.period_id == period_id)
        
        metrics = query.all()
        for metric in metrics:
            if metric.dscr:
                dscr_value = float(metric.dscr)
                if min_value <= dscr_value <= max_value:
                    claim.verification_score = 1.0 - abs(dscr_value - claim.value) / claim.value
                    claim.tolerance_applied = tolerance
                    return True
        
        return False
    
    def _verify_date_in_db(
        self,
        claim: Claim,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> bool:
        """Verify date claim against database"""
        # For dates, we check if the period exists
        # Extract year and quarter/month from claim value
        year = int(claim.value)
        fractional = claim.value - year
        
        # Check FinancialPeriod
        query = self.db.query(FinancialPeriod)
        if property_id:
            query = query.filter(FinancialPeriod.property_id == property_id)
        
        periods = query.all()
        for period in periods:
            # Check if year matches
            if period.period_year == year:
                # Check quarter or month
                if fractional >= 0.1 and fractional < 0.4:  # Q1-Q4
                    quarter = int(fractional * 10)
                    period_quarter = ((period.period_month - 1) // 3) + 1
                    if period_quarter == quarter:
                        claim.verification_score = 1.0
                        return True
                elif fractional >= 0.01:  # Month
                    month = int(fractional * 100)
                    if period.period_month == month:
                        claim.verification_score = 1.0
                        return True
        
        return False
    
    def _verify_against_documents(
        self,
        claim: Claim,
        sources: List[Dict[str, Any]]
    ) -> bool:
        """Verify claim against source documents"""
        if not sources:
            return False
        
        # Check each source document/chunk
        for source in sources[:hallucination_config.MAX_SOURCE_CHECKS]:
            chunk_text = source.get('chunk_text', '') or source.get('text', '')
            if not chunk_text:
                continue
            
            # Search for the claim value in the text
            if self._find_value_in_text(claim, chunk_text):
                claim.verification_score = 0.8  # Lower confidence for document matches
                return True
        
        return False
    
    def _find_value_in_text(self, claim: Claim, text: str) -> bool:
        """Find claim value in text with tolerance"""
        if claim.claim_type == 'currency':
            tolerance = hallucination_config.CURRENCY_TOLERANCE_PERCENT / 100.0
            min_value = claim.value * (1 - tolerance)
            max_value = claim.value * (1 + tolerance)
            
            # Search for currency values in text
            for pattern in self.currency_patterns:
                for match in pattern.finditer(text):
                    value_str = match.group(1)
                    suffix = match.group(0).upper()
                    value = self._parse_currency_value(value_str, suffix)
                    if value and min_value <= value <= max_value:
                        return True
        
        elif claim.claim_type == 'percentage':
            tolerance = hallucination_config.PERCENTAGE_TOLERANCE_PERCENT / 100.0
            min_value = claim.value * (1 - tolerance)
            max_value = claim.value * (1 + tolerance)
            
            # Search for percentages in text
            for pattern in self.percentage_patterns:
                for match in pattern.finditer(text):
                    value_str = match.group(1)
                    try:
                        value = float(value_str)
                        if min_value <= value <= max_value:
                            return True
                    except ValueError:
                        continue
        
        elif claim.claim_type == 'ratio':
            tolerance = hallucination_config.RATIO_TOLERANCE_PERCENT / 100.0
            min_value = claim.value * (1 - tolerance)
            max_value = claim.value * (1 + tolerance)
            
            # Search for ratios in text
            for pattern in self.ratio_patterns:
                for match in pattern.finditer(text):
                    value_str = match.group(1)
                    try:
                        value = float(value_str)
                        if min_value <= value <= max_value:
                            return True
                    except ValueError:
                        continue
        
        return False
    
    def adjust_confidence(
        self,
        original_confidence: float,
        detection_result: Dict[str, Any]
    ) -> float:
        """
        Adjust confidence score based on hallucination detection
        
        Args:
            original_confidence: Original confidence score (0-1)
            detection_result: Result from detect_hallucinations()
        
        Returns:
            Adjusted confidence score
        """
        if not detection_result.get('has_hallucinations', False):
            return original_confidence
        
        # Apply penalty
        adjustment = detection_result.get('confidence_adjustment', 0.0)
        adjusted_confidence = original_confidence + adjustment
        
        # Ensure confidence stays in valid range
        return max(0.0, min(1.0, adjusted_confidence))
    
    def flag_for_review(
        self,
        nlq_query_id: int,
        user_id: int,
        answer: str,
        original_confidence: float,
        detection_result: Dict[str, Any],
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> Optional[HallucinationReview]:
        """
        Flag answer for manual review if hallucinations detected
        
        Args:
            nlq_query_id: ID of the NLQ query
            user_id: User ID who asked the question
            answer: LLM-generated answer
            original_confidence: Original confidence score
            detection_result: Result from detect_hallucinations()
            property_id: Property ID (optional)
            period_id: Period ID (optional)
        
        Returns:
            HallucinationReview object if flagged, None otherwise
        """
        if not hallucination_config.REVIEW_QUEUE_ENABLED or not REVIEW_QUEUE_AVAILABLE:
            return None
        
        if not detection_result.get('has_hallucinations', False):
            return None
        
        if not hallucination_config.AUTO_FLAG_UNVERIFIED:
            return None
        
        try:
            adjusted_confidence = self.adjust_confidence(original_confidence, detection_result)
            
            review = HallucinationReview(
                nlq_query_id=nlq_query_id,
                user_id=user_id,
                original_answer=answer,
                original_confidence=original_confidence,
                adjusted_confidence=adjusted_confidence,
                total_claims=detection_result.get('total_claims', 0),
                verified_claims=detection_result.get('verified_claims', 0),
                unverified_claims=detection_result.get('unverified_claims', 0),
                flagged_claims=detection_result.get('flagged_claims', []),
                status='pending',
                property_id=property_id,
                period_id=period_id
            )
            
            self.db.add(review)
            self.db.commit()
            self.db.refresh(review)
            
            logger.info(
                f"Flagged answer for review: NLQ query {nlq_query_id}, "
                f"{detection_result.get('unverified_claims', 0)} unverified claims"
            )
            
            return review
            
        except Exception as e:
            logger.error(f"Failed to flag answer for review: {e}", exc_info=True)
            self.db.rollback()
            return None

