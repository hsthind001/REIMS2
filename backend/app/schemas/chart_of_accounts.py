from pydantic import BaseModel, ConfigDict, computed_field
from typing import Optional, List, Any
from datetime import datetime
import json


class ChartOfAccountsBase(BaseModel):
    """Base schema for Chart of Accounts"""
    account_code: str
    account_name: str
    account_type: str
    category: Optional[str] = None
    subcategory: Optional[str] = None


class ChartOfAccountsCreate(ChartOfAccountsBase):
    """Schema for creating a new chart of accounts entry"""
    parent_account_code: Optional[str] = None
    document_types: Optional[List[str]] = None
    is_calculated: bool = False
    calculation_formula: Optional[str] = None
    display_order: Optional[int] = None
    is_active: bool = True


class ChartOfAccountsUpdate(BaseModel):
    """Schema for updating a chart of accounts entry"""
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    parent_account_code: Optional[str] = None
    document_types: Optional[List[str]] = None
    is_calculated: Optional[bool] = None
    calculation_formula: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class ChartOfAccountsResponse(ChartOfAccountsBase):
    """Schema for chart of accounts API response"""
    id: int
    parent_account_code: Optional[str] = None
    document_types: Optional[Any] = None  # Can be List[str] or str (JSON)
    is_calculated: bool
    calculation_formula: Optional[str] = None
    display_order: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    def model_post_init(self, __context: Any) -> None:
        """Post init to convert document_types from JSON string to list"""
        if self.document_types and isinstance(self.document_types, str):
            try:
                self.document_types = json.loads(self.document_types)
            except:
                self.document_types = []


class ChartOfAccountsListResponse(BaseModel):
    """Schema for paginated list of chart of accounts"""
    accounts: List[ChartOfAccountsResponse]
    total: int
    skip: int
    limit: int

