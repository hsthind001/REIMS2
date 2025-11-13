"""
Financial Reports Pydantic Schemas

Response models for financial reporting API
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class PropertyInfo(BaseModel):
    """Property information"""
    property_code: str
    property_name: str
    property_type: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class PeriodInfo(BaseModel):
    """Period information"""
    year: int
    month: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class BalanceSheetMetrics(BaseModel):
    """Balance sheet metrics"""
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    debt_to_equity_ratio: Optional[float] = None
    debt_to_assets_ratio: Optional[float] = None
    ltv_ratio: Optional[float] = None
    cash_position: Optional[float] = None
    operating_cash: Optional[float] = None
    restricted_cash: Optional[float] = None


class IncomeStatementMetrics(BaseModel):
    """Income statement metrics"""
    total_revenue: Optional[float] = None
    total_expenses: Optional[float] = None
    net_operating_income: Optional[float] = None
    net_income: Optional[float] = None
    operating_margin: Optional[float] = None
    profit_margin: Optional[float] = None


class CashFlowMetrics(BaseModel):
    """Cash flow metrics"""
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    net_cash_flow: Optional[float] = None
    beginning_cash_balance: Optional[float] = None
    ending_cash_balance: Optional[float] = None


class RentRollMetrics(BaseModel):
    """Rent roll metrics"""
    total_units: Optional[int] = None
    occupied_units: Optional[int] = None
    vacant_units: Optional[int] = None
    occupancy_rate: Optional[float] = None
    total_annual_rent: Optional[float] = None
    avg_rent_per_sqft: Optional[float] = None


class PerformanceMetrics(BaseModel):
    """Performance metrics"""
    noi_per_sqft: Optional[float] = None
    revenue_per_sqft: Optional[float] = None
    expense_ratio: Optional[float] = None


class MetadataInfo(BaseModel):
    """Report metadata"""
    calculated_at: Optional[str] = None


class FinancialSummaryResponse(BaseModel):
    """Complete financial summary for a property/period"""
    property: PropertyInfo
    period: PeriodInfo
    balance_sheet: BalanceSheetMetrics
    income_statement: IncomeStatementMetrics
    cash_flow: CashFlowMetrics
    rent_roll: RentRollMetrics
    performance: PerformanceMetrics
    metadata: MetadataInfo
    
    class Config:
        schema_extra = {
            "example": {
                "property": {
                    "property_code": "WEND001",
                    "property_name": "Wendover Commons",
                    "property_type": "Mixed Use",
                    "city": "Greensboro",
                    "state": "NC"
                },
                "period": {
                    "year": 2024,
                    "month": 12,
                    "start_date": "2024-12-01",
                    "end_date": "2024-12-31"
                },
                "balance_sheet": {
                    "total_assets": 22939865.40,
                    "total_liabilities": 21769610.72,
                    "total_equity": 1170254.68,
                    "current_ratio": 2.0,
                    "debt_to_equity_ratio": 18.60
                },
                "income_statement": {
                    "total_revenue": 3179456.89,
                    "total_expenses": 3751340.64,
                    "net_operating_income": 1860030.71,
                    "net_income": -571883.75,
                    "operating_margin": 58.52,
                    "profit_margin": -17.99
                },
                "rent_roll": {
                    "total_units": 20,
                    "occupied_units": 19,
                    "occupancy_rate": 95.0
                }
            }
        }


class ComparisonPeriod(BaseModel):
    """Period data for comparison"""
    year: int
    month: int
    amount: Optional[float] = None


class VarianceInfo(BaseModel):
    """Variance information"""
    amount: Optional[float] = None
    percentage: Optional[float] = None


class ComparisonAccount(BaseModel):
    """Account comparison data"""
    account_code: str
    account_name: str
    current_period: ComparisonPeriod
    previous_period: ComparisonPeriod
    variance: VarianceInfo
    ytd_amount: Optional[float] = None
    is_income: Optional[bool] = None


class PeriodComparisonResponse(BaseModel):
    """Comparison between two periods"""
    property_code: str
    start_period: PeriodInfo
    end_period: PeriodInfo
    accounts: List[ComparisonAccount]
    total_accounts: int
    
    class Config:
        schema_extra = {
            "example": {
                "property_code": "WEND001",
                "start_period": {"year": 2024, "month": 11},
                "end_period": {"year": 2024, "month": 12},
                "accounts": [
                    {
                        "account_code": "4010-0000",
                        "account_name": "Rental Income",
                        "current_period": {
                            "year": 2024,
                            "month": 12,
                            "amount": 250000.00
                        },
                        "previous_period": {
                            "year": 2024,
                            "month": 11,
                            "amount": 245000.00
                        },
                        "variance": {
                            "amount": 5000.00,
                            "percentage": 2.04
                        },
                        "ytd_amount": 2950000.00,
                        "is_income": True
                    }
                ],
                "total_accounts": 45
            }
        }


class MonthlyDataPoint(BaseModel):
    """Single month data point in trend"""
    month: int
    period_amount: Optional[float] = None
    ytd_amount: Optional[float] = None


class TrendStatistics(BaseModel):
    """Statistical summary of trend"""
    annual_total: Optional[float] = None
    monthly_average: Optional[float] = None
    min_month: Optional[float] = None
    max_month: Optional[float] = None
    std_deviation: Optional[float] = None


class AnnualTrendItem(BaseModel):
    """Single account trend over 12 months"""
    account_code: str
    account_name: str
    monthly_data: List[MonthlyDataPoint]
    statistics: TrendStatistics


class AnnualTrendsResponse(BaseModel):
    """Annual trends for multiple accounts"""
    property_code: str
    year: int
    trends: List[AnnualTrendItem]
    total_accounts: int
    
    class Config:
        schema_extra = {
            "example": {
                "property_code": "WEND001",
                "year": 2024,
                "trends": [
                    {
                        "account_code": "4010-0000",
                        "account_name": "Rental Income",
                        "monthly_data": [
                            {"month": 1, "period_amount": 245000.00, "ytd_amount": 245000.00},
                            {"month": 2, "period_amount": 248000.00, "ytd_amount": 493000.00},
                            {"month": 3, "period_amount": 250000.00, "ytd_amount": 743000.00}
                        ],
                        "statistics": {
                            "annual_total": 2950000.00,
                            "monthly_average": 245833.33,
                            "min_month": 240000.00,
                            "max_month": 252000.00
                        }
                    }
                ],
                "total_accounts": 5
            }
        }


class ExcelExportResponse(BaseModel):
    """Excel export metadata"""
    filename: str
    size_bytes: int
    property_code: str
    period: str
    sheets: List[str]
    
    class Config:
        schema_extra = {
            "example": {
                "filename": "WEND001_2024-12_Financial_Report.xlsx",
                "size_bytes": 45678,
                "property_code": "WEND001",
                "period": "2024-12",
                "sheets": ["Summary", "Balance Sheet", "Income Statement", "Cash Flow", "Rent Roll"]
            }
        }

