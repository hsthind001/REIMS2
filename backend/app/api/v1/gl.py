"""GL ingestion endpoints (placeholder)."""

import io
import csv
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.gl_ingestion_service import GLIngestionService

router = APIRouter()


@router.post("/gl/import/csv")
def import_gl_csv(
    property_id: int = Form(...),
    period_id: Optional[int] = Form(None),
    source_system: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file")
    content = file.file.read().decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))
    service = GLIngestionService(db)
    batch = service.ingest_rows(
        reader,
        property_id=property_id,
        period_id=period_id,
        source_system=source_system,
        file_name=file.filename,
        imported_by=None,
    )
    return {
        "batch_id": batch.id,
        "record_count": batch.record_count,
        "property_id": batch.property_id,
        "period_id": batch.period_id,
    }


@router.get("/gl/batches")
def list_gl_batches(
    property_id: int,
    db: Session = Depends(get_db),
):
    rows = db.execute(
        """
        SELECT id, property_id, period_id, source_system, file_name, record_count, imported_at
        FROM gl_import_batches
        WHERE property_id = :property_id
        ORDER BY imported_at DESC
        LIMIT 50
        """,
        {"property_id": property_id},
    ).fetchall()
    return [
        {
            "id": r[0],
            "property_id": r[1],
            "period_id": r[2],
            "source_system": r[3],
            "file_name": r[4],
            "record_count": r[5],
            "imported_at": r[6],
        }
        for r in rows
    ]
