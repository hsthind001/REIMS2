"""
Period Range Detector

Detects period ranges in filenames and extracts the ending period.
This is critical for handling filenames like "Income_Statement_esp_Accrual-5.25-6.25.pdf"
which represent a period from May 2025 to June 2025.

Financial statements spanning multiple periods are filed under the ending period.
"""

import re
from typing import Optional, Dict, Tuple
from datetime import datetime


class PeriodRangeDetector:
    """
    Detects period ranges in filenames and extracts the ending period.

    Patterns supported:
    - MM.YY-MM.YY (e.g., "5.25-6.25" = May 2025 to June 2025)
    - MM-YY-MM-YY (e.g., "5-25-6-25")
    - YYYY.MM-YYYY.MM (e.g., "2025.05-2025.06")
    - MM/YY-MM/YY or MM/YYYY-MM/YYYY
    """

    PERIOD_RANGE_PATTERNS = [
        # Pattern 1: MM.YY-MM.YY (most common)
        # Example: "5.25-6.25" = May 2025 to June 2025
        r'(\d{1,2})\.(\d{2})-(\d{1,2})\.(\d{2})',

        # Pattern 2: MM-YY-MM-YY
        # Example: "5-25-6-25"
        r'(\d{1,2})-(\d{2})-(\d{1,2})-(\d{2})(?!\.)',

        # Pattern 3: YYYY.MM-YYYY.MM or YYYY-MM-YYYY-MM
        # Example: "2025.05-2025.06" or "2025-05-2025-06"
        r'(\d{4})[\.\-](\d{1,2})[\.\-](\d{4})[\.\-](\d{1,2})',

        # Pattern 4: MM/YY-MM/YY or MM/YYYY-MM/YYYY
        # Example: "5/25-6/25" or "5/2025-6/2025"
        r'(\d{1,2})/(\d{2,4})-(\d{1,2})/(\d{2,4})',
    ]

    def detect_period_range(self, filename: str) -> Optional[Dict]:
        """
        Detect if filename contains a period range.

        Args:
            filename: The filename to analyze

        Returns:
            Dictionary with period range information:
            {
                "is_range": True,
                "start_month": int,
                "start_year": int,
                "end_month": int,
                "end_year": int,
                "pattern": str,
                "matched_text": str
            }
            or None if no range detected
        """
        for pattern in self.PERIOD_RANGE_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                groups = match.groups()

                try:
                    # Pattern 1 & 2: MM.YY-MM.YY or MM-YY-MM-YY
                    if len(groups) == 4 and len(groups[1]) == 2 and len(groups[3]) == 2:
                        start_month = int(groups[0])
                        start_year = self._parse_year(groups[1])
                        end_month = int(groups[2])
                        end_year = self._parse_year(groups[3])

                    # Pattern 3: YYYY.MM-YYYY.MM or YYYY-MM-YYYY-MM
                    elif len(groups) == 4 and len(groups[0]) == 4 and len(groups[2]) == 4:
                        start_year = int(groups[0])
                        start_month = int(groups[1])
                        end_year = int(groups[2])
                        end_month = int(groups[3])

                    # Pattern 4: MM/YY-MM/YY or MM/YYYY-MM/YYYY
                    elif len(groups) == 4:
                        start_month = int(groups[0])
                        start_year = self._parse_year(groups[1])
                        end_month = int(groups[2])
                        end_year = self._parse_year(groups[3])

                    else:
                        continue

                    # Validate months (1-12)
                    if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
                        continue

                    # Validate year progression (end >= start)
                    if end_year < start_year:
                        continue
                    if end_year == start_year and end_month < start_month:
                        continue

                    return {
                        "is_range": True,
                        "start_month": start_month,
                        "start_year": start_year,
                        "end_month": end_month,
                        "end_year": end_year,
                        "pattern": pattern,
                        "matched_text": match.group(0)
                    }

                except (ValueError, IndexError):
                    # Invalid numbers - continue to next pattern
                    continue

        return None

    def get_statement_period(self, period_range: Dict) -> Tuple[int, int]:
        """
        For period range statements, return the ending period
        (the period this statement should be filed under).

        Financial statements spanning multiple periods are typically
        filed under the ending period.

        Args:
            period_range: Dictionary returned by detect_period_range()

        Returns:
            Tuple of (month, year) for the ending period
        """
        return (period_range["end_month"], period_range["end_year"])

    def _parse_year(self, year_str: str) -> int:
        """
        Convert 2-digit or 4-digit year string to 4-digit year.

        Args:
            year_str: Year as string (e.g., "25", "2025")

        Returns:
            4-digit year as integer

        Examples:
            "25" → 2025
            "99" → 1999
            "2025" → 2025
        """
        year = int(year_str)

        if year < 100:
            # 2-digit year - convert to 4-digit
            # Assume 20XX for years 00-50, 19XX for 51-99
            if year <= 50:
                year += 2000
            else:
                year += 1900

        return year

    def format_period_range(self, period_range: Dict) -> str:
        """
        Format a period range for display.

        Args:
            period_range: Dictionary returned by detect_period_range()

        Returns:
            Formatted string like "May 2025 - June 2025"
        """
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        start_month_name = month_names[period_range["start_month"] - 1]
        end_month_name = month_names[period_range["end_month"] - 1]

        if period_range["start_year"] == period_range["end_year"]:
            # Same year
            return f"{start_month_name} - {end_month_name} {period_range['end_year']}"
        else:
            # Different years
            return f"{start_month_name} {period_range['start_year']} - {end_month_name} {period_range['end_year']}"

    def is_likely_period_range_filename(self, filename: str) -> bool:
        """
        Quick check if filename likely contains a period range.

        Args:
            filename: The filename to check

        Returns:
            True if filename likely contains a period range pattern
        """
        # Quick regex check for common patterns
        return bool(re.search(r'\d{1,2}[\.\-/]\d{2,4}[\-]\d{1,2}[\.\-/]\d{2,4}', filename))
