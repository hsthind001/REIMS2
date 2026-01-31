"""
Bulk Import API Endpoints

CSV and Excel file imports for budgets, forecasts, financial data, and chart of accounts
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from fastapi.responses import Response
from typing import Optional
import logging

from app.db.database import get_db
from app.api.dependencies import get_current_user_hybrid, get_current_organization
from app.services.bulk_import_service import BulkImportService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.user import User
from app.models.organization import Organization

# Import rate limiter
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/bulk-import", tags=["bulk_import"])
logger = logging.getLogger(__name__)


@router.post("/budgets")
@limiter.limit("5/minute")  # Rate limit: 5 bulk imports per minute per IP
async def import_budgets(
    request: Request,  # Required for rate limiter
    file: UploadFile = File(...),
    property_id: int = Form(...),
    financial_period_id: int = Form(...),
    budget_name: str = Form(...),
    budget_year: int = Form(...),
    created_by: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Import budget data from CSV/Excel file

    **File Format:** CSV or Excel (.xlsx, .xls)

    **Required Columns:**
    - account_code
    - account_name
    - budgeted_amount

    **Optional Columns:**
    - account_category
    - tolerance_percentage (default 10%)
    - tolerance_amount
    - notes

    **Example CSV:**
    ```csv
    account_code,account_name,budgeted_amount,account_category,tolerance_percentage
    4100,Rental Income,950000.00,Revenue,10.0
    5100,Property Management Fees,45000.00,Operating Expense,10.0
    5200,Utilities,28000.00,Operating Expense,15.0
    ```

    **Returns:**
    - imported: Number of records successfully imported
    - failed: Number of records that failed
    - errors: List of errors with row numbers
    """
    # Verify property and period exist and belong to org
    property = (
        db.query(Property)
        .filter(Property.id == property_id, Property.organization_id == current_org.id)
        .first()
    )
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == financial_period_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Financial period not found")

    # Validate file format
    file_format = _get_file_format(file.filename)
    if not file_format:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Use CSV or Excel (.xlsx, .xls)"
        )

    try:
        # Read file content
        content = await file.read()

        # Import budgets
        service = BulkImportService(db)
        result = service.import_budgets_from_csv(
            file_content=content,
            property_id=property_id,
            financial_period_id=financial_period_id,
            budget_name=budget_name,
            budget_year=budget_year,
            created_by=created_by,
            file_format=file_format
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Budget import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forecasts")
async def import_forecasts(
    file: UploadFile = File(...),
    property_id: int = Form(...),
    financial_period_id: int = Form(...),
    forecast_name: str = Form(...),
    forecast_year: int = Form(...),
    forecast_type: str = Form(...),
    created_by: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Import forecast data from CSV/Excel file

    **Forecast Types:**
    - original: Initial forecast
    - reforecast: Updated forecast
    - rolling: Rolling forecast

    **Required Columns:**
    - account_code
    - account_name
    - forecasted_amount

    **Optional Columns:**
    - account_category
    - tolerance_percentage (default 15%)
    - tolerance_amount
    - assumptions
    - notes
    """
    property = (
        db.query(Property)
        .filter(Property.id == property_id, Property.organization_id == current_org.id)
        .first()
    )
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == financial_period_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Financial period not found")

    # Validate forecast type
    valid_types = ["original", "reforecast", "rolling"]
    if forecast_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid forecast_type. Must be one of: {', '.join(valid_types)}"
        )

    file_format = _get_file_format(file.filename)
    if not file_format:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Use CSV or Excel (.xlsx, .xls)"
        )

    try:
        content = await file.read()

        service = BulkImportService(db)
        result = service.import_forecasts_from_csv(
            file_content=content,
            property_id=property_id,
            financial_period_id=financial_period_id,
            forecast_name=forecast_name,
            forecast_year=forecast_year,
            forecast_type=forecast_type,
            created_by=created_by,
            file_format=file_format
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Forecast import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chart-of-accounts")
async def import_chart_of_accounts(
    file: UploadFile = File(...),
    property_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Import chart of accounts from CSV/Excel file

    Updates existing accounts and creates new ones.

    **Required Columns:**
    - account_code
    - account_name
    - account_type (Asset, Liability, Equity, Revenue, Expense)

    **Optional Columns:**
    - parent_account_code
    - description
    - is_active (default true)

    **Example:**
    ```csv
    account_code,account_name,account_type,parent_account_code,description
    4000,Revenue,Revenue,,Total revenue accounts
    4100,Rental Income,Revenue,4000,Rental income from tenants
    5000,Operating Expenses,Expense,,Total operating expenses
    ```
    """
    property = (
        db.query(Property)
        .filter(Property.id == property_id, Property.organization_id == current_org.id)
        .first()
    )
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    file_format = _get_file_format(file.filename)
    if not file_format:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Use CSV or Excel (.xlsx, .xls)"
        )

    try:
        content = await file.read()

        service = BulkImportService(db)
        result = service.import_chart_of_accounts_from_csv(
            file_content=content,
            property_id=property_id,
            file_format=file_format
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Chart of accounts import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/income-statement")
async def import_income_statement(
    file: UploadFile = File(...),
    property_id: int = Form(...),
    financial_period_id: int = Form(...),
    upload_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Import income statement data from CSV/Excel file (Template v1.0 compliant)

    **Required Columns:**
    - account_code
    - account_name
    - period_amount (or amount for backward compatibility)

    **Optional Columns:**
    - ytd_amount, period_percentage, ytd_percentage
    - line_category, line_subcategory, line_number
    - is_subtotal, is_total, is_income, is_below_the_line
    - account_level, parent_account_code, extraction_confidence, notes

    **Use Cases:**
    - Bulk historical data backload
    - Import from external systems
    - Batch data entry
    """
    property = (
        db.query(Property)
        .filter(Property.id == property_id, Property.organization_id == current_org.id)
        .first()
    )
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == financial_period_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Financial period not found")

    file_format = _get_file_format(file.filename)
    if not file_format:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Use CSV or Excel (.xlsx, .xls)"
        )

    try:
        content = await file.read()

        service = BulkImportService(db)
        result = service.import_income_statement_from_csv(
            file_content=content,
            property_id=property_id,
            financial_period_id=financial_period_id,
            upload_id=upload_id,
            file_format=file_format
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Income statement import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/balance-sheet")
async def import_balance_sheet(
    file: UploadFile = File(...),
    property_id: int = Form(...),
    financial_period_id: int = Form(...),
    upload_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Import balance sheet data from CSV/Excel file (Template v1.0 compliant)

    **Required Columns:**
    - account_code
    - account_name
    - amount

    **Optional Columns:**
    - account_category, account_subcategory, is_subtotal, is_total
    - account_level, parent_account_code, is_debit, is_contra_account
    - extraction_confidence, report_title, period_ending, accounting_basis, notes
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == financial_period_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Financial period not found")

    file_format = _get_file_format(file.filename)
    if not file_format:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Use CSV or Excel (.xlsx, .xls)"
        )

    try:
        content = await file.read()

        service = BulkImportService(db)
        result = service.import_balance_sheet_from_csv(
            file_content=content,
            property_id=property_id,
            financial_period_id=financial_period_id,
            upload_id=upload_id,
            file_format=file_format
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Balance sheet import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cash-flow")
async def import_cash_flow(
    file: UploadFile = File(...),
    property_id: int = Form(...),
    financial_period_id: int = Form(...),
    upload_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Import cash flow data from CSV/Excel file (Template v1.0 compliant)

    **Required Columns:**
    - account_code
    - account_name
    - period_amount (or amount for backward compatibility)

    **Optional Columns:**
    - ytd_amount, period_percentage, ytd_percentage
    - line_section, line_category, line_subcategory, line_number
    - is_subtotal, is_total, is_inflow, cash_flow_category
    - extraction_confidence, notes
    """
    property = (
        db.query(Property)
        .filter(Property.id == property_id, Property.organization_id == current_org.id)
        .first()
    )
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == financial_period_id
    ).first()
    if not period:
        raise HTTPException(status_code=404, detail="Financial period not found")

    file_format = _get_file_format(file.filename)
    if not file_format:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Use CSV or Excel (.xlsx, .xls)"
        )

    try:
        content = await file.read()

        service = BulkImportService(db)
        result = service.import_cash_flow_from_csv(
            file_content=content,
            property_id=property_id,
            financial_period_id=financial_period_id,
            upload_id=upload_id,
            file_format=file_format
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Cash flow import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{data_type}")
def get_import_template(
    data_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get CSV template for a specific data type

    **Data Types:**
    - budget
    - forecast
    - chart_of_accounts
    - income_statement
    - balance_sheet

    **Returns:**
    - CSV file with headers and sample data

    **Example:**
    ```
    GET /bulk-import/templates/budget
    ```

    Downloads a CSV template ready to fill and upload.
    """
    valid_types = ["budget", "forecast", "chart_of_accounts", "income_statement", "balance_sheet"]

    if data_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data_type. Must be one of: {', '.join(valid_types)}"
        )

    service = BulkImportService(db)
    result = service.generate_sample_template(data_type)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    # Return CSV file
    csv_content = result["csv_example"]

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={data_type}_template.csv"
        }
    )


@router.get("/templates/{data_type}/json")
def get_template_json(
    data_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get template structure as JSON

    Returns template information without downloading a file.
    Useful for frontend applications to generate templates dynamically.
    """
    valid_types = ["budget", "forecast", "chart_of_accounts", "income_statement", "balance_sheet", "cash_flow"]

    if data_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data_type. Must be one of: {', '.join(valid_types)}"
        )

    service = BulkImportService(db)
    result = service.generate_sample_template(data_type)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.get("/supported-formats")
def get_supported_formats(
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get list of supported file formats

    Returns information about supported formats and requirements
    """
    return {
        "success": True,
        "supported_formats": [
            {
                "format": "CSV",
                "extensions": [".csv"],
                "mime_types": ["text/csv", "application/csv"],
                "max_file_size_mb": 50,
                "encoding": "UTF-8 or Latin-1",
                "notes": "Comma-separated values, headers required"
            },
            {
                "format": "Excel",
                "extensions": [".xlsx", ".xls"],
                "mime_types": [
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.ms-excel"
                ],
                "max_file_size_mb": 50,
                "notes": "First sheet will be imported, headers required"
            }
        ],
        "data_types": [
            {
                "type": "budget",
                "description": "Budget data with account-level budgeted amounts",
                "required_fields": ["account_code", "account_name", "budgeted_amount"]
            },
            {
                "type": "forecast",
                "description": "Forecast data with account-level forecasted amounts",
                "required_fields": ["account_code", "account_name", "forecasted_amount"]
            },
            {
                "type": "chart_of_accounts",
                "description": "Chart of accounts structure",
                "required_fields": ["account_code", "account_name", "account_type"]
            },
            {
                "type": "income_statement",
                "description": "Income statement financial data",
                "required_fields": ["account_code", "account_name", "amount"]
            },
            {
                "type": "balance_sheet",
                "description": "Balance sheet financial data",
                "required_fields": ["account_code", "account_name", "amount"]
            },
            {
                "type": "cash_flow",
                "description": "Cash flow statement financial data",
                "required_fields": ["account_code", "account_name", "period_amount"]
            }
        ]
    }


def _get_file_format(filename: str) -> Optional[str]:
    """
    Determine file format from filename
    """
    if filename.endswith(".csv"):
        return "csv"
    elif filename.endswith((".xlsx", ".xls")):
        return "excel"
    else:
        return None
