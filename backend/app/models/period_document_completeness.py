"""
Period Document Completeness Model

Tracks which document types have been uploaded and extracted for each property/period.
Enables fast lookup of "complete periods" without querying multiple tables.

Optimizes portfolio DSCR calculation from 261 queries to ~15 queries.
"""
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class PeriodDocumentCompleteness(Base):
    """
    Materialized summary of document completeness per property/period

    This table is automatically updated when:
    - Documents are uploaded and extraction completes
    - Documents are deleted
    - Extraction status changes

    Performance benefit: Eliminates need to query document_uploads
    and check extraction status for every period when finding
    "complete periods" for DSCR calculations.
    """

    __tablename__ = "period_document_completeness"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=False, index=True)

    # Document availability flags
    has_balance_sheet = Column(Boolean, default=False, nullable=False)
    has_income_statement = Column(Boolean, default=False, nullable=False)
    has_cash_flow = Column(Boolean, default=False, nullable=False)
    has_rent_roll = Column(Boolean, default=False, nullable=False)
    has_mortgage_statement = Column(Boolean, default=False, nullable=False)

    # Derived completeness flag (useful for querying)
    # Note: This is computed in application code, not as a generated column
    # to maintain compatibility with SQLite (for tests) and PostgreSQL
    is_complete = Column(Boolean, default=False, nullable=False, index=True)

    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Unique constraint - one record per property/period
    __table_args__ = (
        UniqueConstraint('property_id', 'period_id', name='uq_completeness_property_period'),
        # Composite index for finding complete periods efficiently
        Index('idx_complete_periods', 'property_id', 'period_id', 'is_complete'),
        # Index for finding latest complete period per property
        Index('idx_property_complete_lookup', 'property_id', 'is_complete', 'period_id'),
    )

    # Relationships
    property = relationship("Property", back_populates="document_completeness")
    period = relationship("FinancialPeriod", back_populates="document_completeness")

    def update_completeness(self):
        """
        Update is_complete flag based on individual document flags

        A period is complete when ALL required documents exist:
        - Balance Sheet
        - Income Statement
        - Cash Flow
        - Rent Roll
        - Mortgage Statement
        """
        self.is_complete = (
            self.has_balance_sheet and
            self.has_income_statement and
            self.has_cash_flow and
            self.has_rent_roll and
            self.has_mortgage_statement
        )

    def set_document_uploaded(self, document_type: str, uploaded: bool = True):
        """
        Update document flag for a specific document type

        Args:
            document_type: One of: balance_sheet, income_statement, cash_flow,
                          rent_roll, mortgage_statement
            uploaded: True if document extracted successfully, False if deleted/failed
        """
        document_type = document_type.lower()

        if document_type == 'balance_sheet':
            self.has_balance_sheet = uploaded
        elif document_type == 'income_statement':
            self.has_income_statement = uploaded
        elif document_type == 'cash_flow':
            self.has_cash_flow = uploaded
        elif document_type == 'rent_roll':
            self.has_rent_roll = uploaded
        elif document_type == 'mortgage_statement':
            self.has_mortgage_statement = uploaded
        else:
            # Unknown document type - ignore
            pass

        # Recalculate completeness
        self.update_completeness()

    def get_missing_documents(self) -> list:
        """
        Get list of missing document types

        Returns:
            List of document types that haven't been uploaded yet
        """
        missing = []

        if not self.has_balance_sheet:
            missing.append('balance_sheet')
        if not self.has_income_statement:
            missing.append('income_statement')
        if not self.has_cash_flow:
            missing.append('cash_flow')
        if not self.has_rent_roll:
            missing.append('rent_roll')
        if not self.has_mortgage_statement:
            missing.append('mortgage_statement')

        return missing

    def __repr__(self):
        status = "COMPLETE" if self.is_complete else f"INCOMPLETE ({len(self.get_missing_documents())} missing)"
        return f"<PeriodDocumentCompleteness property_id={self.property_id} period_id={self.period_id} {status}>"
