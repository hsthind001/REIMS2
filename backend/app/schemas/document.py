"""
Document Upload Schemas for API Request/Response
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DocumentTypeEnum(str, Enum):
    """Valid document types"""
    balance_sheet = "balance_sheet"
    income_statement = "income_statement"
    cash_flow = "cash_flow"
    rent_roll = "rent_roll"


class ExtractionStatusEnum(str, Enum):
    """Extraction processing status"""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


# Request Models

class DocumentUploadRequest(BaseModel):
    """Request model for document upload"""
    property_code: str = Field(..., description="Property code (e.g., WEND001)")
    period_year: int = Field(..., ge=2000, le=2100, description="Financial period year")
    period_month: int = Field(..., ge=1, le=12, description="Financial period month (1-12)")
    document_type: DocumentTypeEnum = Field(..., description="Type of financial document")
    
    class Config:
        schema_extra = {
            "example": {
                "property_code": "WEND001",
                "period_year": 2024,
                "period_month": 12,
                "document_type": "balance_sheet"
            }
        }


# Response Models

class DocumentUploadResponse(BaseModel):
    """Response after successful upload"""
    upload_id: int = Field(..., description="Unique upload ID")
    task_id: str = Field(..., description="Celery task ID for extraction")
    message: str = Field(default="Document uploaded successfully")
    file_path: str = Field(..., description="Storage path in MinIO")
    extraction_status: str = Field(default="pending")
    
    class Config:
        schema_extra = {
            "example": {
                "upload_id": 123,
                "task_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                "message": "Document uploaded successfully",
                "file_path": "WEND001/2024/12/balance_sheet_20241103_143022.pdf",
                "extraction_status": "pending"
            }
        }


class DocumentUploadDetail(BaseModel):
    """Detailed upload record with status"""
    id: int
    property_id: int
    period_id: int
    property_code: Optional[str] = None
    period_year: Optional[int] = None
    period_month: Optional[int] = None
    
    # Document info
    document_type: str
    file_name: str
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    file_size_bytes: Optional[int] = None
    
    # Upload tracking
    upload_date: datetime
    uploaded_by: Optional[int] = None
    
    # Extraction status
    extraction_status: str
    extraction_started_at: Optional[datetime] = None
    extraction_completed_at: Optional[datetime] = None
    extraction_id: Optional[int] = None
    
    # Extraction quality metrics (if available)
    extraction_confidence: Optional[float] = None
    extraction_quality: Optional[str] = None
    needs_review: Optional[bool] = None
    
    # Versioning
    version: int
    is_active: bool
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 123,
                "property_id": 1,
                "period_id": 45,
                "property_code": "WEND001",
                "period_year": 2024,
                "period_month": 12,
                "document_type": "balance_sheet",
                "file_name": "balance_sheet_dec_2024.pdf",
                "file_path": "WEND001/2024/12/balance_sheet_20241103_143022.pdf",
                "file_size_bytes": 1048576,
                "upload_date": "2024-11-03T14:30:22",
                "extraction_status": "completed",
                "extraction_confidence": 95.5,
                "extraction_quality": "excellent",
                "version": 1,
                "is_active": True
            }
        }


class DocumentListItem(BaseModel):
    """Simplified document info for list view"""
    id: int
    property_code: Optional[str] = None
    period_year: Optional[int] = None
    period_month: Optional[int] = None
    document_type: str
    file_name: str
    upload_date: datetime
    extraction_status: str
    extraction_confidence: Optional[float] = None
    version: int
    is_active: bool
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Paginated list of documents"""
    total: int = Field(..., description="Total number of uploads matching filters")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Maximum records returned")
    items: List[DocumentListItem] = Field(..., description="List of document uploads")
    
    class Config:
        schema_extra = {
            "example": {
                "total": 156,
                "skip": 0,
                "limit": 100,
                "items": [
                    {
                        "id": 123,
                        "property_code": "WEND001",
                        "period_year": 2024,
                        "period_month": 12,
                        "document_type": "balance_sheet",
                        "file_name": "balance_sheet_dec_2024.pdf",
                        "upload_date": "2024-11-03T14:30:22",
                        "extraction_status": "completed",
                        "extraction_confidence": 95.5,
                        "version": 1,
                        "is_active": True
                    }
                ]
            }
        }


# Financial Data Response Models

