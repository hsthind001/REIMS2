"""
Quality Metrics API

Endpoints for retrieving document extraction quality metrics
"""
from fastapi import APIRouter, HTTPException, status, Query, Path, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, Integer, case
from typing import Optional
from decimal import Decimal

from app.db.database import get_db
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.rent_roll_data import RentRollData
from app.models.mortgage_statement_data import MortgageStatementData
from app.core.redis_client import cached


router = APIRouter()


def calculate_severity_level(
    match_rate: float,
    avg_confidence: float,
    critical_count: int,
    warning_count: int
) -> str:
    """
    Calculate overall severity level based on quality metrics
    
    Critical: match_rate < 99.9% OR avg_confidence < 85% OR critical_count > 0
    Warning: match_rate >= 99.9% AND avg_confidence 85-95% OR warning_count > 0
    Info: avg_confidence 95-100% AND match_rate 100% AND no critical/warning items
    Excellent: avg_confidence > 95% AND match_rate 100% AND no issues
    """
    if match_rate < 99.9 or avg_confidence < 85 or critical_count > 0:
        return "critical"
    elif match_rate < 100 or (avg_confidence >= 85 and avg_confidence < 95) or warning_count > 0:
        return "warning"
    elif avg_confidence >= 95 and match_rate == 100:
        return "excellent"
    else:
        return "info"


@router.get("/quality/document/{upload_id}")
async def get_document_quality(
    upload_id: int = Path(..., description="Document upload ID"),
    db: Session = Depends(get_db)
):
    """
    Get quality metrics for a specific document upload
    
    Returns comprehensive quality metrics including:
    - Total records extracted
    - Match rate (percentage of accounts matched to chart of accounts)
    - Average confidence score
    - Counts by severity level (critical, warning, info)
    - Overall quality assessment
    
    **Quality Thresholds:**
    - Critical: Confidence < 85%, unmatched accounts, match rate < 99.9%
    - Warning: Confidence 85-95%, match rate 99.9-100%
    - Info/Excellent: Confidence > 95%, all accounts matched
    """
    try:
        # Get upload record
        upload = db.query(DocumentUpload).filter(
            DocumentUpload.id == upload_id
        ).first()
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        # Get property and period info
        property_info = db.query(Property).filter(
            Property.id == upload.property_id
        ).first()
        
        period_info = db.query(FinancialPeriod).filter(
            FinancialPeriod.id == upload.period_id
        ).first()
        
        # Query the appropriate data table based on document type
        metrics = {
            "upload_id": upload_id,
            "property_code": property_info.property_code if property_info else None,
            "period_year": period_info.period_year if period_info else None,
            "period_month": period_info.period_month if period_info else None,
            "document_type": upload.document_type,
            "extraction_status": upload.extraction_status,
            "total_records": 0,
            "matched_records": 0,
            "match_rate": 0.0,
            "avg_confidence": 0.0,
            "min_confidence": 0.0,
            "max_confidence": 0.0,
            "needs_review_count": 0,
            "critical_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "severity_level": "info",
            "unmatched_accounts": []
        }
        
        # Select appropriate data table
        if upload.document_type == "balance_sheet":
            DataModel = BalanceSheetData
            amount_field = "amount"
        elif upload.document_type == "income_statement":
            DataModel = IncomeStatementData
            amount_field = "period_amount"
        elif upload.document_type == "cash_flow":
            DataModel = CashFlowData
            amount_field = "period_amount"
        elif upload.document_type == "rent_roll":
            DataModel = RentRollData
            amount_field = "monthly_rent"
        else:
            return metrics  # Unknown document type
        
        # Get all records for this upload
        records = db.query(DataModel).filter(
            DataModel.upload_id == upload_id
        ).all()
        
        if not records:
            return metrics  # No data yet
        
        # Calculate metrics
        total_records = len(records)
        # Rent rolls don't have account_id
        if upload.document_type == "rent_roll":
            matched_records = total_records  # All rent roll records are considered "matched"
        else:
            matched_records = sum(1 for r in records if hasattr(r, 'account_id') and r.account_id is not None)
        match_rate = (matched_records / total_records * 100) if total_records > 0 else 0
        
        # Confidence metrics
        confidences = [float(r.extraction_confidence) for r in records if r.extraction_confidence is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        min_confidence = min(confidences) if confidences else 0
        max_confidence = max(confidences) if confidences else 0
        
        # Count by severity and match strategy
        critical_count = 0
        warning_count = 0
        info_count = 0
        unmatched_accounts = []
        match_strategy_counts = {}
        
        for record in records:
            extraction_conf = float(record.extraction_confidence) if record.extraction_confidence else 0
            match_conf = float(getattr(record, 'match_confidence', 0)) if hasattr(record, 'match_confidence') and getattr(record, 'match_confidence') else 0
            match_strategy = getattr(record, 'match_strategy', 'unknown') if hasattr(record, 'match_strategy') else 'unknown'

            # Rent rolls don't have account_id
            if upload.document_type == "rent_roll":
                is_matched = True  # All rent roll records are considered matched
                validation_score = float(record.validation_score) if hasattr(record, 'validation_score') and record.validation_score else 0
            else:
                is_matched = hasattr(record, 'account_id') and record.account_id is not None

            # Count match strategies
            match_strategy_counts[match_strategy] = match_strategy_counts.get(match_strategy, 0) + 1

            # For rent rolls, use validation_score instead
            if upload.document_type == "rent_roll":
                if validation_score < 85:
                    critical_count += 1
                elif 85 <= validation_score < 95:
                    warning_count += 1
                else:
                    info_count += 1
            else:
                # Critical: extraction < 85% OR match < 95% OR unmatched
                if extraction_conf < 85 or match_conf < 95 or not is_matched:
                    critical_count += 1
                    if not is_matched:
                        unmatched_accounts.append({
                            "account_code": getattr(record, "account_code", None),
                            "account_name": getattr(record, "account_name", None),
                            "amount": float(getattr(record, amount_field, 0)),
                            "extraction_confidence": extraction_conf,
                            "match_confidence": match_conf
                        })
                # Warning: extraction 85-95% AND match 95-100%
                elif extraction_conf < 95:
                    warning_count += 1
                # Info: extraction >= 95% AND match >= 95%
                else:
                    info_count += 1

        needs_review_count = sum(1 for r in records if hasattr(r, 'needs_review') and r.needs_review)
        
        # Calculate overall severity
        severity_level = calculate_severity_level(
            match_rate, avg_confidence, critical_count, warning_count
        )
        
        # Update metrics
        metrics.update({
            "total_records": total_records,
            "matched_records": matched_records,
            "match_rate": round(match_rate, 2),
            "avg_confidence": round(avg_confidence, 2),
            "min_confidence": round(min_confidence, 2),
            "max_confidence": round(max_confidence, 2),
            "needs_review_count": needs_review_count,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "severity_level": severity_level,
            "unmatched_accounts": unmatched_accounts,
            "match_strategy_breakdown": match_strategy_counts
        })
        
        return metrics
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate quality metrics: {str(e)}"
        )


