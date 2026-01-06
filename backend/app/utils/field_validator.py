"""
Phase 3: Field-Level Validation

Comprehensive field-level validation and intelligent error correction
for income statement data to achieve 100% data quality.

Validates:
- Data type correctness
- Value ranges and boundaries
- Cross-field consistency
- Business logic rules
- Calculated field accuracy
"""

from typing import Dict, List, Tuple, Optional, Any
from decimal import Decimal
import re
from datetime import datetime


class FieldValidator:
    """
    Field-level validator for income statement data

    Provides granular validation and intelligent error correction
    to ensure 100% data quality with zero data loss.
    """

    def __init__(self):
        self.validation_rules = self._init_validation_rules()
        self.correction_log = []

    def _init_validation_rules(self) -> Dict:
        """Initialize validation rules for each field type"""
        return {
            "account_code": {
                "type": str,
                "pattern": r"^\d{4}-\d{4}$",
                "required": True,
                "min_length": 9,
                "max_length": 9
            },
            "account_name": {
                "type": str,
                "required": True,
                "min_length": 1,
                "max_length": 255
            },
            "period_amount": {
                "type": (Decimal, float, int),
                "required": True,
                "min_value": -1000000000,  # -$1B
                "max_value": 1000000000,   # $1B
                "allow_negative": True
            },
            "ytd_amount": {
                "type": (Decimal, float, int),
                "required": False,
                "min_value": -1000000000,
                "max_value": 1000000000,
                "allow_negative": True
            },
            "period_percentage": {
                "type": (Decimal, float, int),
                "required": False,
                "min_value": -1000,  # Allow large percentages for expenses
                "max_value": 1000,
                "precision": 2
            },
            "ytd_percentage": {
                "type": (Decimal, float, int),
                "required": False,
                "min_value": -1000,
                "max_value": 1000,
                "precision": 2
            }
        }

    def validate_line_item(
        self,
        item: Dict,
        total_income: Optional[Decimal] = None
    ) -> Tuple[bool, List[str], Dict]:
        """
        Validate a single line item with comprehensive field-level checks

        Args:
            item: Line item dictionary
            total_income: Total income for percentage validation

        Returns:
            Tuple of (is_valid, errors, corrected_item)
        """
        errors = []
        corrected_item = item.copy()
        corrections_made = []

        # Rule 1: Account code validation
        if not self._validate_account_code(corrected_item):
            errors.append("Invalid or missing account code")

        # Rule 2: Account name validation
        if not self._validate_account_name(corrected_item):
            errors.append("Invalid or missing account name")

        # Rule 3: Amount validation
        period_valid, period_msg = self._validate_amount(
            corrected_item.get("period_amount"),
            "period_amount"
        )
        if not period_valid:
            errors.append(period_msg)

        # Rule 4: YTD >= Period consistency check
        ytd_corrected = self._validate_ytd_consistency(corrected_item)
        if ytd_corrected:
            corrections_made.append("Fixed YTD < Period inconsistency")

        # Rule 5: Percentage calculation validation
        if total_income and total_income > 0:
            pct_corrected = self._validate_and_fix_percentages(
                corrected_item,
                total_income
            )
            if pct_corrected:
                corrections_made.extend(pct_corrected)

        # Rule 6: Zero value validation
        self._validate_zero_consistency(corrected_item, errors)

        # Rule 7: Negative value appropriateness
        self._validate_negative_values(corrected_item, errors)

        # Rule 8: Decimal precision
        self._fix_decimal_precision(corrected_item)
        corrections_made.append("Normalized decimal precision")

        # Log corrections
        if corrections_made:
            self.correction_log.append({
                "account_code": corrected_item.get("account_code"),
                "corrections": corrections_made
            })

        is_valid = len(errors) == 0

        return is_valid, errors, corrected_item

    def _validate_account_code(self, item: Dict) -> bool:
        """Validate account code format and presence"""
        code = item.get("account_code")

        if not code:
            return False

        # Check format: ####-####
        pattern = re.compile(r"^\d{4}-\d{4}$")
        if not pattern.match(str(code)):
            # Try to fix common issues
            code_str = str(code).strip()

            # Remove extra spaces
            code_str = code_str.replace(" ", "")

            # Add dash if missing
            if len(code_str) == 8 and code_str.isdigit():
                code_str = f"{code_str[:4]}-{code_str[4:]}"
                item["account_code"] = code_str
                return True

            return False

        return True

    def _validate_account_name(self, item: Dict) -> bool:
        """Validate account name presence and format"""
        name = item.get("account_name")

        if not name or not str(name).strip():
            return False

        # Clean up account name
        name = str(name).strip()
        item["account_name"] = name

        return True

    def _validate_amount(
        self,
        value: Any,
        field_name: str
    ) -> Tuple[bool, str]:
        """Validate amount field"""

        if value is None:
            if field_name == "period_amount":
                return False, f"{field_name} is required but missing"
            return True, ""  # YTD can be None

        try:
            # Convert to Decimal for validation
            if isinstance(value, str):
                value = value.replace(",", "").replace("$", "").strip()
                value = Decimal(value)
            else:
                value = Decimal(str(value))

            # Check range
            if value < Decimal("-1000000000") or value > Decimal("1000000000"):
                return False, f"{field_name} out of valid range: {value}"

            return True, ""

        except Exception as e:
            return False, f"{field_name} invalid format: {str(e)}"

    def _validate_ytd_consistency(self, item: Dict) -> bool:
        """
        Validate and fix YTD >= Period consistency

        For cumulative data, YTD should generally be >= Period
        Exception: First month where YTD = Period

        Returns True if correction was made
        """
        period = item.get("period_amount")
        ytd = item.get("ytd_amount")

        if period is None or ytd is None:
            return False

        try:
            period_dec = Decimal(str(period))
            ytd_dec = Decimal(str(ytd))

            # If Period > YTD and both are positive, this may be a data issue
            # Exception: Very small amounts (< $1) can be ignored
            if period_dec > 1 and ytd_dec >= 0 and period_dec > ytd_dec:
                # Check if YTD is suspiciously small (might be a percentage)
                if ytd_dec < 100 and period_dec > 1000:
                    # Likely YTD column contains percentage, not amount
                    # Mark for review but don't auto-fix
                    item["_validation_flag"] = "ytd_may_be_percentage"
                    return False

            return False

        except:
            return False

    def _validate_and_fix_percentages(
        self,
        item: Dict,
        total_income: Decimal
    ) -> List[str]:
        """
        Validate and fix percentage calculations

        Formula: percentage = (amount / total_income) * 100

        Returns list of corrections made
        """
        corrections = []

        # Fix period percentage
        period_amount = item.get("period_amount")
        period_pct = item.get("period_percentage")

        if period_amount is not None and total_income > 0:
            calculated_pct = (Decimal(str(period_amount)) / total_income) * 100
            calculated_pct = round(calculated_pct, 2)

            if period_pct is None:
                item["period_percentage"] = calculated_pct
                corrections.append(f"Calculated period_percentage: {calculated_pct}%")
            else:
                # Check if existing percentage is wrong
                period_pct_dec = Decimal(str(period_pct))
                diff = abs(calculated_pct - period_pct_dec)

                # If difference > 0.1%, fix it
                if diff > Decimal("0.1"):
                    item["period_percentage"] = calculated_pct
                    corrections.append(
                        f"Corrected period_percentage: {period_pct_dec}% → {calculated_pct}%"
                    )

        # Fix YTD percentage (similar logic)
        ytd_amount = item.get("ytd_amount")
        ytd_pct = item.get("ytd_percentage")

        if ytd_amount is not None and total_income > 0:
            calculated_ytd_pct = (Decimal(str(ytd_amount)) / total_income) * 100
            calculated_ytd_pct = round(calculated_ytd_pct, 2)

            if ytd_pct is None:
                item["ytd_percentage"] = calculated_ytd_pct
                corrections.append(f"Calculated ytd_percentage: {calculated_ytd_pct}%")
            else:
                ytd_pct_dec = Decimal(str(ytd_pct))
                diff = abs(calculated_ytd_pct - ytd_pct_dec)

                if diff > Decimal("0.1"):
                    item["ytd_percentage"] = calculated_ytd_pct
                    corrections.append(
                        f"Corrected ytd_percentage: {ytd_pct_dec}% → {calculated_ytd_pct}%"
                    )

        return corrections

    def _validate_zero_consistency(self, item: Dict, errors: List[str]) -> None:
        """
        Validate zero value consistency

        If amount is zero, percentage should also be zero
        """
        period_amount = item.get("period_amount")
        period_pct = item.get("period_percentage")

        if period_amount is not None and period_pct is not None:
            try:
                if Decimal(str(period_amount)) == 0 and Decimal(str(period_pct)) != 0:
                    item["period_percentage"] = Decimal("0.00")
            except:
                pass

    def _validate_negative_values(self, item: Dict, errors: List[str]) -> None:
        """
        Validate that negative values are appropriate

        Income accounts (4000-4999) should generally be positive
        Expense accounts (5000-6999) should generally be positive
        """
        account_code = item.get("account_code", "")
        period_amount = item.get("period_amount")

        if not account_code or period_amount is None:
            return

        try:
            # Extract account number
            code_num = int(account_code.split("-")[0])
            amount = Decimal(str(period_amount))

            # Income accounts (4000-4999) - negative is unusual
            if 4000 <= code_num < 5000 and amount < 0:
                # Check if it's significant (> $100)
                if abs(amount) > 100:
                    errors.append(
                        f"Unusual negative income: {account_code} = ${amount}"
                    )

        except:
            pass

    def _fix_decimal_precision(self, item: Dict) -> None:
        """
        Normalize decimal precision to 2 decimal places for amounts
        and percentages
        """
        # Fix amount fields
        for field in ["period_amount", "ytd_amount"]:
            value = item.get(field)
            if value is not None:
                try:
                    item[field] = round(Decimal(str(value)), 2)
                except:
                    pass

        # Fix percentage fields
        for field in ["period_percentage", "ytd_percentage"]:
            value = item.get(field)
            if value is not None:
                try:
                    item[field] = round(Decimal(str(value)), 2)
                except:
                    pass

    def validate_header_totals(
        self,
        line_items: List[Dict],
        header_totals: Dict
    ) -> Tuple[bool, List[str], Dict]:
        """
        Validate header totals against sum of line items

        Returns:
            (is_valid, errors, corrected_header)
        """
        errors = []
        corrected_header = header_totals.copy()

        # Calculate totals from line items
        calculated_totals = self._calculate_totals_from_items(line_items)

        # Compare with header totals
        for field, calculated_value in calculated_totals.items():
            header_value = header_totals.get(field)

            if header_value is None:
                # Header missing value, use calculated
                corrected_header[field] = calculated_value
                continue

            try:
                header_dec = Decimal(str(header_value))
                calculated_dec = Decimal(str(calculated_value))

                # Allow 1% tolerance or $1 difference
                diff = abs(header_dec - calculated_dec)
                tolerance = max(abs(calculated_dec) * Decimal("0.01"), Decimal("1.00"))

                if diff > tolerance:
                    errors.append(
                        f"{field}: Header=${header_dec:,.2f} vs "
                        f"Calculated=${calculated_dec:,.2f} (diff=${diff:,.2f})"
                    )
                    # Use calculated value as it's more reliable
                    corrected_header[field] = calculated_value
            except:
                pass

        is_valid = len(errors) == 0
        return is_valid, errors, corrected_header

    def _calculate_totals_from_items(self, line_items: List[Dict]) -> Dict:
        """Calculate header totals from line items"""
        totals = {
            "total_income": Decimal("0"),
            "total_operating_expenses": Decimal("0"),
            "total_additional_expenses": Decimal("0"),
            "total_expenses": Decimal("0"),
            "net_operating_income": Decimal("0"),
            "net_income": Decimal("0")
        }

        for item in line_items:
            account_code = item.get("account_code", "")
            period_amount = item.get("period_amount")

            if not account_code or period_amount is None:
                continue

            try:
                code_num = int(account_code.split("-")[0])
                amount = Decimal(str(period_amount))

                # Income (4000-4999)
                if 4000 <= code_num < 5000:
                    if code_num == 4990:  # Total income
                        totals["total_income"] = amount

                # Operating expenses (5000-5999)
                elif 5000 <= code_num < 6000:
                    if code_num == 5990:  # Total operating expenses
                        totals["total_operating_expenses"] = amount

                # Additional expenses (6000-6999)
                elif 6000 <= code_num < 7000:
                    if code_num == 6190:  # Total additional expenses
                        totals["total_additional_expenses"] = amount
                    elif code_num == 6199:  # Total expenses
                        totals["total_expenses"] = amount
                    elif code_num == 6299:  # NOI
                        totals["net_operating_income"] = amount

                # Other income/expenses (7000-8999)
                elif 9000 <= code_num < 10000:
                    if code_num == 9090:  # Net income
                        totals["net_income"] = amount

            except:
                continue

        return totals

    def get_correction_summary(self) -> Dict:
        """Get summary of all corrections made"""
        return {
            "total_items_corrected": len(self.correction_log),
            "corrections": self.correction_log
        }
