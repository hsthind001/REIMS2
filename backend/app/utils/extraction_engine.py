from typing import Dict, List, Optional, Any, TYPE_CHECKING
import logging
from app.utils.engines.pymupdf_engine import PyMuPDFEngine
from app.utils.engines.pdfplumber_engine import PDFPlumberEngine
from app.utils.engines.base_extractor import ExtractionResult
from app.utils.pdf_classifier import PDFClassifier, DocumentType
from app.utils.quality_validator import QualityValidator
import time

if TYPE_CHECKING:
    from app.services.model_scoring_service import ScoringFactors

# Optional engines with heavy dependencies - import gracefully
logger = logging.getLogger(__name__)



class MultiEngineExtractor:
    """
    Multi-engine PDF extraction orchestrator
    
    Automatically selects and runs optimal extraction engines based on document type,
    validates results, and provides quality scores
    """
    
    def __init__(self, scoring_factors: Optional['ScoringFactors'] = None):
        # Import here to avoid circular import
        from app.services.model_scoring_service import ModelScoringService
        
        # Initialize core engines (always available)
        self.pymupdf = PyMuPDFEngine()
        self.pdfplumber = PDFPlumberEngine()

        # Initialize optional engines via ModelManager (Singleton)
        from app.utils.model_manager import model_manager
        
        self.camelot = model_manager.camelot_engine
        self.ocr = model_manager.ocr_engine
        self.layoutlm = model_manager.layoutlm_engine
        self.easyocr = model_manager.easyocr_engine

        # Initialize utilities
        self.classifier = PDFClassifier()
        self.validator = QualityValidator()
        
        # Initialize external scoring service (models don't calculate their own confidence)
        self.scoring_service = ModelScoringService(scoring_factors=scoring_factors)

        # Log available engines
        available_engines = ['PyMuPDF', 'PDFPlumber']
        if self.camelot:
            available_engines.append('Camelot')
        if self.ocr:
            available_engines.append('OCR')
        if self.layoutlm:
            available_engines.append('LayoutLM')
        if self.easyocr:
            available_engines.append('EasyOCR')
        logger.info(f"MultiEngineExtractor initialized with {len(available_engines)} engines: {available_engines}")
    
    def detect_property_name(self, pdf_data: bytes, available_properties: list) -> Dict:
        """
        Detect property name from PDF content

        Searches for property names, codes, and addresses in first 2 pages

        Args:
            pdf_data: PDF file bytes
            available_properties: List of dicts with property_code, property_name, address

        Returns:
            dict: {
                "detected_property_code": str or None,
                "detected_property_name": str or None,
                "confidence": float,
                "matches_found": list
            }
        """
        try:
            # Quick extraction of first 2 pages
            result = self.pymupdf.extract_text(pdf_data)
            if not result.get("success"):
                return {"detected_property_code": None, "detected_property_name": None, "confidence": 0, "matches_found": []}

            # Get text from first 2 pages
            pages = result.get("pages", [])
            sample_text = ""
            for page in pages[:2]:
                sample_text += page.get("text", "")

            sample_lower = sample_text.lower()

            # Search for each property
            matches = []
            best_match = None
            best_score = 0

            for prop in available_properties:
                score = 0
                prop_matches = []

                # Check property code (e.g., ESP001, HMND001)
                if prop.get('property_code') and prop['property_code'].lower() in sample_lower:
                    score += 40
                    prop_matches.append(f"Code: {prop['property_code']}")

                # Check property name (e.g., "Eastern Shore Plaza", "Hammond Aire")
                if prop.get('property_name'):
                    # Split name into words and check each
                    name_words = prop['property_name'].lower().split()
                    matched_words = sum(1 for word in name_words if len(word) > 3 and word in sample_lower)
                    if matched_words > 0:
                        word_score = (matched_words / len(name_words)) * 30
                        score += word_score
                        prop_matches.append(f"Name: {matched_words}/{len(name_words)} words")

                # Check address/city if available
                if prop.get('city') and prop['city'].lower() in sample_lower:
                    score += 20
                    prop_matches.append(f"City: {prop['city']}")

                if score > best_score:
                    best_score = score
                    best_match = prop
                    matches = prop_matches

            if best_match and best_score >= 30:
                return {
                    "detected_property_code": best_match.get('property_code'),
                    "detected_property_name": best_match.get('property_name'),
                    "confidence": round(best_score, 1),
                    "matches_found": matches
                }

            return {
                "detected_property_code": None,
                "detected_property_name": None,
                "confidence": 0,
                "matches_found": []
            }

        except Exception as e:
            return {
                "detected_property_code": None,
                "detected_property_name": None,
                "confidence": 0,
                "matches_found": [],
                "error": str(e)
            }

    def detect_property_with_intelligence(self, pdf_data: bytes, available_properties: list) -> Dict:
        """
        Enhanced property detection with A/R filtering and header/title focus.

        This method distinguishes between:
        - Primary property (in header, title, entity name)
        - Referenced properties (in A/R line items, notes)

        Scoring Strategy:
        - Header/Title (50% weight): First 5 lines, entity name
        - Metadata Fields (30% weight): "Property:", "Entity:", "Location:"
        - Body Content (20% weight): Mentions NOT in A/R context
        - Filename bonus (+10%): Property abbreviation in filename

        Args:
            pdf_data: PDF file bytes
            available_properties: List of dicts with property_code, property_name, city

        Returns:
            dict: {
                "primary_property": {
                    "code": str,
                    "name": str,
                    "confidence": float,
                    "evidence": [str]
                },
                "referenced_properties": [
                    {
                        "code": str,
                        "name": str,
                        "confidence": float,
                        "evidence": [str]
                    }
                ],
                "recommendation": str,  # property_code to use
                "validation_status": str  # "HIGH_CONFIDENCE", "MEDIUM_CONFIDENCE", "UNCERTAIN"
            }
        """
        import re

        try:
            # Extract text from first page
            result = self.pymupdf.extract_text(pdf_data)
            if not result.get("success"):
                return {
                    "primary_property": None,
                    "referenced_properties": [],
                    "recommendation": None,
                    "validation_status": "UNCERTAIN"
                }

            pages = result.get("pages", [])
            if not pages:
                return {
                    "primary_property": None,
                    "referenced_properties": [],
                    "recommendation": None,
                    "validation_status": "UNCERTAIN"
                }

            first_page_text = pages[0].get("text", "")
            first_page_lines = first_page_text.split('\n')

            # Extract header (first 5 non-empty lines)
            header_lines = [line.strip() for line in first_page_lines[:10] if line.strip()][:5]
            header_text = ' '.join(header_lines)

            # A/R exclusion patterns (case-insensitive)
            ar_patterns = [
                r'receivable\s+from',
                r'due\s+from',
                r'owed\s+by',
                r'a/r\s+',
                r'account\s+receivable',
                r'\b\d{4}-\d{4}\b',  # Account codes like 1100-0001
                r'payable\s+to',
                r'due\s+to'
            ]

            # Property detection results
            property_scores = {}

            for prop in available_properties:
                prop_code = prop.get('property_code', '')
                prop_name = prop.get('property_name', '')
                prop_city = prop.get('city', '')

                if not prop_code:
                    continue

                # Initialize scoring
                header_score = 0
                metadata_score = 0
                body_score = 0
                evidence = []
                ar_mentions = []

                # === LAYER 1: Header/Title Analysis (50% weight, max 50 points) ===
                header_lower = header_text.lower()

                # Check for property code in header
                if prop_code.lower() in header_lower:
                    header_score += 25
                    evidence.append(f"Code '{prop_code}' in header")

                # Check for property name words in header
                if prop_name:
                    name_words = [w for w in prop_name.lower().split() if len(w) > 3]
                    matched = sum(1 for w in name_words if w in header_lower)
                    if matched > 0:
                        name_match_score = (matched / len(name_words)) * 25
                        header_score += name_match_score
                        evidence.append(f"Name words ({matched}/{len(name_words)}) in header")

                # === LAYER 2: Metadata Fields (30% weight, max 30 points) ===
                # Look for "Property:", "Entity:", "Location:" fields
                metadata_patterns = [
                    rf'property\s*:?\s*{re.escape(prop_name)}',
                    rf'entity\s*:?\s*{re.escape(prop_name)}',
                    rf'location\s*:?\s*{re.escape(prop_name)}',
                    rf'property\s*:?\s*{re.escape(prop_code)}',
                ]

                page_lower = first_page_text.lower()
                for pattern in metadata_patterns:
                    if re.search(pattern, page_lower, re.IGNORECASE):
                        metadata_score += 15
                        evidence.append(f"Metadata field match")
                        break

                # Check city in metadata
                if prop_city and re.search(rf'city\s*:?\s*{re.escape(prop_city)}', page_lower, re.IGNORECASE):
                    metadata_score += 15
                    evidence.append(f"City '{prop_city}' in metadata")

                # === LAYER 3: Body Content (20% weight, max 20 points) ===
                # Find mentions NOT in A/R context
                for line in first_page_lines:
                    line_lower = line.lower()

                    # Skip if line contains A/R patterns
                    is_ar_line = any(re.search(pattern, line_lower, re.IGNORECASE) for pattern in ar_patterns)

                    if prop_name and prop_name.lower() in line_lower:
                        if is_ar_line:
                            ar_mentions.append(line.strip())
                        else:
                            body_score += 5  # Non-A/R mention
                            if body_score == 5:  # First non-A/R mention
                                evidence.append(f"Property name in body (non-A/R)")

                    if prop_code.lower() in line_lower:
                        if is_ar_line:
                            ar_mentions.append(line.strip())
                        else:
                            body_score += 5  # Non-A/R mention
                            if len([e for e in evidence if 'code in body' in e.lower()]) == 0:
                                evidence.append(f"Property code in body (non-A/R)")

                # Cap scores at their maximums
                header_score = min(header_score, 50)
                metadata_score = min(metadata_score, 30)
                body_score = min(body_score, 20)

                # Total score
                total_score = header_score + metadata_score + body_score

                # Store results
                property_scores[prop_code] = {
                    "code": prop_code,
                    "name": prop_name,
                    "total_score": total_score,
                    "header_score": header_score,
                    "metadata_score": metadata_score,
                    "body_score": body_score,
                    "evidence": evidence,
                    "ar_mentions": ar_mentions
                }

            # Find primary property (highest score)
            if not property_scores:
                return {
                    "primary_property": None,
                    "referenced_properties": [],
                    "recommendation": None,
                    "validation_status": "UNCERTAIN"
                }

            sorted_properties = sorted(property_scores.items(), key=lambda x: x[1]["total_score"], reverse=True)

            primary_code, primary_data = sorted_properties[0]
            primary_score = primary_data["total_score"]

            # Find referenced properties (lower scores, with A/R mentions)
            referenced = []
            for prop_code, prop_data in sorted_properties[1:]:
                if prop_data["ar_mentions"] and prop_data["total_score"] < primary_score * 0.5:
                    referenced.append({
                        "code": prop_code,
                        "name": prop_data["name"],
                        "confidence": round(prop_data["total_score"], 1),
                        "evidence": prop_data["ar_mentions"][:2]  # First 2 A/R mentions
                    })

            # Determine validation status
            if primary_score >= 60:
                validation_status = "HIGH_CONFIDENCE"
            elif primary_score >= 40:
                validation_status = "MEDIUM_CONFIDENCE"
            else:
                validation_status = "UNCERTAIN"

            return {
                "primary_property": {
                    "code": primary_code,
                    "name": primary_data["name"],
                    "confidence": round(primary_score, 1),
                    "evidence": primary_data["evidence"]
                } if primary_score >= 20 else None,
                "referenced_properties": referenced,
                "recommendation": primary_code if primary_score >= 40 else None,
                "validation_status": validation_status
            }

        except Exception as e:
            logger.error(f"Error in detect_property_with_intelligence: {e}")
            return {
                "primary_property": None,
                "referenced_properties": [],
                "recommendation": None,
                "validation_status": "UNCERTAIN",
                "error": str(e)
            }
    
    def detect_year_and_period(self, pdf_data: bytes) -> Dict:
        """
        Detect year and period from PDF content
        
        Looks for:
        - Year (2020-2030)
        - Month names (January, Feb, etc.)
        - Month numbers (01-12)
        - Common period formats ("December 2024", "12/31/2024", "YE 2024")
        
        Returns:
            dict: {
                "year": int or None,
                "month": int or None,
                "period_text": str,
                "confidence": float
            }
        """
        try:
            import re
            from datetime import datetime
            
            # Quick extraction of first 2 pages
            result = self.pymupdf.extract_text(pdf_data)
            if not result.get("success"):
                return {"year": None, "month": None, "period_text": "", "confidence": 0}
            
            # Get text from first 2 pages
            pages = result.get("pages", [])
            sample_text = ""
            for page in pages[:2]:
                sample_text += page.get("text", "")
            
            # Extract months (names and numbers)
            month_names = {
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

            detected_year = None
            detected_month = None
            
            # PRIORITY 0: For Rent Roll documents, look for "From Date" pattern first
            # Pattern: "From Date: MM/DD/YYYY" or "From Date MM/DD/YYYY"
            from_date_patterns = [
                r'(?:from date|from date:)[:\s]+(\d{1,2})/(\d{1,2})/(\d{4})',
                r'(?:property:.*?from date)[:\s]+(\d{1,2})/(\d{1,2})/(\d{4})',
            ]
            
            for pattern in from_date_patterns:
                match = re.search(pattern, sample_text, re.IGNORECASE)
                if match:
                    try:
                        month = int(match.group(1))
                        day = int(match.group(2))
                        year = int(match.group(3))
                        if 1 <= month <= 12 and 1 <= day <= 31 and 2020 <= year <= 2030:
                            detected_month = month
                            detected_year = year
                            # High confidence for "From Date" - this is the document period
                            break
                    except (ValueError, IndexError):
                        continue

            # PRIORITY 0: For mortgage statements, "LOAN INFORMATION As of Date" is the authoritative statement period
            # This pattern is specific to mortgage statements and takes highest priority
            # Example: "LOAN INFORMATION As of Date 1/25/2023" means the statement is for January 2023
            # Note: Payment Due Date (e.g., "2/06/2023") is NOT the statement period
            mortgage_as_of_date_patterns = [
                r'LOAN\s+INFORMATION\s+As\s+of\s+Date\s+(\d{1,2})/(\d{1,2})/(\d{4})',  # Highest priority for mortgages
                r'PAYMENT\s+INFORMATION\s+As\s+of\s+Date\s+(\d{1,2})/(\d{1,2})/(\d{4})',  # Alternative location
            ]
            
            for pattern in mortgage_as_of_date_patterns:
                match = re.search(pattern, sample_text, re.IGNORECASE)
                if match:
                    try:
                        month = int(match.group(1))
                        day = int(match.group(2))
                        year = int(match.group(3))
                        if 1 <= month <= 12 and 1 <= day <= 31 and 2020 <= year <= 2030:
                            detected_month = month
                            detected_year = year
                            # High confidence for "LOAN INFORMATION As of Date" - this is the statement period
                            return {
                                "year": detected_year,
                                "month": detected_month,
                                "period_text": f"{detected_year}-{detected_month:02d}",
                                "confidence": 100.0  # Very high confidence for this pattern
                            }
                    except (ValueError, IndexError):
                        continue
            
            # PRIORITY 1: Look for statement date patterns (mortgage statements, financial docs)
            # Patterns like "As of Date 2/21/2025" or "Statement Date: 12/31/2024"
            # Check for statement date even if we found a year (statement date is more reliable)
            statement_date_patterns = [
                r'(?:statement date|statement date:)[:\s]+(\d{1,2})/(\d{1,2})/(\d{4})',  # Highest priority - exact "Statement Date"
                r'(?:as of date|as of date:)[:\s]+(\d{1,2})/(\d{1,2})/(\d{4})',
                r'(?:report date|report date:)[:\s]+(\d{1,2})/(\d{1,2})/(\d{4})',
                r'(?:loan information as of date|payment information as of date)[:\s]+(\d{1,2})/(\d{1,2})/(\d{4})',
                r'(?:as of|dated?|for the (?:period|month) ending?)[:\s]+(\d{1,2})/(\d{1,2})/(\d{4})',
                r'(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+statement)',
            ]

            for pattern in statement_date_patterns:
                match = re.search(pattern, sample_text, re.IGNORECASE)
                if match:
                    try:
                        month = int(match.group(1))
                        day = int(match.group(2))
                        year = int(match.group(3))
                        if 1 <= month <= 12 and 1 <= day <= 31 and 2020 <= year <= 2030:
                            # Statement date is authoritative - use it
                            detected_month = month
                            detected_year = year
                            break  # Found a high-confidence statement date
                    except (ValueError, IndexError):
                        continue

            # PRIORITY 2: If no statement date found, look for date in format MM/DD/YYYY
            # But exclude dates that are clearly lease expiration dates (for rent roll documents)
            if detected_month is None or detected_year is None:
                date_matches = re.findall(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', sample_text)
                if date_matches:
                    from collections import Counter
                    months_in_dates = []
                    years_in_dates = []
                    
                    # Filter out lease expiration dates (common in rent roll documents)
                    # Look for dates that appear near "Lease To", "Lease Expiration", etc.
                    sample_lower = sample_text.lower()
                    lease_keywords = ['lease to', 'lease expiration', 'expiration date', 'lease end']
                    
                    for match in date_matches:
                        try:
                            month = int(match[0])
                            day = int(match[1])
                            year = int(match[2])  # match[2] is the year in MM/DD/YYYY format
                            if 1 <= month <= 12 and 1 <= day <= 31 and 2020 <= year <= 2030:
                                # Check if this date appears near lease keywords (likely expiration date)
                                date_str = f"{match[0]}/{match[1]}/{match[2]}"
                                date_pos = sample_text.find(date_str)
                                if date_pos >= 0:
                                    # Check 50 characters before and after the date
                                    context_start = max(0, date_pos - 50)
                                    context_end = min(len(sample_text), date_pos + len(date_str) + 50)
                                    context = sample_text[context_start:context_end].lower()
                                    
                                    # Skip if it's clearly a lease expiration date
                                    is_lease_date = any(keyword in context for keyword in lease_keywords)
                                    if not is_lease_date:
                                        months_in_dates.append(month)
                                        years_in_dates.append(year)
                        except (ValueError, IndexError):
                            continue

                    if months_in_dates:
                        month_counts = Counter(months_in_dates)
                        detected_month = month_counts.most_common(1)[0][0]
                    
                    if detected_year is None and years_in_dates:
                        year_counts = Counter(years_in_dates)
                        detected_year = int(year_counts.most_common(1)[0][0])

            # PRIORITY 3: Fall back to extracting all years and using most common
            # But only if we haven't found a year from priority patterns
            if detected_year is None:
                years = re.findall(r'\b(202[0-9]|2030)\b', sample_text)
                if years:
                    from collections import Counter
                    year_counts = Counter(years)
                    # Get most common year
                    detected_year = int(year_counts.most_common(1)[0][0])
            
            # PRIORITY 4: Fall back to month name search (least reliable)
            # Look for month names in header/title context only, not in table data
            if detected_month is None:
                found_months = []
                sample_lower = sample_text.lower()

                # Try to find month in header/title context (first 500 chars)
                header_text = sample_lower[:500]

                # Look for patterns like "For the period ending January 2025" or "January 2025"
                for month_name, month_num in month_names.items():
                    # Look for month in context phrases
                    context_patterns = [
                        f'for the period ending {month_name}',
                        f'period ending {month_name}',
                        f'month ending {month_name}',
                        f'as of {month_name}',
                        f'ending {month_name}',
                        f'{month_name} \\d{{4}}',  # Month followed by year
                    ]

                    for pattern in context_patterns:
                        if re.search(pattern, header_text, re.IGNORECASE):
                            found_months.append(month_num)
                            break

                # If no context match, fall back to simple search but with lower confidence
                if not found_months:
                    for month_name, month_num in month_names.items():
                        if month_name in header_text:  # Only search header, not full doc
                            found_months.append(month_num)

                detected_month = found_months[0] if found_months else None
            
            # Prioritize explicit period ranges (Dec 2022 - Jan 2023)
            period_range = None
            range_match = re.search(
                r'([A-Za-z]+)\s+(\d{4})\s*(?:[–—-]|to|through)\s*([A-Za-z]+)\s+(\d{4})',
                sample_text,
                re.IGNORECASE
            )
            if range_match:
                start_month_name = range_match.group(1).lower()
                start_year_val = int(range_match.group(2))
                end_month_name = range_match.group(3).lower()
                end_year_val = int(range_match.group(4))
                if start_year_val and end_year_val and end_year_val >= start_year_val:
                    start_month_val = month_names.get(start_month_name)
                    end_month_val = month_names.get(end_month_name)
                    range_text = range_match.group(0).strip()
                    period_range = {
                        "start_year": start_year_val,
                        "end_year": end_year_val,
                        "start_month": start_month_val,
                        "end_month": end_month_val,
                        "text": range_text
                    }
                    detected_year = (
                        end_year_val
                        if detected_year is None or detected_year < end_year_val
                        else detected_year
                    )
                    if end_month_val and (detected_month is None or detected_month < end_month_val):
                        detected_month = end_month_val
            confidence = 0
            period_detection_method = None

            if detected_year:
                # Higher confidence if we found it from "From Date" or statement date patterns
                if any(pattern in sample_text.lower() for pattern in ['from date', 'as of date', 'statement date']):
                    confidence += 70
                    period_detection_method = 'statement_date'
                else:
                    confidence += 50
                    period_detection_method = 'year_scan'

            if detected_month:
                # Higher confidence for months found in date patterns (MM/DD/YYYY)
                if any(pattern in sample_text.lower() for pattern in ['from date', 'as of date', 'statement date']):
                    confidence += 30
                elif '/' in sample_text[:500]:  # Found in date format
                    confidence += 25
                else:
                    # Lower confidence for month name fallback search
                    confidence += 10
                    if period_detection_method:
                        period_detection_method += '_fallback_month'
                    else:
                        period_detection_method = 'fallback_month'
            
            # Boost confidence when we detected an explicit range
            if period_range:
                confidence += 20
                if not period_detection_method:
                    period_detection_method = 'range_detect'
                confidence = max(confidence, 60)
            
            # Find period text for display
            period_text = ""
            if period_range and period_range.get("text"):
                period_text = period_range["text"]
            elif detected_month and detected_year:
                month_name = list(month_names.keys())[list(month_names.values()).index(detected_month)]
                period_text = f"{month_name.capitalize()} {detected_year}"
            elif detected_year:
                period_text = str(detected_year)
            
            return {
                "year": detected_year,
                "month": detected_month,
                "period_text": period_text,
                "confidence": confidence,
                "period_range": period_range
            }
            
        except Exception as e:
            return {
                "year": None,
                "month": None,
                "period_text": "",
                "confidence": 0,
                "error": str(e)
            }
    
    def detect_document_type(self, pdf_data: bytes) -> Dict:
        """
        Quickly detect financial document type from PDF content
        
        Analyzes first 2 pages for keywords to determine if document is:
        - Balance Sheet
        - Income Statement  
        - Cash Flow Statement
        - Rent Roll
        
        Returns:
            dict: {
                "detected_type": str,
                "confidence": float,
                "keywords_found": list
            }
        """
        try:
            # Quick extraction of first 2 pages only for speed
            result = self.pymupdf.extract_text(pdf_data)
            if not result.get("success"):
                return {"detected_type": "unknown", "confidence": 0, "keywords_found": []}
            
            # Get text from first 2 pages
            pages = result.get("pages", [])
            sample_text = ""
            for page in pages[:2]:  # Only first 2 pages
                sample_text += page.get("text", "").lower()
            
            # Define keyword patterns for each document type
            # Priority keywords (exact phrases) are checked first and weighted higher
            priority_keywords = {
                "cash_flow": [
                    "cash flow statement",  # Highest priority - exact phrase
                    "statement of cash flows",  # Alternative format
                ],
                "income_statement": [
                    "income statement",  # Must be exact phrase, not just "statement"
                    "statement of operations",  # Alternative format
                    "profit and loss statement",  # P&L statement
                ],
                "balance_sheet": [
                    "balance sheet",  # Exact phrase
                    "statement of financial position",  # Alternative format
                ],
                "rent_roll": [
                    "rent roll",  # Exact phrase
                    "tenant roll",  # Alternative
                ]
            }
            
            # Secondary keywords (individual words/phrases)
            secondary_keywords = {
                "balance_sheet": [
                    "assets", "liabilities", "equity", "current assets", "long-term assets",
                    "current liabilities", "stockholders equity", "total assets"
                ],
                "income_statement": [
                    "revenue", "profit and loss", "p&l", "operating income",
                    "net income", "gross income", "income and expense"
                ],
                "cash_flow": [
                    "cash flow",  # Individual phrase (lower priority than "cash flow statement")
                    "operating activities", "investing activities", "financing activities",
                    "net cash", "cash from operations", "beginning cash", "ending cash"
                ],
                "rent_roll": [
                    "tenant", "unit", "lease", "sq ft", "square feet",
                    "lease expiration", "monthly rent", "annual rent", "occupancy"
                ]
            }
            
            # Count keywords for each type with weighted scoring
            scores = {}
            found_keywords = {}
            
            # First, check priority keywords (exact phrases) - these get 3x weight
            for doc_type, keyword_list in priority_keywords.items():
                if doc_type not in scores:
                    scores[doc_type] = 0
                    found_keywords[doc_type] = []
                
                for keyword in keyword_list:
                    # Use case-insensitive search but check for whole phrase
                    keyword_lower = keyword.lower()
                    if keyword_lower in sample_text:
                        scores[doc_type] += 3  # 3x weight for priority keywords
                        found_keywords[doc_type].append(keyword)
            
            # Then, check secondary keywords - these get 1x weight
            for doc_type, keyword_list in secondary_keywords.items():
                if doc_type not in scores:
                    scores[doc_type] = 0
                    found_keywords[doc_type] = []
                
                for keyword in keyword_list:
                    keyword_lower = keyword.lower()
                    # For secondary keywords, check if they exist but avoid false positives
                    # Skip if this keyword is part of a priority phrase that was already matched
                    if keyword_lower in sample_text:
                        # Avoid double-counting: if "cash flow statement" was found, don't count "cash flow" again
                        if doc_type == "cash_flow" and keyword == "cash flow":
                            # Only count if "cash flow statement" wasn't already found
                            if "cash flow statement" not in " ".join(found_keywords[doc_type]).lower():
                                scores[doc_type] += 1
                                found_keywords[doc_type].append(keyword)
                        # Avoid false positive: "income statement" should not match "cash flow statement"
                        elif doc_type == "income_statement" and keyword == "income statement":
                            # Only count if it's not part of "cash flow statement"
                            if "cash flow statement" not in sample_text:
                                scores[doc_type] += 1
                                found_keywords[doc_type].append(keyword)
                        else:
                            scores[doc_type] += 1
                            found_keywords[doc_type].append(keyword)
            
            # Determine most likely type
            if max(scores.values()) == 0:
                return {"detected_type": "unknown", "confidence": 0, "keywords_found": []}
            
            detected_type = max(scores, key=scores.get)
            max_score = scores[detected_type]
            
            # Calculate confidence based on score relative to maximum possible
            # Priority keywords are worth 3 points, secondary keywords are worth 1 point
            # Maximum possible score for cash_flow: 3 (cash flow statement) + 3 (statement of cash flows) + 8 (secondary) = 14
            # But we normalize to percentage based on actual matches
            total_possible = len(priority_keywords[detected_type]) * 3 + len(secondary_keywords[detected_type])
            confidence = min((max_score / max(total_possible, 1)) * 100, 100)
            
            return {
                "detected_type": detected_type,
                "confidence": round(confidence, 1),
                "keywords_found": found_keywords[detected_type]
            }
            
        except Exception as e:
            return {
                "detected_type": "unknown",
                "confidence": 0,
                "keywords_found": [],
                "error": str(e)
            }
    
    def extract_with_validation(
        self,
        pdf_data: bytes,
        strategy: str = "auto",
        lang: str = "eng"
    ) -> Dict:
        """
        Extract text with automatic validation
        
        Args:
            pdf_data: PDF file as bytes
            strategy: 'auto', 'fast', 'accurate', 'multi_engine'
            lang: Language code for OCR
        
        Returns:
            dict: Extraction results with quality validation
        """
        start_time = time.time()
        
        try:
            # Step 1: Classify document
            classification = self.classifier.classify(pdf_data)
            doc_type = classification.get("document_type", DocumentType.DIGITAL)
            
            # Step 2: Select extraction strategy
            if strategy == "auto":
                extraction = self._extract_auto(pdf_data, doc_type, lang)
            elif strategy == "fast":
                extraction = self._extract_fast(pdf_data)
            elif strategy == "accurate":
                extraction = self._extract_accurate(pdf_data, lang)
            elif strategy == "multi_engine":
                extraction = self._extract_multi_engine(pdf_data, lang)
            else:
                extraction = self._extract_auto(pdf_data, doc_type, lang)
            
            # Step 3: Validate extraction
            validation = self.validator.validate_extraction(extraction)
            
            # Step 4: Build final result
            processing_time = time.time() - start_time
            
            result = {
                "extraction": extraction,
                "validation": validation,
                "classification": classification,
                "processing_time_seconds": round(processing_time, 2),
                "strategy_used": strategy,
                "quality_level": validation["overall_quality"],
                "confidence_score": validation["confidence_score"],
                "needs_review": validation["confidence_score"] < 85,
                "success": True
            }
            
            return result
        
        except Exception as e:
            return {
                "extraction": {},
                "validation": {},
                "classification": {},
                "success": False,
                "error": str(e)
            }
    
    def _extract_auto(
        self,
        pdf_data: bytes,
        doc_type: DocumentType,
        lang: str
    ) -> Dict:
        """Automatic engine selection based on document type"""
        
        if doc_type == DocumentType.DIGITAL:
            # Use PyMuPDF (fastest and accurate for digital PDFs)
            return self.pymupdf.extract_text(pdf_data)
        
        elif doc_type == DocumentType.SCANNED:
            # Use OCR
            return self.ocr.extract_text_from_pdf(pdf_data, lang=lang)
        
        elif doc_type == DocumentType.TABLE_HEAVY:
            # Use PDFPlumber for better table handling
            return self.pdfplumber.extract_text(pdf_data)
        
        elif doc_type == DocumentType.MIXED:
            # Try PyMuPDF first, fall back to OCR if quality is low
            result = self.pymupdf.extract_text(pdf_data)
            validation = self.validator.validate_extraction(result)
            
            if validation["confidence_score"] < 70:
                # Quality too low, try OCR
                result = self.ocr.extract_text_from_pdf(pdf_data, lang=lang)
            
            return result
        
        else:
            # Default to PyMuPDF
            return self.pymupdf.extract_text(pdf_data)
    
    def _extract_fast(self, pdf_data: bytes) -> Dict:
        """Fast extraction - single engine (PyMuPDF)"""
        return self.pymupdf.extract_text(pdf_data)
    
    def _extract_accurate(self, pdf_data: bytes, lang: str) -> Dict:
        """Accurate extraction - best single engine based on document"""
        classification = self.classifier.classify(pdf_data)
        doc_type = classification.get("document_type", DocumentType.DIGITAL)
        
        return self._extract_auto(pdf_data, doc_type, lang)
    
    def _extract_multi_engine(self, pdf_data: bytes, lang: str) -> Dict:
        """
        Extract with multiple engines and return best result
        
        Most accurate but slowest method
        """
        results = []
        
        # Extract with PyMuPDF
        pymupdf_result = self.pymupdf.extract_text(pdf_data)
        if pymupdf_result["success"]:
            results.append(pymupdf_result)
        
        # Extract with PDFPlumber
        pdfplumber_result = self.pdfplumber.extract_text(pdf_data)
        if pdfplumber_result["success"]:
            results.append(pdfplumber_result)
        
        # If both failed or low quality, try OCR
        if len(results) < 2 or all(len(r.get("text", "")) < 100 for r in results):
            ocr_result = self.ocr.extract_text_from_pdf(pdf_data, lang=lang)
            if ocr_result["success"]:
                results.append(ocr_result)
        
        # Select best result based on validation
        best_result = self._select_best_result(results)
        
        # Add multi-engine metadata
        best_result["engines_used"] = [r.get("engine", "unknown") for r in results]
        best_result["total_engines"] = len(results)
        
        return best_result
    
    def _select_best_result(self, results: List[Dict]) -> Dict:
        """Select best extraction result from multiple engines"""
        if not results:
            return {"engine": "none", "text": "", "success": False, "error": "All engines failed"}
        
        if len(results) == 1:
            return results[0]
        
        # Validate each result
        scored_results = []
        
        for result in results:
            validation = self.validator.validate_extraction(result)
            scored_results.append({
                "result": result,
                "score": validation["confidence_score"]
            })
        
        # Sort by score
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return best result
        return scored_results[0]["result"]
    
    def _convert_confidence_to_score(self, confidence: float) -> float:
        """
        Convert confidence score (0.0-1.0) to extraction score (1-10).
        
        Formula: score = 1 + (confidence * 9)
        - confidence 0.0 → score 1.0
        - confidence 0.5 → score 5.5
        - confidence 1.0 → score 10.0
        
        Args:
            confidence: Confidence score between 0.0 and 1.0
            
        Returns:
            Score between 1.0 and 10.0
        """
        if confidence < 0:
            return 1.0
        if confidence > 1.0:
            return 10.0
        
        score = 1.0 + (confidence * 9.0)
        return round(score, 1)
    
    def extract_with_all_models_scored(
        self,
        pdf_data: bytes,
        lang: str = "eng"
    ) -> Dict[str, Any]:
        """
        Extract using ALL available models and score each on 1-10 scale.
        
        This method runs all available extraction engines (including AI models)
        and returns a scored comparison of their results.
        
        Args:
            pdf_data: Binary PDF data
            lang: Language code for OCR engines (default: "eng")
        
        Returns:
            dict: {
                "results": [
                    {
                        "model": "PyMuPDF",
                        "score": 8.5,
                        "confidence": 0.85,
                        "success": True,
                        "text_length": 5000,
                        "processing_time_ms": 120,
                        "extracted_data": {...},
                        "error": None
                    },
                    ...
                ],
                "best_model": "LayoutLM",
                "best_score": 9.2,
                "total_models": 6,
                "successful_models": 5
            }
        """
        all_results = []
        
        # List of all available engines with their display names
        engines_to_run = [
            ("PyMuPDF", self.pymupdf),
            ("PDFPlumber", self.pdfplumber),
        ]
        
        # Add optional engines if available
        if self.camelot:
            engines_to_run.append(("Camelot", self.camelot))
        if self.ocr:
            engines_to_run.append(("Tesseract OCR", self.ocr))
        if self.layoutlm:
            engines_to_run.append(("LayoutLMv3", self.layoutlm))
        if self.easyocr:
            engines_to_run.append(("EasyOCR", self.easyocr))
        
        logger.info(f"Running {len(engines_to_run)} extraction engines for scoring...")
        
        # Run all engines
        for engine_name, engine in engines_to_run:
            try:
                logger.info(f"Running {engine_name}...")
                
                # Handle different engine types
                # Most engines have extract() method returning ExtractionResult
                # OCR engine has extract_text_from_pdf() returning Dict
                extracted_data = {}
                processing_time_ms = 0.0
                success = True
                error = None
                
                try:
                    if hasattr(engine, 'extract'):
                        result = engine.extract(pdf_data, lang=lang)
                        
                        # Extract data (NOT confidence - models don't calculate it)
                        if hasattr(result, 'extracted_data') and result.extracted_data:
                            extracted_data = result.extracted_data
                        
                        # Get processing time
                        if hasattr(result, 'processing_time_ms') and result.processing_time_ms:
                            processing_time_ms = float(result.processing_time_ms)
                        
                        success = result.success if hasattr(result, 'success') else True
                        if not success:
                            error = getattr(result, 'error_message', 'Extraction failed')
                    elif hasattr(engine, 'extract_text_from_pdf'):
                        # OCR engine uses extract_text_from_pdf()
                        result = engine.extract_text_from_pdf(pdf_data, lang=lang)
                        
                        # Convert dict result to extracted_data format
                        extracted_data = {
                            'text': result.get('text', ''),
                            'pages': result.get('pages', []),
                            'total_pages': result.get('total_pages', 0),
                            'total_words': result.get('total_words', 0),
                            'total_chars': result.get('total_chars', 0)
                        }
                        processing_time_ms = 0.0  # OCR doesn't track time
                        success = result.get('success', False)
                        if not success:
                            error = result.get('error', 'Extraction failed')
                    else:
                        # Fallback: try extract_text() method
                        result = engine.extract_text(pdf_data)
                        
                        # Convert dict result to extracted_data format
                        extracted_data = {
                            'text': result.get('text', ''),
                            'pages': result.get('pages', []),
                            'total_pages': result.get('total_pages', 0),
                            'total_words': result.get('total_words', 0),
                            'total_chars': result.get('total_chars', 0)
                        }
                        processing_time_ms = 0.0
                        success = result.get('success', False)
                        if not success:
                            error = result.get('error', 'Extraction failed')
                except Exception as e:
                    success = False
                    error = str(e)
                    extracted_data = {}
                
                # Score externally using client-defined factors (NOT model's internal confidence)
                scoring_result = self.scoring_service.score_extraction_result(
                    model_name=engine_name,
                    extracted_data=extracted_data,
                    processing_time_ms=processing_time_ms,
                    success=success,
                    error=error
                )
                
                score = scoring_result['score']
                confidence = scoring_result['confidence']
                
                # Extract text length from extracted_data
                text_length = len(extracted_data.get('text', '')) if extracted_data else 0
                
                # Prepare result dict
                result_dict = {
                    "model": engine_name,
                    "score": score,
                    "confidence": confidence,
                    "success": success,
                    "text_length": text_length,
                    "processing_time_ms": round(processing_time_ms, 2),
                    "extracted_data": extracted_data,
                    "score_breakdown": scoring_result.get('score_breakdown', {}),
                    "error": error
                }
                
                # Add page count if available
                if extracted_data and 'total_pages' in extracted_data:
                    result_dict["page_count"] = extracted_data['total_pages']
                
                all_results.append(result_dict)
                logger.info(f"{engine_name} completed: score={score}, confidence={confidence:.3f}, text_length={text_length}")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"{engine_name} failed: {error_msg}")
                all_results.append({
                    "model": engine_name,
                    "score": 0.0,
                    "confidence": 0.0,
                    "success": False,
                    "text_length": 0,
                    "processing_time_ms": 0.0,
                    "extracted_data": {},
                    "error": error_msg
                })
        
        # Find best model
        successful_results = [r for r in all_results if r['success']]
        if successful_results:
            best = max(successful_results, key=lambda x: x['score'])
            best_model = best['model']
            best_score = best['score']
        else:
            best_model = None
            best_score = 0.0
        
        # Calculate average score
        avg_score = 0.0
        if successful_results:
            avg_score = sum(r['score'] for r in successful_results) / len(successful_results)
        
        logger.info(f"All models completed. Best: {best_model} (score: {best_score})")
        
        return {
            "results": all_results,
            "best_model": best_model,
            "best_score": round(best_score, 1),
            "total_models": len(all_results),
            "successful_models": len(successful_results),
            "average_score": round(avg_score, 1)
        }
    
    def extract_with_consensus(
        self,
        pdf_data: bytes,
        engines: Optional[List[str]] = None,
        lang: str = "eng"
    ) -> Dict:
        """
        Extract with multiple engines and calculate consensus
        
        Args:
            pdf_data: PDF file as bytes
            engines: List of engine names to use (None = all)
            lang: Language for OCR
        
        Returns:
            dict: All extraction results with consensus analysis
        """
        try:
            extractions = []
            
            # Determine which engines to use
            if engines is None:
                engines = ["pymupdf", "pdfplumber"]  # Default pair
            
            # Run each engine
            if "pymupdf" in engines:
                result = self.pymupdf.extract_text(pdf_data)
                if result["success"]:
                    extractions.append(result)
            
            if "pdfplumber" in engines:
                result = self.pdfplumber.extract_text(pdf_data)
                if result["success"]:
                    extractions.append(result)
            
            if "ocr" in engines:
                result = self.ocr.extract_text_from_pdf(pdf_data, lang=lang)
                if result["success"]:
                    extractions.append(result)
            
            # Calculate consensus
            consensus = self.validator.calculate_consensus_score(extractions)
            
            # Select best extraction
            best_extraction = self._select_best_result(extractions)
            
            # Validate best extraction
            validation = self.validator.validate_extraction(best_extraction)
            
            return {
                "primary_extraction": best_extraction,
                "all_extractions": extractions,
                "consensus": consensus,
                "validation": validation,
                "total_engines_used": len(extractions),
                "confidence_score": validation["confidence_score"],
                "quality_level": validation["overall_quality"],
                "success": True
            }
        
        except Exception as e:
            return {
                "primary_extraction": {},
                "all_extractions": [],
                "consensus": {},
                "validation": {},
                "success": False,
                "error": str(e)
            }
    
    def extract_tables_comprehensive(self, pdf_data: bytes) -> Dict:
        """
        Extract tables using multiple engines for best accuracy
        
        Combines Camelot and PDFPlumber results
        """
        try:
            # Try Camelot first (best for bordered tables)
            camelot_lattice = self.camelot.extract_tables(pdf_data, flavor="lattice")
            camelot_stream = self.camelot.extract_tables(pdf_data, flavor="stream")
            
            # Try PDFPlumber
            pdfplumber_result = self.pdfplumber.extract_tables(pdf_data)
            
            # Combine results
            all_tables = []
            
            if camelot_lattice["success"]:
                all_tables.extend(camelot_lattice.get("tables", []))
            
            if camelot_stream["success"]:
                all_tables.extend(camelot_stream.get("tables", []))
            
            if pdfplumber_result["success"]:
                all_tables.extend(pdfplumber_result.get("tables", []))
            
            # Remove duplicates (basic heuristic)
            unique_tables = self._deduplicate_tables(all_tables)
            
            return {
                "tables": unique_tables,
                "total_tables": len(unique_tables),
                "engines_used": ["camelot_lattice", "camelot_stream", "pdfplumber"],
                "success": True
            }
        
        except Exception as e:
            return {
                "tables": [],
                "total_tables": 0,
                "success": False,
                "error": str(e)
            }
    
    def _deduplicate_tables(self, tables: List[Dict]) -> List[Dict]:
        """Remove duplicate tables (simple implementation)"""
        # In production, implement more sophisticated deduplication
        # For now, just return all tables
        return tables
    
    def extract_with_confidence(
        self,
        pdf_data: bytes,
        run_all_engines: bool = True
    ) -> List[ExtractionResult]:
        """
        NEW METHOD: Extract using all engines and return ExtractionResult objects.
        
        This method uses the new BaseExtractor framework and returns
        ExtractionResult objects with confidence scores for metadata tracking.
        
        Args:
            pdf_data: PDF file as bytes
            run_all_engines: If True, runs all 3 engines. If False, runs based on doc type
        
        Returns:
            List of ExtractionResult objects from each engine
        """
        results = []
        
        if run_all_engines:
            # Run all three main engines for maximum confidence
            
            # PyMuPDF - Good for text
            try:
                pymupdf_result = self.pymupdf.extract(
                    pdf_data,
                    extract_tables=False,
                    extract_metadata=True
                )
                results.append(pymupdf_result)
            except Exception as e:
                # Add failed result
                results.append(ExtractionResult(
                    engine_name="pymupdf",
                    extracted_data={},
                    success=False,
                    error_message=str(e)
                ))
            
            # PDFPlumber - Best for tables
            try:
                pdfplumber_result = self.pdfplumber.extract(
                    pdf_data,
                    extract_tables=True
                )
                results.append(pdfplumber_result)
            except Exception as e:
                results.append(ExtractionResult(
                    engine_name="pdfplumber",
                    extracted_data={},
                    success=False,
                    error_message=str(e)
                ))
            
            # Camelot - Best for complex tables
            try:
                camelot_result = self.camelot.extract(
                    pdf_data,
                    flavor="both"  # Try both lattice and stream
                )
                results.append(camelot_result)
            except Exception as e:
                results.append(ExtractionResult(
                    engine_name="camelot",
                    extracted_data={},
                    success=False,
                    error_message=str(e)
                ))
        
        else:
            # Run engines based on document type (optimized)
            classification = self.classifier.classify(pdf_data)
            doc_type = classification.get("document_type", DocumentType.DIGITAL)
            recommended = self._get_recommended_engines(doc_type)
            
            if "pymupdf" in recommended:
                try:
                    results.append(self.pymupdf.extract(pdf_data, extract_metadata=True))
                except Exception as e:
                    results.append(ExtractionResult(
                        engine_name="pymupdf",
                        extracted_data={},
                        success=False,
                        error_message=str(e)
                    ))
            
            if "pdfplumber" in recommended:
                try:
                    results.append(self.pdfplumber.extract(pdf_data, extract_tables=True))
                except Exception as e:
                    results.append(ExtractionResult(
                        engine_name="pdfplumber",
                        extracted_data={},
                        success=False,
                        error_message=str(e)
                    ))
            
            if "camelot" in recommended:
                try:
                    results.append(self.camelot.extract(pdf_data, flavor="both"))
                except Exception as e:
                    results.append(ExtractionResult(
                        engine_name="camelot",
                        extracted_data={},
                        success=False,
                        error_message=str(e)
                    ))
        
        return results