@router.get("/quality/summary")
@cached(key_prefix="quality:summary", ttl=300)
async def get_quality_summary(
    property_code: Optional[str] = Query(None, description="Filter by property code"),
    db: Session = Depends(get_db)
):
    """
    Get aggregate quality summary across all documents
    
    Optionally filter by property code to get property-specific summary.
    Returns:
    - Total documents processed
    - Overall match rate
    - Average confidence
    - Count of items by severity
    - Count of items needing review
    """
    try:
        # Build base query
        query = db.query(DocumentUpload)
        
        if property_code:
            property_obj = db.query(Property).filter(
                Property.property_code == property_code
            ).first()
            if property_obj:
                query = query.filter(DocumentUpload.property_id == property_obj.id)
        
        # Get all completed uploads
        uploads = query.filter(
            DocumentUpload.extraction_status == 'completed'
        ).all()
        
        if not uploads:
            return {
                "total_documents": 0,
                "total_records": 0,
                "overall_match_rate": 0.0,
                "overall_avg_confidence": 0.0,
                "critical_count": 0,
                "warning_count": 0,
                "info_count": 0,
                "needs_review_count": 0,
                "by_document_type": {}
            }
        
        # Aggregate across all uploads
        total_records = 0
        total_matched = 0
        all_confidences = []
        total_critical = 0
        total_warning = 0
        total_info = 0
        total_needs_review = 0
        by_doc_type = {}
        
        for upload in uploads:
            # Get data for each upload
            if upload.document_type == "balance_sheet":
                records = db.query(BalanceSheetData).filter(
                    BalanceSheetData.upload_id == upload.id
                ).all()
            elif upload.document_type == "income_statement":
                records = db.query(IncomeStatementData).filter(
                    IncomeStatementData.upload_id == upload.id
                ).all()
            elif upload.document_type == "cash_flow":
                records = db.query(CashFlowData).filter(
                    CashFlowData.upload_id == upload.id
                ).all()
            elif upload.document_type == "rent_roll":
                records = db.query(RentRollData).filter(
                    RentRollData.upload_id == upload.id
                ).all()
            elif upload.document_type == "mortgage_statement":
                records = db.query(MortgageStatementData).filter(
                    MortgageStatementData.upload_id == upload.id
                ).all()
            else:
                continue
            
            doc_type = upload.document_type
            if doc_type not in by_doc_type:
                by_doc_type[doc_type] = {
                    "count": 0,
                    "total_records": 0,
                    "matched_records": 0,
                    "avg_confidence": 0.0
                }
            
            by_doc_type[doc_type]["count"] += 1
            
            for record in records:
                total_records += 1
                by_doc_type[doc_type]["total_records"] += 1

                # Rent rolls and mortgage statements don't have account_id, skip matching logic for them
                if doc_type not in ["rent_roll", "mortgage_statement"]:
                    if hasattr(record, 'account_id') and record.account_id is not None:
                        total_matched += 1
                        by_doc_type[doc_type]["matched_records"] += 1
                else:
                    # For rent rolls and mortgage statements, consider all as "matched"
                    total_matched += 1
                    by_doc_type[doc_type]["matched_records"] += 1

                conf = float(record.extraction_confidence) if record.extraction_confidence else 0
                all_confidences.append(conf)

                # For rent rolls and mortgage statements, use extraction confidence
                if doc_type in ["rent_roll", "mortgage_statement"]:
                    validation_score = float(record.validation_score) if hasattr(record, 'validation_score') and record.validation_score else 0
                    if validation_score < 85:
                        total_critical += 1
                    elif 85 <= validation_score < 95:
                        total_warning += 1
                    else:
                        total_info += 1
                else:
                    is_matched = hasattr(record, 'account_id') and record.account_id is not None
                    # Get match confidence for non-rent-roll records
                    match_conf = float(getattr(record, 'match_confidence', 0)) if hasattr(record, 'match_confidence') and getattr(record, 'match_confidence') else 0
                    # Critical: extraction < 85% OR match < 95% OR unmatched
                    if conf < 85 or match_conf < 95 or not is_matched:
                        total_critical += 1
                    # Warning: extraction 85-95% AND match >= 95% AND matched
                    elif 85 <= conf < 95:
                        total_warning += 1
                    # Info: extraction >= 95% AND match >= 95%
                    else:
                        total_info += 1

                if hasattr(record, 'needs_review') and record.needs_review:
                    total_needs_review += 1
        
        # Calculate aggregates
        overall_match_rate = (total_matched / total_records * 100) if total_records > 0 else 0
        overall_avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
        
        # Calculate per-document-type averages
        for doc_type in by_doc_type:
            dt = by_doc_type[doc_type]
            dt["match_rate"] = (dt["matched_records"] / dt["total_records"] * 100) if dt["total_records"] > 0 else 0
        
        return {
            "total_documents": len(uploads),
            "total_records": total_records,
            "overall_match_rate": round(overall_match_rate, 2),
            "overall_avg_confidence": round(overall_avg_confidence, 2),
            "critical_count": total_critical,
            "warning_count": total_warning,
            "info_count": total_info,
            "needs_review_count": total_needs_review,
            "by_document_type": by_doc_type
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quality summary: {str(e)}"
        )


