"""
General Ledger models for GL ingestion and forensic analysis.
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Numeric, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class GLImportBatch(Base):
    __tablename__ = "gl_import_batches"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey("financial_periods.id", ondelete="CASCADE"), nullable=True, index=True)
    source_system = Column(String(100), nullable=True)
    file_name = Column(String(255), nullable=True)
    imported_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    record_count = Column(Integer, default=0)
    imported_at = Column(DateTime(timezone=True), server_default=func.now())

    entries = relationship("GeneralLedgerEntry", back_populates="batch", cascade="all, delete-orphan")


class GeneralLedgerEntry(Base):
    __tablename__ = "general_ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    period_id = Column(Integer, ForeignKey("financial_periods.id", ondelete="CASCADE"), nullable=True, index=True)
    batch_id = Column(Integer, ForeignKey("gl_import_batches.id", ondelete="SET NULL"), nullable=True, index=True)

    entry_date = Column(Date, nullable=True)
    account_code = Column(String(50), nullable=True, index=True)
    account_name = Column(String(255), nullable=True)
    amount = Column(Numeric(15, 2), nullable=False)
    debit_credit = Column(String(10), nullable=True)  # debit/credit
    description = Column(Text, nullable=True)
    vendor_name = Column(String(255), nullable=True)
    reference = Column(String(255), nullable=True)
    transaction_id = Column(String(255), nullable=True)
    is_adjustment = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    batch = relationship("GLImportBatch", back_populates="entries")


Index("ix_gl_property_period", GeneralLedgerEntry.property_id, GeneralLedgerEntry.period_id)
Index("ix_gl_account", GeneralLedgerEntry.account_code)
Index("ix_gl_entry_date", GeneralLedgerEntry.entry_date)
