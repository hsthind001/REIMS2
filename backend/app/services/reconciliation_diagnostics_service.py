"""
Reconciliation Diagnostics Service

Provides detailed diagnostics when matches fail, suggests alternative account codes,
identifies missing data requirements, and recommends fixes based on learned patterns.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.services.account_code_discovery_service import AccountCodeDiscoveryService
from app.services.match_learning_service import MatchLearningService
from app.models.discovered_account_code import DiscoveredAccountCode
from app.models.account_code_pattern import AccountCodePattern
from app.models.account_code_synonym import AccountCodeSynonym
from app.models.learned_match_pattern import LearnedMatchPattern
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData
from app.models.forensic_reconciliation_session import ForensicReconciliationSession
from app.models.forensic_match import ForensicMatch

logger = logging.getLogger(__name__)


class ReconciliationDiagnosticsService:
    """Service for providing intelligent diagnostics"""
    
    def __init__(self, db: Session):
        """
        Initialize diagnostics service
        
        Args:
            db: Database session
        """
        self.db = db
        self.discovery_service = AccountCodeDiscoveryService(db)
        self.learning_service = MatchLearningService(db)
    
    def get_diagnostics(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, Any]:
        """
        Get comprehensive diagnostics for reconciliation
        
        Args:
            property_id: Property ID
            period_id: Period ID
            
        Returns:
            Dict with diagnostic information
        """
        logger.info(f"Generating diagnostics for property {property_id}, period {period_id}")
        
        diagnostics = {
            'property_id': property_id,
            'period_id': period_id,
            'data_availability': self._check_data_availability(property_id, period_id),
            'discovered_accounts': self._get_discovered_accounts(property_id, period_id),
            'missing_accounts': self._identify_missing_accounts(property_id, period_id),
            'suggested_fixes': self._suggest_fixes(property_id, period_id),
            'learned_patterns': self._get_relevant_patterns(property_id, period_id),
            'recommendations': []
        }
        
        # Generate recommendations
        diagnostics['recommendations'] = self._generate_recommendations(diagnostics)
        
        return diagnostics
    
    def _check_data_availability(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, Any]:
        """Check what data is available"""
        availability = {
            'balance_sheet': {
                'has_data': False,
                'record_count': 0,
                'account_codes': []
            },
            'income_statement': {
                'has_data': False,
                'record_count': 0,
                'account_codes': []
            },
            'cash_flow': {
                'has_data': False,
                'record_count': 0,
                'account_codes': []
            },
            'rent_roll': {
                'has_data': False,
                'record_count': 0
            },
            'mortgage_statement': {
                'has_data': False,
                'record_count': 0
            }
        }
        
        # Check balance sheet
        bs_count = self.db.query(func.count(BalanceSheetData.id)).filter(
            and_(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.period_id == period_id
            )
        ).scalar()
        bs_codes = self.db.query(BalanceSheetData.account_code).filter(
            and_(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.period_id == period_id
            )
        ).distinct().all()
        availability['balance_sheet'] = {
            'has_data': bs_count > 0,
            'record_count': bs_count,
            'account_codes': [code[0] for code in bs_codes[:20]]  # Limit to 20
        }
        
        # Check income statement
        is_count = self.db.query(func.count(IncomeStatementData.id)).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id
            )
        ).scalar()
        is_codes = self.db.query(IncomeStatementData.account_code).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id
            )
        ).distinct().all()
        availability['income_statement'] = {
            'has_data': is_count > 0,
            'record_count': is_count,
            'account_codes': [code[0] for code in is_codes[:20]]
        }
        
        # Check cash flow
        cf_count = self.db.query(func.count(CashFlowData.id)).filter(
            and_(
                CashFlowData.property_id == property_id,
                CashFlowData.period_id == period_id
            )
        ).scalar()
        cf_codes = self.db.query(CashFlowData.account_code).filter(
            and_(
                CashFlowData.property_id == property_id,
                CashFlowData.period_id == period_id
            )
        ).distinct().all()
        availability['cash_flow'] = {
            'has_data': cf_count > 0,
            'record_count': cf_count,
            'account_codes': [code[0] for code in cf_codes[:20]]
        }
        
        # Check rent roll
        rr_count = self.db.query(func.count(RentRollData.id)).filter(
            and_(
                RentRollData.property_id == property_id,
                RentRollData.period_id == period_id
            )
        ).scalar()
        availability['rent_roll'] = {
            'has_data': rr_count > 0,
            'record_count': rr_count
        }
        
        # Check mortgage statement
        ms_count = self.db.query(func.count(MortgageStatementData.id)).filter(
            and_(
                MortgageStatementData.property_id == property_id,
                MortgageStatementData.period_id == period_id
            )
        ).scalar()
        
        # If no data records but document upload exists, check document_uploads
        has_upload = False
        if ms_count == 0:
            from app.models.document_upload import DocumentUpload
            upload_count = self.db.query(func.count(DocumentUpload.id)).filter(
                and_(
                    DocumentUpload.property_id == property_id,
                    DocumentUpload.period_id == period_id,
                    DocumentUpload.document_type == 'mortgage_statement',
                    DocumentUpload.extraction_status.in_(['completed', 'validating'])
                )
            ).scalar()
            has_upload = upload_count > 0
        
        availability['mortgage_statement'] = {
            'has_data': ms_count > 0 or has_upload,
            'record_count': ms_count,
            'has_upload_but_no_data': has_upload and ms_count == 0  # Flag for re-extraction needed
        }
        
        return availability
    
    def _get_discovered_accounts(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get discovered account codes for this property/period"""
        discovered = {}
        
        for doc_type in ['balance_sheet', 'income_statement', 'cash_flow']:
            codes = self.discovery_service.get_discovered_codes(
                document_type=doc_type,
                property_id=property_id,
                period_id=period_id
            )
            discovered[doc_type] = [{
                'account_code': code.account_code,
                'account_name': code.account_name,
                'account_type': code.account_type,
                'occurrence_count': code.occurrence_count
            } for code in codes[:50]]  # Limit to 50 per type
        
        return discovered
    
    def _identify_missing_accounts(
        self,
        property_id: int,
        period_id: int
    ) -> Dict[str, List[str]]:
        """Identify missing accounts that are typically needed for reconciliation"""
        missing = {
            'balance_sheet': [],
            'income_statement': [],
            'cash_flow': []
        }
        
        # Expected accounts for reconciliation
        expected_accounts = {
            'balance_sheet': [
                ('3995-0000', 'Current Period Earnings'),
                ('3910-0000', 'Retained Earnings'),
                ('0122-0000', 'Cash - Operating'),
                ('2610-0000', 'Long-Term Debt')
            ],
            'income_statement': [
                ('9090-0000', 'Net Income'),
                ('4010-0000', 'Base Rentals'),
                ('6520-0000', 'Interest Expense')
            ],
            'cash_flow': [
                ('9999-0000', 'Ending Cash')
            ]
        }
        
        # Check balance sheet
        bs_codes = {code[0] for code in self.db.query(BalanceSheetData.account_code).filter(
            and_(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.period_id == period_id
            )
        ).distinct().all()}
        
        for code, name in expected_accounts['balance_sheet']:
            # Check exact code
            if code not in bs_codes:
                # Check for similar codes (fuzzy)
                similar = self._find_similar_accounts(code, name, 'balance_sheet', property_id, period_id)
                if not similar:
                    missing['balance_sheet'].append(f"{code} - {name}")
        
        # Check income statement
        is_codes = {code[0] for code in self.db.query(IncomeStatementData.account_code).filter(
            and_(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id
            )
        ).distinct().all()}
        
        for code, name in expected_accounts['income_statement']:
            if code not in is_codes:
                similar = self._find_similar_accounts(code, name, 'income_statement', property_id, period_id)
                if not similar:
                    missing['income_statement'].append(f"{code} - {name}")
        
        # Check cash flow
        cf_codes = {code[0] for code in self.db.query(CashFlowData.account_code).filter(
            and_(
                CashFlowData.property_id == property_id,
                CashFlowData.period_id == period_id
            )
        ).distinct().all()}
        
        for code, name in expected_accounts['cash_flow']:
            if code not in cf_codes:
                similar = self._find_similar_accounts(code, name, 'cash_flow', property_id, period_id)
                if not similar:
                    missing['cash_flow'].append(f"{code} - {name}")
        
        return missing
    
    def _find_similar_accounts(
        self,
        expected_code: str,
        expected_name: str,
        document_type: str,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """Find similar accounts using discovered codes and synonyms"""
        similar = []
        
        # Check discovered codes
        discovered = self.discovery_service.get_discovered_codes(
            document_type=document_type,
            property_id=property_id,
            period_id=period_id
        )
        
        for code in discovered:
            # Check code similarity (prefix match)
            if expected_code and code.account_code:
                if expected_code[:3] == code.account_code[:3]:  # Same prefix
                    similar.append({
                        'account_code': code.account_code,
                        'account_name': code.account_name,
                        'similarity_type': 'code_prefix',
                        'confidence': 70.0
                    })
            
            # Check name similarity
            if expected_name.lower() in code.account_name.lower():
                similar.append({
                    'account_code': code.account_code,
                    'account_name': code.account_name,
                    'similarity_type': 'name_contains',
                    'confidence': 80.0
                })
        
        # Check synonyms
        synonyms = self.learning_service.get_synonyms(account_code=expected_code)
        for synonym in synonyms:
            similar.append({
                'account_code': synonym.canonical_account_code,
                'account_name': synonym.canonical_account_name,
                'similarity_type': 'synonym',
                'confidence': float(synonym.combined_confidence)
            })
        
        return similar[:5]  # Return top 5
    
    def _suggest_fixes(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """Suggest fixes based on missing accounts and learned patterns"""
        fixes = []
        
        missing = self._identify_missing_accounts(property_id, period_id)
        
        # Suggest fixes for missing accounts
        for doc_type, missing_list in missing.items():
            for missing_account in missing_list:
                code, name = missing_account.split(' - ', 1)
                similar = self._find_similar_accounts(code, name, doc_type, property_id, period_id)
                
                if similar:
                    fixes.append({
                        'issue': f"Missing account: {missing_account}",
                        'suggestion': f"Found similar account: {similar[0]['account_code']} - {similar[0]['account_name']}",
                        'confidence': similar[0]['confidence'],
                        'action': 'use_similar_account',
                        'similar_accounts': similar
                    })
                else:
                    fixes.append({
                        'issue': f"Missing account: {missing_account}",
                        'suggestion': f"Upload {doc_type.replace('_', ' ').title()} document with this account",
                        'confidence': 0.0,
                        'action': 'upload_document'
                    })
        
        return fixes
    
    def _get_relevant_patterns(
        self,
        property_id: int,
        period_id: int
    ) -> List[Dict[str, Any]]:
        """Get relevant learned patterns for this property/period"""
        patterns = self.learning_service.get_learned_patterns(min_success_rate=70.0)
        
        # Filter patterns that might be relevant
        relevant = []
        for pattern in patterns[:10]:  # Top 10 patterns
            relevant.append({
                'pattern_name': pattern.pattern_name,
                'source_document_type': pattern.source_document_type,
                'target_document_type': pattern.target_document_type,
                'source_account_code': pattern.source_account_code,
                'target_account_code': pattern.target_account_code,
                'relationship_type': pattern.relationship_type,
                'success_rate': float(pattern.success_rate),
                'average_confidence': float(pattern.average_confidence) if pattern.average_confidence else 0.0
            })
        
        return relevant
    
    def _generate_recommendations(
        self,
        diagnostics: Dict[str, Any]
    ) -> List[str]:
        """Generate human-readable recommendations"""
        recommendations = []
        
        # Check data availability
        availability = diagnostics['data_availability']
        if not availability['balance_sheet']['has_data']:
            recommendations.append("Upload Balance Sheet document for this period")
        if not availability['income_statement']['has_data']:
            recommendations.append("Upload Income Statement document for this period")
        
        # Check missing accounts
        missing = diagnostics['missing_accounts']
        if missing['balance_sheet']:
            recommendations.append(f"Balance Sheet missing accounts: {', '.join(missing['balance_sheet'][:3])}")
        if missing['income_statement']:
            recommendations.append(f"Income Statement missing accounts: {', '.join(missing['income_statement'][:3])}")
        
        # Check if we have enough data for reconciliation
        total_records = (
            availability['balance_sheet']['record_count'] +
            availability['income_statement']['record_count'] +
            availability['cash_flow']['record_count']
        )
        if total_records < 10:
            recommendations.append("Insufficient data for reconciliation. Upload more documents.")
        
        # Check learned patterns
        if diagnostics['learned_patterns']:
            recommendations.append(f"Found {len(diagnostics['learned_patterns'])} learned patterns that may help with matching")
        
        if not recommendations:
            recommendations.append("Data looks good. Try running reconciliation.")
        
        return recommendations

