"""
Cash Flow Statement Schemas - Template v1.0 Compliant

Comprehensive Pydantic schemas for Cash Flow Statement data including:
- Header with all summary metrics
- Line items with full categorization
- Adjustments with entity tracking
- Cash account reconciliations
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class CashFlowHeaderResponse(BaseModel):
    """Cash Flow Statement header with all summary metrics"""
    id: int
    property_id: int
    period_id: int
    upload_id: Optional[int]
    
    # Property Identification
    property_name: str
    property_code: str
    
    # Period Information
    report_period_start: date
    report_period_end: date
    accounting_basis: str
    report_generation_date: Optional[date]
    
    # Income Summary
    total_income: float
    base_rentals: Optional[float]
    total_recovery_income: Optional[float]
    total_other_income: Optional[float]
    
    # Expense Summary
    total_operating_expenses: float
    total_property_expenses: Optional[float]
    total_utility_expenses: Optional[float]
    total_contracted_expenses: Optional[float]
    total_rm_expenses: Optional[float]
    total_admin_expenses: Optional[float]
    total_additional_operating_expenses: Optional[float]
    total_management_fees: Optional[float]
    total_ll_expenses: Optional[float]
    total_expenses: float
    
    # Performance Metrics
    net_operating_income: float
    noi_percentage: Optional[float]
    mortgage_interest: Optional[float]
    depreciation: Optional[float]
    amortization: Optional[float]
    total_other_income_expense: Optional[float]
    net_income: float
    net_income_percentage: Optional[float]
    
    # Cash Flow
    total_adjustments: Optional[float]
    cash_flow: float
    cash_flow_percentage: Optional[float]
    
    # Cash Accounts
    beginning_cash_balance: Optional[float]
    ending_cash_balance: Optional[float]
    cash_difference: Optional[float]
    
    # Quality Metrics
    extraction_confidence: Optional[float]
    validation_passed: Optional[bool]
    needs_review: bool
    
    class Config:
        from_attributes = True


class CashFlowLineItemResponse(BaseModel):
    """Cash Flow line item with full categorization"""
    id: int
    header_id: Optional[int]
    property_id: int
    period_id: int
    account_id: Optional[int]
    
    # Account Information
    account_code: str
    account_name: str
    
    # Financial Data - Multi-column
    period_amount: float
    ytd_amount: Optional[float]
    period_percentage: Optional[float]
    ytd_percentage: Optional[float]
    
    # Classification
    line_section: Optional[str]  # INCOME, OPERATING_EXPENSE, ADDITIONAL_EXPENSE, PERFORMANCE_METRICS
    line_category: Optional[str]  # Base Rental Income, Utility Expenses, etc.
    line_subcategory: Optional[str]  # Base Rentals, Electricity Service, etc.
    
    # Structure
    line_number: Optional[int]
    is_subtotal: bool
    is_total: bool
    parent_line_id: Optional[int]
    
    # Page Tracking
    page_number: Optional[int]
    
    # Quality
    extraction_confidence: Optional[float]
    needs_review: bool
    
    class Config:
        from_attributes = True


class CashFlowAdjustmentResponse(BaseModel):
    """Cash Flow adjustment item"""
    id: int
    header_id: int
    property_id: int
    period_id: int
    
    # Adjustment Details
    adjustment_category: str  # AR_CHANGES, PROPERTY_EQUIPMENT, ACCUMULATED_DEPRECIATION, etc.
    adjustment_name: str
    adjustment_description: Optional[str]
    
    # Amount
    amount: float
    is_increase: Optional[bool]
    
    # Related Entities
    account_code: Optional[str]
    related_property: Optional[str]  # For inter-property transfers
    related_entity: Optional[str]  # For A/P and loans
    
    # Position
    line_number: Optional[int]
    is_subtotal: bool
    page_number: Optional[int]
    
    # Quality
    extraction_confidence: Optional[float]
    needs_review: bool
    
    class Config:
        from_attributes = True


class CashAccountReconciliationResponse(BaseModel):
    """Cash account reconciliation"""
    id: int
    header_id: int
    property_id: int
    period_id: int
    
    # Account Information
    account_name: str
    account_type: str  # operating, escrow, other
    account_code: Optional[str]
    
    # Balances
    beginning_balance: float
    ending_balance: float
    difference: float
    
    # Validation
    difference_calculated: Optional[float]
    difference_matches: bool
    
    # Flags
    is_negative_balance: bool
    is_escrow_account: bool
    is_total_row: bool
    
    # Position
    line_number: Optional[int]
    page_number: Optional[int]
    
    # Quality
    extraction_confidence: Optional[float]
    needs_review: bool
    
    class Config:
        from_attributes = True


class CompleteCashFlowStatementResponse(BaseModel):
    """Complete Cash Flow Statement with all components"""
    header: CashFlowHeaderResponse
    line_items: List[CashFlowLineItemResponse]
    adjustments: List[CashFlowAdjustmentResponse]
    cash_accounts: List[CashAccountReconciliationResponse]
    
    # Summary Statistics
    total_line_items: int
    total_adjustments: int
    total_cash_accounts: int
    
    # Categorized Line Items (for easier access)
    income_items: List[CashFlowLineItemResponse] = []
    operating_expense_items: List[CashFlowLineItemResponse] = []
    additional_expense_items: List[CashFlowLineItemResponse] = []
    performance_metric_items: List[CashFlowLineItemResponse] = []
    
    # Validation Summary
    validation_passed: bool
    validation_errors: int = 0
    validation_warnings: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "header": {
                    "property_name": "Eastern Shore Plaza (esp)",
                    "property_code": "esp",
                    "total_income": 3426774.19,
                    "total_expenses": 1338869.05,
                    "net_operating_income": 2087905.14,
                    "noi_percentage": 60.93,
                    "net_income": 209459.72,
                    "cash_flow": 249667.51,
                    "cash_flow_percentage": 7.29
                },
                "total_line_items": 85,
                "total_adjustments": 25,
                "total_cash_accounts": 3,
                "validation_passed": True
            }
        }


class CashFlowSummaryResponse(BaseModel):
    """Summary metrics for dashboard display"""
    property_code: str
    period_year: int
    period_month: int
    
    # Key Metrics
    total_income: float
    total_expenses: float
    net_operating_income: float
    noi_percentage: float
    net_income: float
    cash_flow: float
    
    # Quality Indicators
    extraction_confidence: float
    validation_passed: bool
    needs_review: bool
    
    class Config:
        from_attributes = True

