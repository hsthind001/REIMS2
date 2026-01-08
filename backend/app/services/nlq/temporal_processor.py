"""
Temporal Query Processor for NLQ System

Handles natural language date/time expressions and converts them to structured
temporal filters for database queries.

Examples:
- "in November 2025" → {"year": 2025, "month": 11}
- "last 3 months" → {"start_date": "2025-10-01", "end_date": "2026-01-01"}
- "Q4 2025" → {"start_date": "2025-10-01", "end_date": "2025-12-31"}
- "year to date" → {"start_date": "2025-01-01", "end_date": "2026-01-08"}
- "between August and December 2025" → {"start_date": "2025-08-01", "end_date": "2025-12-31"}
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from dateutil.relativedelta import relativedelta
import dateparser
import parsedatetime
from loguru import logger

from app.config.nlq_config import nlq_config


class TemporalProcessor:
    """
    Processes temporal expressions in natural language queries

    Supports:
    - Absolute dates: "November 2025", "2025-11-15", "Nov 15, 2025"
    - Relative dates: "last month", "last 3 months", "yesterday"
    - Period expressions: "Q4 2025", "fiscal year 2025"
    - Range expressions: "between Aug and Dec 2025"
    - Special keywords: "YTD", "MTD", "QTD"
    """

    def __init__(self):
        """Initialize temporal processor"""
        self.calendar = parsedatetime.Calendar()
        self.month_names = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }

    def extract_temporal_info(self, query: str) -> Dict[str, Any]:
        """
        Extract all temporal information from a query

        Args:
            query: Natural language query

        Returns:
            Dict with temporal filters:
            {
                "has_temporal": bool,
                "temporal_type": "absolute|relative|period|range",
                "filters": {
                    "year": int,
                    "month": int,
                    "start_date": str,
                    "end_date": str,
                    "period_type": str
                },
                "original_expression": str,
                "normalized_expression": str
            }
        """
        query_lower = query.lower()

        # Try different temporal extraction methods in order
        methods = [
            self._extract_ytd_mtd_qtd,
            self._extract_quarter,
            self._extract_month_year,
            self._extract_date_range,
            self._extract_relative_period,
            self._extract_specific_date,
            self._extract_fiscal_year,
        ]

        for method in methods:
            result = method(query_lower, query)
            if result and result.get("has_temporal"):
                logger.debug(f"Temporal extraction via {method.__name__}: {result}")
                return result

        # No temporal information found
        return {
            "has_temporal": False,
            "temporal_type": None,
            "filters": {},
            "original_expression": None,
            "normalized_expression": None
        }

    def _extract_ytd_mtd_qtd(self, query_lower: str, query: str) -> Optional[Dict]:
        """Extract YTD, MTD, QTD expressions"""
        patterns = [
            (r'\b(year to date|ytd)\b', 'ytd'),
            (r'\b(month to date|mtd)\b', 'mtd'),
            (r'\b(quarter to date|qtd)\b', 'qtd')
        ]

        for pattern, period_type in patterns:
            match = re.search(pattern, query_lower)
            if match:
                start_date, end_date = self._get_period_range(period_type)
                return {
                    "has_temporal": True,
                    "temporal_type": "period",
                    "filters": {
                        "start_date": start_date,
                        "end_date": end_date,
                        "period_type": period_type
                    },
                    "original_expression": match.group(0),
                    "normalized_expression": period_type.upper()
                }

        return None

    def _extract_quarter(self, query_lower: str, query: str) -> Optional[Dict]:
        """Extract quarter expressions like 'Q4 2025', 'fourth quarter 2025'"""
        # Pattern: Q1-Q4 YYYY
        pattern = r'\b([Qq][1-4])\s*(\d{4})\b'
        match = re.search(pattern, query)
        if match:
            quarter = int(match.group(1)[1])
            year = int(match.group(2))
            start_date, end_date = self._get_quarter_range(quarter, year)

            return {
                "has_temporal": True,
                "temporal_type": "period",
                "filters": {
                    "quarter": quarter,
                    "year": year,
                    "start_date": start_date,
                    "end_date": end_date,
                    "period_type": "quarter"
                },
                "original_expression": match.group(0),
                "normalized_expression": f"Q{quarter} {year}"
            }

        # Pattern: "first quarter", "second quarter", etc.
        quarter_words = {
            'first': 1, '1st': 1,
            'second': 2, '2nd': 2,
            'third': 3, '3rd': 3,
            'fourth': 4, '4th': 4, 'last': 4
        }
        pattern = r'\b(' + '|'.join(quarter_words.keys()) + r')\s+quarter\s*(\d{4})?'
        match = re.search(pattern, query_lower)
        if match:
            quarter = quarter_words[match.group(1)]
            year = int(match.group(2)) if match.group(2) else datetime.now().year
            start_date, end_date = self._get_quarter_range(quarter, year)

            return {
                "has_temporal": True,
                "temporal_type": "period",
                "filters": {
                    "quarter": quarter,
                    "year": year,
                    "start_date": start_date,
                    "end_date": end_date,
                    "period_type": "quarter"
                },
                "original_expression": match.group(0),
                "normalized_expression": f"Q{quarter} {year}"
            }

        return None

    def _extract_month_year(self, query_lower: str, query: str) -> Optional[Dict]:
        """Extract month-year expressions like 'November 2025', 'Nov 2025'"""
        # Pattern: Month YYYY
        pattern = r'\b(' + '|'.join(self.month_names.keys()) + r')\s+(\d{4})\b'
        match = re.search(pattern, query_lower)
        if match:
            month_str = match.group(1)
            month = self.month_names[month_str]
            year = int(match.group(2))

            # Get first and last day of month
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

            return {
                "has_temporal": True,
                "temporal_type": "absolute",
                "filters": {
                    "year": year,
                    "month": month,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "period_type": "month"
                },
                "original_expression": match.group(0),
                "normalized_expression": f"{month_str.capitalize()} {year}"
            }

        # Pattern: in YYYY (just year)
        pattern = r'\bin\s+(\d{4})\b|\bduring\s+(\d{4})\b|\bfor\s+(\d{4})\b'
        match = re.search(pattern, query_lower)
        if match:
            year = int(match.group(1) or match.group(2) or match.group(3))
            start_date = datetime(year, 1, 1).date()
            end_date = datetime(year, 12, 31).date()

            return {
                "has_temporal": True,
                "temporal_type": "absolute",
                "filters": {
                    "year": year,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "period_type": "year"
                },
                "original_expression": match.group(0),
                "normalized_expression": f"Year {year}"
            }

        return None

    def _extract_date_range(self, query_lower: str, query: str) -> Optional[Dict]:
        """Extract date range expressions like 'between Aug and Dec 2025'"""
        # Pattern: between MONTH and MONTH YEAR
        pattern = r'between\s+(' + '|'.join(self.month_names.keys()) + r')\s+and\s+(' + \
                  '|'.join(self.month_names.keys()) + r')\s*(\d{4})?'
        match = re.search(pattern, query_lower)
        if match:
            start_month_str = match.group(1)
            end_month_str = match.group(2)
            year = int(match.group(3)) if match.group(3) else datetime.now().year

            start_month = self.month_names[start_month_str]
            end_month = self.month_names[end_month_str]

            start_date = datetime(year, start_month, 1).date()
            if end_month == 12:
                end_date = datetime(year, 12, 31).date()
            else:
                end_date = (datetime(year, end_month + 1, 1).date() - timedelta(days=1))

            return {
                "has_temporal": True,
                "temporal_type": "range",
                "filters": {
                    "start_year": year,
                    "start_month": start_month,
                    "end_year": year,
                    "end_month": end_month,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "period_type": "range"
                },
                "original_expression": match.group(0),
                "normalized_expression": f"{start_month_str.capitalize()} to {end_month_str.capitalize()} {year}"
            }

        return None

    def _extract_relative_period(self, query_lower: str, query: str) -> Optional[Dict]:
        """Extract relative periods like 'last 3 months', 'past year'"""
        # Pattern: last N months/years/quarters
        pattern = r'\b(?:last|past|previous)\s+(\d+)\s+(month|months|year|years|quarter|quarters)\b'
        match = re.search(pattern, query_lower)
        if match:
            count = int(match.group(1))
            unit = match.group(2).rstrip('s')  # Remove plural 's'

            today = datetime.now().date()
            if unit == 'month':
                start_date = (datetime.now() - relativedelta(months=count)).date()
                end_date = today
            elif unit == 'year':
                start_date = (datetime.now() - relativedelta(years=count)).date()
                end_date = today
            elif unit == 'quarter':
                start_date = (datetime.now() - relativedelta(months=count * 3)).date()
                end_date = today
            else:
                return None

            return {
                "has_temporal": True,
                "temporal_type": "relative",
                "filters": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "period_type": f"last_{count}_{unit}s",
                    "relative_count": count,
                    "relative_unit": unit
                },
                "original_expression": match.group(0),
                "normalized_expression": f"Last {count} {unit}s"
            }

        # Pattern: last month/year/quarter (singular, no count)
        pattern = r'\b(?:last|previous)\s+(month|year|quarter)\b'
        match = re.search(pattern, query_lower)
        if match:
            unit = match.group(1)
            today = datetime.now().date()

            if unit == 'month':
                # Last month = previous calendar month
                first_day_this_month = today.replace(day=1)
                end_date = first_day_this_month - timedelta(days=1)
                start_date = end_date.replace(day=1)
            elif unit == 'year':
                year = today.year - 1
                start_date = datetime(year, 1, 1).date()
                end_date = datetime(year, 12, 31).date()
            elif unit == 'quarter':
                # Last quarter
                current_quarter = ((today.month - 1) // 3) + 1
                last_quarter = current_quarter - 1 if current_quarter > 1 else 4
                year = today.year if current_quarter > 1 else today.year - 1
                start_date, end_date = self._get_quarter_range(last_quarter, year)
            else:
                return None

            return {
                "has_temporal": True,
                "temporal_type": "relative",
                "filters": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "period_type": f"last_{unit}",
                    "relative_unit": unit
                },
                "original_expression": match.group(0),
                "normalized_expression": f"Last {unit}"
            }

        return None

    def _extract_specific_date(self, query_lower: str, query: str) -> Optional[Dict]:
        """Extract specific dates like '2025-11-15', 'November 15, 2025'"""
        # Try using dateparser for flexible date parsing
        parsed_date = dateparser.parse(
            query,
            settings={
                'PREFER_DATES_FROM': 'past',
                'RETURN_AS_TIMEZONE_AWARE': False
            }
        )

        if parsed_date and parsed_date.date() != datetime.now().date():
            # Found a specific date that's not today
            date_obj = parsed_date.date()
            return {
                "has_temporal": True,
                "temporal_type": "absolute",
                "filters": {
                    "year": date_obj.year,
                    "month": date_obj.month,
                    "day": date_obj.day,
                    "date": date_obj.isoformat(),
                    "period_type": "day"
                },
                "original_expression": query,
                "normalized_expression": date_obj.strftime("%B %d, %Y")
            }

        return None

    def _extract_fiscal_year(self, query_lower: str, query: str) -> Optional[Dict]:
        """Extract fiscal year expressions"""
        pattern = r'\bfiscal\s+year\s+(\d{4})\b|\bfy\s*(\d{4})\b'
        match = re.search(pattern, query_lower)
        if match:
            year = int(match.group(1) or match.group(2))
            fiscal_start_month = nlq_config.FISCAL_YEAR_START_MONTH

            start_date = datetime(year, fiscal_start_month, 1).date()
            end_date = datetime(year + 1, fiscal_start_month, 1).date() - timedelta(days=1)

            return {
                "has_temporal": True,
                "temporal_type": "period",
                "filters": {
                    "fiscal_year": year,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "period_type": "fiscal_year"
                },
                "original_expression": match.group(0),
                "normalized_expression": f"Fiscal Year {year}"
            }

        return None

    def _get_period_range(self, period_type: str) -> Tuple[str, str]:
        """Get date range for YTD, MTD, QTD"""
        today = datetime.now().date()

        if period_type == 'ytd':
            start_date = datetime(today.year, nlq_config.FISCAL_YEAR_START_MONTH, 1).date()
            end_date = today
        elif period_type == 'mtd':
            start_date = today.replace(day=1)
            end_date = today
        elif period_type == 'qtd':
            current_quarter = ((today.month - nlq_config.FISCAL_YEAR_START_MONTH) // 3) + 1
            quarter_start_month = nlq_config.FISCAL_YEAR_START_MONTH + (current_quarter - 1) * 3
            start_date = datetime(today.year, quarter_start_month, 1).date()
            end_date = today
        else:
            raise ValueError(f"Unknown period type: {period_type}")

        return start_date.isoformat(), end_date.isoformat()

    def _get_quarter_range(self, quarter: int, year: int) -> Tuple[str, str]:
        """Get date range for a specific quarter"""
        fiscal_start_month = nlq_config.FISCAL_YEAR_START_MONTH
        quarter_start_month = fiscal_start_month + (quarter - 1) * 3

        if quarter_start_month > 12:
            quarter_start_month -= 12
            year += 1

        start_date = datetime(year, quarter_start_month, 1).date()

        # End of quarter (last day of third month)
        end_month = quarter_start_month + 2
        end_year = year
        if end_month > 12:
            end_month -= 12
            end_year += 1

        if end_month == 12:
            end_date = datetime(end_year, 12, 31).date()
        else:
            end_date = (datetime(end_year, end_month + 1, 1).date() - timedelta(days=1))

        return start_date.isoformat(), end_date.isoformat()

    def build_temporal_filters(
        self,
        temporal_info: Dict[str, Any],
        statement_type: str = "balance_sheet"
    ) -> Dict[str, Any]:
        """
        Build SQL filters from temporal information

        Args:
            temporal_info: Result from extract_temporal_info()
            statement_type: Type of financial statement

        Returns:
            Dict with SQL filter parameters
        """
        if not temporal_info.get("has_temporal"):
            return {}

        filters = temporal_info["filters"]
        sql_filters = {}

        # Year/month filters for monthly statements
        if "year" in filters and "month" in filters:
            sql_filters["year"] = filters["year"]
            sql_filters["month"] = filters["month"]

        # Date range filters
        if "start_date" in filters:
            sql_filters["start_date"] = filters["start_date"]
        if "end_date" in filters:
            sql_filters["end_date"] = filters["end_date"]

        # Quarter filter
        if "quarter" in filters:
            sql_filters["quarter"] = filters["quarter"]

        # Period type for aggregation
        if "period_type" in filters:
            sql_filters["period_type"] = filters["period_type"]

        return sql_filters

    def format_temporal_context(self, temporal_info: Dict[str, Any]) -> str:
        """
        Format temporal information for LLM context

        Args:
            temporal_info: Result from extract_temporal_info()

        Returns:
            Human-readable temporal context string
        """
        if not temporal_info.get("has_temporal"):
            return "No specific time period mentioned"

        normalized = temporal_info.get("normalized_expression", "Unknown period")
        filters = temporal_info.get("filters", {})

        context_parts = [f"Time Period: {normalized}"]

        if "start_date" in filters and "end_date" in filters:
            context_parts.append(f"Date Range: {filters['start_date']} to {filters['end_date']}")

        if "period_type" in filters:
            context_parts.append(f"Period Type: {filters['period_type']}")

        return " | ".join(context_parts)


# Singleton instance
temporal_processor = TemporalProcessor()
