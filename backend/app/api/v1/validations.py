"""
Validations API - Query and manage financial data validation results
"""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

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

