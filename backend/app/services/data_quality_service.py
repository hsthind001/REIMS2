"""
Data Quality Service

Calculates quality index for documents and periods.
Aggregates: extraction_confidence, validation_pass_rate, unmatched_accounts, manual_corrections.
"""

from typing import Dict, Optional, Any, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import logging

from app.models.data_quality import DataQualityScore
from app.models.document_upload import DocumentUpload
from app.models.chart_of_accounts import ChartOfAccounts

logger = logging.getLogger(__name__)


class DataQualityService:
    """
    Calculates data quality scores for documents and periods.
    
    Quality Index (0-100) combines:
    - Completeness (0-100)
    - Consistency (0-100)
    - Timeliness (0-100)
    - Validity (0-100)
    """
    
    def __init__(self, db: Session):
        """Initialize data quality service."""
        self.db = db
        
        # Component weights
        self.weights = {
            'completeness': 0.30,
            'consistency': 0.25,
            'timeliness': 0.20,
            'validity': 0.25
        }
    
    def calculate_quality_score(
        self,
        document_id: int,
        period_id: int,
        property_id: int
    ) -> DataQualityScore:
        """
        Calculate quality score for a document/period.
        
        Args:
            document_id: Document ID
            period_id: Period ID
            property_id: Property ID
            
        Returns:
            DataQualityScore record
        """
        # Calculate component scores
        completeness = self._calculate_completeness(document_id, period_id)
        consistency = self._calculate_consistency(document_id, period_id)
        timeliness = self._calculate_timeliness(document_id, period_id)
        validity = self._calculate_validity(document_id, period_id)
        
        # Calculate weighted quality index
        quality_index = (
            completeness * self.weights['completeness'] +
            consistency * self.weights['consistency'] +
            timeliness * self.weights['timeliness'] +
            validity * self.weights['validity']
        )
        
        # Get extraction and match confidence
        extraction_confidence = self._get_extraction_confidence(document_id)
        match_confidence = self._get_match_confidence(document_id)
        
        # Get unmatched accounts and manual corrections
        unmatched_count = self._get_unmatched_accounts_count(document_id)
        manual_corrections = self._get_manual_corrections_count(document_id)
        
        # Create or update quality score
        quality_score = self.db.query(DataQualityScore).filter(
            and_(
                DataQualityScore.document_id == document_id,
                DataQualityScore.period_id == period_id,
                DataQualityScore.property_id == property_id
            )
        ).first()
        
        if not quality_score:
            quality_score = DataQualityScore(
                document_id=document_id,
                period_id=period_id,
                property_id=property_id,
                quality_index=Decimal(str(quality_index)),
                completeness=Decimal(str(completeness)),
                consistency=Decimal(str(consistency)),
                timeliness=Decimal(str(timeliness)),
                validity=Decimal(str(validity)),
                extraction_confidence_avg=Decimal(str(extraction_confidence)) if extraction_confidence else None,
                match_confidence_avg=Decimal(str(match_confidence)) if match_confidence else None,
                unmatched_accounts_count=unmatched_count,
                manual_corrections_count=manual_corrections
            )
            self.db.add(quality_score)
        else:
            quality_score.quality_index = Decimal(str(quality_index))
            quality_score.completeness = Decimal(str(completeness))
            quality_score.consistency = Decimal(str(consistency))
            quality_score.timeliness = Decimal(str(timeliness))
            quality_score.validity = Decimal(str(validity))
            quality_score.extraction_confidence_avg = Decimal(str(extraction_confidence)) if extraction_confidence else None
            quality_score.match_confidence_avg = Decimal(str(match_confidence)) if match_confidence else None
            quality_score.unmatched_accounts_count = unmatched_count
            quality_score.manual_corrections_count = manual_corrections
            quality_score.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(quality_score)
        
        return quality_score
    
    def _calculate_completeness(self, document_id: int, period_id: int) -> float:
        """Calculate completeness score (0-100)."""
        # Get expected accounts for document type
        document = self.db.query(DocumentUpload).filter(
            DocumentUpload.id == document_id
        ).first()
        
        if not document:
            return 0.0
        
        # Get expected accounts for document type
        from app.models.chart_of_accounts import ChartOfAccounts
        expected_accounts = self.db.query(func.count(ChartOfAccounts.id)).filter(
            ChartOfAccounts.document_type == document.document_type
        ).scalar()
        
        # Get extracted accounts
        if document.document_type == 'income_statement':
            from app.models.income_statement_data import IncomeStatementData
            extracted_count = self.db.query(func.count(func.distinct(IncomeStatementData.account_code))).filter(
                IncomeStatementData.upload_id == document_id
            ).scalar()
        else:
            from app.models.balance_sheet_data import BalanceSheetData
            extracted_count = self.db.query(func.count(func.distinct(BalanceSheetData.account_code))).filter(
                BalanceSheetData.upload_id == document_id
            ).scalar()
        
        if expected_accounts == 0:
            return 100.0  # No expected accounts
        
        completeness = (extracted_count / expected_accounts) * 100
        return min(100.0, max(0.0, completeness))
    
    def _calculate_consistency(self, document_id: int, period_id: int) -> float:
        """Calculate consistency score (0-100)."""
        # Check for validation rule failures
        from app.models.validation_result import ValidationResult
        total_rules = self.db.query(func.count(ValidationResult.id)).filter(
            ValidationResult.upload_id == document_id
        ).scalar()
        
        passed_rules = self.db.query(func.count(ValidationResult.id)).filter(
            and_(
                ValidationResult.upload_id == document_id,
                ValidationResult.passed == True
            )
        ).scalar()
        
        if total_rules == 0:
            return 100.0
        
        consistency = (passed_rules / total_rules) * 100
        return min(100.0, max(0.0, consistency))
    
    def _calculate_timeliness(self, document_id: int, period_id: int) -> float:
        """Calculate timeliness score (0-100)."""
        document = self.db.query(DocumentUpload).filter(
            DocumentUpload.id == document_id
        ).first()
        
        if not document or not document.upload_date:
            return 50.0  # Default
        
        # Get period end date
        from app.models.financial_period import FinancialPeriod
        period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.id == period_id
        ).first()
        
        if not period or not period.period_end_date:
            return 50.0
        
        # Calculate days between period end and upload
        days_delay = (document.upload_date - period.period_end_date).days
        
        # Score: 0 days = 100, 30 days = 50, 60+ days = 0
        if days_delay <= 0:
            timeliness = 100.0
        elif days_delay <= 30:
            timeliness = 100.0 - (days_delay / 30.0 * 50.0)
        else:
            timeliness = max(0.0, 50.0 - ((days_delay - 30) / 30.0 * 50.0))
        
        return timeliness
    
    def _calculate_validity(self, document_id: int, period_id: int) -> float:
        """Calculate validity score (0-100)."""
        # Based on unmatched accounts and manual corrections
        unmatched = self._get_unmatched_accounts_count(document_id)
        corrections = self._get_manual_corrections_count(document_id)
        
        # Get total accounts
        document = self.db.query(DocumentUpload).filter(
            DocumentUpload.id == document_id
        ).first()
        
        if not document:
            return 0.0
        
        if document.document_type == 'income_statement':
            from app.models.income_statement_data import IncomeStatementData
            total_accounts = self.db.query(func.count(IncomeStatementData.id)).filter(
                IncomeStatementData.upload_id == document_id
            ).scalar()
        else:
            from app.models.balance_sheet_data import BalanceSheetData
            total_accounts = self.db.query(func.count(BalanceSheetData.id)).filter(
                BalanceSheetData.upload_id == document_id
            ).scalar()
        
        if total_accounts == 0:
            return 100.0
        
        # Penalize unmatched and corrections
        validity = 100.0 - ((unmatched + corrections) / total_accounts * 100.0)
        return max(0.0, validity)
    
    def _get_extraction_confidence(self, document_id: int) -> Optional[float]:
        """Get average extraction confidence."""
        # Placeholder - would get from extraction results
        return 0.95
    
    def _get_match_confidence(self, document_id: int) -> Optional[float]:
        """Get average match confidence."""
        # Placeholder - would get from matching results
        return 0.90
    
    def _get_unmatched_accounts_count(self, document_id: int) -> int:
        """Get count of unmatched accounts."""
        # Placeholder - would query unmatched accounts
        return 0
    
    def _get_manual_corrections_count(self, document_id: int) -> int:
        """Get count of manual corrections."""
        # Placeholder - would query correction history
        return 0
    
    def suppress_low_quality_anomalies(
        self,
        quality_threshold: float = 70.0
    ) -> int:
        """
        Suppress or down-weight anomalies from low-quality data.
        
        Args:
            quality_threshold: Minimum quality index (0-100)
            
        Returns:
            Number of anomalies suppressed
        """
        # Get low-quality documents
        low_quality_docs = self.db.query(DataQualityScore.document_id).filter(
            DataQualityScore.quality_index < quality_threshold
        ).distinct().all()
        
        doc_ids = [doc.document_id for doc in low_quality_docs]
        
        if not doc_ids:
            return 0
        
        # Suppress anomalies from low-quality documents
        suppressed = self.db.query(AnomalyDetection).filter(
            AnomalyDetection.document_id.in_(doc_ids)
        ).update({
            AnomalyDetection.suppressed_until: datetime.utcnow() + timedelta(days=30),
            AnomalyDetection.suppression_reason: f'Low data quality (quality_index < {quality_threshold})'
        })
        
        self.db.commit()
        
        logger.info(f"Suppressed {suppressed} anomalies from {len(doc_ids)} low-quality documents")
        
        return suppressed
