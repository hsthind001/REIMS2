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
        "income_statement": ["account_code", "account_name", "amount"],
        "balance_sheet": ["account_code", "account_name", "amount"],
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
        file_format: str = "csv"
    ) -> Dict:
        """
        Import income statement data from CSV/Excel file

        Expected columns:
        - account_code (required)
        - account_name (required)
        - amount (required)
        - notes (optional)
        """
        try:
            df = self._parse_file(file_content, file_format)

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

                    notes = str(row.get("notes", "")).strip() or None

                    # Create income statement record
                    income_data = IncomeStatementData(
                        property_id=property_id,
                        financial_period_id=financial_period_id,
                        account_code=account_code,
                        account_name=account_name,
                        amount=amount,
                        notes=notes
                    )

                    self.db.add(income_data)
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
            logger.error(f"Income statement import failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def import_balance_sheet_from_csv(
        self,
        file_content: bytes,
        property_id: int,
        financial_period_id: int,
        file_format: str = "csv"
    ) -> Dict:
        """
        Import balance sheet data from CSV/Excel file

        Expected columns:
        - account_code (required)
        - account_name (required)
        - amount (required)
        - notes (optional)
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

                    notes = str(row.get("notes", "")).strip() or None

                    # Create balance sheet record
                    balance_data = BalanceSheetData(
                        property_id=property_id,
                        financial_period_id=financial_period_id,
                        account_code=account_code,
                        account_name=account_name,
                        amount=amount,
                        notes=notes
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
                "columns": ["account_code", "account_name", "amount", "notes"],
                "sample_data": [
                    ["1100", "Cash and Cash Equivalents", "125000.00", ""],
                    ["1500", "Property, Plant & Equipment", "4500000.00", ""],
                    ["2100", "Long-term Debt", "3150000.00", ""]
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
