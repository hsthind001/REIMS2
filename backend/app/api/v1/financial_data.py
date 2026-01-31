"""
Financial Data Viewer API

Endpoints for viewing extracted financial data with quality indicators
"""
from fastapi import APIRouter, HTTPException, status, Query, Path, Depends
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from decimal import Decimal

from app.db.database import get_db
from app.api.dependencies import get_current_user_hybrid, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.repositories.tenant_scoped import get_upload_for_org
from app.models.document_upload import DocumentUpload
from app.models.financial_period import FinancialPeriod
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData


router = APIRouter()


def get_severity_from_confidences(extraction_conf: float, match_conf: float, is_matched: bool) -> str:
    """Calculate severity level from extraction and match confidence"""
    if extraction_conf < 85 or not is_matched:
        return "critical"
    elif match_conf < 95 or extraction_conf < 95:
        return "warning"
    else:
        return "excellent"


def format_match_strategy(strategy: str) -> Dict[str, str]:
    """Format match strategy for display"""
    strategy_info = {
        "exact_code": {"label": "Exact Code Match", "description": "Account code matched exactly"},
        "fuzzy_code": {"label": "Fuzzy Code Match", "description": "Account code matched with OCR correction"},
        "exact_name": {"label": "Exact Name Match", "description": "Account name matched exactly"},
        "fuzzy_name": {"label": "Fuzzy Name Match", "description": "Account name matched with similarity"},
        "fuzzy_name_variation": {"label": "Name Variation Match", "description": "Account name matched with abbreviation expansion"},
        "unmatched": {"label": "Unmatched", "description": "No matching account found"},
        "legacy_match": {"label": "Legacy Match", "description": "Matched before strategy tracking"},
        "unknown": {"label": "Unknown", "description": "Match strategy not recorded"}
    }
    
    return strategy_info.get(strategy, {"label": strategy.replace("_", " ").title(), "description": "Custom match strategy"})


