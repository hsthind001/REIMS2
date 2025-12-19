"""
Validations API - Query and manage financial data validation results
"""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy import func, case

from app.db.database import get_db
from app.services.validation_service import ValidationService
from app.models.document_upload import DocumentUpload
from app.models.validation_rule import ValidationRule
from app.models.validation_result import ValidationResult


router = APIRouter()


# Response Models

class ValidationSummaryResponse(BaseModel):
    """Quick summary of validation results"""
    upload_id: int
    total_checks: int
    passed_checks: int
    failed_checks: int
    warnings: int
    errors: int
    overall_passed: bool
    
    class Config:
        schema_extra = {
            "example": {
                "upload_id": 123,
                "total_checks": 10,
                "passed_checks": 8,
                "failed_checks": 2,
                "warnings": 1,
                "errors": 1,
                "overall_passed": False
            }
        }


class ValidationDetailItem(BaseModel):
    """Detailed validation result"""
    id: int
    rule_id: int
    rule_name: Optional[str] = None
    rule_description: Optional[str] = None
    passed: bool
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    difference: Optional[float] = None
    difference_percentage: Optional[float] = None
    error_message: Optional[str] = None
    severity: str
    
    class Config:
        from_attributes = True


class ValidationDetailResponse(BaseModel):
    """Complete validation results with details"""
    upload_id: int
    property_code: Optional[str] = None
    document_type: str
    extraction_status: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    warnings: int
    errors: int
    overall_passed: bool
    validation_results: List[ValidationDetailItem]
    
    class Config:
        schema_extra = {
            "example": {
                "upload_id": 123,
                "property_code": "WEND001",
                "document_type": "balance_sheet",
                "extraction_status": "completed",
                "total_checks": 5,
                "passed_checks": 4,
                "failed_checks": 1,
                "warnings": 0,
                "errors": 1,
                "overall_passed": False,
                "validation_results": [
                    {
                        "id": 1,
                        "rule_id": 1,
                        "rule_name": "balance_sheet_equation",
                        "passed": False,
                        "expected_value": 22939865.40,
                        "actual_value": 22939870.00,
                        "difference": 4.60,
                        "difference_percentage": 0.00002,
                        "error_message": "Assets don't equal Liabilities + Equity",
                        "severity": "error"
                    }
                ]
            }
        }


class ValidationRuleItem(BaseModel):
    """Validation rule definition"""
    id: int
    rule_name: str
    rule_description: Optional[str] = None
    document_type: str
    rule_type: str
    rule_formula: Optional[str] = None
    severity: str
    is_active: bool
    
    class Config:
        from_attributes = True


class RuleStatisticsItem(BaseModel):
    """Rule statistics for dashboard"""
    rule_id: int
    rule_name: str
    rule_description: Optional[str] = None
    document_type: str
    rule_type: str
    severity: str
    is_active: bool
    total_tests: int
    passed_count: int
    failed_count: int
    pass_rate: float
    last_executed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class RuleStatisticsSummary(BaseModel):
    """Summary statistics for all rules"""
    total_rules: int
    active_rules: int
    total_checks: int
    overall_pass_rate: float
    critical_failures: int
    warnings: int
    errors: int


class RuleStatisticsResponse(BaseModel):
    """Response with rule statistics and summary"""
    rules: List[RuleStatisticsItem]
    summary: RuleStatisticsSummary


class PassRateTrend(BaseModel):
    """Pass rate trend data point"""
    date: str
    pass_rate: float
    total_tests: int


class FailureDistribution(BaseModel):
    """Failure distribution by category"""
    severity: Optional[str] = None
    document_type: Optional[str] = None
    count: int
    percentage: float


class TopFailingRule(BaseModel):
    """Top failing rule information"""
    rule_id: int
    rule_name: str
    document_type: str
    failure_count: int
    failure_rate: float
    total_tests: int


class DocumentTypePerformance(BaseModel):
    """Performance metrics by document type"""
    document_type: str
    total_rules: int
    total_tests: int
    pass_rate: float
    failure_count: int


class ValidationAnalyticsResponse(BaseModel):
    """Comprehensive analytics response"""
    pass_rate_trends: Dict[str, List[PassRateTrend]]  # Key: '7d', '30d', '90d'
    failure_distribution: List[FailureDistribution]
    top_failing_rules: List[TopFailingRule]
    document_type_performance: List[DocumentTypePerformance]


class ValidationRunResponse(BaseModel):
    """Response after running validation"""
    upload_id: int
    success: bool
    message: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    overall_passed: bool


