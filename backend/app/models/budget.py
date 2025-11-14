"""
Budget Model

Stores budgeted financial data for properties
Enables variance analysis (Actual vs Budget)
"""
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

from app.db.database import Base


class BudgetStatus(str, enum.Enum):
    """Budget status"""
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    REVISED = "REVISED"
    ARCHIVED = "ARCHIVED"


class Budget(Base):
    """
    Budget Model

    Stores budgeted financial data at the account level
    """
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    financial_period_id = Column(Integer, ForeignKey("financial_periods.id"), nullable=False, index=True)

    # Budget details
    budget_name = Column(String(200), nullable=False)  # e.g., "2025 Annual Budget"
    budget_year = Column(Integer, nullable=False, index=True)
    budget_period_type = Column(String(20), nullable=False)  # monthly, quarterly, annual

    # Status
    status = Column(SQLEnum(BudgetStatus), nullable=False, default=BudgetStatus.DRAFT, index=True)

    # Approval tracking
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Account-level budget
    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(200), nullable=True)
    account_category = Column(String(100), nullable=True)  # Revenue, Operating Expense, etc.

    # Budget amounts
    budgeted_amount = Column(Numeric(15, 2), nullable=False)

    # Tolerance settings
    tolerance_percentage = Column(Numeric(5, 2), nullable=True)  # e.g., 10.00 = 10%
    tolerance_amount = Column(Numeric(15, 2), nullable=True)  # Absolute dollar tolerance

    # Notes
    notes = Column(String(500), nullable=True)

    # Additional metadata
    metadata = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    property = relationship("Property", backref="budgets")
    financial_period = relationship("FinancialPeriod", backref="budgets")
    approved_by_user = relationship("User", foreign_keys=[approved_by], backref="budgets_approved")
    created_by_user = relationship("User", foreign_keys=[created_by], backref="budgets_created")

    def __repr__(self):
        return f"<Budget(id={self.id}, property_id={self.property_id}, account={self.account_code}, amount={self.budgeted_amount})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "property_id": self.property_id,
            "financial_period_id": self.financial_period_id,
            "budget_name": self.budget_name,
            "budget_year": self.budget_year,
            "budget_period_type": self.budget_period_type,
            "status": self.status.value if self.status else None,
            "account_code": self.account_code,
            "account_name": self.account_name,
            "account_category": self.account_category,
            "budgeted_amount": float(self.budgeted_amount) if self.budgeted_amount else 0,
            "tolerance_percentage": float(self.tolerance_percentage) if self.tolerance_percentage else None,
            "tolerance_amount": float(self.tolerance_amount) if self.tolerance_amount else None,
            "notes": self.notes,
            "metadata": self.metadata,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }

    def is_within_tolerance(self, actual_amount: float) -> bool:
        """
        Check if actual amount is within budget tolerance

        Returns True if within tolerance, False otherwise
        """
        budget_amount = float(self.budgeted_amount)
        variance = abs(actual_amount - budget_amount)

        # Check percentage tolerance
        if self.tolerance_percentage:
            max_variance = budget_amount * (float(self.tolerance_percentage) / 100)
            if variance <= max_variance:
                return True

        # Check absolute tolerance
        if self.tolerance_amount:
            if variance <= float(self.tolerance_amount):
                return True

        # If no tolerance set, use default 10%
        if not self.tolerance_percentage and not self.tolerance_amount:
            default_tolerance = budget_amount * 0.10
            return variance <= default_tolerance

        return False


class Forecast(Base):
    """
    Forecast Model

    Stores forecasted financial data (rolling forecasts, reforecasts)
    """
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)

    # Reference
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    financial_period_id = Column(Integer, ForeignKey("financial_periods.id"), nullable=False, index=True)

    # Forecast details
    forecast_name = Column(String(200), nullable=False)  # e.g., "Q2 2025 Reforecast"
    forecast_year = Column(Integer, nullable=False, index=True)
    forecast_period_type = Column(String(20), nullable=False)  # monthly, quarterly, annual
    forecast_type = Column(String(50), nullable=False)  # original, reforecast, rolling

    # Status
    status = Column(SQLEnum(BudgetStatus), nullable=False, default=BudgetStatus.DRAFT, index=True)

    # Forecast date (when forecast was created)
    forecast_date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Account-level forecast
    account_code = Column(String(50), nullable=False, index=True)
    account_name = Column(String(200), nullable=True)
    account_category = Column(String(100), nullable=True)

    # Forecast amounts
    forecasted_amount = Column(Numeric(15, 2), nullable=False)

    # Variance tolerance
    tolerance_percentage = Column(Numeric(5, 2), nullable=True)
    tolerance_amount = Column(Numeric(15, 2), nullable=True)

    # Forecast assumptions
    assumptions = Column(String(1000), nullable=True)

    # Notes
    notes = Column(String(500), nullable=True)

    # Additional metadata
    metadata = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    property = relationship("Property", backref="forecasts")
    financial_period = relationship("FinancialPeriod", backref="forecasts")
    created_by_user = relationship("User", foreign_keys=[created_by], backref="forecasts_created")

    def __repr__(self):
        return f"<Forecast(id={self.id}, property_id={self.property_id}, account={self.account_code}, amount={self.forecasted_amount})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "property_id": self.property_id,
            "financial_period_id": self.financial_period_id,
            "forecast_name": self.forecast_name,
            "forecast_year": self.forecast_year,
            "forecast_period_type": self.forecast_period_type,
            "forecast_type": self.forecast_type,
            "status": self.status.value if self.status else None,
            "forecast_date": self.forecast_date.isoformat() if self.forecast_date else None,
            "account_code": self.account_code,
            "account_name": self.account_name,
            "account_category": self.account_category,
            "forecasted_amount": float(self.forecasted_amount) if self.forecasted_amount else 0,
            "tolerance_percentage": float(self.tolerance_percentage) if self.tolerance_percentage else None,
            "tolerance_amount": float(self.tolerance_amount) if self.tolerance_amount else None,
            "assumptions": self.assumptions,
            "notes": self.notes,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }

    def is_within_tolerance(self, actual_amount: float) -> bool:
        """
        Check if actual amount is within forecast tolerance
        """
        forecast_amount = float(self.forecasted_amount)
        variance = abs(actual_amount - forecast_amount)

        # Check percentage tolerance
        if self.tolerance_percentage:
            max_variance = forecast_amount * (float(self.tolerance_percentage) / 100)
            if variance <= max_variance:
                return True

        # Check absolute tolerance
        if self.tolerance_amount:
            if variance <= float(self.tolerance_amount):
                return True

        # Default 15% tolerance for forecasts (more lenient than budgets)
        if not self.tolerance_percentage and not self.tolerance_amount:
            default_tolerance = forecast_amount * 0.15
            return variance <= default_tolerance

        return False
