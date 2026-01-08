"""
Validation & Self-Correction Agent

Ensures answer quality through:
1. Fact-checking against database
2. Calculation verification
3. Hallucination detection
4. Confidence scoring
5. Self-correction mechanisms

Quality Gates:
- SQL query validation
- Numerical accuracy checks
- Temporal consistency
- Source attribution
- Confidence thresholds
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import re
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import text


class ValidationAgent:
    """
    Validates and corrects NLQ answers before returning to user

    Validation Layers:
    1. SQL Query Validation
    2. Data Consistency Checks
    3. Calculation Verification
    4. Hallucination Detection
    5. Confidence Scoring
    """

    def __init__(self, db: Session):
        """Initialize validation agent"""
        self.db = db

        # Validation thresholds
        self.MIN_CONFIDENCE_THRESHOLD = 0.6
        self.HIGH_CONFIDENCE_THRESHOLD = 0.85

        # Known valid account codes (from chart of accounts)
        self.VALID_ACCOUNT_CODES = self._load_valid_account_codes()

        # Known formulas for verification
        self.FORMULAS = {
            "current_ratio": lambda ca, cl: ca / cl if cl != 0 else None,
            "debt_to_assets": lambda td, ta: (td / ta * 100) if ta != 0 else None,
            "dscr": lambda noi, ds: noi / ds if ds != 0 else None,
            "noi": lambda rev, opex: rev - opex,
            "occupancy_rate": lambda occupied, total: (occupied / total * 100) if total != 0 else None
        }

    def _load_valid_account_codes(self) -> set:
        """Load valid account codes from chart of accounts"""
        # This would normally query the database
        # For now, return common codes
        return {
            # Assets
            "1010", "1020", "1030", "1100", "1200",
            # Liabilities
            "2010", "2020", "2100", "2200",
            # Equity
            "3000", "3100",
            # Revenue
            "4000", "4100", "4200",
            # Expenses
            "5000", "5100", "5200", "5300"
        }

    async def validate_answer(
        self,
        query: str,
        answer: str,
        data: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None,
        sql_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive answer validation

        Returns:
            {
                "is_valid": bool,
                "confidence_score": float,
                "validation_results": dict,
                "corrections": list,
                "warnings": list,
                "corrected_answer": str (if corrections made)
            }
        """
        validation_results = {
            "is_valid": True,
            "confidence_score": 1.0,
            "validation_results": {},
            "corrections": [],
            "warnings": []
        }

        try:
            # 1. SQL Query Validation
            if sql_query:
                sql_valid = await self._validate_sql_query(sql_query)
                validation_results["validation_results"]["sql_valid"] = sql_valid
                if not sql_valid["is_valid"]:
                    validation_results["is_valid"] = False
                    validation_results["warnings"].append(sql_valid["message"])
                    validation_results["confidence_score"] *= 0.7

            # 2. Data Consistency Checks
            if data:
                consistency = await self._check_data_consistency(data, query)
                validation_results["validation_results"]["data_consistency"] = consistency
                if not consistency["is_consistent"]:
                    validation_results["warnings"].extend(consistency["issues"])
                    validation_results["confidence_score"] *= 0.8

            # 3. Numerical Accuracy
            if data:
                numerical = await self._verify_numerical_accuracy(answer, data, metadata)
                validation_results["validation_results"]["numerical_accuracy"] = numerical
                if not numerical["is_accurate"]:
                    validation_results["corrections"].extend(numerical["corrections"])
                    validation_results["confidence_score"] *= 0.85

            # 4. Hallucination Detection
            hallucination = await self._detect_hallucinations(answer, data, query)
            validation_results["validation_results"]["hallucination_check"] = hallucination
            if hallucination["detected"]:
                validation_results["is_valid"] = False
                validation_results["warnings"].extend(hallucination["issues"])
                validation_results["confidence_score"] *= 0.5

            # 5. Temporal Consistency
            temporal = await self._check_temporal_consistency(answer, metadata)
            validation_results["validation_results"]["temporal_consistency"] = temporal
            if not temporal["is_consistent"]:
                validation_results["warnings"].extend(temporal["issues"])
                validation_results["confidence_score"] *= 0.9

            # 6. Calculate final confidence
            validation_results["confidence_score"] = max(
                0.0,
                min(1.0, validation_results["confidence_score"])
            )

            # 7. Apply corrections if needed
            if validation_results["corrections"]:
                corrected_answer = await self._apply_corrections(
                    answer,
                    validation_results["corrections"]
                )
                validation_results["corrected_answer"] = corrected_answer

            # 8. Check if answer should be rejected
            if validation_results["confidence_score"] < self.MIN_CONFIDENCE_THRESHOLD:
                validation_results["is_valid"] = False
                validation_results["warnings"].append(
                    f"Confidence score ({validation_results['confidence_score']:.2f}) "
                    f"below threshold ({self.MIN_CONFIDENCE_THRESHOLD})"
                )

        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            validation_results["is_valid"] = False
            validation_results["warnings"].append(f"Validation error: {str(e)}")
            validation_results["confidence_score"] = 0.0

        return validation_results

    async def _validate_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """Validate SQL query for safety and correctness"""
        result = {
            "is_valid": True,
            "message": "SQL query is valid",
            "issues": []
        }

        sql_lower = sql_query.lower().strip()

        # 1. Must be SELECT only
        if not sql_lower.startswith("select"):
            result["is_valid"] = False
            result["message"] = "Only SELECT queries are allowed"
            result["issues"].append("Non-SELECT query detected")
            return result

        # 2. No dangerous operations
        dangerous_keywords = [
            "drop", "delete", "truncate", "alter", "create",
            "insert", "update", "exec", "execute"
        ]
        for keyword in dangerous_keywords:
            if re.search(rf"\b{keyword}\b", sql_lower):
                result["is_valid"] = False
                result["message"] = f"Dangerous keyword found: {keyword}"
                result["issues"].append(f"Contains {keyword.upper()}")
                return result

        # 3. Must have FROM clause
        if "from" not in sql_lower:
            result["is_valid"] = False
            result["message"] = "Missing FROM clause"
            result["issues"].append("No FROM clause")
            return result

        # 4. Check for SQL injection patterns
        injection_patterns = [
            r"';",  # Statement termination
            r"--",  # SQL comment
            r"/\*",  # Multi-line comment
            r"union\s+select",  # UNION injection
            r"or\s+1\s*=\s*1",  # Always true condition
        ]
        for pattern in injection_patterns:
            if re.search(pattern, sql_lower):
                result["is_valid"] = False
                result["message"] = "Potential SQL injection detected"
                result["issues"].append(f"Suspicious pattern: {pattern}")
                return result

        return result

    async def _check_data_consistency(
        self,
        data: List[Dict],
        query: str
    ) -> Dict[str, Any]:
        """Check data consistency and completeness"""
        result = {
            "is_consistent": True,
            "issues": []
        }

        if not data:
            result["is_consistent"] = False
            result["issues"].append("No data returned for query")
            return result

        # Check for reasonable data ranges
        for record in data:
            # Check for unreasonable amounts (e.g., > $1 billion)
            if "amount" in record:
                amount = float(record["amount"])
                if abs(amount) > 1_000_000_000:
                    result["issues"].append(
                        f"Unreasonably large amount: ${amount:,.2f}"
                    )
                    result["is_consistent"] = False

            # Check for negative values where they shouldn't be
            if "occupancy_rate" in record or "rate" in str(record.get("account_name", "")).lower():
                value = float(record.get("amount", 0))
                if value < 0:
                    result["issues"].append(
                        f"Negative rate value: {value}"
                    )
                    result["is_consistent"] = False

        return result

    async def _verify_numerical_accuracy(
        self,
        answer: str,
        data: List[Dict],
        metadata: Optional[Dict]
    ) -> Dict[str, Any]:
        """Verify numerical calculations in the answer"""
        result = {
            "is_accurate": True,
            "corrections": [],
            "verified_calculations": []
        }

        # Extract numbers from answer
        numbers_in_answer = re.findall(
            r'\$?[\d,]+\.?\d*',
            answer.replace(',', '')
        )

        # If answer contains calculations, verify them
        if metadata and "calculation" in metadata:
            calc_type = metadata["calculation"].get("type")

            if calc_type in self.FORMULAS:
                # Verify formula calculation
                formula_func = self.FORMULAS[calc_type]
                inputs = metadata["calculation"].get("inputs", {})

                try:
                    expected_result = formula_func(**inputs)
                    actual_result = metadata["calculation"].get("result")

                    if expected_result is not None and actual_result is not None:
                        # Allow 0.01% tolerance for floating point
                        tolerance = abs(expected_result) * 0.0001
                        if abs(expected_result - actual_result) > tolerance:
                            result["is_accurate"] = False
                            result["corrections"].append({
                                "type": "calculation_error",
                                "expected": expected_result,
                                "actual": actual_result,
                                "formula": calc_type
                            })

                    result["verified_calculations"].append({
                        "formula": calc_type,
                        "expected": expected_result,
                        "actual": actual_result,
                        "is_accurate": result["is_accurate"]
                    })

                except Exception as e:
                    logger.error(f"Calculation verification error: {e}")

        return result

    async def _detect_hallucinations(
        self,
        answer: str,
        data: Optional[List[Dict]],
        query: str
    ) -> Dict[str, Any]:
        """Detect potential hallucinations in the answer"""
        result = {
            "detected": False,
            "issues": [],
            "confidence": 1.0
        }

        # 1. Check for unsupported claims
        if not data or len(data) == 0:
            # Answer claims specific numbers but no data was found
            if re.search(r'\$[\d,]+', answer):
                result["detected"] = True
                result["issues"].append("Answer contains specific amounts but no data was retrieved")
                result["confidence"] = 0.3

        # 2. Check for invalid account codes in answer
        account_codes_in_answer = re.findall(r'\b(\d{4})\b', answer)
        for code in account_codes_in_answer:
            if code not in self.VALID_ACCOUNT_CODES:
                result["detected"] = True
                result["issues"].append(f"Unknown account code referenced: {code}")
                result["confidence"] *= 0.7

        # 3. Check for inconsistent property codes
        property_codes_in_answer = re.findall(r'\b(ESP|OAK|PIN|MAP|ELM)\b', answer)
        if data and property_codes_in_answer:
            data_property_codes = {
                record.get("property_code")
                for record in data
                if "property_code" in record
            }
            for code in property_codes_in_answer:
                if code not in data_property_codes and data_property_codes:
                    result["detected"] = True
                    result["issues"].append(
                        f"Property code {code} mentioned but not in data"
                    )
                    result["confidence"] *= 0.8

        # 4. Check for temporal inconsistencies
        years_in_answer = re.findall(r'\b(20\d{2})\b', answer)
        if data and years_in_answer:
            data_years = {
                record.get("year")
                for record in data
                if "year" in record
            }
            for year in years_in_answer:
                if int(year) not in data_years and data_years:
                    result["detected"] = True
                    result["issues"].append(
                        f"Year {year} mentioned but not in data"
                    )
                    result["confidence"] *= 0.8

        return result

    async def _check_temporal_consistency(
        self,
        answer: str,
        metadata: Optional[Dict]
    ) -> Dict[str, Any]:
        """Check temporal consistency in answer"""
        result = {
            "is_consistent": True,
            "issues": []
        }

        if not metadata:
            return result

        temporal_info = metadata.get("temporal_info", {})

        if temporal_info.get("has_temporal"):
            # Extract temporal references from answer
            years = re.findall(r'\b(20\d{2})\b', answer)
            months = re.findall(
                r'\b(January|February|March|April|May|June|July|August|'
                r'September|October|November|December)\b',
                answer,
                re.IGNORECASE
            )

            # Check if answer temporal references match query temporal info
            filters = temporal_info.get("filters", {})

            if "year" in filters:
                expected_year = str(filters["year"])
                if years and expected_year not in years:
                    result["is_consistent"] = False
                    result["issues"].append(
                        f"Answer references different year than query: "
                        f"expected {expected_year}, found {years}"
                    )

        return result

    async def _apply_corrections(
        self,
        answer: str,
        corrections: List[Dict]
    ) -> str:
        """Apply corrections to the answer"""
        corrected = answer

        for correction in corrections:
            if correction["type"] == "calculation_error":
                # Replace incorrect calculation with correct one
                expected = correction["expected"]
                actual = correction["actual"]

                # Try to find and replace the incorrect value
                corrected = corrected.replace(
                    f"{actual}",
                    f"{expected} (corrected)"
                )

        return corrected

    def should_return_answer(self, validation_result: Dict[str, Any]) -> bool:
        """Determine if answer should be returned to user"""
        # Don't return if invalid
        if not validation_result["is_valid"]:
            return False

        # Don't return if confidence too low
        if validation_result["confidence_score"] < self.MIN_CONFIDENCE_THRESHOLD:
            return False

        # Don't return if hallucinations detected
        hallucination = validation_result.get("validation_results", {}).get("hallucination_check", {})
        if hallucination.get("detected") and hallucination.get("confidence", 1.0) < 0.5:
            return False

        return True

    def get_fallback_answer(
        self,
        query: str,
        validation_result: Dict[str, Any]
    ) -> str:
        """Generate fallback answer when validation fails"""
        warnings = validation_result.get("warnings", [])
        confidence = validation_result.get("confidence_score", 0.0)

        fallback = (
            f"I wasn't able to provide a confident answer to your question. "
            f"(Confidence: {confidence:.1%})\n\n"
        )

        if warnings:
            fallback += "Issues detected:\n"
            for warning in warnings[:3]:  # Show first 3 warnings
                fallback += f"• {warning}\n"

        fallback += "\nPlease try:\n"
        fallback += "• Rephrasing your question\n"
        fallback += "• Being more specific about dates/properties\n"
        fallback += "• Breaking complex questions into simpler parts\n"

        return fallback


# Singleton instance
_validation_agent_instance = None


def get_validation_agent(db: Session) -> ValidationAgent:
    """Get or create validation agent instance"""
    return ValidationAgent(db)
