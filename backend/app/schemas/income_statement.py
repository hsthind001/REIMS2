"""
Income Statement Schemas - Template v1.0 Compliant

Comprehensive Pydantic schemas for Income Statement data including:
- Header with all summary metrics
- Line items with full categorization and hierarchy
- Complete statement with categorized sections
- Summary responses for dashboard display
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class IncomeStatementHeaderResponse(BaseModel):
    """Income Statement header with all summary metrics (Template v1.0)"""
    id: int
    property_id: int
    period_id: int
    upload_id: Optional[int] = None
    
    # ==================== PROPERTY IDENTIFICATION ====================
    property_name: str = Field(..., description="Full property name")
    property_code: str = Field(..., description="Property code (e.g., 'esp', 'hmnd')")
    
    # ==================== PERIOD INFORMATION ====================
    report_period_start: date = Field(..., description="Period start date")
    report_period_end: date = Field(..., description="Period end date")
    period_type: str = Field(..., description="Monthly, Annual, or Quarterly")
    accounting_basis: str = Field(..., description="Accrual or Cash")
    report_generation_date: Optional[date] = Field(None, description="Date report was generated")
    
    # ==================== INCOME SUMMARY ====================
    total_income: float = Field(..., description="Total Income (4990-0000)")
    base_rentals: Optional[float] = Field(None, description="Base Rentals (4010-0000)")
    total_recovery_income: Optional[float] = Field(None, description="Tax + Insurance + CAM reimbursements")
    total_other_income: Optional[float] = Field(None, description="Interest, fees, misc income")
    
    # ==================== OPERATING EXPENSE SUMMARY ====================
    total_operating_expenses: float = Field(..., description="Total Operating Expenses (5990-0000)")
    total_property_expenses: Optional[float] = Field(None, description="Property Tax + Insurance")
    total_utility_expenses: Optional[float] = Field(None, description="Total Utility Expense (5199-0000)")
    total_contracted_expenses: Optional[float] = Field(None, description="Total Contracted Expenses (5299-0000)")
    total_rm_expenses: Optional[float] = Field(None, description="Total R&M (5399-0000)")
    total_admin_expenses: Optional[float] = Field(None, description="Total Administration (5499-0000)")
    
    # ==================== ADDITIONAL EXPENSE SUMMARY ====================
    total_additional_operating_expenses: Optional[float] = Field(None, description="Total Additional Operating Expenses (6190-0000)")
    total_management_fees: Optional[float] = Field(None, description="Management fees total")
    total_leasing_costs: Optional[float] = Field(None, description="Leasing commissions + TI")
    total_ll_expenses: Optional[float] = Field(None, description="Total Landlord Expenses (6069-0000)")
    
    # ==================== TOTAL EXPENSES ====================
    total_expenses: float = Field(..., description="Total Expenses (6199-0000)")
    
    # ==================== NET OPERATING INCOME (NOI) ====================
    net_operating_income: float = Field(..., description="NOI (6299-0000) = Total Income - Total Expenses")
    noi_percentage: Optional[float] = Field(None, description="NOI % = (NOI / Total Income) * 100")
    
    # ==================== OTHER INCOME/EXPENSES (BELOW THE LINE) ====================
    mortgage_interest: Optional[float] = Field(None, description="Mortgage Interest (7010-0000)")
    depreciation: Optional[float] = Field(None, description="Depreciation (7020-0000)")
    amortization: Optional[float] = Field(None, description="Amortization (7030-0000)")
    total_other_income_expense: Optional[float] = Field(None, description="Total Other Income/Expense (7090-0000)")
    
    # ==================== NET INCOME (BOTTOM LINE) ====================
    net_income: float = Field(..., description="Net Income (9090-0000) = NOI - Other Expenses")
    net_income_percentage: Optional[float] = Field(None, description="Net Income % = (Net Income / Total Income) * 100")
    
    # ==================== QUALITY METRICS ====================
    extraction_confidence: Optional[float] = Field(None, description="Overall extraction confidence 0-100")
    validation_passed: Optional[bool] = Field(False, description="All critical validations passed")
    needs_review: bool = Field(False, description="Requires manual review")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "property_code": "esp",
                "property_name": "Eastern Shore Plaza (esp)",
                "period_type": "Monthly",
                "accounting_basis": "Accrual",
                "total_income": 3426774.19,
                "total_operating_expenses": 1121922.50,
                "total_additional_operating_expenses": 216946.55,
                "total_expenses": 1338869.05,
                "net_operating_income": 2087905.14,
                "noi_percentage": 60.93,
                "net_income": 209459.72,
                "net_income_percentage": 6.11,
                "extraction_confidence": 98.5,
                "validation_passed": True
            }
        }


class IncomeStatementLineItemResponse(BaseModel):
    """Income Statement line item with full categorization (Template v1.0)"""
    id: int
    header_id: Optional[int] = None
    property_id: int
    period_id: int
    account_id: Optional[int] = None
    
    # ==================== ACCOUNT INFORMATION ====================
    account_code: str = Field(..., description="Account code (e.g., '4010-0000')")
    account_name: str = Field(..., description="Account description")
    
    # ==================== FINANCIAL DATA - MULTI-COLUMN ====================
    period_amount: float = Field(..., description="Period to Date amount")
    ytd_amount: Optional[float] = Field(None, description="Year to Date amount")
    period_percentage: Optional[float] = Field(None, description="Period to Date percentage")
    ytd_percentage: Optional[float] = Field(None, description="Year to Date percentage")
    
    # ==================== TEMPLATE V1.0: HEADER METADATA ====================
    period_type: Optional[str] = Field(None, description="Monthly, Annual, Quarterly")
    accounting_basis: Optional[str] = Field(None, description="Accrual or Cash")
    report_generation_date: Optional[date] = Field(None, description="Report generation date")
    page_number: Optional[int] = Field(None, description="Page number in source PDF")
    
    # ==================== TEMPLATE V1.0: HIERARCHICAL STRUCTURE ====================
    is_subtotal: bool = Field(False, description="Is this a subtotal line (e.g., Total Utilities)")
    is_total: bool = Field(False, description="Is this a total line (e.g., TOTAL INCOME)")
    line_category: Optional[str] = Field(None, description="INCOME, OPERATING_EXPENSE, ADDITIONAL_EXPENSE, OTHER_EXPENSE, SUMMARY")
    line_subcategory: Optional[str] = Field(None, description="utilities, contracted, repair_maintenance, administration, etc.")
    line_number: Optional[int] = Field(None, description="Sequential line number in statement")
    account_level: Optional[int] = Field(None, description="Hierarchy depth (1-4)")
    
    # ==================== CLASSIFICATION ====================
    is_income: Optional[bool] = Field(None, description="TRUE for income, FALSE for expense")
    is_below_the_line: bool = Field(False, description="TRUE for depreciation, amortization, mortgage interest")
    
    # ==================== EXTRACTION QUALITY ====================
    extraction_confidence: Optional[float] = Field(None, description="0-100 from PDF extraction")
    match_confidence: Optional[float] = Field(None, description="0-100 from account matching")
    extraction_method: Optional[str] = Field(None, description="table, text, template")
    
    # ==================== REVIEW FLAGS ====================
    needs_review: bool = Field(False, description="Requires manual review")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "account_code": "4010-0000",
                "account_name": "Base Rentals",
                "period_amount": 229422.31,
                "ytd_amount": 2768568.46,
                "period_percentage": 89.18,
                "ytd_percentage": 81.43,
                "line_category": "INCOME",
                "line_subcategory": "Primary Income",
                "is_subtotal": False,
                "is_total": False,
                "is_below_the_line": False,
                "line_number": 1,
                "extraction_confidence": 99.2
            }
        }


class CompleteIncomeStatementResponse(BaseModel):
    """Complete Income Statement with all components (Template v1.0)"""
    header: IncomeStatementHeaderResponse
    line_items: List[IncomeStatementLineItemResponse]
    
    # ==================== SUMMARY STATISTICS ====================
    total_line_items: int = Field(..., description="Total number of line items")
    
    # ==================== CATEGORIZED LINE ITEMS (FOR EASIER ACCESS) ====================
    income_items: List[IncomeStatementLineItemResponse] = Field(default_factory=list, description="Income section items (4000 series)")
    operating_expense_items: List[IncomeStatementLineItemResponse] = Field(default_factory=list, description="Operating expense items (5000 series)")
    additional_expense_items: List[IncomeStatementLineItemResponse] = Field(default_factory=list, description="Additional expense items (6000 series)")
    other_expense_items: List[IncomeStatementLineItemResponse] = Field(default_factory=list, description="Other expenses - below the line (7000 series)")
    summary_items: List[IncomeStatementLineItemResponse] = Field(default_factory=list, description="Summary/total items (NOI, Net Income)")
    
    # ==================== VALIDATION SUMMARY ====================
    validation_passed: bool = Field(False, description="All critical validations passed")
    validation_errors: int = Field(0, description="Number of critical validation errors")
    validation_warnings: int = Field(0, description="Number of validation warnings")
    
    class Config:
        schema_extra = {
            "example": {
                "header": {
                    "property_name": "Eastern Shore Plaza (esp)",
                    "property_code": "esp",
                    "period_type": "Monthly",
                    "total_income": 3426774.19,
                    "total_operating_expenses": 1121922.50,
                    "total_additional_operating_expenses": 216946.55,
                    "total_expenses": 1338869.05,
                    "net_operating_income": 2087905.14,
                    "noi_percentage": 60.93,
                    "net_income": 209459.72,
                    "net_income_percentage": 6.11
                },
                "total_line_items": 87,
                "validation_passed": True,
                "validation_errors": 0,
                "validation_warnings": 0
            }
        }


class IncomeStatementSummaryResponse(BaseModel):
    """Summary metrics for dashboard display"""
    property_code: str = Field(..., description="Property code")
    period_year: int = Field(..., description="Fiscal year")
    period_month: int = Field(..., description="Month (1-12)")
    
    # ==================== KEY METRICS ====================
    total_income: float = Field(..., description="Total Income")
    total_operating_expenses: float = Field(..., description="Total Operating Expenses")
    total_additional_operating_expenses: Optional[float] = Field(None, description="Total Additional Operating Expenses")
    total_expenses: float = Field(..., description="Total Expenses")
    net_operating_income: float = Field(..., description="Net Operating Income (NOI)")
    noi_percentage: float = Field(..., description="NOI Margin %")
    net_income: float = Field(..., description="Net Income (Bottom Line)")
    net_income_percentage: Optional[float] = Field(None, description="Net Income Margin %")
    
    # ==================== QUALITY INDICATORS ====================
    extraction_confidence: float = Field(..., description="Overall extraction confidence")
    validation_passed: bool = Field(..., description="All critical validations passed")
    needs_review: bool = Field(..., description="Requires manual review")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "property_code": "esp",
                "period_year": 2024,
                "period_month": 12,
                "total_income": 3426774.19,
                "total_expenses": 1338869.05,
                "net_operating_income": 2087905.14,
                "noi_percentage": 60.93,
                "net_income": 209459.72,
                "net_income_percentage": 6.11,
                "extraction_confidence": 98.5,
                "validation_passed": True,
                "needs_review": False
            }
        }

