"""Escrow document link model for FA-MORT-4: linking escrow activity to supporting documents."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class EscrowDocumentLink(Base):
    """
    Links a supporting document to escrow activity for a property/period/type.

    Used by FA-MORT-4 to require documentation when material escrow disbursements
    (tax, insurance, reserves) are present. Escrow types: property_tax, insurance,
    reserves, general.
    """

    __tablename__ = "escrow_document_links"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey("financial_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    document_upload_id = Column(
        Integer, ForeignKey("document_uploads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    escrow_type = Column(String(50), nullable=False, index=True)  # property_tax, insurance, reserves, general

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "property_id", "period_id", "document_upload_id", "escrow_type", name="uq_escrow_link_prop_period_doc_type"
        ),
        Index("ix_escrow_document_links_property_period_type", "property_id", "period_id", "escrow_type"),
    )

    property = relationship("Property", backref="escrow_document_links")
    period = relationship("FinancialPeriod", backref="escrow_document_links")
    document_upload = relationship("DocumentUpload", backref="escrow_document_links")
