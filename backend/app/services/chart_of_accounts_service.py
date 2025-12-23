"""
Chart of Accounts Service

Manages account synonyms and mappings for improved matching accuracy.
Supports learning from historical approvals.
"""
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.account_synonym import AccountSynonym
from app.models.account_mapping import AccountMapping

logger = logging.getLogger(__name__)


class ChartOfAccountsService:
    """Service for managing account synonyms and mappings"""
    
    def __init__(self, db: Session):
        """
        Initialize chart of accounts service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def find_synonyms(
        self,
        account_name: str,
        account_code: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        Find synonyms for an account name
        
        Args:
            account_name: Account name to find synonyms for
            account_code: Optional account code
            
        Returns:
            List of synonym dictionaries with canonical_name and confidence
        """
        synonyms = []
        
        # Search by account name (case-insensitive)
        query = self.db.query(AccountSynonym).filter(
            and_(
                AccountSynonym.is_active == True,
                or_(
                    AccountSynonym.synonym.ilike(f'%{account_name}%'),
                    AccountSynonym.canonical_name.ilike(f'%{account_name}%')
                )
            )
        )
        
        if account_code:
            query = query.filter(
                or_(
                    AccountSynonym.account_code == account_code,
                    AccountSynonym.account_code.is_(None)
                )
            )
        
        results = query.order_by(AccountSynonym.confidence.desc()).all()
        
        for result in results:
            synonyms.append({
                'synonym': result.synonym,
                'canonical_name': result.canonical_name,
                'account_code': result.account_code,
                'confidence': float(result.confidence),
                'source': result.source
            })
        
        return synonyms
    
    def get_canonical_name(
        self,
        account_name: str,
        account_code: Optional[str] = None
    ) -> Optional[str]:
        """
        Get canonical name for an account
        
        Args:
            account_name: Account name
            account_code: Optional account code
            
        Returns:
            Canonical name or None if not found
        """
        synonyms = self.find_synonyms(account_name, account_code)
        if synonyms:
            # Return the highest confidence canonical name
            return synonyms[0]['canonical_name']
        return None
    
    def find_mapping(
        self,
        source_account_code: str,
        target_account_code: str,
        source_document_type: Optional[str] = None,
        target_document_type: Optional[str] = None
    ) -> Optional[AccountMapping]:
        """
        Find an account mapping
        
        Args:
            source_account_code: Source account code
            target_account_code: Target account code
            source_document_type: Optional source document type
            target_document_type: Optional target document type
            
        Returns:
            AccountMapping or None
        """
        query = self.db.query(AccountMapping).filter(
            and_(
                AccountMapping.source_account_code == source_account_code,
                AccountMapping.target_account_code == target_account_code,
                AccountMapping.is_active == True
            )
        )
        
        if source_document_type:
            query = query.filter(
                or_(
                    AccountMapping.source_document_type == source_document_type,
                    AccountMapping.source_document_type.is_(None)
                )
            )
        
        if target_document_type:
            query = query.filter(
                or_(
                    AccountMapping.target_document_type == target_document_type,
                    AccountMapping.target_document_type.is_(None)
                )
            )
        
        return query.order_by(AccountMapping.confidence_score.desc()).first()
    
    def suggest_mapping(
        self,
        source_account_code: str,
        source_account_name: Optional[str] = None,
        source_document_type: Optional[str] = None,
        target_document_type: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        Suggest account mappings based on historical approvals
        
        Args:
            source_account_code: Source account code
            source_account_name: Optional source account name
            target_document_type: Optional target document type
            
        Returns:
            List of suggested mappings with confidence scores
        """
        query = self.db.query(AccountMapping).filter(
            and_(
                AccountMapping.source_account_code == source_account_code,
                AccountMapping.is_active == True,
                AccountMapping.approved_count >= 3  # Only suggest if approved 3+ times
            )
        )
        
        if source_document_type:
            query = query.filter(
                or_(
                    AccountMapping.source_document_type == source_document_type,
                    AccountMapping.source_document_type.is_(None)
                )
            )
        
        if target_document_type:
            query = query.filter(
                or_(
                    AccountMapping.target_document_type == target_document_type,
                    AccountMapping.target_document_type.is_(None)
                )
            )
        
        mappings = query.order_by(
            AccountMapping.confidence_score.desc(),
            AccountMapping.approved_count.desc()
        ).limit(5).all()
        
        suggestions = []
        for mapping in mappings:
            suggestions.append({
                'target_account_code': mapping.target_account_code,
                'target_account_name': mapping.target_account_name,
                'confidence': float(mapping.confidence_score),
                'approved_count': mapping.approved_count,
                'rejected_count': mapping.rejected_count,
                'mapping_type': mapping.mapping_type
            })
        
        return suggestions
    
    def record_approval(
        self,
        source_account_code: str,
        target_account_code: str,
        source_document_type: Optional[str] = None,
        target_document_type: Optional[str] = None,
        mapping_type: str = 'exact',
        approved_by: Optional[int] = None
    ) -> AccountMapping:
        """
        Record an approval of an account mapping (learns from user decisions)
        
        Args:
            source_account_code: Source account code
            target_account_code: Target account code
            source_document_type: Optional source document type
            target_document_type: Optional target document type
            mapping_type: Mapping type (exact, fuzzy, calculated, inferred)
            approved_by: User ID who approved
            
        Returns:
            Updated or created AccountMapping
        """
        from datetime import datetime
        
        # Find existing mapping
        mapping = self.find_mapping(
            source_account_code,
            target_account_code,
            source_document_type,
            target_document_type
        )
        
        if mapping:
            # Update existing mapping
            mapping.approved_count += 1
            mapping.last_approved_at = datetime.utcnow()
            mapping.last_approved_by = approved_by
            
            # Recalculate confidence: (approved / (approved + rejected)) * 100
            total = mapping.approved_count + mapping.rejected_count
            if total > 0:
                mapping.confidence_score = Decimal((mapping.approved_count / total) * 100)
            else:
                mapping.confidence_score = Decimal('50.00')
        else:
            # Create new mapping
            mapping = AccountMapping(
                source_account_code=source_account_code,
                target_account_code=target_account_code,
                source_document_type=source_document_type,
                target_document_type=target_document_type,
                mapping_type=mapping_type,
                approved_count=1,
                rejected_count=0,
                last_approved_at=datetime.utcnow(),
                last_approved_by=approved_by,
                confidence_score=Decimal('100.00')  # First approval = 100%
            )
            self.db.add(mapping)
        
        self.db.commit()
        self.db.refresh(mapping)
        
        logger.info(f"Recorded approval for mapping {source_account_code} -> {target_account_code}")
        
        return mapping
    
    def record_rejection(
        self,
        source_account_code: str,
        target_account_code: str,
        source_document_type: Optional[str] = None,
        target_document_type: Optional[str] = None
    ) -> Optional[AccountMapping]:
        """
        Record a rejection of an account mapping
        
        Args:
            source_account_code: Source account code
            target_account_code: Target account code
            source_document_type: Optional source document type
            target_document_type: Optional target document type
            
        Returns:
            Updated AccountMapping or None if not found
        """
        mapping = self.find_mapping(
            source_account_code,
            target_account_code,
            source_document_type,
            target_document_type
        )
        
        if mapping:
            mapping.rejected_count += 1
            
            # Recalculate confidence
            total = mapping.approved_count + mapping.rejected_count
            if total > 0:
                mapping.confidence_score = Decimal((mapping.approved_count / total) * 100)
            else:
                mapping.confidence_score = Decimal('0.00')
            
            # Deactivate if confidence drops too low
            if mapping.confidence_score < Decimal('30.00'):
                mapping.is_active = False
            
            self.db.commit()
            self.db.refresh(mapping)
            
            logger.info(f"Recorded rejection for mapping {source_account_code} -> {target_account_code}")
        
        return mapping
    
    def add_synonym(
        self,
        synonym: str,
        canonical_name: str,
        account_code: Optional[str] = None,
        confidence: float = 100.0,
        source: str = 'manual'
    ) -> AccountSynonym:
        """
        Add a new account synonym
        
        Args:
            synonym: Synonym text
            canonical_name: Canonical account name
            account_code: Optional account code
            confidence: Confidence score (0-100)
            source: Source (manual or learned)
            
        Returns:
            Created AccountSynonym
        """
        # Check if synonym already exists
        existing = self.db.query(AccountSynonym).filter(
            and_(
                AccountSynonym.account_code == account_code,
                AccountSynonym.synonym == synonym
            )
        ).first()
        
        if existing:
            # Update existing
            existing.canonical_name = canonical_name
            existing.confidence = Decimal(str(confidence))
            existing.source = source
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # Create new
        synonym_obj = AccountSynonym(
            account_code=account_code,
            synonym=synonym,
            canonical_name=canonical_name,
            confidence=Decimal(str(confidence)),
            source=source
        )
        self.db.add(synonym_obj)
        self.db.commit()
        self.db.refresh(synonym_obj)
        
        return synonym_obj

