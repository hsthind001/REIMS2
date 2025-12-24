"""
Match Learning Service

Analyzes successful matches to extract patterns, builds synonym dictionaries,
and creates confidence models based on historical success.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.learned_match_pattern import LearnedMatchPattern
from app.models.account_code_synonym import AccountCodeSynonym
from app.models.match_confidence_model import MatchConfidenceModel
from app.models.forensic_match import ForensicMatch
from app.models.reconciliation_learning_log import ReconciliationLearningLog

logger = logging.getLogger(__name__)


class MatchLearningService:
    """Service for learning from successful matches"""
    
    def __init__(self, db: Session):
        """
        Initialize match learning service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def analyze_successful_matches(
        self,
        session_id: Optional[int] = None,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze successful matches to extract patterns
        
        Args:
            session_id: Optional session ID filter
            property_id: Optional property filter
            period_id: Optional period filter
            
        Returns:
            Dict with analysis results
        """
        logger.info(f"Analyzing successful matches (session_id={session_id}, property_id={property_id}, period_id={period_id})")
        
        # Get approved matches
        query = self.db.query(ForensicMatch).filter(
            ForensicMatch.status == 'approved'
        )
        
        if session_id:
            query = query.filter(ForensicMatch.session_id == session_id)
        if property_id:
            # Need to join with session to filter by property
            from app.models.forensic_reconciliation_session import ForensicReconciliationSession
            query = query.join(ForensicReconciliationSession).filter(
                ForensicReconciliationSession.property_id == property_id
            )
        if period_id:
            from app.models.forensic_reconciliation_session import ForensicReconciliationSession
            query = query.join(ForensicReconciliationSession).filter(
                ForensicReconciliationSession.period_id == period_id
            )
        
        approved_matches = query.all()
        
        if not approved_matches:
            logger.warning("No approved matches found for analysis")
            return {
                'patterns_created': 0,
                'synonyms_created': 0,
                'message': 'No approved matches found'
            }
        
        # Extract patterns
        patterns = self._extract_patterns(approved_matches)
        
        # Build synonyms
        synonyms = self._build_synonyms(approved_matches)
        
        # Update confidence models
        confidence_updates = self._update_confidence_models(approved_matches)
        
        # Log learning activity
        self._log_learning_activity(
            activity_type='pattern_analysis',
            activity_name='Analyze Successful Matches',
            property_id=property_id,
            period_id=period_id,
            session_id=session_id,
            result_data={
                'patterns_created': len(patterns),
                'synonyms_created': len(synonyms),
                'matches_analyzed': len(approved_matches)
            }
        )
        
        logger.info(f"Analysis complete: {len(patterns)} patterns, {len(synonyms)} synonyms")
        
        return {
            'patterns_created': len(patterns),
            'synonyms_created': len(synonyms),
            'confidence_updates': confidence_updates,
            'matches_analyzed': len(approved_matches)
        }
    
    def _extract_patterns(
        self,
        matches: List[ForensicMatch]
    ) -> List[LearnedMatchPattern]:
        """Extract patterns from successful matches"""
        patterns = []
        
        # Group matches by source/target document types and relationship
        pattern_groups = defaultdict(list)
        for match in matches:
            key = (
                match.source_document_type,
                match.target_document_type,
                match.relationship_type,
                match.source_account_code,
                match.target_account_code
            )
            pattern_groups[key].append(match)
        
        # Create patterns from groups
        for key, group_matches in pattern_groups.items():
            if len(group_matches) < 2:  # Need at least 2 matches to create a pattern
                continue
            
            source_doc_type, target_doc_type, relationship_type, source_code, target_code = key
            
            # Calculate statistics
            confidences = [float(m.confidence_score) for m in group_matches if m.confidence_score]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            min_confidence = min(confidences) if confidences else 0.0
            max_confidence = max(confidences) if confidences else 0.0
            
            # Check if pattern already exists
            existing = self.db.query(LearnedMatchPattern).filter(
                and_(
                    LearnedMatchPattern.source_document_type == source_doc_type,
                    LearnedMatchPattern.target_document_type == target_doc_type,
                    LearnedMatchPattern.source_account_code == source_code,
                    LearnedMatchPattern.target_account_code == target_code,
                    LearnedMatchPattern.relationship_type == relationship_type
                )
            ).first()
            
            if existing:
                # Update existing pattern
                existing.match_count += len(group_matches)
                existing.success_count += len([m for m in group_matches if m.status == 'approved'])
                existing.success_rate = Decimal(str((existing.success_count / existing.match_count) * 100)) if existing.match_count > 0 else Decimal('0')
                existing.average_confidence = Decimal(str(avg_confidence))
                existing.min_confidence = Decimal(str(min_confidence))
                existing.max_confidence = Decimal(str(max_confidence))
                existing.last_used_at = datetime.now()
                patterns.append(existing)
            else:
                # Create new pattern
                first_match = group_matches[0]
                pattern = LearnedMatchPattern(
                    pattern_name=f"{source_doc_type}_{target_doc_type}_{relationship_type}_{source_code}_{target_code}",
                    pattern_type=first_match.match_type,
                    source_document_type=source_doc_type,
                    source_account_code=source_code,
                    source_account_name=first_match.source_account_name,
                    target_document_type=target_doc_type,
                    target_account_code=target_code,
                    target_account_name=first_match.target_account_name,
                    relationship_type=relationship_type,
                    relationship_formula=first_match.relationship_formula,
                    match_count=len(group_matches),
                    success_count=len([m for m in group_matches if m.status == 'approved']),
                    success_rate=Decimal(str((len([m for m in group_matches if m.status == 'approved']) / len(group_matches)) * 100)),
                    average_confidence=Decimal(str(avg_confidence)),
                    min_confidence=Decimal(str(min_confidence)),
                    max_confidence=Decimal(str(max_confidence)),
                    is_active=True,
                    priority=len(group_matches)  # More matches = higher priority
                )
                patterns.append(pattern)
                self.db.add(pattern)
        
        self.db.commit()
        return patterns
    
    def _build_synonyms(
        self,
        matches: List[ForensicMatch]
    ) -> List[AccountCodeSynonym]:
        """Build account code synonyms from successful matches"""
        synonyms = []
        
        # Group by source account codes/names
        source_groups = defaultdict(list)
        for match in matches:
            if match.source_account_code and match.source_account_name:
                source_groups[match.source_account_code].append(match.source_account_name)
            if match.target_account_code and match.target_account_name:
                source_groups[match.target_account_code].append(match.target_account_name)
        
        # Create synonyms for variations
        for account_code, names in source_groups.items():
            unique_names = list(set(names))
            if len(unique_names) <= 1:
                continue
            
            # Use most common name as canonical
            name_counter = Counter(names)
            canonical_name = name_counter.most_common(1)[0][0]
            
            # Create synonyms for other names
            for name in unique_names:
                if name == canonical_name:
                    continue
                
                # Check if synonym already exists
                existing = self.db.query(AccountCodeSynonym).filter(
                    and_(
                        AccountCodeSynonym.canonical_account_code == account_code,
                        AccountCodeSynonym.synonym_name == name
                    )
                ).first()
                
                if existing:
                    existing.usage_count += names.count(name)
                    existing.success_count += 1  # This match was approved
                    existing.success_rate = Decimal(str((existing.success_count / existing.usage_count) * 100)) if existing.usage_count > 0 else Decimal('0')
                    synonyms.append(existing)
                else:
                    # Calculate similarity (simple for now, can be enhanced with NLP)
                    similarity = self._calculate_name_similarity(canonical_name, name)
                    
                    synonym = AccountCodeSynonym(
                        canonical_account_code=account_code,
                        canonical_account_name=canonical_name,
                        synonym_name=name,
                        code_similarity=Decimal('100.0'),  # Same code
                        name_similarity=Decimal(str(similarity)),
                        combined_confidence=Decimal(str(similarity)),
                        usage_count=names.count(name),
                        success_count=1,
                        success_rate=Decimal('100.0'),  # Approved match
                        is_active=True
                    )
                    synonyms.append(synonym)
                    self.db.add(synonym)
        
        self.db.commit()
        return synonyms
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate simple string similarity (can be enhanced with NLP)"""
        # Simple word overlap similarity
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return (len(intersection) / len(union)) * 100 if union else 0.0
    
    def _update_confidence_models(
        self,
        matches: List[ForensicMatch]
    ) -> Dict[str, Any]:
        """Update confidence models based on match results"""
        # For now, just track statistics
        # In Phase 5, this will train actual ML models
        
        if not matches:
            return {'updated': False, 'message': 'No matches to analyze'}
        
        # Calculate confidence statistics by match type
        by_type = defaultdict(list)
        for match in matches:
            if match.confidence_score:
                by_type[match.match_type].append(float(match.confidence_score))
        
        stats = {}
        for match_type, confidences in by_type.items():
            if confidences:
                stats[match_type] = {
                    'average': sum(confidences) / len(confidences),
                    'min': min(confidences),
                    'max': max(confidences),
                    'count': len(confidences)
                }
        
        return {
            'updated': True,
            'statistics': stats,
            'message': 'Confidence statistics updated'
        }
    
    def _log_learning_activity(
        self,
        activity_type: str,
        activity_name: str,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None,
        session_id: Optional[int] = None,
        result_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log learning activity"""
        log = ReconciliationLearningLog(
            activity_type=activity_type,
            activity_name=activity_name,
            property_id=property_id,
            period_id=period_id,
            session_id=session_id,
            activity_data=result_data or {},
            result_type='success',
            is_successful=True,
            triggered_by='automatic'
        )
        self.db.add(log)
        self.db.commit()
    
    def get_learned_patterns(
        self,
        source_document_type: Optional[str] = None,
        target_document_type: Optional[str] = None,
        min_success_rate: float = 70.0
    ) -> List[LearnedMatchPattern]:
        """
        Get learned patterns with filters
        
        Args:
            source_document_type: Filter by source document type
            target_document_type: Filter by target document type
            min_success_rate: Minimum success rate threshold
            
        Returns:
            List of learned patterns
        """
        query = self.db.query(LearnedMatchPattern).filter(
            and_(
                LearnedMatchPattern.is_active == True,
                LearnedMatchPattern.success_rate >= Decimal(str(min_success_rate))
            )
        )
        
        if source_document_type:
            query = query.filter(LearnedMatchPattern.source_document_type == source_document_type)
        if target_document_type:
            query = query.filter(LearnedMatchPattern.target_document_type == target_document_type)
        
        return query.order_by(
            LearnedMatchPattern.priority.desc(),
            LearnedMatchPattern.success_rate.desc()
        ).all()
    
    def get_synonyms(
        self,
        account_code: Optional[str] = None,
        account_name: Optional[str] = None
    ) -> List[AccountCodeSynonym]:
        """
        Get account code synonyms
        
        Args:
            account_code: Filter by canonical account code
            account_name: Filter by synonym name
            
        Returns:
            List of synonyms
        """
        query = self.db.query(AccountCodeSynonym).filter(
            AccountCodeSynonym.is_active == True
        )
        
        if account_code:
            query = query.filter(AccountCodeSynonym.canonical_account_code == account_code)
        if account_name:
            query = query.filter(AccountCodeSynonym.synonym_name.ilike(f"%{account_name}%"))
        
        return query.order_by(AccountCodeSynonym.combined_confidence.desc()).all()