@router.get("/financial-data/{upload_id}")
async def get_financial_data(
    upload_id: int = Path(..., description="Document upload ID"),
    filter_needs_review: Optional[bool] = Query(None, description="Filter to only items needing review"),
    filter_critical: Optional[bool] = Query(None, description="Filter to only critical items"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get extracted financial data for a specific document upload with quality indicators
    
    Returns line-by-line financial data with:
    - Extraction confidence
    - Match confidence  
    - Match strategy
    - Severity level
    - Review status
    
    Supports filtering by review status and severity level.
    """
    try:
        upload = get_upload_for_org(db, current_org.id, upload_id)
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        # Get property and period info (upload already validated for org)
        from app.models.property import Property
        property_info = db.query(Property).filter(Property.id == upload.property_id).first()
        
        period_info = db.query(FinancialPeriod).filter(
            FinancialPeriod.id == upload.period_id
        ).first()
        
        # Select appropriate data model based on document type
        if upload.document_type == "balance_sheet":
            DataModel = BalanceSheetData
            amount_fields = ["amount"]
        elif upload.document_type == "income_statement":
            DataModel = IncomeStatementData
            amount_fields = ["period_amount", "ytd_amount"]
        elif upload.document_type == "cash_flow":
            DataModel = CashFlowData
            amount_fields = ["period_amount", "ytd_amount"]
        elif upload.document_type == "rent_roll":
            DataModel = RentRollData
            amount_fields = ["monthly_rent"]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported document type: {upload.document_type}"
            )
        
        # Build query
        query = db.query(DataModel).filter(
            DataModel.upload_id == upload_id
        )
        
        # Apply filters
        if filter_needs_review is not None:
            query = query.filter(DataModel.needs_review == filter_needs_review)
        
        # Get all records (will filter critical in Python if needed)
        all_records = query.all()
        
        # Build response items
        items = []
        for record in all_records:
            extraction_conf = float(record.extraction_confidence) if record.extraction_confidence else 0.0
            match_conf = float(getattr(record, 'match_confidence', 0)) if hasattr(record, 'match_confidence') and getattr(record, 'match_confidence') else 0.0
            match_strategy = getattr(record, 'match_strategy', 'unknown') if hasattr(record, 'match_strategy') else 'unknown'
            is_matched = record.account_id is not None
            
            # Calculate severity
            severity = get_severity_from_confidences(extraction_conf, match_conf, is_matched)
            
            # Apply critical filter if requested
            if filter_critical and severity != "critical":
                continue
            
            # Get match strategy info
            strategy_info = format_match_strategy(match_strategy)
            
            # Build amounts dict
            amounts = {}
            for field in amount_fields:
                if hasattr(record, field):
                    value = getattr(record, field)
                    amounts[field] = float(value) if value is not None else None
            
            # Build item (base fields)
            item = {
                "id": record.id,
                "extraction_confidence": extraction_conf,
                "severity": severity,
                "needs_review": record.needs_review,
                "reviewed": record.reviewed,
                "review_notes": record.review_notes,
            }
            
            # Add document-type specific fields
            if upload.document_type == "rent_roll":
                # Rent roll specific fields
                import json
                validation_flags = []
                if hasattr(record, 'validation_flags_json') and record.validation_flags_json:
                    try:
                        validation_flags = json.loads(record.validation_flags_json.replace("'", '"'))
                    except:
                        validation_flags = []
                
                item.update({
                    "unit_number": getattr(record, "unit_number", None),
                    "tenant_name": getattr(record, "tenant_name", None),
                    "amounts": amounts,
                    "lease_end_date": str(getattr(record, "lease_end_date", None)) if getattr(record, "lease_end_date", None) else None,
                    "occupancy_status": getattr(record, "occupancy_status", None),
                    "validation_score": float(getattr(record, "validation_score", 0)) if hasattr(record, "validation_score") and getattr(record, "validation_score") else 0.0,
                    "validation_flags": validation_flags,
                    "critical_flag_count": getattr(record, "critical_flag_count", 0),
                    "warning_flag_count": getattr(record, "warning_flag_count", 0),
                    "info_flag_count": getattr(record, "info_flag_count", 0)
                })
            else:
                # Financial statement fields
                item.update({
                    "account_code": getattr(record, "account_code", None),
                    "account_name": getattr(record, "account_name", None),
                    "amounts": amounts,
                    "line_number": getattr(record, "line_number", None),
                    "is_subtotal": getattr(record, "is_subtotal", False),
                    "is_total": getattr(record, "is_total", False),
                    "match_confidence": match_conf,
                    "match_strategy": match_strategy,
                    "match_strategy_label": strategy_info["label"],
                    "match_strategy_description": strategy_info["description"],
                    "page_number": getattr(record, "page_number", None)
                })
            
            items.append(item)
        
        # Apply pagination
        total = len(items)
        paginated_items = items[skip:skip + limit]
        
        return {
            "upload_id": upload_id,
            "property_code": property_info.property_code if property_info else None,
            "property_name": property_info.property_name if property_info else None,
            "period_year": period_info.period_year if period_info else None,
            "period_month": period_info.period_month if period_info else None,
            "document_type": upload.document_type,
            "extraction_status": upload.extraction_status,
            "total_items": total,
            "items": paginated_items,
            "skip": skip,
            "limit": limit
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve financial data: {str(e)}"
        )


@router.get("/financial-data/{upload_id}/summary")
async def get_financial_data_summary(
    upload_id: int = Path(..., description="Document upload ID"),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for extracted financial data
    
    Returns:
    - Total items
    - Items by severity (critical, warning, excellent)
    - Items by match strategy
    - Average confidences
    - Review status counts
    """
    try:
        # Get upload
        upload = db.query(DocumentUpload).filter(
            DocumentUpload.id == upload_id
        ).first()
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        # Get data model
        if upload.document_type == "balance_sheet":
            DataModel = BalanceSheetData
        elif upload.document_type == "income_statement":
            DataModel = IncomeStatementData
        elif upload.document_type == "cash_flow":
            DataModel = CashFlowData
        elif upload.document_type == "rent_roll":
            DataModel = RentRollData
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported document type: {upload.document_type}"
            )
        
        # Get all records
        records = db.query(DataModel).filter(
            DataModel.upload_id == upload_id
        ).all()
        
        if not records:
            return {
                "upload_id": upload_id,
                "total_items": 0,
                "by_severity": {},
                "by_match_strategy": {},
                "avg_extraction_confidence": 0.0,
                "avg_match_confidence": 0.0,
                "needs_review_count": 0,
                "reviewed_count": 0
            }
        
        # Calculate statistics
        total_items = len(records)
        by_severity = {"critical": 0, "warning": 0, "excellent": 0}
        by_match_strategy = {}
        extraction_confidences = []
        match_confidences = []
        needs_review_count = 0
        reviewed_count = 0
        
        for record in records:
            extraction_conf = float(record.extraction_confidence) if record.extraction_confidence else 0.0
            match_conf = float(getattr(record, 'match_confidence', 0)) if hasattr(record, 'match_confidence') and getattr(record, 'match_confidence') else 0.0
            match_strategy = getattr(record, 'match_strategy', 'unknown') if hasattr(record, 'match_strategy') else 'unknown'
            is_matched = record.account_id is not None
            
            extraction_confidences.append(extraction_conf)
            if match_conf > 0:
                match_confidences.append(match_conf)
            
            # Count by severity
            severity = get_severity_from_confidences(extraction_conf, match_conf, is_matched)
            by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # Count by match strategy
            strategy_info = format_match_strategy(match_strategy)
            strategy_label = strategy_info["label"]
            by_match_strategy[strategy_label] = by_match_strategy.get(strategy_label, 0) + 1
            
            # Review counts
            if record.needs_review:
                needs_review_count += 1
            if record.reviewed:
                reviewed_count += 1
        
        avg_extraction_conf = sum(extraction_confidences) / len(extraction_confidences) if extraction_confidences else 0.0
        avg_match_conf = sum(match_confidences) / len(match_confidences) if match_confidences else 0.0
        
        return {
            "upload_id": upload_id,
            "total_items": total_items,
            "by_severity": by_severity,
            "by_match_strategy": by_match_strategy,
            "avg_extraction_confidence": round(avg_extraction_conf, 2),
            "avg_match_confidence": round(avg_match_conf, 2),
            "needs_review_count": needs_review_count,
            "reviewed_count": reviewed_count,
            "unreviewed_count": needs_review_count - reviewed_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate summary: {str(e)}"
        )

