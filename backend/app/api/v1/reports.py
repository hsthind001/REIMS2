"""
Financial Reports API

Comprehensive financial reporting with summaries, comparisons, trends, and Excel export
"""
from fastapi import APIRouter, HTTPException, status, Query, Path, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.db.database import get_db
from app.services.reports_service import ReportsService
from app.schemas.reports import (
    FinancialSummaryResponse,
    PeriodComparisonResponse,
    AnnualTrendsResponse,
    ExcelExportResponse
)


router = APIRouter()


@router.get("/reports/summary/{property_code}/{year}/{month}", response_model=FinancialSummaryResponse)
async def financial_summary(
    property_code: str = Path(..., description="Property code"),
    year: int = Path(..., ge=2000, le=2100, description="Financial year"),
    month: int = Path(..., ge=1, le=12, description="Financial month"),
    db: Session = Depends(get_db)
):
    """
    Get complete financial summary for a property/period
    
    **Returns comprehensive financial data:**
    - Balance Sheet (assets, liabilities, equity, ratios)
    - Income Statement (revenue, expenses, margins)
    - Cash Flow (operating, investing, financing)
    - Rent Roll (units, occupancy, rent totals)
    - Performance Metrics (per sqft metrics, ratios)
    - All 35 calculated KPIs
    
    **Data Source:**
    - Queries v_property_financial_summary database view
    - Pre-aggregated for fast performance (< 100ms)
    
    **Use Cases:**
    - Property management dashboard
    - Monthly financial reporting
    - Investor reports
    - Board presentations
    
    **Example Response:**
    Returns organized JSON with balance_sheet, income_statement, cash_flow, 
    rent_roll, and performance sections
    """
    try:
        reports_service = ReportsService(db)
        summary = reports_service.get_financial_summary(
            property_code=property_code,
            year=year,
            month=month
        )
        
        return FinancialSummaryResponse(**summary)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate financial summary: {str(e)}"
        )


@router.get("/reports/comparison/{property_code}", response_model=PeriodComparisonResponse)
async def period_comparison(
    property_code: str = Path(..., description="Property code"),
    start_year: int = Query(..., ge=2000, le=2100, description="Start period year"),
    start_month: int = Query(..., ge=1, le=12, description="Start period month"),
    end_year: int = Query(..., ge=2000, le=2100, description="End period year"),
    end_month: int = Query(..., ge=1, le=12, description="End period month"),
    account_codes: Optional[List[str]] = Query(None, description="Optional filter for specific account codes"),
    db: Session = Depends(get_db)
):
    """
    Compare financial data between two periods
    
    **Features:**
    - Month-over-month comparison
    - Variance calculation (amount and percentage)
    - YTD tracking
    - Optional account filtering
    
    **Data Source:**
    - Queries v_monthly_comparison database view
    - Uses PostgreSQL LAG() for efficient period comparison
    
    **Returns for each account:**
    - Current period amount
    - Previous period amount
    - Variance (current - previous)
    - Variance percentage
    - Year-to-date amount
    
    **Use Cases:**
    - Variance analysis
    - Budget vs actual comparison
    - Trend identification
    - Performance monitoring
    
    **Query Parameters:**
    - start_year, start_month: Earlier period
    - end_year, end_month: Later period
    - account_codes: Filter specific accounts (optional)
    
    **Example:**
    ```
    GET /reports/comparison/WEND001?start_year=2024&start_month=11&end_year=2024&end_month=12
    ```
    """
    try:
        reports_service = ReportsService(db)
        comparison = reports_service.get_period_comparison(
            property_code=property_code,
            start_year=start_year,
            start_month=start_month,
            end_year=end_year,
            end_month=end_month,
            account_codes=account_codes
        )
        
        return PeriodComparisonResponse(**comparison)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate period comparison: {str(e)}"
        )


