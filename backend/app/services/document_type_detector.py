"""
Document Type Detector Service

Detects document type and month from filenames using pattern matching.
"""
import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DocumentTypeDetector:
    """
    Detects document type and month from filenames using pattern matching.
    """
    
    # Document type patterns (case-insensitive)
    DOCUMENT_TYPE_PATTERNS = {
        'balance_sheet': [
            r'balance.*sheet',
            r'\bbalance\b',
            r'\bbs\b',
            r'balance.*statement'
        ],
        'income_statement': [
            r'income.*statement',
            r'\bincome\b',
            r'p&l',
            r'p\s*&\s*l',
            r'profit.*loss',
            r'profit.*and.*loss',
            r'pl\b'
        ],
        'cash_flow': [
            r'cash.*flow',
            r'\bcf\b',
            r'cashflow',
            r'cash.*flow.*statement'
        ],
        'rent_roll': [
            r'rent.*roll',
            r'rentroll',
            r'lease.*roll',
            r'tenant.*roll'
        ]
    }
    
    # Month name mapping
    MONTH_NAMES = {
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
    
    # Quarter to month mapping (Q1 = Jan, Q2 = Apr, Q3 = Jul, Q4 = Oct)
    QUARTER_MONTHS = {
        'q1': 1, 'q2': 4, 'q3': 7, 'q4': 10
    }
    
    def detect_from_filename(self, filename: str) -> Dict[str, Any]:
        """
        Detect document type from filename patterns.
        
        Args:
            filename: Original filename (e.g., "ESP_2024_12_Balance_Sheet.pdf")
        
        Returns:
            {
                "document_type": "balance_sheet" | "income_statement" | "cash_flow" | "rent_roll" | "unknown",
                "confidence": float (0.0-1.0),
                "detected_pattern": str
            }
        """
        filename_lower = filename.lower()
        
        # Try each document type pattern
        for doc_type, patterns in self.DOCUMENT_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, filename_lower, re.IGNORECASE):
                    # Calculate confidence based on pattern specificity
                    confidence = 0.9 if 'sheet' in pattern or 'statement' in pattern else 0.7
                    logger.info(f"Detected document type '{doc_type}' from filename '{filename}' using pattern '{pattern}'")
                    return {
                        "document_type": doc_type,
                        "confidence": confidence,
                        "detected_pattern": pattern
                    }
        
        # No pattern matched
        logger.warning(f"Could not detect document type from filename '{filename}'")
        return {
            "document_type": "unknown",
            "confidence": 0.0,
            "detected_pattern": None
        }
    
    def detect_month_from_filename(self, filename: str, year: int) -> Optional[int]:
        """
        Extract month from filename patterns.
        
        Supports:
        - Numeric month: "ESP_2024_12_Balance_Sheet.pdf" → 12
        - Month name: "ESP_2024_December_Balance_Sheet.pdf" → 12
        - Quarter: "ESP_2024_Q4_Balance_Sheet.pdf" → 10 (Q4 = Oct)
        - Month abbreviation: "ESP_2024_Dec_Balance_Sheet.pdf" → 12
        
        Args:
            filename: Original filename
            year: Year for context (used in some patterns)
        
        Returns:
            Month number (1-12) if detected, None otherwise
        """
        filename_lower = filename.lower()
        
        # Pattern 1: Numeric month (1-12) after year
        # Examples: "ESP_2024_12_...", "2024_12_...", "2024-12-..."
        numeric_patterns = [
            rf'{year}[_\-\s]+(\d{{1,2}})[_\-\s]',  # Year followed by 1-2 digits
            rf'(\d{{1,2}})[_\-\s]+{year}',  # 1-2 digits followed by year
            rf'[_\-\s](\d{{1,2}})[_\-\s]',  # Standalone 1-2 digits
        ]
        
        for pattern in numeric_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                month_num = int(match.group(1))
                if 1 <= month_num <= 12:
                    logger.info(f"Detected month {month_num} from filename '{filename}' using numeric pattern")
                    return month_num
        
        # Pattern 2: Month name (full or abbreviated)
        for month_name, month_num in self.MONTH_NAMES.items():
            # Look for month name as whole word
            pattern = rf'\b{re.escape(month_name)}\b'
            if re.search(pattern, filename_lower, re.IGNORECASE):
                logger.info(f"Detected month {month_num} ({month_name}) from filename '{filename}'")
                return month_num
        
        # Pattern 3: Quarter (Q1, Q2, Q3, Q4)
        quarter_pattern = r'\bq([1-4])\b'
        match = re.search(quarter_pattern, filename_lower, re.IGNORECASE)
        if match:
            quarter = match.group(1).lower()
            month_num = self.QUARTER_MONTHS.get(f'q{quarter}')
            if month_num:
                logger.info(f"Detected month {month_num} from quarter Q{quarter} in filename '{filename}'")
                return month_num
        
        # Pattern 4: Month number in filename without year context
        # Look for standalone 01-12 or 1-12
        standalone_month = re.search(r'[_\-\s](\d{1,2})[_\-\s]', filename_lower)
        if standalone_month:
            month_num = int(standalone_month.group(1))
            if 1 <= month_num <= 12:
                # Additional validation: check if it's not part of a date or year
                context = filename_lower[max(0, standalone_month.start()-5):standalone_month.end()+5]
                if not re.search(r'\d{4}', context):  # Not near a 4-digit year
                    logger.info(f"Detected month {month_num} from standalone pattern in filename '{filename}'")
                    return month_num
        
        logger.info(f"Could not detect month from filename '{filename}', will default to 1")
        return None

