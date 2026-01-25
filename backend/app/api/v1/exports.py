"""
Export API Endpoints

Provides endpoints for exporting financial data to Excel and CSV formats
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.export_service import ExportService
from app.api.dependencies import get_current_user, get_current_organization
from app.models.user import User


router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/balance-sheet/excel")
async def export_balance_sheet_excel(
    property_code: str = Query(..., description="Property code"),
    year: int = Query(..., description="Period year"),
    month: int = Query(..., ge=1, le=12, description="Period month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org = Depends(get_current_organization)
):
    """
    Export balance sheet to Excel format
    
    Returns formatted Excel file with balance sheet data
    """
    try:
        export_service = ExportService(db)
        excel_bytes = export_service.export_balance_sheet_excel(property_code, year, month, organization_id=current_org.id)
        
        filename = f"{property_code}_Balance_Sheet_{year}_{month:02d}.xlsx"
        
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/income-statement/excel")
async def export_income_statement_excel(
    property_code: str = Query(..., description="Property code"),
    year: int = Query(..., description="Period year"),
    month: int = Query(..., ge=1, le=12, description="Period month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org = Depends(get_current_organization)
):
    """
    Export income statement to Excel format
    
    Returns formatted Excel file with income statement data
    """
    try:
        export_service = ExportService(db)
        excel_bytes = export_service.export_income_statement_excel(property_code, year, month, organization_id=current_org.id)
        
        filename = f"{property_code}_Income_Statement_{year}_{month:02d}.xlsx"
        
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/csv")
async def export_to_csv(
    property_code: str = Query(..., description="Property code"),
    year: int = Query(..., description="Period year"),
    month: int = Query(..., ge=1, le=12, description="Period month"),
    document_type: str = Query(..., description="Document type (balance_sheet, income_statement, cash_flow)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_org = Depends(get_current_organization)
):
    """
    Export financial data to CSV format
    
    Returns CSV file with financial data
    """
    try:
        export_service = ExportService(db)
        csv_bytes = export_service.export_to_csv(property_code, year, month, document_type, organization_id=current_org.id)
        
        filename = f"{property_code}_{document_type}_{year}_{month:02d}.csv"
        
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