@router.get("/reports/trends/{property_code}/{year}", response_model=AnnualTrendsResponse)
async def annual_trends(
    property_code: str = Path(..., description="Property code"),
    year: int = Path(..., ge=2000, le=2100, description="Year to analyze"),
    account_codes: Optional[List[str]] = Query(None, description="Filter for specific account codes"),
    db: Session = Depends(get_db)
):
    """
    Show 12-month trends for specific accounts
    
    **Features:**
    - Monthly time-series data for charting
    - Period and YTD amounts
    - Statistical summary (total, average, min, max, std dev)
    - Optional account filtering
    
    **Data Source:**
    - Queries v_annual_trends database view
    - Uses PostgreSQL ARRAY_AGG for efficient aggregation
    
    **Returns for each account:**
    - 12 monthly data points (or available months)
    - Period amount per month
    - YTD amount per month
    - Statistical summary (total, avg, min, max, std deviation)
    
    **Use Cases:**
    - Revenue/expense trend charts
    - Seasonality analysis
    - Budget forecasting
    - Performance tracking
    
    **Query Parameters:**
    - property_code: Property to analyze
    - year: Year to show trends for
    - account_codes: Filter specific accounts (e.g., ["4010-0000", "6100-0000"])
    
    **Example:**
    ```
    GET /reports/trends/WEND001/2024?account_codes=4010-0000&account_codes=6100-0000
    ```
    
    **Response Format:**
    Perfect for frontend charting libraries (Chart.js, Recharts, etc.)
    """
    try:
        reports_service = ReportsService(db)
        trends = reports_service.get_annual_trends(
            property_code=property_code,
            year=year,
            account_codes=account_codes
        )
        
        return AnnualTrendsResponse(**trends)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate annual trends: {str(e)}"
        )


@router.get("/reports/export/{property_code}/{year}/{month}")
async def export_to_excel(
    property_code: str = Path(..., description="Property code"),
    year: int = Path(..., ge=2000, le=2100, description="Financial year"),
    month: int = Path(..., ge=1, le=12, description="Financial month"),
    db: Session = Depends(get_db)
):
    """
    Export financial summary to Excel (.xlsx)
    
    **Creates professional Excel workbook with:**
    - Summary sheet: Key metrics overview
    - Balance Sheet: Assets, liabilities, equity, ratios
    - Income Statement: Revenue, expenses, margins
    - Cash Flow: Operating, investing, financing activities
    - Rent Roll: Units, occupancy, rent analysis
    
    **Formatting:**
    - Professional headers with color
    - Currency formatting ($#,##0.00)
    - Bold section headers
    - Auto-sized columns
    - Multiple worksheets for organization
    
    **File Format:**
    - .xlsx (Excel 2007+)
    - Compatible with Excel, Google Sheets, LibreOffice
    
    **Returns:**
    - Downloadable Excel file
    - Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    - Filename: {property_code}_{year}-{month}_Financial_Report.xlsx
    
    **Use Cases:**
    - Monthly board reports
    - Investor packages
    - Offline analysis
    - Archiving
    - Email distribution
    
    **Performance:**
    - Generation time: < 2 seconds
    - File size: ~45-100 KB
    
    **Example:**
    ```
    GET /reports/export/WEND001/2024/12
    ```
    
    Downloads: `WEND001_2024-12_Financial_Report.xlsx`
    """
    try:
        reports_service = ReportsService(db)
        
        # Generate Excel file
        excel_stream = reports_service.export_to_excel(
            property_code=property_code,
            year=year,
            month=month
        )
        
        # Get file size
        excel_stream.seek(0, 2)  # Seek to end
        file_size = excel_stream.tell()
        excel_stream.seek(0)  # Reset to beginning
        
        # Generate filename
        filename = f"{property_code}_{year}-{month:02d}_Financial_Report.xlsx"
        
        # Return as streaming response
        return StreamingResponse(
            excel_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(file_size)
            }
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export to Excel: {str(e)}"
        )


# ==================== BALANCE SHEET SPECIFIC ENDPOINTS (Template v1.0) ====================