@router.get("/quality/statistics/yearly")
@cached(key_prefix="quality:stats:yearly", ttl=3600)
async def get_yearly_statistics(
    db: Session = Depends(get_db)
):
    """
    Get yearly statistics for match rates and confidence scores
    
    Returns comprehensive statistics by document type and year:
    - Balance Sheet: match %, extraction confidence, match confidence
    - Income Statement: match %, extraction confidence, match confidence
    - Cash Flow: match %, extraction confidence, match confidence
    - Rent Roll: validation score, flag counts, occupancy
    
    Response format:
    {
      "2025": {
        "balance_sheet": {
          "total_records": 48,
          "matched_records": 47,
          "match_rate": 97.9,
          "avg_extraction_confidence": 94.5,
          "avg_match_confidence": 96.2,
          "needs_review_count": 3,
          "match_strategies": {...}
        },
        ...
      },
      "2024": {...}
    }
    """
    try:
        from collections import defaultdict
        
        yearly_stats = defaultdict(lambda: {
            "balance_sheet": {},
            "income_statement": {},
            "cash_flow": {},
            "rent_roll": {}
        })
        
        # ==================== BALANCE SHEET STATISTICS ====================
        bs_query = db.query(
            FinancialPeriod.period_year,
            sql_func.count(BalanceSheetData.id).label('total_records'),
            sql_func.count(BalanceSheetData.account_id).label('matched_records'),
            sql_func.avg(BalanceSheetData.extraction_confidence).label('avg_extraction'),
            sql_func.avg(BalanceSheetData.match_confidence).label('avg_match'),
            sql_func.sum(sql_func.cast(BalanceSheetData.needs_review, Integer)).label('needs_review_count')
        ).join(
            FinancialPeriod, BalanceSheetData.period_id == FinancialPeriod.id
        ).group_by(
            FinancialPeriod.period_year
        ).all()
        
        for year, total, matched, avg_ext, avg_match, needs_review in bs_query:
            match_rate = (matched / total * 100) if total > 0 else 0
            yearly_stats[year]["balance_sheet"] = {
                "total_records": total,
                "matched_records": matched,
                "unmatched_records": total - matched,
                "match_rate": round(match_rate, 2),
                "avg_extraction_confidence": round(float(avg_ext) if avg_ext else 0, 2),
                "avg_match_confidence": round(float(avg_match) if avg_match else 0, 2),
                "needs_review_count": needs_review or 0
            }
        
        # ==================== INCOME STATEMENT STATISTICS ====================
        is_query = db.query(
            FinancialPeriod.period_year,
            sql_func.count(IncomeStatementData.id).label('total_records'),
            sql_func.count(IncomeStatementData.account_id).label('matched_records'),
            sql_func.avg(IncomeStatementData.extraction_confidence).label('avg_extraction'),
            sql_func.avg(IncomeStatementData.match_confidence).label('avg_match'),
            sql_func.sum(sql_func.cast(IncomeStatementData.needs_review, Integer)).label('needs_review_count')
        ).join(
            FinancialPeriod, IncomeStatementData.period_id == FinancialPeriod.id
        ).group_by(
            FinancialPeriod.period_year
        ).all()
        
        for year, total, matched, avg_ext, avg_match, needs_review in is_query:
            match_rate = (matched / total * 100) if total > 0 else 0
            yearly_stats[year]["income_statement"] = {
                "total_records": total,
                "matched_records": matched,
                "unmatched_records": total - matched,
                "match_rate": round(match_rate, 2),
                "avg_extraction_confidence": round(float(avg_ext) if avg_ext else 0, 2),
                "avg_match_confidence": round(float(avg_match) if avg_match else 0, 2),
                "needs_review_count": needs_review or 0
            }
        
        # ==================== CASH FLOW STATISTICS ====================
        cf_query = db.query(
            FinancialPeriod.period_year,
            sql_func.count(CashFlowData.id).label('total_records'),
            sql_func.count(CashFlowData.account_id).label('matched_records'),
            sql_func.avg(CashFlowData.extraction_confidence).label('avg_extraction'),
            sql_func.avg(CashFlowData.match_confidence).label('avg_match'),
            sql_func.sum(sql_func.cast(CashFlowData.needs_review, Integer)).label('needs_review_count')
        ).join(
            FinancialPeriod, CashFlowData.period_id == FinancialPeriod.id
        ).group_by(
            FinancialPeriod.period_year
        ).all()
        
        for year, total, matched, avg_ext, avg_match, needs_review in cf_query:
            match_rate = (matched / total * 100) if total > 0 else 0
            yearly_stats[year]["cash_flow"] = {
                "total_records": total,
                "matched_records": matched,
                "unmatched_records": total - matched,
                "match_rate": round(match_rate, 2),
                "avg_extraction_confidence": round(float(avg_ext) if avg_ext else 0, 2),
                "avg_match_confidence": round(float(avg_match) if avg_match else 0, 2),
                "needs_review_count": needs_review or 0
            }
        
        # ==================== RENT ROLL STATISTICS ====================
        rr_query = db.query(
            FinancialPeriod.period_year,
            sql_func.count(RentRollData.id).label('total_units'),
            sql_func.sum(
                case((RentRollData.occupancy_status == 'occupied', 1), else_=0)
            ).label('occupied_units'),
            sql_func.avg(RentRollData.extraction_confidence).label('avg_extraction'),
            sql_func.avg(RentRollData.validation_score).label('avg_validation'),
            sql_func.sum(RentRollData.critical_flag_count).label('total_critical'),
            sql_func.sum(RentRollData.warning_flag_count).label('total_warning'),
            sql_func.sum(sql_func.cast(RentRollData.needs_review, Integer)).label('needs_review_count')
        ).join(
            FinancialPeriod, RentRollData.period_id == FinancialPeriod.id
        ).group_by(
            FinancialPeriod.period_year
        ).all()
        
        for year, total, occupied, avg_ext, avg_val, critical, warning, needs_review in rr_query:
            occupancy_rate = (occupied / total * 100) if total > 0 else 0
            yearly_stats[year]["rent_roll"] = {
                "total_units": total,
                "occupied_units": occupied,
                "vacant_units": total - occupied,
                "occupancy_rate": round(occupancy_rate, 2),
                "avg_extraction_confidence": round(float(avg_ext) if avg_ext else 0, 2),
                "avg_validation_score": round(float(avg_val) if avg_val else 0, 2),
                "total_critical_flags": critical or 0,
                "total_warning_flags": warning or 0,
                "needs_review_count": needs_review or 0
            }
        
        # Convert defaultdict to regular dict and sort by year descending
        result = dict(sorted(yearly_stats.items(), key=lambda x: x[0], reverse=True))
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get yearly statistics: {str(e)}"
        )

