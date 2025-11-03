"""
Review Workflow Pydantic Schemas

Request and response models for the review workflow API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class ReviewQueueItem(BaseModel):
    """Single item in the review queue"""
    record_id: int
    table_name: str
    property_code: str
    property_name: str
    period_year: int
    period_month: int
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    unit_number: Optional[str] = None
    amount: Optional[float] = None
    period_amount: Optional[float] = None
    monthly_rent: Optional[float] = None
    extraction_confidence: Optional[float] = None
    needs_review: bool
    reviewed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "record_id": 123,
                "table_name": "balance_sheet_data",
                "property_code": "WEND001",
                "property_name": "Wendover Commons",
                "period_year": 2024,
                "period_month": 12,
                "account_code": "1010-0000",
                "account_name": "Cash - Operating",
                "unit_number": None,
                "amount": 50000.00,
                "extraction_confidence": 95.5,
                "needs_review": True,
                "reviewed": False,
                "created_at": "2024-12-01T10:00:00Z"
            }
        }


class ReviewQueueResponse(BaseModel):
    """Response for review queue listing"""
    items: List[ReviewQueueItem]
    total: int = Field(..., description="Total number of items needing review")
    skip: int = Field(..., description="Number of items skipped (pagination)")
    limit: int = Field(..., description="Maximum items returned")
    has_more: bool = Field(..., description="Whether more items exist beyond this page")
    
    class Config:
        schema_extra = {
            "example": {
                "items": [],
                "total": 25,
                "skip": 0,
                "limit": 100,
                "has_more": False
            }
        }


class ApproveRecordRequest(BaseModel):
    """Request to approve a record"""
    table_name: str = Field(..., description="Table name (balance_sheet_data, income_statement_data, etc.)")
    notes: Optional[str] = Field(None, description="Optional approval notes")
    
    class Config:
        schema_extra = {
            "example": {
                "table_name": "balance_sheet_data",
                "notes": "Verified against source document - amounts correct"
            }
        }


class ApproveRecordResponse(BaseModel):
    """Response after approving a record"""
    success: bool
    message: str
    record_id: int
    table_name: str
    reviewed_at: Optional[datetime] = None
    audit_trail_id: Optional[int] = None
    already_reviewed: Optional[bool] = False
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "success": True,
                "message": "Record approved",
                "record_id": 123,
                "table_name": "balance_sheet_data",
                "reviewed_at": "2024-12-01T10:30:00Z",
                "audit_trail_id": 456,
                "already_reviewed": False
            }
        }


class CorrectRecordRequest(BaseModel):
    """Request to correct field values in a record"""
    table_name: str = Field(..., description="Table name (balance_sheet_data, income_statement_data, etc.)")
    corrections: Dict[str, Any] = Field(
        ..., 
        description="Dictionary of field_name: new_value pairs. Supports numeric and text fields."
    )
    notes: Optional[str] = Field(None, description="Reason for correction")
    recalculate_metrics: bool = Field(True, description="Whether to trigger metrics recalculation")
    
    class Config:
        schema_extra = {
            "example": {
                "table_name": "balance_sheet_data",
                "corrections": {
                    "amount": 52000.00,
                    "account_name": "Cash - Operating Account"
                },
                "notes": "Corrected amount based on bank statement verification",
                "recalculate_metrics": True
            }
        }


class CorrectRecordResponse(BaseModel):
    """Response after correcting a record"""
    success: bool
    message: str
    record_id: int
    table_name: str
    changed_fields: List[str]
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]
    reviewed_at: Optional[datetime] = None
    audit_trail_id: Optional[int] = None
    metrics_recalculated: bool = False
    metrics_calculated: Optional[int] = None
    metrics_error: Optional[str] = None
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "success": True,
                "message": "Corrected 2 field(s)",
                "record_id": 123,
                "table_name": "balance_sheet_data",
                "changed_fields": ["amount", "account_name"],
                "old_values": {
                    "amount": 50000.00,
                    "account_name": "Cash - Operating"
                },
                "new_values": {
                    "amount": 52000.00,
                    "account_name": "Cash - Operating Account"
                },
                "reviewed_at": "2024-12-01T10:35:00Z",
                "audit_trail_id": 457,
                "metrics_recalculated": True,
                "metrics_calculated": 18
            }
        }


class RecordDetailResponse(BaseModel):
    """Detailed information about a record"""
    record_id: int
    table_name: str
    property_code: str
    property_name: str
    period_year: int
    period_month: int
    needs_review: bool
    reviewed: bool
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    extraction_confidence: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Additional fields will be dynamically added based on table
    
    class Config:
        extra = "allow"  # Allow additional fields from the model
        from_attributes = True
        schema_extra = {
            "example": {
                "record_id": 123,
                "table_name": "balance_sheet_data",
                "property_code": "WEND001",
                "property_name": "Wendover Commons",
                "period_year": 2024,
                "period_month": 12,
                "needs_review": True,
                "reviewed": False,
                "reviewed_by": None,
                "reviewed_at": None,
                "review_notes": None,
                "extraction_confidence": 95.5,
                "created_at": "2024-12-01T10:00:00Z",
                "updated_at": None,
                "account_code": "1010-0000",
                "account_name": "Cash - Operating",
                "amount": 50000.00
            }
        }


class ReviewSummaryResponse(BaseModel):
    """Summary statistics for review workflow"""
    total_needs_review: int = Field(..., description="Total records needing review")
    by_table: Dict[str, int] = Field(..., description="Count by table name")
    by_property: Dict[str, int] = Field(..., description="Count by property code")
    avg_confidence: Optional[float] = Field(None, description="Average extraction confidence")
    
    class Config:
        schema_extra = {
            "example": {
                "total_needs_review": 25,
                "by_table": {
                    "balance_sheet_data": 10,
                    "income_statement_data": 8,
                    "cash_flow_data": 5,
                    "rent_roll_data": 2
                },
                "by_property": {
                    "WEND001": 15,
                    "ESP001": 10
                },
                "avg_confidence": 92.5
            }
        }

