"""
Bulk Import Service

Handles CSV and Excel file imports for:
- Budgets
- Forecasts
- Chart of Accounts
- Financial Data (Income Statement, Balance Sheet)
- Historical Data Backload

Provides validation, error handling, and import statistics.
"""
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, InvalidOperation
from datetime import datetime
import logging
import io
import csv
import pandas as pd

from app.models.budget import Budget, Forecast, BudgetStatus
from app.models.chart_of_accounts import ChartOfAccounts
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.cash_flow_header import CashFlowHeader
from app.models.balance_sheet_data import BalanceSheetData
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)


class BulkImportService:
    """
    Bulk Import Service

    Supports CSV and Excel file imports with validation and error handling
    """

    # Required columns for each data type
    REQUIRED_COLUMNS = {
        "budget": ["account_code", "account_name", "budgeted_amount"],
        "forecast": ["account_code", "account_name", "forecasted_amount"],
        "chart_of_accounts": ["account_code", "account_name", "account_type"],
        "income_statement": ["account_code", "account_name", "period_amount"],  # Updated to period_amount
        "balance_sheet": ["account_code", "account_name", "amount"],
        "cash_flow": ["account_code", "account_name", "period_amount"],  # Added cash flow
    }

    def __init__(self, db: Session):
        self.db = db

    def import_budgets_from_csv(
        self,
        file_content: bytes,
        property_id: int,
        financial_period_id: int,
        budget_name: str,
        budget_year: int,
        created_by: int,
        file_format: str = "csv"
    ) -> Dict:
        """
        Import budget data from CSV/Excel file

        Expected columns:
        - account_code (required)
        - account_name (required)
        - budgeted_amount (required)
        - account_category (optional)
        - tolerance_percentage (optional)
        - tolerance_amount (optional)
        - notes (optional)
        """
        try:
            # Parse file
            df = self._parse_file(file_content, file_format)

            # Validate columns
            validation = self._validate_columns(df, "budget")
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "missing_columns": validation.get("missing_columns", [])
                }

            # Verify property and period exist
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == financial_period_id
            ).first()
            if not period:
                return {"success": False, "error": "Financial period not found"}

            # Import budgets
            imported = 0
            failed = 0
            errors = []

            for index, row in df.iterrows():
                try:
                    # Validate and convert data
                    account_code = str(row["account_code"]).strip()
                    account_name = str(row["account_name"]).strip()
                    budgeted_amount = self._parse_decimal(row["budgeted_amount"])

                    if budgeted_amount is None:
                        errors.append({
                            "row": index + 2,  # +2 for header and 0-indexing
                            "error": "Invalid budgeted_amount"
                        })
                        failed += 1
                        continue

                    # Optional fields
                    account_category = str(row.get("account_category", "")).strip() or None
                    tolerance_pct = self._parse_decimal(row.get("tolerance_percentage"))
                    tolerance_amt = self._parse_decimal(row.get("tolerance_amount"))
                    notes = str(row.get("notes", "")).strip() or None

                    # Create budget record
                    budget = Budget(
                        property_id=property_id,
                        financial_period_id=financial_period_id,
                        budget_name=budget_name,
                        budget_year=budget_year,
                        budget_period_type=period.period_type,
                        status=BudgetStatus.DRAFT,
                        account_code=account_code,
                        account_name=account_name,
                        account_category=account_category,
                        budgeted_amount=budgeted_amount,
                        tolerance_percentage=tolerance_pct,
                        tolerance_amount=tolerance_amt,
                        notes=notes,
                        created_by=created_by
                    )

                    self.db.add(budget)
                    imported += 1

                except Exception as e:
                    errors.append({
                        "row": index + 2,
                        "error": str(e)
                    })
                    failed += 1

            # Commit if any succeeded
            if imported > 0:
                self.db.commit()

            return {
                "success": True,
                "imported": imported,
                "failed": failed,
                "total_rows": len(df),
                "errors": errors,
                "budget_name": budget_name,
                "property_id": property_id,
                "financial_period_id": financial_period_id
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Budget import failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def import_forecasts_from_csv(
        self,
        file_content: bytes,
        property_id: int,
        financial_period_id: int,
        forecast_name: str,
        forecast_year: int,
        forecast_type: str,
        created_by: int,
        file_format: str = "csv"
    ) -> Dict:
        """
        Import forecast data from CSV/Excel file

        Expected columns:
        - account_code (required)
        - account_name (required)
        - forecasted_amount (required)
        - account_category (optional)
        - tolerance_percentage (optional)
        - tolerance_amount (optional)
        - assumptions (optional)
        - notes (optional)
        """
        try:
            # Parse file
            df = self._parse_file(file_content, file_format)

            # Validate columns
            validation = self._validate_columns(df, "forecast")
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "missing_columns": validation.get("missing_columns", [])
                }

            # Verify property and period
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == financial_period_id
            ).first()
            if not period:
                return {"success": False, "error": "Financial period not found"}

            # Import forecasts
            imported = 0
            failed = 0
            errors = []

            for index, row in df.iterrows():
                try:
                    account_code = str(row["account_code"]).strip()
                    account_name = str(row["account_name"]).strip()
                    forecasted_amount = self._parse_decimal(row["forecasted_amount"])

                    if forecasted_amount is None:
                        errors.append({
                            "row": index + 2,
                            "error": "Invalid forecasted_amount"
                        })
                        failed += 1
                        continue

                    # Optional fields
                    account_category = str(row.get("account_category", "")).strip() or None
                    tolerance_pct = self._parse_decimal(row.get("tolerance_percentage"))
                    tolerance_amt = self._parse_decimal(row.get("tolerance_amount"))
                    assumptions = str(row.get("assumptions", "")).strip() or None
                    notes = str(row.get("notes", "")).strip() or None

                    # Create forecast record
                    forecast = Forecast(
                        property_id=property_id,
                        financial_period_id=financial_period_id,
                        forecast_name=forecast_name,
                        forecast_year=forecast_year,
                        forecast_period_type=period.period_type,
                        forecast_type=forecast_type,
                        status=BudgetStatus.DRAFT,
                        account_code=account_code,
                        account_name=account_name,
                        account_category=account_category,
                        forecasted_amount=forecasted_amount,
                        tolerance_percentage=tolerance_pct,
                        tolerance_amount=tolerance_amt,
                        assumptions=assumptions,
                        notes=notes,
                        created_by=created_by
                    )

                    self.db.add(forecast)
                    imported += 1

                except Exception as e:
                    errors.append({
                        "row": index + 2,
                        "error": str(e)
                    })
                    failed += 1

            if imported > 0:
                self.db.commit()

            return {
                "success": True,
                "imported": imported,
                "failed": failed,
                "total_rows": len(df),
                "errors": errors,
                "forecast_name": forecast_name,
                "forecast_type": forecast_type
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Forecast import failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def import_chart_of_accounts_from_csv(
        self,
        file_content: bytes,
        property_id: int,
        file_format: str = "csv"
    ) -> Dict:
        """
        Import chart of accounts from CSV/Excel file

        Expected columns:
        - account_code (required)
        - account_name (required)
        - account_type (required)
        - parent_account_code (optional)
        - description (optional)
        - is_active (optional)
        """
        try:
            df = self._parse_file(file_content, file_format)

            validation = self._validate_columns(df, "chart_of_accounts")
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "missing_columns": validation.get("missing_columns", [])
                }

            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            imported = 0
            failed = 0
            updated = 0
            errors = []

            for index, row in df.iterrows():
                try:
                    account_code = str(row["account_code"]).strip()
                    account_name = str(row["account_name"]).strip()
                    account_type = str(row["account_type"]).strip()

                    # Optional fields
                    parent_code = str(row.get("parent_account_code", "")).strip() or None
                    description = str(row.get("description", "")).strip() or None
                    is_active = self._parse_boolean(row.get("is_active", True))

                    # Check if account exists
                    existing = self.db.query(ChartOfAccounts).filter(
                        ChartOfAccounts.property_id == property_id,
                        ChartOfAccounts.account_code == account_code
                    ).first()

                    if existing:
                        # Update existing
                        existing.account_name = account_name
                        existing.account_type = account_type
                        existing.parent_account_code = parent_code
                        existing.description = description
                        existing.is_active = is_active
                        updated += 1
                    else:
                        # Create new
                        account = ChartOfAccounts(
                            property_id=property_id,
                            account_code=account_code,
                            account_name=account_name,
                            account_type=account_type,
                            parent_account_code=parent_code,
                            description=description,
                            is_active=is_active
                        )
                        self.db.add(account)
                        imported += 1

                except Exception as e:
                    errors.append({
                        "row": index + 2,
                        "error": str(e)
                    })
                    failed += 1

            if imported > 0 or updated > 0:
                self.db.commit()

            return {
                "success": True,
                "imported": imported,
                "updated": updated,
                "failed": failed,
                "total_rows": len(df),
                "errors": errors
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Chart of accounts import failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def import_income_statement_from_csv(
        self,
        file_content: bytes,
        property_id: int,
        financial_period_id: int,
        upload_id: Optional[int] = None,
        file_format: str = "csv"
    ) -> Dict:
        """
        Import income statement data from CSV/Excel file (Template v1.0 compliant)

        Required columns:
        - account_code (required)
        - account_name (required)
        - period_amount (required) - Period to Date amount

        Optional columns:
        - ytd_amount - Year to Date amount
        - period_percentage - Period percentage of revenue
        - ytd_percentage - YTD percentage of revenue
        - line_category - INCOME, OPERATING_EXPENSE, ADDITIONAL_EXPENSE, OTHER_EXPENSE, SUMMARY
        - line_subcategory - Primary Income, Utility, Contracted, R&M, Administration, etc.
        - line_number - Sequential line number
        - is_subtotal - Boolean flag for subtotal lines
        - is_total - Boolean flag for total lines
        - is_income - Boolean flag (TRUE for income, FALSE for expense)
        - is_below_the_line - Boolean flag for depreciation, amortization, mortgage interest
        - account_level - Hierarchy depth (1-4)
        - parent_account_code - Parent account code
        - extraction_confidence - Confidence score (0-100)
        - notes - Additional notes
        """
        try:
            from app.models.income_statement_header import IncomeStatementHeader
            from app.models.income_statement_data import IncomeStatementData
            from datetime import datetime
            
            df = self._parse_file(file_content, file_format)

            # Flexible validation - accept either period_amount or amount (backward compatibility)
            if "period_amount" not in df.columns and "amount" in df.columns:
                df["period_amount"] = df["amount"]
            
            validation = self._validate_columns(df, "income_statement")
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "missing_columns": validation.get("missing_columns", [])
                }

            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == financial_period_id
            ).first()
            if not period:
                return {"success": False, "error": "Financial period not found"}

            # Delete existing data for this property/period (replace strategy)
            deleted_header = self.db.query(IncomeStatementHeader).filter(
                IncomeStatementHeader.property_id == property_id,
                IncomeStatementHeader.period_id == financial_period_id
            ).delete(synchronize_session=False)
            
            deleted_items = self.db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == financial_period_id
            ).delete(synchronize_session=False)

            imported = 0
            failed = 0
            errors = []
            line_items = []

            # First pass: Import line items
            for index, row in df.iterrows():
                try:
                    account_code = str(row["account_code"]).strip()
                    account_name = str(row["account_name"]).strip()
                    period_amount = self._parse_decimal(row.get("period_amount") or row.get("amount"))

                    if period_amount is None:
                        errors.append({
                            "row": index + 2,
                            "error": "Invalid period_amount"
                        })
                        failed += 1
                        continue

                    # Optional fields with defaults
                    ytd_amount = self._parse_decimal(row.get("ytd_amount"))
                    period_percentage = self._parse_decimal(row.get("period_percentage"))
                    ytd_percentage = self._parse_decimal(row.get("ytd_percentage"))
                    line_category = str(row.get("line_category", "")).strip() or None
                    line_subcategory = str(row.get("line_subcategory", "")).strip() or None
                    line_number = int(row.get("line_number", index + 1))
                    is_subtotal = self._parse_boolean(row.get("is_subtotal", False))
                    is_total = self._parse_boolean(row.get("is_total", False))
                    is_income = self._parse_boolean(row.get("is_income", account_code.startswith("4")))
                    is_below_the_line = self._parse_boolean(row.get("is_below_the_line", False))
                    account_level = int(row.get("account_level", 1))
                    parent_account_code = str(row.get("parent_account_code", "")).strip() or None
                    extraction_confidence = self._parse_decimal(row.get("extraction_confidence"))
                    notes = str(row.get("notes", "")).strip() or None

                    # Create income statement record
                    income_data = IncomeStatementData(
                        property_id=property_id,
                        period_id=financial_period_id,
                        upload_id=upload_id,
                        account_code=account_code,
                        account_name=account_name,
                        period_amount=period_amount,
                        ytd_amount=ytd_amount,
                        period_percentage=period_percentage,
                        ytd_percentage=ytd_percentage,
                        line_category=line_category,
                        line_subcategory=line_subcategory,
                        line_number=line_number,
                        is_subtotal=is_subtotal,
                        is_total=is_total,
                        is_income=is_income,
                        is_below_the_line=is_below_the_line,
                        account_level=account_level,
                        parent_account_code=parent_account_code,
                        extraction_confidence=extraction_confidence,
                        review_notes=notes
                    )

                    self.db.add(income_data)
                    line_items.append(income_data)
                    imported += 1

                except Exception as e:
                    errors.append({
                        "row": index + 2,
                        "error": str(e)
                    })
                    failed += 1

            # Calculate totals for header
            total_income = sum(item.period_amount for item in line_items if item.is_income and not item.is_total)
            total_expenses = sum(item.period_amount for item in line_items if not item.is_income and not item.is_total)
            noi = total_income - total_expenses

            # Create header if we have data
            if imported > 0:
                header = IncomeStatementHeader(
                    property_id=property_id,
                    period_id=financial_period_id,
                    upload_id=upload_id,
                    property_name=property.property_name,
                    property_code=property.property_code,
                    report_period_start=period.period_start,
                    report_period_end=period.period_end,
                    period_type=period.period_type or "Monthly",
                    accounting_basis="Accrual",  # Default, can be overridden
                    total_income=total_income,
                    total_operating_expenses=total_expenses,
                    net_operating_income=noi,
                    net_income=noi  # Simplified - can be enhanced
                )
                self.db.add(header)
                self.db.commit()
                self.db.refresh(header)
                
                # Link line items to header
                for item in line_items:
                    item.header_id = header.id
                self.db.commit()

            return {
                "success": True,
                "imported": imported,
                "failed": failed,
                "total_rows": len(df),
                "errors": errors,
                "header_id": header.id if imported > 0 else None
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Income statement import failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def import_balance_sheet_from_csv(
        self,
        file_content: bytes,
        property_id: int,
        financial_period_id: int,
        upload_id: Optional[int] = None,
        file_format: str = "csv"
    ) -> Dict:
        """
        Import balance sheet data from CSV/Excel file (Template v1.0 compliant)

        Required columns:
        - account_code (required)
        - account_name (required)
        - amount (required)

        Optional columns:
        - account_category - ASSETS, LIABILITIES, CAPITAL
        - account_subcategory - Current Assets, Property & Equipment, Current Liabilities, etc.
        - is_subtotal - Boolean flag for subtotal lines
        - is_total - Boolean flag for total lines
        - account_level - Hierarchy depth (1-4)
        - parent_account_code - Parent account code
        - is_debit - Boolean (TRUE for assets/expenses, FALSE for liabilities/equity)
        - is_contra_account - Boolean for accumulated depreciation, distributions
        - expected_sign - positive, negative, either
        - extraction_confidence - Confidence score (0-100)
        - report_title - Document title
        - period_ending - Period ending date string
        - accounting_basis - Accrual or Cash
        - notes - Additional notes
        """
        try:
            df = self._parse_file(file_content, file_format)

            validation = self._validate_columns(df, "balance_sheet")
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "missing_columns": validation.get("missing_columns", [])
                }

            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == financial_period_id
            ).first()
            if not period:
                return {"success": False, "error": "Financial period not found"}

            # Delete existing data for this property/period (replace strategy)
            deleted_items = self.db.query(BalanceSheetData).filter(
                BalanceSheetData.property_id == property_id,
                BalanceSheetData.period_id == financial_period_id
            ).delete(synchronize_session=False)

            imported = 0
            failed = 0
            errors = []

            for index, row in df.iterrows():
                try:
                    account_code = str(row["account_code"]).strip()
                    account_name = str(row["account_name"]).strip()
                    amount = self._parse_decimal(row["amount"])

                    if amount is None:
                        errors.append({
                            "row": index + 2,
                            "error": "Invalid amount"
                        })
                        failed += 1
                        continue

                    # Optional fields with defaults
                    account_category = str(row.get("account_category", "")).strip() or None
                    account_subcategory = str(row.get("account_subcategory", "")).strip() or None
                    is_subtotal = self._parse_boolean(row.get("is_subtotal", False))
                    is_total = self._parse_boolean(row.get("is_total", False))
                    account_level = int(row.get("account_level", 1))
                    parent_account_code = str(row.get("parent_account_code", "")).strip() or None
                    
                    # Determine is_debit based on account code or explicit value
                    is_debit = None
                    if "is_debit" in row:
                        is_debit = self._parse_boolean(row["is_debit"])
                    else:
                        # Auto-detect: Assets (1xxx) and Expenses (5xxx, 6xxx) are debits
                        if account_code.startswith(("1", "5", "6")):
                            is_debit = True
                        else:
                            is_debit = False
                    
                    is_contra_account = self._parse_boolean(row.get("is_contra_account", False))
                    expected_sign = str(row.get("expected_sign", "")).strip() or None
                    extraction_confidence = self._parse_decimal(row.get("extraction_confidence"))
                    report_title = str(row.get("report_title", "Balance Sheet")).strip()
                    period_ending = str(row.get("period_ending", "")).strip() or None
                    accounting_basis = str(row.get("accounting_basis", "Accrual")).strip()
                    notes = str(row.get("notes", "")).strip() or None

                    # Create balance sheet record
                    balance_data = BalanceSheetData(
                        property_id=property_id,
                        period_id=financial_period_id,
                        upload_id=upload_id,
                        account_code=account_code,
                        account_name=account_name,
                        amount=amount,
                        account_category=account_category,
                        account_subcategory=account_subcategory,
                        is_subtotal=is_subtotal,
                        is_total=is_total,
                        account_level=account_level,
                        parent_account_code=parent_account_code,
                        is_debit=is_debit,
                        is_contra_account=is_contra_account,
                        expected_sign=expected_sign,
                        extraction_confidence=extraction_confidence,
                        report_title=report_title,
                        period_ending=period_ending,
                        accounting_basis=accounting_basis,
                        review_notes=notes
                    )

                    self.db.add(balance_data)
                    imported += 1

                except Exception as e:
                    errors.append({
                        "row": index + 2,
                        "error": str(e)
                    })
                    failed += 1

            if imported > 0:
                self.db.commit()

            return {
                "success": True,
                "imported": imported,
                "failed": failed,
                "total_rows": len(df),
                "errors": errors
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Balance sheet import failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def import_cash_flow_from_csv(
        self,
        file_content: bytes,
        property_id: int,
        financial_period_id: int,
        upload_id: Optional[int] = None,
        file_format: str = "csv"
    ) -> Dict:
        """
        Import cash flow data from CSV/Excel file (Template v1.0 compliant)

        Required columns:
        - account_code (required)
        - account_name (required)
        - period_amount (required) - Period to Date amount

        Optional columns:
        - ytd_amount - Year to Date amount
        - period_percentage - Period percentage
        - ytd_percentage - YTD percentage
        - line_section - INCOME, OPERATING_EXPENSE, ADDITIONAL_EXPENSE, PERFORMANCE_METRICS
        - line_category - Base Rental Income, Recovery Income, Property Expenses, etc.
        - line_subcategory - Tax Recovery, Insurance Recovery, Electricity, etc.
        - line_number - Sequential line number
        - is_subtotal - Boolean flag for subtotal lines
        - is_total - Boolean flag for total lines
        - is_inflow - Boolean (TRUE for cash in, FALSE for cash out)
        - cash_flow_category - operating, investing, financing
        - parent_line_id - Link to parent subtotal/total
        - extraction_confidence - Confidence score (0-100)
        - notes - Additional notes
        """
        try:
            from datetime import datetime
            
            df = self._parse_file(file_content, file_format)

            # Flexible validation - accept either period_amount or amount (backward compatibility)
            if "period_amount" not in df.columns and "amount" in df.columns:
                df["period_amount"] = df["amount"]
            
            # Validate required columns
            required = ["account_code", "account_name", "period_amount"]
            missing = [col for col in required if col not in df.columns]
            if missing:
                return {
                    "success": False,
                    "error": f"Missing required columns: {', '.join(missing)}",
                    "missing_columns": missing
                }

            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == financial_period_id
            ).first()
            if not period:
                return {"success": False, "error": "Financial period not found"}

            # Delete existing data for this property/period (replace strategy)
            deleted_header = self.db.query(CashFlowHeader).filter(
                CashFlowHeader.property_id == property_id,
                CashFlowHeader.period_id == financial_period_id
            ).delete(synchronize_session=False)
            
            deleted_items = self.db.query(CashFlowData).filter(
                CashFlowData.property_id == property_id,
                CashFlowData.period_id == financial_period_id
            ).delete(synchronize_session=False)

            imported = 0
            failed = 0
            errors = []
            line_items = []

            # First pass: Import line items
            for index, row in df.iterrows():
                try:
                    account_code = str(row["account_code"]).strip()
                    account_name = str(row["account_name"]).strip()
                    period_amount = self._parse_decimal(row.get("period_amount") or row.get("amount"))

                    if period_amount is None:
                        errors.append({
                            "row": index + 2,
                            "error": "Invalid period_amount"
                        })
                        failed += 1
                        continue

                    # Optional fields with defaults
                    ytd_amount = self._parse_decimal(row.get("ytd_amount"))
                    period_percentage = self._parse_decimal(row.get("period_percentage"))
                    ytd_percentage = self._parse_decimal(row.get("ytd_percentage"))
                    line_section = str(row.get("line_section", "")).strip() or None
                    line_category = str(row.get("line_category", "")).strip() or None
                    line_subcategory = str(row.get("line_subcategory", "")).strip() or None
                    line_number = int(row.get("line_number", index + 1))
                    is_subtotal = self._parse_boolean(row.get("is_subtotal", False))
                    is_total = self._parse_boolean(row.get("is_total", False))
                    
                    # Determine is_inflow based on account code or explicit value
                    is_inflow = None
                    if "is_inflow" in row:
                        is_inflow = self._parse_boolean(row["is_inflow"])
                    else:
                        # Auto-detect: Income accounts (4xxx) are inflows
                        is_inflow = account_code.startswith("4")
                    
                    cash_flow_category = str(row.get("cash_flow_category", "operating")).strip()
                    parent_line_id = int(row.get("parent_line_id")) if pd.notna(row.get("parent_line_id")) else None
                    extraction_confidence = self._parse_decimal(row.get("extraction_confidence"))
                    notes = str(row.get("notes", "")).strip() or None

                    # Create cash flow record
                    cash_flow_data = CashFlowData(
                        property_id=property_id,
                        period_id=financial_period_id,
                        upload_id=upload_id,
                        account_code=account_code,
                        account_name=account_name,
                        period_amount=period_amount,
                        ytd_amount=ytd_amount,
                        period_percentage=period_percentage,
                        ytd_percentage=ytd_percentage,
                        line_section=line_section,
                        line_category=line_category,
                        line_subcategory=line_subcategory,
                        line_number=line_number,
                        is_subtotal=is_subtotal,
                        is_total=is_total,
                        is_inflow=is_inflow,
                        cash_flow_category=cash_flow_category,
                        parent_line_id=parent_line_id,
                        extraction_confidence=extraction_confidence,
                        review_notes=notes
                    )

                    self.db.add(cash_flow_data)
                    line_items.append(cash_flow_data)
                    imported += 1

                except Exception as e:
                    errors.append({
                        "row": index + 2,
                        "error": str(e)
                    })
                    failed += 1

            # Calculate totals for header
            total_income = sum(item.period_amount for item in line_items if item.is_inflow and not item.is_total)
            total_expenses = sum(abs(item.period_amount) for item in line_items if not item.is_inflow and not item.is_total)
            net_cash_flow = total_income - total_expenses

            # Create header if we have data
            header = None
            if imported > 0:
                header = CashFlowHeader(
                    property_id=property_id,
                    period_id=financial_period_id,
                    upload_id=upload_id,
                    property_name=property.property_name,
                    property_code=property.property_code,
                    report_period_start=period.period_start,
                    report_period_end=period.period_end,
                    period_type=period.period_type or "Monthly",
                    accounting_basis="Accrual",  # Default
                    total_income=total_income,
                    total_expenses=total_expenses,
                    net_cash_flow=net_cash_flow
                )
                self.db.add(header)
                self.db.commit()
                self.db.refresh(header)
                
                # Link line items to header
                for item in line_items:
                    item.header_id = header.id
                self.db.commit()

            return {
                "success": True,
                "imported": imported,
                "failed": failed,
                "total_rows": len(df),
                "errors": errors,
                "header_id": header.id if header else None
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Cash flow import failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _parse_file(self, file_content: bytes, file_format: str) -> pd.DataFrame:
        """
        Parse CSV or Excel file into pandas DataFrame
        """
        if file_format.lower() == "csv":
            # Try different encodings
            try:
                return pd.read_csv(io.BytesIO(file_content))
            except UnicodeDecodeError:
                return pd.read_csv(io.BytesIO(file_content), encoding='latin-1')
        elif file_format.lower() in ["xlsx", "xls", "excel"]:
            return pd.read_excel(io.BytesIO(file_content))
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

    def _validate_columns(self, df: pd.DataFrame, data_type: str) -> Dict:
        """
        Validate that required columns are present
        """
        required = self.REQUIRED_COLUMNS.get(data_type, [])
        missing = [col for col in required if col not in df.columns]

        if missing:
            return {
                "valid": False,
                "error": f"Missing required columns: {', '.join(missing)}",
                "missing_columns": missing
            }

        return {"valid": True}

    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """
        Parse value to Decimal, handling various formats
        """
        if pd.isna(value) or value is None or value == "":
            return None

        try:
            # Remove currency symbols and commas
            if isinstance(value, str):
                value = value.replace("$", "").replace(",", "").strip()

            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    def _parse_boolean(self, value: Any) -> bool:
        """
        Parse value to boolean
        """
        if pd.isna(value) or value is None:
            return True  # Default to True

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "y", "active"]

        return bool(value)

    def generate_sample_template(self, data_type: str) -> Dict:
        """
        Generate sample CSV template for a data type

        Returns sample data and column headers
        """
        templates = {
            "budget": {
                "columns": ["account_code", "account_name", "budgeted_amount", "account_category", "tolerance_percentage", "notes"],
                "sample_data": [
                    ["4100", "Rental Income", "950000.00", "Revenue", "10.0", "Primary revenue source"],
                    ["5100", "Property Management Fees", "45000.00", "Operating Expense", "10.0", ""],
                    ["5200", "Utilities", "28000.00", "Operating Expense", "15.0", "Electric, water, gas"]
                ]
            },
            "forecast": {
                "columns": ["account_code", "account_name", "forecasted_amount", "account_category", "tolerance_percentage", "assumptions"],
                "sample_data": [
                    ["4100", "Rental Income", "1020000.00", "Revenue", "15.0", "Assuming 3% rent increase"],
                    ["5100", "Property Management Fees", "48000.00", "Operating Expense", "15.0", "4.5% of rental income"]
                ]
            },
            "chart_of_accounts": {
                "columns": ["account_code", "account_name", "account_type", "parent_account_code", "description", "is_active"],
                "sample_data": [
                    ["4000", "Revenue", "Revenue", "", "Total revenue accounts", "true"],
                    ["4100", "Rental Income", "Revenue", "4000", "Rental income from tenants", "true"],
                    ["5000", "Operating Expenses", "Expense", "", "Total operating expenses", "true"]
                ]
            },
            "income_statement": {
                "columns": ["account_code", "account_name", "amount", "notes"],
                "sample_data": [
                    ["4100", "Rental Income", "987500.00", ""],
                    ["5100", "Property Management Fees", "44250.00", ""],
                    ["5200", "Utilities", "31200.00", "Higher due to winter months"]
                ]
            },
            "balance_sheet": {
                "columns": ["account_code", "account_name", "amount", "account_category", "account_subcategory", "is_subtotal", "is_total", "notes"],
                "sample_data": [
                    ["1100", "Cash and Cash Equivalents", "125000.00", "ASSETS", "Current Assets", "false", "false", ""],
                    ["1500", "Property, Plant & Equipment", "4500000.00", "ASSETS", "Property & Equipment", "false", "false", ""],
                    ["2100", "Long-term Debt", "3150000.00", "LIABILITIES", "Long Term Liabilities", "false", "false", ""]
                ]
            },
            "cash_flow": {
                "columns": ["account_code", "account_name", "period_amount", "ytd_amount", "line_section", "line_category", "is_inflow", "notes"],
                "sample_data": [
                    ["4010-0000", "Base Rentals", "215671.29", "2588055.53", "INCOME", "Primary Income", "true", ""],
                    ["5010-0000", "Property Tax", "12500.00", "150000.00", "OPERATING_EXPENSE", "Property Expenses", "false", ""],
                    ["5990-0000", "Total Operating Expenses", "85000.00", "1020000.00", "OPERATING_EXPENSE", "Total", "false", ""]
                ]
            }
        }

        template = templates.get(data_type)
        if not template:
            return {"success": False, "error": f"Unknown data type: {data_type}"}

        return {
            "success": True,
            "data_type": data_type,
            "columns": template["columns"],
            "sample_data": template["sample_data"],
            "csv_example": self._generate_csv_string(template["columns"], template["sample_data"])
        }

    def _generate_csv_string(self, columns: List[str], data: List[List[str]]) -> str:
        """
        Generate CSV string from columns and data
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(data)
        return output.getvalue()
