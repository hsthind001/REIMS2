"""GL ingestion service for importing transaction-level data."""

import csv
from datetime import datetime
from typing import Iterable, Dict, Any

from sqlalchemy.orm import Session

from app.models.general_ledger import GLImportBatch, GeneralLedgerEntry


class GLIngestionService:
    def __init__(self, db: Session):
        self.db = db

    def ingest_rows(
        self,
        rows: Iterable[Dict[str, Any]],
        property_id: int,
        period_id: int | None,
        source_system: str | None = None,
        file_name: str | None = None,
        imported_by: int | None = None,
    ) -> GLImportBatch:
        batch = GLImportBatch(
            property_id=property_id,
            period_id=period_id,
            source_system=source_system,
            file_name=file_name,
            imported_by=imported_by,
            record_count=0,
        )
        self.db.add(batch)
        self.db.flush()

        count = 0
        for row in rows:
            amount = row.get("amount")
            if amount in (None, ""):
                continue
            entry = GeneralLedgerEntry(
                property_id=property_id,
                period_id=period_id,
                batch_id=batch.id,
                entry_date=self._parse_date(row.get("entry_date")),
                account_code=row.get("account_code"),
                account_name=row.get("account_name"),
                amount=float(amount),
                debit_credit=row.get("debit_credit"),
                description=row.get("description"),
                vendor_name=row.get("vendor_name"),
                reference=row.get("reference"),
                transaction_id=row.get("transaction_id"),
                is_adjustment=bool(row.get("is_adjustment", False)),
            )
            self.db.add(entry)
            count += 1

        batch.record_count = count
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def ingest_csv(
        self,
        file_path: str,
        property_id: int,
        period_id: int | None,
        source_system: str | None = None,
        imported_by: int | None = None,
    ) -> GLImportBatch:
        with open(file_path, "r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return self.ingest_rows(
                reader,
                property_id=property_id,
                period_id=period_id,
                source_system=source_system,
                file_name=file_path,
                imported_by=imported_by,
            )

    @staticmethod
    def _parse_date(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.strptime(str(value), fmt).date()
            except ValueError:
                continue
        return None
