"""
Relationship Discovery Service

Uses machine learning to discover new relationships between documents,
identifies patterns in successful matches, and suggests new matching rules.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.learned_match_pattern import LearnedMatchPattern
from app.models.account_code_pattern import AccountCodePattern
from app.models.reconciliation_learning_log import ReconciliationLearningLog
from app.models.forensic_match import ForensicMatch
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData

logger = logging.getLogger(__name__)


class RelationshipDiscoveryService:
    """Service for discovering relationships using ML"""
    
    def __init__(self, db: Session):
        """
        Initialize relationship discovery service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def discover_relationships(
        self,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Discover new relationships between documents using ML
        
        Args:
            property_id: Optional property filter
            period_id: Optional period filter
            
        Returns:
            Dict with discovered relationships
        """
        logger.info(f"Discovering relationships (property_id={property_id}, period_id={period_id})")
        
        # Step 1: Analyze successful matches for patterns
        patterns = self._analyze_match_patterns(property_id, period_id)
        
        # Step 2: Discover account correlations
        correlations = self._discover_account_correlations(property_id, period_id)
        
        # Step 3: Cluster similar relationships
        clusters = self._cluster_relationships(patterns)
        
        # Step 4: Suggest new rules
        suggested_rules = self._suggest_new_rules(patterns, correlations, clusters)
        
        # Log discovery activity
        self._log_discovery_activity(
            property_id=property_id,
            period_id=period_id,
            patterns_found=len(patterns),
            correlations_found=len(correlations),
            rules_suggested=len(suggested_rules)
        )
        
        return {
            'patterns_discovered': len(patterns),
            'correlations_discovered': len(correlations),
            'clusters_created': len(clusters),
            'rules_suggested': len(suggested_rules),
            'suggested_rules': suggested_rules
        }
    
    def _analyze_match_patterns(
        self,
        property_id: Optional[int],
        period_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Analyze successful matches to find patterns"""
        # Get approved matches
        query = self.db.query(ForensicMatch).filter(
            ForensicMatch.status == 'approved'
        )
        
        if property_id:
            from app.models.forensic_reconciliation_session import ForensicReconciliationSession
            query = query.join(ForensicReconciliationSession).filter(
                ForensicReconciliationSession.property_id == property_id
            )
        if period_id:
            from app.models.forensic_reconciliation_session import ForensicReconciliationSession
            query = query.join(ForensicReconciliationSession).filter(
                ForensicReconciliationSession.period_id == period_id
            )
        
        matches = query.all()
        
        # Group by relationship characteristics
        patterns = defaultdict(list)
        for match in matches:
            key = (
                match.source_document_type,
                match.target_document_type,
                match.relationship_type
            )
            patterns[key].append(match)
        
        # Extract pattern information
        pattern_list = []
        for key, match_group in patterns.items():
            if len(match_group) >= 2:  # Need at least 2 matches for a pattern
                source_doc, target_doc, rel_type = key
                
                # Calculate statistics
                confidences = [float(m.confidence_score) for m in match_group if m.confidence_score]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                pattern_list.append({
                    'source_document_type': source_doc,
                    'target_document_type': target_doc,
                    'relationship_type': rel_type,
                    'match_count': len(match_group),
                    'average_confidence': avg_confidence,
                    'matches': match_group[:5]  # Sample matches
                })
        
        return pattern_list
    
    def _discover_account_correlations(
        self,
        property_id: Optional[int],
        period_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Discover correlations between accounts across documents"""
        correlations = []
        
        # Get all data for the property/period
        bs_data = self._get_account_data('balance_sheet', property_id, period_id)
        is_data = self._get_account_data('income_statement', property_id, period_id)
        cf_data = self._get_account_data('cash_flow', property_id, period_id)
        
        # Find accounts that appear together frequently
        # Simple correlation: accounts that appear in same periods
        if property_id and period_id:
            # For specific property/period, check if accounts co-occur
            bs_codes = {r['account_code'] for r in bs_data if r.get('account_code')}
            is_codes = {r['account_code'] for r in is_data if r.get('account_code')}
            cf_codes = {r['account_code'] for r in cf_data if r.get('account_code')}
            
            # Cross-document correlations
            if bs_codes and is_codes:
                # Check for potential relationships
                for bs_code in list(bs_codes)[:10]:  # Sample
                    for is_code in list(is_codes)[:10]:
                        # Simple heuristic: codes with similar prefixes might be related
                        if bs_code and is_code:
                            if bs_code[:2] == is_code[:2] or abs(int(bs_code[:4]) - int(is_code[:4])) < 100:
                                correlations.append({
                                    'source_code': bs_code,
                                    'target_code': is_code,
                                    'source_doc': 'balance_sheet',
                                    'target_doc': 'income_statement',
                                    'correlation_type': 'code_similarity',
                                    'confidence': 50.0
                                })
        
        return correlations
    
    def _get_account_data(
        self,
        document_type: str,
        property_id: Optional[int],
        period_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Get account data for a document type"""
        if document_type == 'balance_sheet':
            query = self.db.query(
                BalanceSheetData.account_code,
                BalanceSheetData.account_name,
                func.sum(BalanceSheetData.amount).label('total_amount')
            ).group_by(
                BalanceSheetData.account_code,
                BalanceSheetData.account_name
            )
            if property_id:
                query = query.filter(BalanceSheetData.property_id == property_id)
            if period_id:
                query = query.filter(BalanceSheetData.period_id == period_id)
            results = query.all()
            return [{'account_code': r.account_code, 'account_name': r.account_name, 'amount': r.total_amount} for r in results]
        
        elif document_type == 'income_statement':
            query = self.db.query(
                IncomeStatementData.account_code,
                IncomeStatementData.account_name,
                func.sum(IncomeStatementData.period_amount).label('total_amount')
            ).group_by(
                IncomeStatementData.account_code,
                IncomeStatementData.account_name
            )
            if property_id:
                query = query.filter(IncomeStatementData.property_id == property_id)
            if period_id:
                query = query.filter(IncomeStatementData.period_id == period_id)
            results = query.all()
            return [{'account_code': r.account_code, 'account_name': r.account_name, 'amount': r.total_amount} for r in results]
        
        elif document_type == 'cash_flow':
            query = self.db.query(
                CashFlowData.account_code,
                CashFlowData.account_name,
                func.sum(CashFlowData.period_amount).label('total_amount')
            ).group_by(
                CashFlowData.account_code,
                CashFlowData.account_name
            )
            if property_id:
                query = query.filter(CashFlowData.property_id == property_id)
            if period_id:
                query = query.filter(CashFlowData.period_id == period_id)
            results = query.all()
            return [{'account_code': r.account_code, 'account_name': r.account_name, 'amount': r.total_amount} for r in results]
        
        return []
    
    def _cluster_relationships(
        self,
        patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Cluster similar relationships"""
        # Simple clustering by relationship type and document types
        clusters = defaultdict(list)
        
        for pattern in patterns:
            key = (
                pattern['source_document_type'],
                pattern['target_document_type'],
                pattern['relationship_type']
            )
            clusters[key].append(pattern)
        
        cluster_list = []
        for key, pattern_group in clusters.items():
            if len(pattern_group) >= 2:
                cluster_list.append({
                    'cluster_id': f"{key[0]}_{key[1]}_{key[2]}",
                    'source_document_type': key[0],
                    'target_document_type': key[1],
                    'relationship_type': key[2],
                    'pattern_count': len(pattern_group),
                    'average_confidence': sum(p['average_confidence'] for p in pattern_group) / len(pattern_group)
                })
        
        return cluster_list
    
    def _suggest_new_rules(
        self,
        patterns: List[Dict[str, Any]],
        correlations: List[Dict[str, Any]],
        clusters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Suggest new matching rules based on discovered patterns"""
        suggested_rules = []
        
        # Suggest rules from clusters
        for cluster in clusters:
            if cluster['pattern_count'] >= 3 and cluster['average_confidence'] >= 80.0:
                suggested_rules.append({
                    'rule_name': f"Auto-discovered: {cluster['source_document_type']} to {cluster['target_document_type']}",
                    'source_document_type': cluster['source_document_type'],
                    'target_document_type': cluster['target_document_type'],
                    'relationship_type': cluster['relationship_type'],
                    'confidence': cluster['average_confidence'],
                    'evidence_count': cluster['pattern_count'],
                    'suggestion_type': 'cluster_based'
                })
        
        # Suggest rules from correlations
        for correlation in correlations:
            if correlation['confidence'] >= 60.0:
                suggested_rules.append({
                    'rule_name': f"Auto-discovered: {correlation['source_code']} correlates with {correlation['target_code']}",
                    'source_code': correlation['source_code'],
                    'target_code': correlation['target_code'],
                    'source_document_type': correlation['source_doc'],
                    'target_document_type': correlation['target_doc'],
                    'relationship_type': 'correlation',
                    'confidence': correlation['confidence'],
                    'evidence_count': 1,
                    'suggestion_type': 'correlation_based'
                })
        
        return suggested_rules
    
    def _log_discovery_activity(
        self,
        property_id: Optional[int],
        period_id: Optional[int],
        patterns_found: int,
        correlations_found: int,
        rules_suggested: int
    ) -> None:
        """Log relationship discovery activity"""
        log = ReconciliationLearningLog(
            activity_type='relationship_discovery',
            activity_name='Discover Relationships',
            property_id=property_id,
            period_id=period_id,
            activity_data={
                'patterns_found': patterns_found,
                'correlations_found': correlations_found,
                'rules_suggested': rules_suggested
            },
            result_type='success',
            is_successful=True,
            triggered_by='automatic'
        )
        self.db.add(log)
        self.db.commit()

