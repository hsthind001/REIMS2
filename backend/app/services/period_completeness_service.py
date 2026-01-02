"""
Period Document Completeness Service

Manages the period_document_completeness table to track which documents
have been uploaded and extracted for each property/period.

This service is called automatically when:
- Document extraction completes
- Documents are deleted
- Extraction status changes

Enables fast lookup of "complete periods" without querying multiple tables.
"""
from sqlalchemy.orm import Session
from app.models.period_document_completeness import PeriodDocumentCompleteness
from app.models.mortgage_statement_data import MortgageStatementData
from app.core.redis_client import invalidate_portfolio_cache
import logging

logger = logging.getLogger(__name__)


class PeriodCompletenessService:
    """Service for tracking document completeness per property/period"""

    def __init__(self, db: Session):
        self.db = db

    def update_document_status(
        self,
        property_id: int,
        period_id: int,
        document_type: str,
        extraction_completed: bool
    ) -> PeriodDocumentCompleteness:
        """
        Update document completeness status after extraction

        Args:
            property_id: Property ID
            period_id: Period ID
            document_type: Type of document (balance_sheet, income_statement, etc.)
            extraction_completed: True if extraction successful, False if deleted/failed

        Returns:
            Updated PeriodDocumentCompleteness record
        """
        # Get or create completeness record
        completeness = self.db.query(PeriodDocumentCompleteness).filter(
            PeriodDocumentCompleteness.property_id == property_id,
            PeriodDocumentCompleteness.period_id == period_id
        ).first()

        if not completeness:
            completeness = PeriodDocumentCompleteness(
                property_id=property_id,
                period_id=period_id
            )
            self.db.add(completeness)
            logger.info(f"Created new document completeness record: property={property_id}, period={period_id}")

        # Update document flag
        old_is_complete = completeness.is_complete
        completeness.set_document_uploaded(document_type, extraction_completed)

        # Check for mortgage data if needed
        if document_type == 'mortgage_statement' or not completeness.has_mortgage_statement:
            has_mortgage_data = self.db.query(MortgageStatementData).filter(
                MortgageStatementData.property_id == property_id,
                MortgageStatementData.period_id == period_id
            ).first() is not None

            if has_mortgage_data:
                completeness.has_mortgage_statement = True
                completeness.update_completeness()

        self.db.commit()
        self.db.refresh(completeness)

        # Log status change
        if old_is_complete != completeness.is_complete:
            if completeness.is_complete:
                logger.info(
                    f"✅ Period NOW COMPLETE: property={property_id}, period={period_id}. "
                    f"All 5 documents uploaded!"
                )
                # Invalidate portfolio cache when a period becomes complete
                invalidate_portfolio_cache()
            else:
                logger.info(
                    f"⚠️  Period incomplete: property={property_id}, period={period_id}. "
                    f"Missing: {', '.join(completeness.get_missing_documents())}"
                )
        else:
            logger.debug(
                f"Updated document completeness: property={property_id}, period={period_id}, "
                f"{document_type}={extraction_completed}, "
                f"Complete={completeness.is_complete}"
            )

        return completeness

    def check_period_complete(self, property_id: int, period_id: int) -> bool:
        """
        Check if a period has all required documents

        Args:
            property_id: Property ID
            period_id: Period ID

        Returns:
            True if period is complete, False otherwise
        """
        completeness = self.db.query(PeriodDocumentCompleteness).filter(
            PeriodDocumentCompleteness.property_id == property_id,
            PeriodDocumentCompleteness.period_id == period_id
        ).first()

        if not completeness:
            return False

        return completeness.is_complete

    def get_missing_documents(self, property_id: int, period_id: int) -> list:
        """
        Get list of missing document types for a period

        Args:
            property_id: Property ID
            period_id: Period ID

        Returns:
            List of missing document types (e.g., ['mortgage_statement', 'rent_roll'])
        """
        completeness = self.db.query(PeriodDocumentCompleteness).filter(
            PeriodDocumentCompleteness.property_id == property_id,
            PeriodDocumentCompleteness.period_id == period_id
        ).first()

        if not completeness:
            # No record exists - all documents are missing
            return ['balance_sheet', 'income_statement', 'cash_flow', 'rent_roll', 'mortgage_statement']

        return completeness.get_missing_documents()
