"""
Account Code Discovery Service

Scans all financial data tables to discover actual account codes,
builds taxonomy, creates pattern library, and maps semantic account names.
"""
import logging
import re
from typing import Dict, List, Optional, Any, Set
from decimal import Decimal
from collections import defaultdict, Counter
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, and_, or_

from app.models.discovered_account_code import DiscoveredAccountCode
from app.models.account_code_pattern import AccountCodePattern
from app.models.account_semantic_mapping import AccountSemanticMapping
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.chart_of_accounts import ChartOfAccounts

logger = logging.getLogger(__name__)


class AccountCodeDiscoveryService:
    """Service for discovering account codes from financial data"""
    
    def __init__(self, db: Session):
        """
        Initialize account code discovery service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def discover_all_account_codes(
        self,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Discover all account codes from financial data tables
        
        Args:
            property_id: Optional property filter
            period_id: Optional period filter
            document_type: Optional document type filter
            
        Returns:
            Dict with discovery results
        """
        logger.info(f"Starting account code discovery (property_id={property_id}, period_id={period_id}, doc_type={document_type})")
        
        results = {
            'balance_sheet': self._discover_balance_sheet_codes(property_id, period_id),
            'income_statement': self._discover_income_statement_codes(property_id, period_id),
            'cash_flow': self._discover_cash_flow_codes(property_id, period_id),
            'rent_roll': self._discover_rent_roll_codes(property_id, period_id),
            'mortgage_statement': self._discover_mortgage_statement_codes(property_id, period_id),
        }
        
        # Store discovered codes
        total_discovered = 0
        for doc_type, codes in results.items():
            if document_type and doc_type != document_type:
                continue
            for code_info in codes:
                self._store_discovered_code(code_info, doc_type)
                total_discovered += 1
        
        # Build patterns
        patterns = self._build_patterns(results)
        
        # Build semantic mappings
        semantic_mappings = self._build_semantic_mappings(results)
        
        logger.info(f"Discovery complete: {total_discovered} codes, {len(patterns)} patterns, {len(semantic_mappings)} mappings")
        
        return {
            'total_codes_discovered': total_discovered,
            'by_document_type': {k: len(v) for k, v in results.items()},
            'patterns_created': len(patterns),
            'semantic_mappings_created': len(semantic_mappings),
            'details': results
        }
    
    def _discover_balance_sheet_codes(
        self,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Discover account codes from balance sheet data"""
        query = self.db.query(
            BalanceSheetData.account_code,
            BalanceSheetData.account_name,
            BalanceSheetData.account_category,
            BalanceSheetData.account_subcategory,
            func.count(BalanceSheetData.id).label('count'),
            func.count(distinct(BalanceSheetData.property_id)).label('property_count'),
            func.count(distinct(BalanceSheetData.period_id)).label('period_count')
        ).group_by(
            BalanceSheetData.account_code,
            BalanceSheetData.account_name,
            BalanceSheetData.account_category,
            BalanceSheetData.account_subcategory
        )
        
        if property_id:
            query = query.filter(BalanceSheetData.property_id == property_id)
        if period_id:
            query = query.filter(BalanceSheetData.period_id == period_id)
        
        results = query.all()
        
        return [{
            'account_code': r.account_code,
            'account_name': r.account_name,
            'account_type': None,  # Balance sheet doesn't have account_type, infer from category
            'category': r.account_category,
            'subcategory': r.account_subcategory,
            'occurrence_count': r.count,
            'property_count': r.property_count,
            'period_count': r.period_count
        } for r in results]
    
    def _discover_income_statement_codes(
        self,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Discover account codes from income statement data"""
        query = self.db.query(
            IncomeStatementData.account_code,
            IncomeStatementData.account_name,
            IncomeStatementData.is_income,
            func.count(IncomeStatementData.id).label('count'),
            func.count(distinct(IncomeStatementData.property_id)).label('property_count'),
            func.count(distinct(IncomeStatementData.period_id)).label('period_count')
        ).group_by(
            IncomeStatementData.account_code,
            IncomeStatementData.account_name,
            IncomeStatementData.is_income
        )
        
        if property_id:
            query = query.filter(IncomeStatementData.property_id == property_id)
        if period_id:
            query = query.filter(IncomeStatementData.period_id == period_id)
        
        results = query.all()
        
        return [{
            'account_code': r.account_code,
            'account_name': r.account_name,
            'account_type': 'income' if r.is_income else 'expense',
            'category': None,
            'subcategory': None,
            'occurrence_count': r.count,
            'property_count': r.property_count,
            'period_count': r.period_count
        } for r in results]
    
    def _discover_cash_flow_codes(
        self,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Discover account codes from cash flow data"""
        query = self.db.query(
            CashFlowData.account_code,
            CashFlowData.account_name,
            CashFlowData.cash_flow_category,
            func.count(CashFlowData.id).label('count'),
            func.count(distinct(CashFlowData.property_id)).label('property_count'),
            func.count(distinct(CashFlowData.period_id)).label('period_count')
        ).group_by(
            CashFlowData.account_code,
            CashFlowData.account_name,
            CashFlowData.cash_flow_category
        )
        
        if property_id:
            query = query.filter(CashFlowData.property_id == property_id)
        if period_id:
            query = query.filter(CashFlowData.period_id == period_id)
        
        results = query.all()
        
        return [{
            'account_code': r.account_code,
            'account_name': r.account_name,
            'account_type': 'cash_flow',
            'category': r.cash_flow_category,
            'subcategory': None,
            'occurrence_count': r.count,
            'property_count': r.property_count,
            'period_count': r.period_count
        } for r in results]
    
    def _discover_rent_roll_codes(
        self,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Discover account codes from rent roll data (uses tenant names)"""
        query = self.db.query(
            RentRollData.tenant_name,
            func.count(RentRollData.id).label('count'),
            func.count(distinct(RentRollData.property_id)).label('property_count'),
            func.count(distinct(RentRollData.period_id)).label('period_count')
        ).group_by(RentRollData.tenant_name)
        
        if property_id:
            query = query.filter(RentRollData.property_id == property_id)
        if period_id:
            query = query.filter(RentRollData.period_id == period_id)
        
        results = query.all()
        
        return [{
            'account_code': None,  # Rent roll doesn't have account codes
            'account_name': r.tenant_name,
            'account_type': 'rent_roll',
            'category': None,
            'subcategory': None,
            'occurrence_count': r.count,
            'property_count': r.property_count,
            'period_count': r.period_count
        } for r in results]
    
    def _discover_mortgage_statement_codes(
        self,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Discover account codes from mortgage statement data"""
        query = self.db.query(
            MortgageStatementData.loan_number,
            func.count(MortgageStatementData.id).label('count'),
            func.count(distinct(MortgageStatementData.property_id)).label('property_count'),
            func.count(distinct(MortgageStatementData.period_id)).label('period_count')
        ).group_by(MortgageStatementData.loan_number)
        
        if property_id:
            query = query.filter(MortgageStatementData.property_id == property_id)
        if period_id:
            query = query.filter(MortgageStatementData.period_id == period_id)
        
        results = query.all()
        
        return [{
            'account_code': r.loan_number,
            'account_name': f"Loan {r.loan_number}",
            'account_type': 'mortgage',
            'category': None,
            'subcategory': None,
            'occurrence_count': r.count,
            'property_count': r.property_count,
            'period_count': r.period_count
        } for r in results]
    
    def _store_discovered_code(
        self,
        code_info: Dict[str, Any],
        document_type: str
    ) -> Optional[DiscoveredAccountCode]:
        """Store or update discovered account code"""
        if not code_info.get('account_code'):
            return None  # Skip codes without account_code (like rent roll)
        
        # Check if code already exists
        existing = self.db.query(DiscoveredAccountCode).filter(
            and_(
                DiscoveredAccountCode.account_code == code_info['account_code'],
                DiscoveredAccountCode.document_type == document_type
            )
        ).first()
        
        if existing:
            # Update existing record
            existing.occurrence_count += code_info.get('occurrence_count', 1)
            existing.property_count = max(existing.property_count, code_info.get('property_count', 1))
            existing.period_count = max(existing.period_count, code_info.get('period_count', 1))
            existing.account_name = code_info.get('account_name', existing.account_name)
            existing.account_type = code_info.get('account_type') or existing.account_type
            existing.category = code_info.get('category') or existing.category
            existing.subcategory = code_info.get('subcategory') or existing.subcategory
            existing.last_seen_at = datetime.now()
            return existing
        else:
            # Create new record
            discovered = DiscoveredAccountCode(
                account_code=code_info['account_code'],
                account_name=code_info.get('account_name', ''),
                document_type=document_type,
                source_table=f"{document_type}_data",
                occurrence_count=code_info.get('occurrence_count', 1),
                property_count=code_info.get('property_count', 1),
                period_count=code_info.get('period_count', 1),
                account_type=code_info.get('account_type'),
                category=code_info.get('category'),
                subcategory=code_info.get('subcategory'),
                confidence_score=Decimal('100.0')
            )
            self.db.add(discovered)
            return discovered
    
    def _build_patterns(
        self,
        results: Dict[str, List[Dict[str, Any]]]
    ) -> List[AccountCodePattern]:
        """Build account code patterns from discovered codes"""
        patterns = []
        
        # Pattern 1: Code range patterns (e.g., 0122-0000 to 0129-0000)
        for doc_type, codes in results.items():
            code_ranges = self._identify_code_ranges(codes)
            for range_info in code_ranges:
                pattern = AccountCodePattern(
                    pattern_name=f"{doc_type}_code_range_{range_info['start']}_to_{range_info['end']}",
                    pattern_type='range',
                    pattern_definition=f"Account codes from {range_info['start']} to {range_info['end']}",
                    pattern_json={
                        'start': range_info['start'],
                        'end': range_info['end'],
                        'document_type': doc_type
                    },
                    match_rule=f"account_code >= '{range_info['start']}' AND account_code <= '{range_info['end']}'",
                    document_type=doc_type,
                    account_type=range_info.get('account_type'),
                    match_count=range_info.get('count', 0),
                    is_active=True
                )
                patterns.append(pattern)
        
        # Pattern 2: Regex patterns (e.g., codes starting with specific prefix)
        for doc_type, codes in results.items():
            regex_patterns = self._identify_regex_patterns(codes)
            for regex_info in regex_patterns:
                pattern = AccountCodePattern(
                    pattern_name=f"{doc_type}_regex_{regex_info['pattern']}",
                    pattern_type='regex',
                    pattern_definition=regex_info['description'],
                    pattern_json={
                        'regex': regex_info['pattern'],
                        'document_type': doc_type
                    },
                    match_rule=f"account_code ~ '{regex_info['pattern']}'",
                    document_type=doc_type,
                    account_type=regex_info.get('account_type'),
                    match_count=regex_info.get('count', 0),
                    is_active=True
                )
                patterns.append(pattern)
        
        # Store patterns
        for pattern in patterns:
            # Check if pattern already exists
            existing = self.db.query(AccountCodePattern).filter(
                and_(
                    AccountCodePattern.pattern_name == pattern.pattern_name,
                    AccountCodePattern.pattern_type == pattern.pattern_type
                )
            ).first()
            
            if not existing:
                self.db.add(pattern)
        
        return patterns
    
    def _identify_code_ranges(
        self,
        codes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify code ranges from discovered codes"""
        ranges = []
        code_list = [c['account_code'] for c in codes if c.get('account_code')]
        
        if not code_list:
            return ranges
        
        # Group by prefix (first 4 characters)
        prefix_groups = defaultdict(list)
        for code in code_list:
            if len(code) >= 4:
                prefix = code[:4]
                prefix_groups[prefix].append(code)
        
        # Identify ranges within each prefix group
        for prefix, group_codes in prefix_groups.items():
            if len(group_codes) >= 3:  # Only create range if 3+ codes
                sorted_codes = sorted(set(group_codes))
                # Simple range detection: consecutive codes
                start = sorted_codes[0]
                end = sorted_codes[-1]
                ranges.append({
                    'start': start,
                    'end': end,
                    'count': len(group_codes),
                    'account_type': codes[0].get('account_type') if codes else None
                })
        
        return ranges
    
    def _identify_regex_patterns(
        self,
        codes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify regex patterns from discovered codes"""
        patterns = []
        code_list = [c['account_code'] for c in codes if c.get('account_code')]
        
        if not code_list:
            return patterns
        
        # Pattern 1: Codes starting with specific digits (e.g., 012%, 261%)
        prefix_counter = Counter()
        for code in code_list:
            if len(code) >= 3:
                prefix = code[:3]
                prefix_counter[prefix] += 1
        
        for prefix, count in prefix_counter.items():
            if count >= 2:  # At least 2 codes with this prefix
                patterns.append({
                    'pattern': f"^{prefix}",
                    'description': f"Account codes starting with {prefix}",
                    'count': count,
                    'account_type': codes[0].get('account_type') if codes else None
                })
        
        # Pattern 2: Codes with specific format (e.g., XXXX-0000)
        format_counter = Counter()
        for code in code_list:
            if '-' in code:
                parts = code.split('-')
                if len(parts) == 2:
                    format_key = f"{len(parts[0])}-{len(parts[1])}"
                    format_counter[format_key] += 1
        
        for format_key, count in format_counter.items():
            if count >= 5:  # At least 5 codes with this format
                patterns.append({
                    'pattern': r'^\d{4}-\d{4}$',  # Example: 0122-0000
                    'description': f"Account codes with format {format_key}",
                    'count': count,
                    'account_type': None
                })
        
        return patterns
    
    def _build_semantic_mappings(
        self,
        results: Dict[str, List[Dict[str, Any]]]
    ) -> List[AccountSemanticMapping]:
        """Build semantic mappings between account names and codes"""
        mappings = []
        
        # For now, create simple name-to-code mappings
        # In Phase 5, this will use NLP embeddings
        for doc_type, codes in results.items():
            for code_info in codes:
                if not code_info.get('account_code') or not code_info.get('account_name'):
                    continue
                
                # Check if mapping already exists
                existing = self.db.query(AccountSemanticMapping).filter(
                    and_(
                        AccountSemanticMapping.account_name == code_info['account_name'],
                        AccountSemanticMapping.account_code == code_info['account_code'],
                        AccountSemanticMapping.document_type == doc_type
                    )
                ).first()
                
                if not existing:
                    mapping = AccountSemanticMapping(
                        account_name=code_info['account_name'],
                        account_code=code_info['account_code'],
                        document_type=doc_type,
                        semantic_similarity=Decimal('100.0'),  # Exact match
                        fuzzy_match_score=Decimal('100.0'),
                        combined_confidence=Decimal('100.0'),
                        match_count=code_info.get('occurrence_count', 1),
                        is_active=True
                    )
                    mappings.append(mapping)
                    self.db.add(mapping)
        
        return mappings
    
    def get_discovered_codes(
        self,
        document_type: Optional[str] = None,
        account_type: Optional[str] = None,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> List[DiscoveredAccountCode]:
        """
        Get discovered account codes with filters
        
        Args:
            document_type: Filter by document type
            account_type: Filter by account type
            property_id: Filter by property
            period_id: Filter by period
            
        Returns:
            List of discovered account codes
        """
        query = self.db.query(DiscoveredAccountCode)
        
        if document_type:
            query = query.filter(DiscoveredAccountCode.document_type == document_type)
        if account_type:
            query = query.filter(DiscoveredAccountCode.account_type == account_type)
        
        return query.order_by(DiscoveredAccountCode.occurrence_count.desc()).all()
    
    def find_account_code_by_name(
        self,
        account_name: str,
        document_type: Optional[str] = None
    ) -> List[DiscoveredAccountCode]:
        """
        Find account codes by account name (fuzzy matching)
        
        Args:
            account_name: Account name to search for
            document_type: Optional document type filter
            
        Returns:
            List of matching discovered account codes
        """
        query = self.db.query(DiscoveredAccountCode).filter(
            DiscoveredAccountCode.account_name.ilike(f"%{account_name}%")
        )
        
        if document_type:
            query = query.filter(DiscoveredAccountCode.document_type == document_type)
        
        return query.order_by(DiscoveredAccountCode.occurrence_count.desc()).limit(10).all()

