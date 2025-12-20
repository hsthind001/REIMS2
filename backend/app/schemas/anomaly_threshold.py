from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class AnomalyThresholdBase(BaseModel):
    """Base schema for Anomaly Threshold"""
    account_code: str = Field(..., description="Account code (e.g., '5400-0002')")
    account_name: str = Field(..., description="Account name (e.g., 'Salaries Expense')")
    threshold_value: Decimal = Field(..., description="Percentage threshold as decimal (e.g., 0.01 = 1%)")
    is_active: bool = Field(True, description="Whether this threshold is active")


class AnomalyThresholdCreate(AnomalyThresholdBase):
    """Schema for creating a new anomaly threshold"""
    pass


class AnomalyThresholdUpdate(BaseModel):
    """Schema for updating an anomaly threshold"""
    account_name: Optional[str] = Field(None, description="Account name")
    threshold_value: Optional[Decimal] = Field(None, description="Percentage threshold as decimal (e.g., 0.01 = 1%)")
    is_active: Optional[bool] = Field(None, description="Whether this threshold is active")


class AnomalyThresholdResponse(AnomalyThresholdBase):
    """Schema for anomaly threshold API response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class AnomalyThresholdListResponse(BaseModel):
    """Schema for list of anomaly thresholds"""
    thresholds: list[AnomalyThresholdResponse]
    total: int


class DefaultThresholdResponse(BaseModel):
    """Schema for default threshold response"""
    default_threshold: Decimal = Field(..., description="Default percentage threshold as decimal (e.g., 0.01 = 1%)")
    description: Optional[str] = None


class DefaultThresholdUpdate(BaseModel):
    """Schema for updating default threshold"""
    default_threshold: Decimal = Field(..., description="Default percentage threshold as decimal (e.g., 0.01 = 1%)")