class BalanceSheetDataItem(BaseModel):
    """Balance sheet line item"""
    account_code: str
    account_name: str
    amount: float
    extraction_confidence: Optional[float] = None
    needs_review: bool = False
    
    class Config:
        from_attributes = True


class IncomeStatementDataItem(BaseModel):
    """Income statement line item"""
    account_code: str
    account_name: str
    period_amount: float
    ytd_amount: Optional[float] = None
    period_percentage: Optional[float] = None
    ytd_percentage: Optional[float] = None
    extraction_confidence: Optional[float] = None
    needs_review: bool = False
    
    class Config:
        from_attributes = True


class CashFlowDataItem(BaseModel):
    """Cash flow line item"""
    account_code: str
    account_name: str
    period_amount: float
    cash_flow_category: Optional[str] = None
    is_inflow: Optional[bool] = None
    extraction_confidence: Optional[float] = None
    needs_review: bool = False
    
    class Config:
        from_attributes = True


class RentRollDataItem(BaseModel):
    """Rent roll line item"""
    unit_number: str
    tenant_name: str
    lease_start_date: Optional[datetime] = None
    lease_end_date: Optional[datetime] = None
    unit_area_sqft: Optional[float] = None
    monthly_rent: Optional[float] = None
    annual_rent: Optional[float] = None
    occupancy_status: str
    extraction_confidence: Optional[float] = None
    needs_review: bool = False
    
    class Config:
        from_attributes = True


class FinancialMetricsData(BaseModel):
    """Calculated financial metrics"""
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    total_revenue: Optional[float] = None
    total_expenses: Optional[float] = None
    net_operating_income: Optional[float] = None
    net_income: Optional[float] = None
    occupancy_rate: Optional[float] = None
    debt_service_coverage_ratio: Optional[float] = None
    
    class Config:
        from_attributes = True


class ValidationResultItem(BaseModel):
    """Validation result for an upload"""
    rule_id: int
    rule_name: Optional[str] = None
    passed: bool
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    difference: Optional[float] = None
    difference_percentage: Optional[float] = None
    error_message: Optional[str] = None
    severity: Optional[str] = None
    
    class Config:
        from_attributes = True


class ExtractedDataResponse(BaseModel):
    """Complete extracted financial data from upload"""
    upload_id: int
    property_code: str
    period_year: int
    period_month: int
    document_type: str
    extraction_status: str
    extraction_confidence: Optional[float] = None
    
    # Financial data by type
    balance_sheet_data: List[BalanceSheetDataItem] = []
    income_statement_data: List[IncomeStatementDataItem] = []
    cash_flow_data: List[CashFlowDataItem] = []
    rent_roll_data: List[RentRollDataItem] = []
    financial_metrics: Optional[FinancialMetricsData] = None
    
    # Validation results
    validation_results: List[ValidationResultItem] = []
    validation_passed: bool = True
    validation_summary: dict = {}
    
    class Config:
        schema_extra = {
            "example": {
                "upload_id": 123,
                "property_code": "WEND001",
                "period_year": 2024,
                "period_month": 12,
                "document_type": "balance_sheet",
                "extraction_status": "completed",
                "extraction_confidence": 95.5,
                "balance_sheet_data": [
                    {
                        "account_code": "0122-0000",
                        "account_name": "Cash - Operating",
                        "amount": 211729.81,
                        "extraction_confidence": 98.0,
                        "needs_review": False
                    }
                ],
                "financial_metrics": {
                    "total_assets": 22939865.40,
                    "total_liabilities": 21769610.72,
                    "net_income": -571883.75
                },
                "validation_results": [],
                "validation_passed": True,
                "validation_summary": {
                    "total_checks": 5,
                    "passed_checks": 5,
                    "failed_checks": 0
                }
            }
        }


class DocumentDownloadResponse(BaseModel):
    """Response with presigned download URL"""
    upload_id: int
    file_name: str
    file_size_bytes: Optional[int] = None
    download_url: str = Field(..., description="Presigned URL valid for 1 hour")
    expires_in_seconds: int = Field(default=3600)
    
    class Config:
        schema_extra = {
            "example": {
                "upload_id": 123,
                "file_name": "balance_sheet_dec_2024.pdf",
                "file_size_bytes": 1048576,
                "download_url": "http://localhost:9000/reims/WEND001/2024/12/balance_sheet.pdf?...",
                "expires_in_seconds": 3600
            }
        }