# Endpoints

# IMPORTANT: More specific routes must come BEFORE parameterized routes
# Order matters in FastAPI routing!

@router.get("/validations/analytics", response_model=ValidationAnalyticsResponse)
async def get_validation_analytics(
    days: int = Query(90, ge=7, le=365, description="Number of days for trend analysis"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive validation analytics
    
    Returns:
    - Pass rate trends over time (7, 30, 90 days)
    - Failure distribution by severity and document type
    - Top failing rules
    - Document type performance metrics
    """
    try:
        from collections import defaultdict
        
        # Calculate date ranges
        now = datetime.now()
        date_ranges = {
            '7d': now - timedelta(days=7),
            '30d': now - timedelta(days=30),
            '90d': now - timedelta(days=90)
        }
        
        # 1. Pass Rate Trends Over Time
        pass_rate_trends = {}
        for period_name, start_date in date_ranges.items():
            # Get daily pass rates
            daily_stats = db.query(
                func.date(ValidationResult.created_at).label('date'),
                func.count(ValidationResult.id).label('total_tests'),
                func.sum(case((ValidationResult.passed == True, 1), else_=0)).label('passed_count')
            ).filter(
                ValidationResult.created_at >= start_date
            ).group_by(
                func.date(ValidationResult.created_at)
            ).order_by(
                func.date(ValidationResult.created_at)
            ).all()
            
            trends = []
            for date_obj, total, passed in daily_stats:
                pass_rate = (passed / total * 100) if total > 0 else 0.0
                trends.append(PassRateTrend(
                    date=date_obj.isoformat(),
                    pass_rate=round(pass_rate, 2),
                    total_tests=int(total or 0)
                ))
            
            pass_rate_trends[period_name] = trends
        
        # 2. Failure Distribution by Severity and Document Type
        failure_distribution = []
        
        # By severity
        severity_failures = db.query(
            ValidationResult.severity,
            func.count(ValidationResult.id).label('count')
        ).filter(
            ValidationResult.passed == False
        ).group_by(
            ValidationResult.severity
        ).all()
        
        total_failures = sum(count for _, count in severity_failures)
        
        for severity, count in severity_failures:
            if total_failures > 0:
                failure_distribution.append(FailureDistribution(
                    severity=severity,
                    document_type=None,
                    count=int(count),
                    percentage=round((count / total_failures * 100), 2)
                ))
        
        # By document type
        doc_type_failures = db.query(
            ValidationRule.document_type,
            func.count(ValidationResult.id).label('count')
        ).join(
            ValidationResult, ValidationResult.rule_id == ValidationRule.id
        ).filter(
            ValidationResult.passed == False
        ).group_by(
            ValidationRule.document_type
        ).all()
        
        for doc_type, count in doc_type_failures:
            if total_failures > 0:
                failure_distribution.append(FailureDistribution(
                    severity=None,
                    document_type=doc_type,
                    count=int(count),
                    percentage=round((count / total_failures * 100), 2)
                ))
        
        # 3. Top Failing Rules (by failure rate)
        top_failing = db.query(
            ValidationRule.id,
            ValidationRule.rule_name,
            ValidationRule.document_type,
            func.count(ValidationResult.id).label('total_tests'),
            func.sum(case((ValidationResult.passed == False, 1), else_=0)).label('failure_count')
        ).join(
            ValidationResult, ValidationResult.rule_id == ValidationRule.id
        ).group_by(
            ValidationRule.id,
            ValidationRule.rule_name,
            ValidationRule.document_type
        ).having(
            func.count(ValidationResult.id) > 0
        ).order_by(
            (func.sum(case((ValidationResult.passed == False, 1), else_=0)) / func.count(ValidationResult.id)).desc()
        ).limit(10).all()
        
        top_failing_rules = []
        for rule_id, rule_name, doc_type, total, failures in top_failing:
            failure_rate = (failures / total * 100) if total > 0 else 0.0
            top_failing_rules.append(TopFailingRule(
                rule_id=rule_id,
                rule_name=rule_name,
                document_type=doc_type,
                failure_count=int(failures or 0),
                failure_rate=round(failure_rate, 2),
                total_tests=int(total or 0)
            ))
        
        # 4. Document Type Performance
        doc_performance = db.query(
            ValidationRule.document_type,
            func.count(func.distinct(ValidationRule.id)).label('total_rules'),
            func.count(ValidationResult.id).label('total_tests'),
            func.sum(case((ValidationResult.passed == True, 1), else_=0)).label('passed_count'),
            func.sum(case((ValidationResult.passed == False, 1), else_=0)).label('failure_count')
        ).join(
            ValidationResult, ValidationResult.rule_id == ValidationRule.id
        ).group_by(
            ValidationRule.document_type
        ).all()
        
        document_type_performance = []
        for doc_type, total_rules, total_tests, passed, failures in doc_performance:
            pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0.0
            document_type_performance.append(DocumentTypePerformance(
                document_type=doc_type,
                total_rules=int(total_rules or 0),
                total_tests=int(total_tests or 0),
                pass_rate=round(pass_rate, 2),
                failure_count=int(failures or 0)
            ))
        
        return ValidationAnalyticsResponse(
            pass_rate_trends=pass_rate_trends,
            failure_distribution=failure_distribution,
            top_failing_rules=top_failing_rules,
            document_type_performance=document_type_performance
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get validation analytics: {str(e)}"
        )


@router.get("/validations/rules", response_model=List[ValidationRuleItem])
async def list_validation_rules(
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    severity: Optional[str] = Query(None, description="Filter by severity (error, warning, info)"),
    db: Session = Depends(get_db)
):
    """
    List all available validation rules
    
    Filters:
    - document_type: balance_sheet, income_statement, cash_flow, rent_roll, cross_statement
    - is_active: Only active rules
    - severity: error, warning, info
    
    Returns:
    - List of all validation rules with specifications
    """
    try:
        query = db.query(ValidationRule)
        
        if document_type:
            query = query.filter(ValidationRule.document_type == document_type)
        
        if is_active is not None:
            query = query.filter(ValidationRule.is_active == is_active)
        
        if severity:
            query = query.filter(ValidationRule.severity == severity)
        
        rules = query.order_by(ValidationRule.document_type, ValidationRule.id).all()
        
        return [
            ValidationRuleItem(
                id=rule.id,
                rule_name=rule.rule_name,
                rule_description=rule.rule_description,
                document_type=rule.document_type,
                rule_type=rule.rule_type,
                rule_formula=rule.rule_formula,
                severity=rule.severity,
                is_active=rule.is_active
            )
            for rule in rules
        ]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list validation rules: {str(e)}"
        )


@router.get("/validations/rules/statistics", response_model=RuleStatisticsResponse)
async def get_rule_statistics(
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    date_from: Optional[str] = Query(None, description="Filter results from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter results to date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated statistics for all validation rules
    
    Returns:
    - Per-rule statistics (pass/fail counts, pass rates, last execution)
    - Summary statistics (total rules, overall pass rate, etc.)
    
    Filters:
    - document_type: Filter by document type
    - severity: Filter by severity level
    - date_from/date_to: Filter results by date range
    """
    try:
        # Build base query for validation results
        results_query = db.query(
            ValidationResult.rule_id,
            func.count(ValidationResult.id).label('total_tests'),
            func.sum(case((ValidationResult.passed == True, 1), else_=0)).label('passed_count'),
            func.sum(case((ValidationResult.passed == False, 1), else_=0)).label('failed_count'),
            func.max(ValidationResult.created_at).label('last_executed_at')
        ).group_by(ValidationResult.rule_id)
        
        # Apply date filters if provided
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
                results_query = results_query.filter(ValidationResult.created_at >= date_from_obj)
            except ValueError:
                pass  # Invalid date format, ignore
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
                # Add one day to include the entire day
                date_to_obj = date_to_obj + timedelta(days=1)
                results_query = results_query.filter(ValidationResult.created_at < date_to_obj)
            except ValueError:
                pass  # Invalid date format, ignore
        
        # Get aggregated results
        aggregated_results = results_query.all()
        
        # Create a dictionary for quick lookup
        results_dict = {
            rule_id: {
                'total_tests': total_tests or 0,
                'passed_count': int(passed_count or 0),
                'failed_count': int(failed_count or 0),
                'last_executed_at': last_executed_at
            }
            for rule_id, total_tests, passed_count, failed_count, last_executed_at in aggregated_results
        }
        
        # Get all rules (with optional filters)
        rules_query = db.query(ValidationRule)
        
        if document_type:
            rules_query = rules_query.filter(ValidationRule.document_type == document_type)
        
        if severity:
            rules_query = rules_query.filter(ValidationRule.severity == severity)
        
        rules = rules_query.order_by(ValidationRule.document_type, ValidationRule.id).all()
        
        # Build statistics items
        rule_statistics = []
        total_checks = 0
        total_passed = 0
        total_failed = 0
        critical_failures = 0
        warnings = 0
        errors = 0
        
        for rule in rules:
            stats = results_dict.get(rule.id, {
                'total_tests': 0,
                'passed_count': 0,
                'failed_count': 0,
                'last_executed_at': None
            })
            
            total_tests = stats['total_tests']
            passed_count = stats['passed_count']
            failed_count = stats['failed_count']
            pass_rate = (passed_count / total_tests * 100) if total_tests > 0 else 0.0
            
            rule_statistics.append(RuleStatisticsItem(
                rule_id=rule.id,
                rule_name=rule.rule_name,
                rule_description=rule.rule_description,
                document_type=rule.document_type,
                rule_type=rule.rule_type,
                severity=rule.severity,
                is_active=rule.is_active,
                total_tests=total_tests,
                passed_count=passed_count,
                failed_count=failed_count,
                pass_rate=round(pass_rate, 2),
                last_executed_at=stats['last_executed_at'],
                created_at=rule.created_at
            ))
            
            # Aggregate summary statistics
            total_checks += total_tests
            total_passed += passed_count
            total_failed += failed_count
            
            if rule.severity == 'error':
                errors += failed_count
            elif rule.severity == 'warning':
                warnings += failed_count
            
            # Count critical failures (errors with failures)
            if rule.severity == 'error' and failed_count > 0:
                critical_failures += failed_count
        
        # Calculate overall pass rate
        overall_pass_rate = (total_passed / total_checks * 100) if total_checks > 0 else 0.0
        
        # Count active rules
        active_rules = sum(1 for r in rules if r.is_active)
        
        summary = RuleStatisticsSummary(
            total_rules=len(rules),
            active_rules=active_rules,
            total_checks=total_checks,
            overall_pass_rate=round(overall_pass_rate, 2),
            critical_failures=critical_failures,
            warnings=warnings,
            errors=errors
        )
        
        return RuleStatisticsResponse(
            rules=rule_statistics,
            summary=summary
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rule statistics: {str(e)}"
        )


@router.get("/validations/rules/{rule_id}/results", response_model=List[ValidationDetailItem])
async def get_rule_results(
    rule_id: int,
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Get recent validation results for a specific rule
    
    Returns:
    - List of validation results with details
    - Paginated results (limit/offset)
    """
    try:
        # Verify rule exists
        rule = db.query(ValidationRule).filter(ValidationRule.id == rule_id).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found"
            )
        
        # Get validation results for this rule
        results = db.query(
            ValidationResult,
            DocumentUpload
        ).join(
            DocumentUpload, ValidationResult.upload_id == DocumentUpload.id
        ).filter(
            ValidationResult.rule_id == rule_id
        ).order_by(
            ValidationResult.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        # Get property codes for uploads
        from app.models.property import Property
        property_map = {}
        property_ids = [result[1].property_id for result in results if result[1].property_id]
        if property_ids:
            properties = db.query(Property).filter(
                Property.id.in_(property_ids)
            ).all()
            property_map = {p.id: p.property_code for p in properties}
        
        # Build response items
        result_items = []
        for result, upload in results:
            property_code = property_map.get(upload.property_id) if upload.property_id else None
            
            result_items.append(ValidationDetailItem(
                id=result.id,
                rule_id=result.rule_id,
                rule_name=rule.rule_name,
                rule_description=rule.rule_description,
                passed=result.passed,
                expected_value=float(result.expected_value) if result.expected_value else None,
                actual_value=float(result.actual_value) if result.actual_value else None,
                difference=float(result.difference) if result.difference else None,
                difference_percentage=float(result.difference_percentage) if result.difference_percentage else None,
                error_message=result.error_message,
                severity=result.severity
            ))
        
        return result_items
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rule results: {str(e)}"
        )


@router.get("/validations/{upload_id}", response_model=ValidationDetailResponse)
async def get_validation_results(
    upload_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all validation results for an upload
    
    Returns:
    - Summary of validation checks (passed/failed)
    - Detailed results for each validation rule
    - Property and document information
    
    Use this endpoint after extraction completes to verify data quality
    """
    try:
        # Get upload with property info
        upload_query = db.query(
            DocumentUpload,
            ValidationRule.rule_name,
            ValidationRule.rule_description
        ).outerjoin(
            ValidationResult, ValidationResult.upload_id == DocumentUpload.id
        ).outerjoin(
            ValidationRule, ValidationResult.rule_id == ValidationRule.id
        ).filter(
            DocumentUpload.id == upload_id
        ).first()
        
        if not upload_query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        upload = upload_query[0] if isinstance(upload_query, tuple) else upload_query
        
        # Get property code
        from app.models.property import Property
        property_obj = db.query(Property).filter(Property.id == upload.property_id).first()
        property_code = property_obj.property_code if property_obj else None
        
        # Get all validation results for this upload
        results = db.query(
            ValidationResult,
            ValidationRule.rule_name,
            ValidationRule.rule_description
        ).join(
            ValidationRule, ValidationResult.rule_id == ValidationRule.id
        ).filter(
            ValidationResult.upload_id == upload_id
        ).all()
        
        # Build response
        validation_items = []
        for result, rule_name, rule_desc in results:
            validation_items.append(ValidationDetailItem(
                id=result.id,
                rule_id=result.rule_id,
                rule_name=rule_name,
                rule_description=rule_desc,
                passed=result.passed,
                expected_value=float(result.expected_value) if result.expected_value else None,
                actual_value=float(result.actual_value) if result.actual_value else None,
                difference=float(result.difference) if result.difference else None,
                difference_percentage=float(result.difference_percentage) if result.difference_percentage else None,
                error_message=result.error_message,
                severity=result.severity
            ))
        
        # Calculate summary
        total_checks = len(validation_items)
        passed_checks = sum(1 for item in validation_items if item.passed)
        failed_checks = total_checks - passed_checks
        warnings = sum(1 for item in validation_items if item.severity == "warning")
        errors = sum(1 for item in validation_items if item.severity == "error")
        
        return ValidationDetailResponse(
            upload_id=upload.id,
            property_code=property_code,
            document_type=upload.document_type,
            extraction_status=upload.extraction_status,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warnings=warnings,
            errors=errors,
            overall_passed=failed_checks == 0,
            validation_results=validation_items
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get validation results: {str(e)}"
        )


@router.post("/validations/{upload_id}/run", response_model=ValidationRunResponse)
async def run_validation(
    upload_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually trigger validation for an upload
    
    Useful for:
    - Re-validation after manual data corrections
    - Running validation on previously uploaded documents
    - Testing validation rules
    
    Returns:
    - Summary of validation run
    - Pass/fail counts
    """
    try:
        # Verify upload exists
        upload = db.query(DocumentUpload).filter(
            DocumentUpload.id == upload_id
        ).first()
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        # Check if extraction is completed
        if upload.extraction_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot validate - extraction status is '{upload.extraction_status}'. Must be 'completed'."
            )
        
        # Delete existing validation results for this upload (re-validation)
        db.query(ValidationResult).filter(
            ValidationResult.upload_id == upload_id
        ).delete()
        db.commit()
        
        # Run validation
        validation_service = ValidationService(db, tolerance_percentage=1.0)
        validation_result = validation_service.validate_upload(upload_id)
        
        if not validation_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Validation failed: {validation_result.get('error')}"
            )
        
        return ValidationRunResponse(
            upload_id=upload_id,
            success=True,
            message="Validation completed",
            total_checks=validation_result["total_checks"],
            passed_checks=validation_result["passed_checks"],
            failed_checks=validation_result["failed_checks"],
            overall_passed=validation_result["overall_passed"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run validation: {str(e)}"
        )


@router.get("/validations/{upload_id}/summary", response_model=ValidationSummaryResponse)
async def get_validation_summary(
    upload_id: int,
    db: Session = Depends(get_db)
):
    """
    Get quick validation summary
    
    Returns:
    - Pass/fail counts
    - Warning/error counts
    - Overall pass status
    
    Lightweight endpoint for dashboard views
    """
    try:
        # Verify upload exists
        upload = db.query(DocumentUpload).filter(
            DocumentUpload.id == upload_id
        ).first()
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload {upload_id} not found"
            )
        
        # Get validation results count
        results = db.query(ValidationResult).filter(
            ValidationResult.upload_id == upload_id
        ).all()
        
        total_checks = len(results)
        passed_checks = sum(1 for r in results if r.passed)
        failed_checks = total_checks - passed_checks
        warnings = sum(1 for r in results if r.severity == "warning")
        errors = sum(1 for r in results if r.severity == "error")
        
        return ValidationSummaryResponse(
            upload_id=upload_id,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warnings=warnings,
            errors=errors,
            overall_passed=failed_checks == 0
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get validation summary: {str(e)}"
        )

