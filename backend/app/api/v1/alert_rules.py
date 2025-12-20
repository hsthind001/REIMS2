"""
Alert Rules API Endpoints
Manage alert rules for automatic alert generation
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from app.db.database import get_db
from app.models.alert_rule import AlertRule
from app.services.alert_rules_service import AlertRulesService
from app.services.alert_rule_templates import AlertRuleTemplates
from app.models.user import User
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/alert-rules", tags=["alert_rules"])
logger = logging.getLogger(__name__)


class AlertRuleCreate(BaseModel):
    """Schema for creating alert rule"""
    rule_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    rule_type: str = Field(..., description="Rule type: threshold, statistical, trend, composite")
    field_name: str = Field(..., min_length=1, max_length=100)
    condition: str = Field(..., description="Condition: greater_than, less_than, equals, etc.")
    threshold_value: Optional[float] = None
    severity: str = Field(default="warning", description="Severity: critical, high, medium, low, warning, info")
    is_active: bool = Field(default=True)
    rule_expression: Optional[dict] = None
    severity_mapping: Optional[dict] = None
    cooldown_period: Optional[int] = Field(default=60, ge=0, description="Minutes between alerts")
    rule_dependencies: Optional[dict] = None
    property_specific: bool = Field(default=False)
    property_id: Optional[int] = None
    rule_template_id: Optional[int] = None


class AlertRuleUpdate(BaseModel):
    """Schema for updating alert rule"""
    rule_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    rule_type: Optional[str] = None
    field_name: Optional[str] = Field(None, min_length=1, max_length=100)
    condition: Optional[str] = None
    threshold_value: Optional[float] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None
    rule_expression: Optional[dict] = None
    severity_mapping: Optional[dict] = None
    cooldown_period: Optional[int] = Field(None, ge=0)
    rule_dependencies: Optional[dict] = None
    property_specific: Optional[bool] = None
    property_id: Optional[int] = None


class AlertRuleResponse(BaseModel):
    """Alert rule response schema"""
    id: int
    rule_name: str
    description: Optional[str]
    rule_type: str
    field_name: str
    condition: str
    threshold_value: Optional[float]
    severity: str
    is_active: bool
    rule_expression: Optional[dict]
    severity_mapping: Optional[dict]
    cooldown_period: Optional[int]
    rule_dependencies: Optional[dict]
    property_specific: bool
    property_id: Optional[int]
    rule_template_id: Optional[int]
    execution_count: Optional[int]
    last_triggered_at: Optional[str]
    created_at: str
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class RuleTestRequest(BaseModel):
    """Schema for testing a rule"""
    property_id: int
    period_id: int
    rule_config: Optional[dict] = None  # Override rule config for testing


@router.get("", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    rule_type: Optional[str] = Query(None, description="Filter by rule type"),
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all alert rules with optional filtering"""
    query = db.query(AlertRule)
    
    if property_id is not None:
        query = query.filter(
            (AlertRule.property_id == property_id) | (AlertRule.property_specific == False)
        )
    
    if is_active is not None:
        query = query.filter(AlertRule.is_active == is_active)
    
    if rule_type:
        valid_rule_types = ["threshold", "statistical", "trend", "composite"]
        if rule_type not in valid_rule_types:
            raise HTTPException(status_code=400, detail=f"Invalid rule_type: {rule_type}")
        query = query.filter(AlertRule.rule_type == rule_type)
    
    rules = query.order_by(AlertRule.created_at.desc()).offset(skip).limit(limit).all()
    
    return [AlertRuleResponse(**rule.to_dict()) for rule in rules]


