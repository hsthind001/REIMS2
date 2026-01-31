"""
Concordance Table API Endpoints

Provides endpoints for viewing and exporting concordance tables
comparing extraction results across all models.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.responses import Response
from typing import Optional
import logging

from app.db.database import get_db
from app.api.dependencies import get_current_user_hybrid, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.repositories.tenant_scoped import get_upload_for_org
from app.services.concordance_service import ConcordanceService

router = APIRouter(prefix="/concordance", tags=["concordance"])
logger = logging.getLogger(__name__)


@router.get("/{upload_id}")
async def get_concordance_table(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get concordance table for a document upload
    
    Returns field-by-field comparison showing values from each model
    and agreement percentages.
    
    **Response Format:**
    ```json
    {
        "success": true,
        "upload_id": 45,
        "concordance_table": [
            {
                "field": "account_4010_0000",
                "field_display_name": "Base Rentals",
                "account_code": "4010-0000",
                "values": {
                    "pymupdf": "$215,671.29",
                    "pdfplumber": "$215,671.29",
                    "camelot": "$215,671.29",
                    "layoutlm": "$215,671.29",
                    "easyocr": "$215,671.29",
                    "tesseract": "$215,671.29"
                },
                "agreement_percentage": 100.0,
                "has_consensus": true,
                "is_perfect_agreement": true,
                "conflicting_models": [],
                "final_value": "215671.29",
                "final_model": "pymupdf"
            },
            ...
        ],
        "summary": {
            "total_fields": 45,
            "perfect_agreement": 40,
            "partial_agreement": 5,
            "no_agreement": 0,
            "overall_agreement_percentage": 95.5
        }
    }
    ```
    """
    upload = get_upload_for_org(db, current_org.id, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    service = ConcordanceService(db)
    result = service.get_concordance_table(upload_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get concordance table"))
    
    return result


@router.get("/{upload_id}/export/csv")
async def export_concordance_table_csv(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Export concordance table as CSV
    
    Returns CSV file with field-by-field comparison across all models.
    """
    upload = get_upload_for_org(db, current_org.id, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    service = ConcordanceService(db)
    csv_content = service.export_concordance_table_csv(upload_id)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=concordance_table_{upload_id}.csv"
        }
    )


@router.get("/{upload_id}/export/excel")
async def export_concordance_table_excel(
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Export concordance table as Excel
    
    Returns Excel file with field-by-field comparison and formatting.
    """
    try:
        import pandas as pd
        import io
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="pandas and openpyxl are required for Excel export. Install with: pip install pandas openpyxl"
        )

    upload = get_upload_for_org(db, current_org.id, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    service = ConcordanceService(db)
    result = service.get_concordance_table(upload_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    # Convert to DataFrame
    rows = []
    for record in result["concordance_table"]:
        values = record["values"]
        row = {
            "Field Name": record.get("field_name") or record.get("field", ""),
            "Display Name": record["field_display_name"],
            "Account Code": record.get("account_code", ""),
            "PyMuPDF": values.get("pymupdf", "") or "",
            "PDFPlumber": values.get("pdfplumber", "") or "",
            "Camelot": values.get("camelot", "") or "",
            "LayoutLMv3": values.get("layoutlm", "") or "",
            "EasyOCR": values.get("easyocr", "") or "",
            "Tesseract": values.get("tesseract", "") or "",
            "Final Value": record["final_value"] or "",
            "Agreement %": f"{record['agreement_percentage']:.1f}%",
            "Consensus": "✅" if record["has_consensus"] else "⚠️",
            "Conflicting Models": ", ".join(record["conflicting_models"])
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Concordance Table', index=False)
    
    output.seek(0)
    
    return Response(
        content=output.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=concordance_table_{upload_id}.xlsx"
        }
    )

