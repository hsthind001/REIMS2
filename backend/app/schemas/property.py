from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
import re


class PropertyBase(BaseModel):
    property_code: str
    property_name: str = Field(..., min_length=3, max_length=100)
    property_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: str = 'USA'
    total_area_sqft: Optional[Decimal] = None
    acquisition_date: Optional[date] = None
    ownership_structure: Optional[str] = None
    status: str = 'active'
    notes: Optional[str] = None


class PropertyCreate(PropertyBase):
    
    @field_validator('property_code')
    @classmethod
    def validate_property_code(cls, v):
        """Validate property code format: 2-5 letters + 3 digits (e.g., ESP001, WEND001)"""
        if not re.match(r'^[A-Z]{2,5}\d{3}$', v):
            raise ValueError('Property code must be 2-5 uppercase letters followed by 3 digits (e.g., ESP001)')
        return v
    
    @field_validator('property_name')
    @classmethod
    def validate_property_name(cls, v):
        """Validate property name is not empty and has minimum length"""
        if not v or v.strip() == '':
            raise ValueError('Property name cannot be empty')
        if len(v.strip()) < 3:
            raise ValueError('Property name must be at least 3 characters')
        return v.strip()
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate property status"""
        valid_statuses = ['active', 'sold', 'under_contract']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v
    
    @field_validator('total_area_sqft')
    @classmethod
    def validate_area(cls, v):
        """Validate area is positive"""
        if v is not None and v <= 0:
            raise ValueError('Total area must be greater than 0')
        return v


class PropertyUpdate(BaseModel):
    property_code: Optional[str] = None
    property_name: Optional[str] = Field(None, min_length=3, max_length=100)
    property_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    
    @field_validator('property_name')
    @classmethod
    def validate_property_name(cls, v):
        """Validate property name if provided"""
        if v is not None:
            if v.strip() == '':
                raise ValueError('Property name cannot be empty')
            if len(v.strip()) < 3:
                raise ValueError('Property name must be at least 3 characters')
            return v.strip()
        return v


class Property(PropertyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    organization_id: Optional[int] = None

    class Config:
        from_attributes = True


# Alias for PropertyResponse as specified in Sprint 1.2
PropertyResponse = Property


class FinancialPeriodBase(BaseModel):
    property_id: int
    period_year: int
    period_month: int
    period_start_date: date
    period_end_date: date
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None


class FinancialPeriodCreate(FinancialPeriodBase):
    
    @field_validator('period_month')
    @classmethod
    def validate_month(cls, v):
        """Validate period month is between 1-12"""
        if not 1 <= v <= 12:
            raise ValueError('Period month must be between 1 and 12')
        return v
    
    @field_validator('fiscal_quarter')
    @classmethod
    def validate_fiscal_quarter(cls, v):
        """Validate fiscal quarter is 1-4 or None"""
        if v is not None and not 1 <= v <= 4:
            raise ValueError('Fiscal quarter must be between 1 and 4')
        return v
    
    @field_validator('period_end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """Validate end date is after start date"""
        if 'period_start_date' in info.data and v < info.data['period_start_date']:
            raise ValueError('Period end date must be after start date')
        return v


class FinancialPeriod(FinancialPeriodBase):
    id: int
    is_closed: bool
    created_at: datetime

    class Config:
        from_attributes = True