@router.get("/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific alert rule by ID"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    return AlertRuleResponse(**rule.to_dict())


@router.post("", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new alert rule"""
    # Validate rule_type (allow string values)
    valid_rule_types = ["threshold", "statistical", "trend", "composite"]
    if rule_data.rule_type not in valid_rule_types:
        raise HTTPException(status_code=400, detail=f"Invalid rule_type: {rule_data.rule_type}. Must be one of: {valid_rule_types}")
    
    # Validate condition (allow string values)
    valid_conditions = ["greater_than", "less_than", "equals", "not_equals", "percentage_change", "z_score", "trend_up", "trend_down", "absolute_change"]
    if rule_data.condition not in valid_conditions:
        raise HTTPException(status_code=400, detail=f"Invalid condition: {rule_data.condition}. Must be one of: {valid_conditions}")
    
    # Validate property_id if property_specific
    if rule_data.property_specific and not rule_data.property_id:
        raise HTTPException(
            status_code=400,
            detail="property_id is required when property_specific is True"
        )
    
    # Create rule
    rule = AlertRule(
        rule_name=rule_data.rule_name,
        description=rule_data.description,
        rule_type=rule_data.rule_type,
        field_name=rule_data.field_name,
        condition=rule_data.condition,
        threshold_value=rule_data.threshold_value,
        severity=rule_data.severity,
        is_active=rule_data.is_active,
        rule_expression=rule_data.rule_expression,
        severity_mapping=rule_data.severity_mapping,
        cooldown_period=rule_data.cooldown_period,
        rule_dependencies=rule_data.rule_dependencies,
        property_specific=rule_data.property_specific,
        property_id=rule_data.property_id,
        rule_template_id=rule_data.rule_template_id,
        execution_count=0
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    logger.info(f"Alert rule created: {rule.id} - {rule.rule_name}")
    
    return AlertRuleResponse(**rule.to_dict())


@router.put("/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    rule_data: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing alert rule"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    # Update fields
    update_data = rule_data.model_dump(exclude_unset=True)
    
    # Validate rule_type if provided
    if "rule_type" in update_data:
        valid_rule_types = ["threshold", "statistical", "trend", "composite"]
        if update_data["rule_type"] not in valid_rule_types:
            raise HTTPException(status_code=400, detail=f"Invalid rule_type: {update_data['rule_type']}")
    
    # Validate condition if provided
    if "condition" in update_data:
        valid_conditions = ["greater_than", "less_than", "equals", "not_equals", "percentage_change", "z_score", "trend_up", "trend_down", "absolute_change"]
        if update_data["condition"] not in valid_conditions:
            raise HTTPException(status_code=400, detail=f"Invalid condition: {update_data['condition']}")
    
    for key, value in update_data.items():
        setattr(rule, key, value)
    
    rule.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(rule)
    
    logger.info(f"Alert rule updated: {rule.id} - {rule.rule_name}")
    
    return AlertRuleResponse(**rule.to_dict())


@router.delete("/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an alert rule"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    db.delete(rule)
    db.commit()
    
    logger.info(f"Alert rule deleted: {rule_id}")
    
    return None


@router.post("/{rule_id}/test", status_code=200)
async def test_alert_rule(
    rule_id: int,
    test_request: RuleTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test an alert rule against specific property/period data"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    # Override rule config if provided
    if test_request.rule_config:
        # Temporarily update rule for testing
        for key, value in test_request.rule_config.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
    
    # Evaluate rule
    service = AlertRulesService(db)
    result = service.evaluate_rule(
        rule=rule,
        property_id=test_request.property_id,
        period_id=test_request.period_id
    )
    
    return {
        "success": True,
        "rule_id": rule_id,
        "property_id": test_request.property_id,
        "period_id": test_request.period_id,
        "result": result
    }


@router.get("/templates/list", status_code=200)
async def list_rule_templates(
    current_user: User = Depends(get_current_user)
):
    """Get all available rule templates"""
    templates = AlertRuleTemplates.get_all_templates()
    return {
        "success": True,
        "templates": templates,
        "total": len(templates)
    }


@router.get("/templates/{template_id}", status_code=200)
async def get_rule_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific rule template"""
    template = AlertRuleTemplates.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "success": True,
        "template": template
    }


@router.post("/templates/{template_id}/create", response_model=AlertRuleResponse, status_code=201)
async def create_rule_from_template(
    template_id: str,
    property_id: Optional[int] = Query(None, description="Create property-specific rule"),
    threshold_override: Optional[float] = Query(None, description="Override default threshold"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create an alert rule from a template"""
    try:
        config = AlertRuleTemplates.create_rule_from_template(
            template_id=template_id,
            property_id=property_id,
            threshold_override=threshold_override
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Create rule from config
    rule = AlertRule(**config)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    # Update template_id reference
    rule.rule_template_id = rule.id  # Self-reference for template-based rules
    db.commit()
    db.refresh(rule)
    
    logger.info(f"Alert rule created from template: {rule.id} - {rule.rule_name}")
    
    return AlertRuleResponse(**rule.to_dict())


@router.post("/{rule_id}/activate", response_model=AlertRuleResponse)
async def activate_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate an alert rule"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    rule.is_active = True
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    
    return AlertRuleResponse(**rule.to_dict())


@router.post("/{rule_id}/deactivate", response_model=AlertRuleResponse)
async def deactivate_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate an alert rule"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    rule.is_active = False
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    
    return AlertRuleResponse(**rule.to_dict())