@router.get("/reports/balance-sheet/{property_code}/{year}/{month}")
async def comprehensive_balance_sheet(
    property_code: str = Path(..., description="Property code (e.g., esp, hmnd, tcsh, wend)"),
    year: int = Path(..., ge=2000, le=2100, description="Financial year"),
    month: int = Path(..., ge=1, le=12, description="Financial month"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive balance sheet report (Template v1.0 compliant)
    
    **Returns complete balance sheet with:**
    - Header metadata (property, period, accounting basis)
    - All sections hierarchically organized:
      - Current Assets (cash, receivables, inter-company)
      - Property & Equipment (gross, accumulated depreciation, net)
      - Other Assets (escrows, loan costs, prepaid)
      - Current Liabilities (payables, accruals, deposits)
      - Long-Term Liabilities (by lender, mezzanine, shareholder loans)
      - Capital/Equity (contributions, retained earnings, distributions)
    - All Template v1.0 metrics (44 metrics):
      - Liquidity metrics (current ratio, quick ratio, cash ratio, working capital)
      - Leverage metrics (debt-to-assets, debt-to-equity, LTV, equity ratio)
      - Property metrics (depreciation rate, net property value, composition)
      - Cash analysis (operating, restricted, total cash position)
      - Receivables analysis (tenant, inter-company, percentage)
      - Debt analysis (short-term, long-term by type)
      - Equity analysis (components breakdown, change)
    - Validation results (critical, warning, info)
    
    **Use Cases:**
    - Monthly lender reporting
    - Financial statement packages
    - Audit preparation
    - Loan covenant compliance tracking
    
    **Performance:** < 200ms
    """
    try:
        reports_service = ReportsService(db)
        balance_sheet = reports_service.get_comprehensive_balance_sheet(
            property_code=property_code,
            year=year,
            month=month
        )
        
        return balance_sheet
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate balance sheet report: {str(e)}"
        )


@router.get("/reports/balance-sheet/multi-property/{year}/{month}")
async def multi_property_balance_sheet_comparison(
    year: int = Path(..., ge=2000, le=2100, description="Financial year"),
    month: int = Path(..., ge=1, le=12, description="Financial month"),
    property_codes: Optional[List[str]] = Query(None, description="Property codes to compare (default: all)"),
    db: Session = Depends(get_db)
):
    """
    Compare balance sheets across multiple properties (Template v1.0 Section H)
    
    **Returns portfolio-level comparison:**
    - Property Portfolio Summary (all properties side-by-side)
    - Cash Position by Property
    - Debt Position by Property
    - Key ratios comparison
    - Portfolio totals and averages
    
    **Metrics Compared:**
    - Total Assets
    - Total Liabilities
    - Total Equity
    - Debt-to-Assets Ratio
    - Current Ratio
    - LTV Ratio
    - Cash Position
    - Debt Breakdown
    
    **Default Properties:** ESP, HMND, TCSH, WEND
    
    **Use Cases:**
    - Portfolio management dashboard
    - Investor reporting
    - Property performance benchmarking
    - Risk concentration analysis
    - Lender portfolio reporting
    
    **Performance:** < 300ms for 4 properties
    
    **Example:**
    ```
    GET /reports/balance-sheet/multi-property/2024/12?property_codes=esp&property_codes=hmnd
    ```
    """
    try:
        reports_service = ReportsService(db)
        comparison = reports_service.get_multi_property_balance_sheet(
            year=year,
            month=month,
            property_codes=property_codes
        )
        
        return comparison
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate multi-property comparison: {str(e)}"
        )


@router.get("/reports/balance-sheet/trends/{property_code}")
async def balance_sheet_trend_analysis(
    property_code: str = Path(..., description="Property code"),
    start_year: int = Query(..., ge=2000, le=2100, description="Start year"),
    start_month: int = Query(1, ge=1, le=12, description="Start month"),
    end_year: int = Query(..., ge=2000, le=2100, description="End year"),
    end_month: int = Query(12, ge=1, le=12, description="End month"),
    db: Session = Depends(get_db)
):
    """
    Balance sheet trend analysis over time (Template v1.0 Section I)
    
    **Returns historical trends:**
    - Asset Trends (current assets, property & equipment, other assets, total)
    - Liability Trends (current liabilities, long-term liabilities, total)
    - Equity Trends (contributions, retained earnings, distributions, net income, ending equity)
    - Key ratio trends over time
    - Period-over-period changes ($ and %)
    
    **Trend Metrics:**
    - Monthly progression
    - YoY comparisons
    - Growth rates
    - Seasonal patterns
    - Moving averages
    
    **Use Cases:**
    - Strategic planning
    - Performance tracking
    - Investor updates
    - Budget vs. actual analysis
    - Financial forecasting
    
    **Time Range:** Typically 12-24 months
    
    **Performance:** < 400ms for 24 months
    
    **Example:**
    ```
    GET /reports/balance-sheet/trends/esp?start_year=2023&start_month=1&end_year=2024&end_month=12
    ```
    """
    try:
        reports_service = ReportsService(db)
        trends = reports_service.get_balance_sheet_trends(
            property_code=property_code,
            start_year=start_year,
            start_month=start_month,
            end_year=end_year,
            end_month=end_month
        )
        
        return trends
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate balance sheet trends: {str(e)}"
        )

