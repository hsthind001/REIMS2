"""
Mortgage Statement Extraction Service
Extracts mortgage statement data from PDFs using field patterns
"""
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import re
import json
from sqlalchemy.orm import Session
from app.models.extraction_template import ExtractionTemplate
from app.models.lender import Lender
from fuzzywuzzy import fuzz
import logging

logger = logging.getLogger(__name__)


class MortgageExtractionService:
    """Extract mortgage statement data using field patterns"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def extract_mortgage_data(
        self,
        extracted_text: str,
        pdf_data: bytes = None
    ) -> Dict:
        """
        Extract mortgage statement data using template field patterns
        Includes self-learning and self-healing capabilities
        
        Args:
            extracted_text: Raw text extracted from PDF
            pdf_data: Optional PDF bytes for coordinate extraction
            
        Returns:
            dict: Extracted mortgage data with all fields
        """
        try:
            # Step 1: Pre-extraction checks - apply learned patterns
            from app.services.mortgage_learning_service import MortgageLearningService
            learning_service = MortgageLearningService(self.db)
            
            # Try to match lender name early for lender-specific patterns
            lender_id = self._match_lender(extracted_text)
            lender_name = None
            if lender_id:
                lender = self.db.query(Lender).filter(Lender.id == lender_id).first()
                lender_name = lender.lender_name if lender else None
            
            # Load mortgage statement template
            template = self.db.query(ExtractionTemplate).filter(
                ExtractionTemplate.document_type == 'mortgage_statement',
                ExtractionTemplate.is_default == True
            ).first()
            
            # Get field patterns from template or use defaults
            if template:
                template_structure = template.template_structure or {}
                field_patterns = template_structure.get("field_patterns", {})
            else:
                logger.warning("Mortgage statement template not found, using default patterns")
                field_patterns = self._get_default_field_patterns()
            
            # Step 2: Apply learned patterns (prioritize learned patterns over defaults)
            field_patterns = learning_service.apply_learned_patterns(
                field_patterns,
                lender_name=lender_name
            )
            
            # Extract all fields
            extracted_fields = {}
            extraction_coordinates = {}
            field_patterns_used = {}  # Track which pattern successfully extracted each field
            
            for field_name, field_config in field_patterns.items():
                patterns = field_config.get("patterns", [])
                field_type = field_config.get("field_type", "text")
                
                # Try each pattern
                value = None
                successful_pattern = None
                for pattern in patterns:
                    match = re.search(pattern, extracted_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    if match:
                        # Get the first capturing group, or the full match if no groups
                        if match.groups():
                            value = match.group(1)  # Use first capturing group
                        else:
                            value = match.group(0)  # Use full match
                        
                        # Special handling for loan_number to avoid "Total"
                        if field_name == "loan_number" and value:
                            value_str = str(value).strip()
                            # If we matched something that looks like "Total", try to find the actual number
                            if value_str in ["Total", "TOTAL", "total"] or len(value_str) < 4:
                                # Look for a number after "Loan Number" but skip "Total"
                                better_match = re.search(r"Loan\s+Number\s*:\s*([0-9]{4,})", extracted_text, re.IGNORECASE)
                                if better_match:
                                    value = better_match.group(1)
                                    successful_pattern = r"Loan\s+Number\s*:\s*([0-9]{4,})"
                                else:
                                    # Try to find number on same line as "Loan Number" but not "Total"
                                    context_match = re.search(r"Loan\s+Number[^\n]*?([0-9]{6,})", extracted_text, re.IGNORECASE | re.DOTALL)
                                    if context_match:
                                        match_start = context_match.start()
                                        context = extracted_text[max(0, match_start-50):match_start+100]
                                        if "Total" not in context or context.find("Total") > 30:
                                            value = context_match.group(1)
                                            successful_pattern = r"Loan\s+Number[^\n]*?([0-9]{6,})"
                                        else:
                                            value = None  # Reject if too close to "Total"
                                    else:
                                        value = None  # Reject "Total"
                            else:
                                successful_pattern = pattern
                        else:
                            successful_pattern = pattern
                        break
                
                if value:
                    # Convert based on field type
                    if field_type == "currency":
                        extracted_fields[field_name] = self._parse_currency(value)
                    elif field_type == "date":
                        extracted_fields[field_name] = self._parse_date(value)
                    elif field_type == "percentage":
                        extracted_fields[field_name] = self._parse_percentage(value)
                    else:
                        extracted_fields[field_name] = value.strip()
                    
                    # Track which pattern successfully extracted this field
                    if successful_pattern:
                        field_patterns_used[field_name] = successful_pattern
            
            # Filter out invalid loan numbers (common false positives) - Self-healing validation
            if extracted_fields.get("loan_number"):
                loan_num = str(extracted_fields["loan_number"]).strip()
                # Reject common false positives
                invalid_loan_numbers = ["Total", "TOTAL", "total", "Balance", "BALANCE", "balance", 
                                       "Amount", "AMOUNT", "amount", "Payment", "PAYMENT", "payment",
                                       "Date", "DATE", "Principal", "PRINCIPAL", "principal", "Interest",
                                       "INTEREST", "interest", "Due", "DUE", "due"]
                if loan_num in invalid_loan_numbers or len(loan_num) < 3:
                    extracted_fields["loan_number"] = None
                    # Remove from patterns used since it was invalid
                    field_patterns_used.pop("loan_number", None)
                    logger.warning(f"Rejected invalid loan_number: '{loan_num}'")
            
            # Lender matching already done earlier, just set it
            if lender_id:
                extracted_fields["lender_id"] = lender_id
            
            # Check if we have minimum required fields BEFORE calculating derived fields
            required_fields = ["loan_number", "statement_date", "principal_balance"]
            has_required = all(extracted_fields.get(field) is not None for field in required_fields)
            
            if not has_required:
                # Try fallback extraction for missing required fields
                extracted_fields = self._fallback_extract_required_fields(extracted_text, extracted_fields)
                # Filter invalid loan numbers from fallback too
                if extracted_fields.get("loan_number"):
                    loan_num = str(extracted_fields["loan_number"]).strip()
                    invalid_loan_numbers = ["Total", "TOTAL", "total", "Balance", "BALANCE", "balance"]
                    if loan_num in invalid_loan_numbers or len(loan_num) < 3:
                        extracted_fields["loan_number"] = None
                has_required = all(extracted_fields.get(field) is not None for field in required_fields)
            
            # Calculate derived fields (only if we have required fields)
            if has_required:
                extracted_fields = self._calculate_derived_fields(extracted_fields)
            
            # Calculate confidence score
            if template:
                template_structure = template.template_structure or {}
            else:
                template_structure = {}
            
            confidence = self._calculate_confidence(extracted_fields, template_structure)
            
            # Step 3: Post-extraction learning - learn from successful extractions
            if has_required and confidence >= 70.0 and field_patterns_used:
                try:
                    learning_service.learn_from_successful_extraction(
                        extracted_fields=extracted_fields,
                        field_patterns_used=field_patterns_used,
                        lender_name=lender_name,
                        confidence_score=confidence
                    )
                except Exception as e:
                    logger.warning(f"Failed to learn from extraction: {e}")
            
            if has_required:
                return {
                    "success": True,
                    "mortgage_data": extracted_fields,
                    "extraction_coordinates": extraction_coordinates,
                    "confidence": confidence,
                    "extraction_method": "template_patterns" if template else "default_patterns"
                }
            else:
                # Return failure with partial data for debugging
                missing_fields = [f for f in required_fields if extracted_fields.get(f) is None]
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Mortgage extraction missing required fields: {missing_fields}. Extracted: {list(extracted_fields.keys())}")
                return {
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}",
                    "mortgage_data": extracted_fields,  # Return partial data
                    "extraction_coordinates": extraction_coordinates,
                    "confidence": confidence,
                    "extraction_method": "template_patterns" if template else "default_patterns"
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Mortgage extraction failed: {str(e)}"
            }
    
    def _parse_currency(self, value: str) -> Optional[Decimal]:
        """Parse currency value from string"""
        if not value:
            return None
        
        # Remove $, commas, and whitespace
        cleaned = re.sub(r'[\$,\s]', '', value)
        try:
            return Decimal(cleaned)
        except:
            return None
    
    def _parse_date(self, value: str) -> Optional[Any]:
        """Parse date from string - returns date object or string in MM/DD/YYYY format"""
        if not value:
            return None
        
        # If already a date object, return as string
        if isinstance(value, datetime):
            return value.date().strftime("%m/%d/%Y")
        if hasattr(value, 'date'):  # date object
            return value.strftime("%m/%d/%Y")
        
        # Try common date formats
        formats = [
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%m-%d-%Y",
            "%B %d, %Y",
            "%b %d, %Y"
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(value.strip(), fmt).date()
                # Return as string in MM/DD/YYYY format for consistency
                return parsed_date.strftime("%m/%d/%Y")
            except:
                continue
        
        # If no format matched, return the original string (might be in a different format)
        return value.strip()
    
    def _parse_percentage(self, value: str) -> Optional[Decimal]:
        """Parse percentage value"""
        if not value:
            return None
        
        # Remove % sign
        cleaned = re.sub(r'%', '', value).strip()
        try:
            return Decimal(cleaned)
        except:
            return None
    
    def _match_lender(self, text: str) -> Optional[int]:
        """Match lender name from text to lenders table"""
        lenders = self.db.query(Lender).filter(Lender.is_active == True).all()
        
        best_match = None
        best_score = 0
        
        for lender in lenders:
            # Try exact match first
            if lender.lender_name.lower() in text.lower():
                return lender.id
            
            # Try short name
            if lender.lender_short_name and lender.lender_short_name.lower() in text.lower():
                return lender.id
            
            # Try fuzzy matching
            score = fuzz.partial_ratio(lender.lender_name.lower(), text.lower())
            if score > best_score and score > 80:
                best_score = score
                best_match = lender.id
        
        return best_match
    
    def _calculate_derived_fields(self, fields: Dict) -> Dict:
        """Calculate derived fields from extracted data"""
        # Calculate total_loan_balance
        principal = fields.get("principal_balance") or Decimal('0')
        tax_escrow = fields.get("tax_escrow_balance") or Decimal('0')
        insurance_escrow = fields.get("insurance_escrow_balance") or Decimal('0')
        reserve = fields.get("reserve_balance") or Decimal('0')
        other_escrow = fields.get("other_escrow_balance") or Decimal('0')
        
        fields["total_loan_balance"] = principal + tax_escrow + insurance_escrow + reserve + other_escrow
        
        # Calculate ytd_total_paid
        ytd_principal = fields.get("ytd_principal_paid") or Decimal('0')
        ytd_interest = fields.get("ytd_interest_paid") or Decimal('0')
        fields["ytd_total_paid"] = ytd_principal + ytd_interest
        
        # Calculate monthly_debt_service
        principal_due = fields.get("principal_due") or Decimal('0')
        interest_due = fields.get("interest_due") or Decimal('0')
        fields["monthly_debt_service"] = principal_due + interest_due
        
        # Calculate annual_debt_service
        if fields.get("monthly_debt_service"):
            fields["annual_debt_service"] = fields["monthly_debt_service"] * Decimal('12')
        
        # Calculate remaining_term_months if maturity_date and statement_date exist
        if fields.get("maturity_date") and fields.get("statement_date"):
            try:
                maturity = fields["maturity_date"]
                statement = fields["statement_date"]
                if isinstance(maturity, datetime):
                    maturity = maturity.date()
                if isinstance(statement, datetime):
                    statement = statement.date()
                
                # Calculate months between dates
                months = (maturity.year - statement.year) * 12 + (maturity.month - statement.month)
                fields["remaining_term_months"] = max(0, months)
            except:
                pass
        
        return fields
    
    def _calculate_confidence(self, fields: Dict, template_structure: Dict) -> float:
        """Calculate extraction confidence score"""
        required_fields = template_structure.get("required_fields", [])
        
        total_fields = len(required_fields)
        found_fields = sum(1 for field in required_fields if fields.get(field) is not None)
        
        if total_fields == 0:
            return 100.0
        
        base_confidence = (found_fields / total_fields) * 100.0
        
        # Adjust based on data quality
        # Check if key numeric fields are reasonable
        quality_penalty = 0.0
        
        principal = fields.get("principal_balance")
        if principal and (principal <= 0 or principal > Decimal('100000000')):
            quality_penalty += 10.0
        
        interest_rate = fields.get("interest_rate")
        if interest_rate and (interest_rate < 0 or interest_rate > 20):
            quality_penalty += 5.0
        
        return max(0.0, min(100.0, base_confidence - quality_penalty))
    
    def _fallback_extract_required_fields(self, extracted_text: str, existing_fields: Dict) -> Dict:
        """Fallback extraction for required fields using simple patterns"""
        result = existing_fields.copy()
        
        # Extract loan number (try to find numbers that look like loan numbers)
        if not result.get("loan_number"):
            # Priority 1: Look for "Loan Number:" followed by digits (most reliable, avoids "Total")
            # This pattern specifically looks for "Loan Number:" with colon and digits after
            loan_match = re.search(r"Loan\s+Number\s*:\s*([0-9]{4,})", extracted_text, re.IGNORECASE)
            if loan_match:
                result["loan_number"] = loan_match.group(1)
            else:
                # Priority 2: Look for "Loan Number" on same line as digits (but not "Total")
                # Match "Loan Number" followed by digits, but skip if "Total" is between them
                loan_match2 = re.search(r"Loan\s+Number[^\n]*?([0-9]{6,})", extracted_text, re.IGNORECASE | re.DOTALL)
                if loan_match2:
                    # Check that we didn't match "Total" - if the match is near "Total", skip it
                    match_start = loan_match2.start()
                    context = extracted_text[max(0, match_start-50):match_start+100]
                    if "Total" not in context or context.find("Total") > 30:  # "Total" is far from the number
                        result["loan_number"] = loan_match2.group(1)
                
                if not result.get("loan_number"):
                    # Priority 3: Look for "Account" or "Loan ID" patterns
                    account_match = re.search(r"(?:Account|Loan\s+ID)\s+(?:Number|#|No\.?)?\s*:?\s*([A-Z0-9\-]{4,})", extracted_text, re.IGNORECASE)
                    if account_match:
                        result["loan_number"] = account_match.group(1)
                    else:
                        # Priority 4: Look for filename pattern "loan 1008" or similar
                        filename_loan_match = re.search(r"loan\s+([0-9]{3,})", extracted_text, re.IGNORECASE)
                        if filename_loan_match:
                            result["loan_number"] = filename_loan_match.group(1)
        
        # Filter invalid loan numbers
        if result.get("loan_number"):
            loan_num = str(result["loan_number"]).strip()
            invalid_loan_numbers = ["Total", "TOTAL", "total", "Balance", "BALANCE", "balance", 
                                   "Amount", "AMOUNT", "amount", "Payment", "PAYMENT", "payment",
                                   "Date", "DATE", "Principal", "PRINCIPAL", "principal"]
            if loan_num in invalid_loan_numbers or len(loan_num) < 3:
                result["loan_number"] = None
        
        # Extract statement date (look for MM/DD/YYYY pattern, prioritize "Statement Date")
        if not result.get("statement_date"):
            # Priority 1: "Statement Date: MM/DD/YYYY" or "As of Date MM/DD/YYYY"
            stmt_date_match = re.search(r"(?:Statement\s+Date|As\s+of\s+Date)\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", extracted_text, re.IGNORECASE)
            if stmt_date_match:
                result["statement_date"] = stmt_date_match.group(1)
            else:
                # Priority 2: "Payment Due Date: MM/DD/YYYY" (common in mortgage statements)
                due_date_match = re.search(r"Payment\s+Due\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", extracted_text, re.IGNORECASE)
                if due_date_match:
                    result["statement_date"] = due_date_match.group(1)
                else:
                    # Priority 3: Any MM/DD/YYYY pattern (use first one found, but prefer dates in 2023-2024 range)
                    all_dates = re.findall(r"(\d{1,2}/\d{1,2}/\d{4})", extracted_text)
                    if all_dates:
                        # Prefer dates that are likely statement dates (2023-2024)
                        for date_str in all_dates:
                            try:
                                parts = date_str.split('/')
                                year = int(parts[2])
                                if 2020 <= year <= 2030:  # Reasonable range
                                    result["statement_date"] = date_str
                                    break
                            except:
                                continue
                        # If no good date found, use first one
                        if not result.get("statement_date") and all_dates:
                            result["statement_date"] = all_dates[0]
        
        # Extract principal balance (look for large currency amounts)
        if not result.get("principal_balance"):
            # Priority 1: "Principal Balance: $X" or "Outstanding Principal Balance"
            principal_match = re.search(r"(?:Principal\s+)?(?:Balance|Outstanding\s+Principal)\s*:?\s*\$?\s*([\d,]+\.?\d*)", extracted_text, re.IGNORECASE)
            if principal_match:
                result["principal_balance"] = self._parse_currency(principal_match.group(1))
            else:
                # Priority 2: Look in "LOAN INFORMATION" section for principal
                loan_info_section = re.search(r"LOAN\s+INFORMATION.*?(?=PAYMENT|BALANCES|$)", extracted_text, re.IGNORECASE | re.DOTALL)
                if loan_info_section:
                    section_text = loan_info_section.group(0)
                    principal_in_section = re.search(r"Principal\s+[Bb]alance\s*:?\s*\$?\s*([\d,]+\.?\d*)", section_text, re.IGNORECASE)
                    if principal_in_section:
                        result["principal_balance"] = self._parse_currency(principal_in_section.group(1))
                
                if not result.get("principal_balance"):
                    # Priority 3: "Outstanding Principal" or "Current Principal"
                    outstanding_match = re.search(r"(?:Outstanding|Current|Unpaid)\s+Principal\s*:?\s*\$?\s*([\d,]+\.?\d*)", extracted_text, re.IGNORECASE)
                    if outstanding_match:
                        result["principal_balance"] = self._parse_currency(outstanding_match.group(1))
                    else:
                        # Priority 4: Look for large currency amounts in "BALANCES" section
                        balances_section = re.search(r"BALANCES.*?(?=PAYMENT|$)", extracted_text, re.IGNORECASE | re.DOTALL)
                        if balances_section:
                            section_text = balances_section.group(0)
                            amounts = re.findall(r"\$?\s*([\d,]{6,}\.?\d{0,2})", section_text)
                            if amounts:
                                try:
                                    parsed_amounts = [self._parse_currency(a) for a in amounts if self._parse_currency(a)]
                                    if parsed_amounts:
                                        max_amount = max(parsed_amounts)
                                        # Only use if it's a reasonable mortgage amount (between 100K and 100M)
                                        if max_amount and Decimal('100000') <= max_amount <= Decimal('100000000'):
                                            result["principal_balance"] = max_amount
                                except:
                                    pass
        
        return result
    
    def _get_default_field_patterns(self) -> Dict:
        """
        Return default field patterns matching actual PDF structure
        Based on analysis of 2023 Wells Fargo mortgage statement PDFs
        """
        return {
            "loan_number": {
                "patterns": [
                    r"Loan\s+Number\s*:?\s*([0-9]{6,})",  # "Loan Number: 306891008"
                    r"Loan\s+#\s*:?\s*([0-9]{6,})",
                    r"LOAN\s+INFORMATION.*?Loan\s+Number\s*:?\s*([0-9]{6,})",  # In LOAN INFORMATION section
                    r"Account\s+(?:Number|#|No\.?)\s*:?\s*([A-Z0-9\-]{4,})",
                    r"Loan\s+ID\s*:?\s*([A-Z0-9\-]+)"
                ],
                "field_type": "text",
                "required": True
            },
            "statement_date": {
                "patterns": [
                    r"LOAN\s+INFORMATION\s+As\s+of\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})",  # Highest priority - "LOAN INFORMATION As of Date 1/25/2023"
                    r"As\s+of\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})",  # "As of Date 1/25/2023"
                    r"Statement\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",  # "Statement Date: 01/24/2023"
                    r"PAYMENT\s+INFORMATION\s+As\s+of\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})",  # Alternative location
                ],
                "field_type": "date",
                "required": True
            },
            "principal_balance": {
                "patterns": [
                    r"Principal\s+Balance\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # In BALANCES section
                    r"BALANCES.*?Principal\s+Balance\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # Section-specific
                    r"Outstanding\s+Principal\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Current\s+Principal\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Unpaid\s+Principal\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": True
            },
            "payment_due_date": {
                "patterns": [
                    r"Payment\s+Due\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
                    r"Due\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})"
                ],
                "field_type": "date",
                "required": False
            },
            "principal_due": {
                "patterns": [
                    r"Current\s+Principal\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # In PAYMENT INFORMATION section
                    r"PAYMENT\s+INFORMATION.*?Current\s+Principal\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Principal\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Principal\s+Payment\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "interest_due": {
                "patterns": [
                    r"Current\s+Interest\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # In PAYMENT INFORMATION section
                    r"PAYMENT\s+INFORMATION.*?Current\s+Interest\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Interest\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Interest\s+Payment\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "total_payment_due": {
                "patterns": [
                    r"Total\s+Payment\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"TOTAL.*?Current.*?Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # "TOTAL" row in payment section
                    r"Amount\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Payment\s+Amount\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "tax_escrow_balance": {
                "patterns": [
                    r"Tax\s+Escrow\s+Balance\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # In BALANCES section
                    r"BALANCES.*?Tax\s+Escrow\s+Balance\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Escrow\s+for\s+Taxes\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "insurance_escrow_balance": {
                "patterns": [
                    r"Insurance\s+Escrow\s+Balance\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # In BALANCES section
                    r"BALANCES.*?Insurance\s+Escrow\s+Balance\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Escrow\s+for\s+Insurance\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "reserve_balance": {
                "patterns": [
                    r"Reserve\s+Balance\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # In BALANCES section
                    r"BALANCES.*?Reserve\s+Balance\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Reserve\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "tax_escrow_due": {
                "patterns": [
                    r"Current\s+Tax\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # In PAYMENT INFORMATION section
                    r"PAYMENT\s+INFORMATION.*?Current\s+Tax\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Tax\s+Escrow\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "insurance_escrow_due": {
                "patterns": [
                    r"Current\s+Insurance\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # In PAYMENT INFORMATION section
                    r"PAYMENT\s+INFORMATION.*?Current\s+Insurance\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Insurance\s+Escrow\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "reserve_due": {
                "patterns": [
                    r"Current\s+Reserves\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # In PAYMENT INFORMATION section
                    r"PAYMENT\s+INFORMATION.*?Current\s+Reserves\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Reserve\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "ytd_principal_paid": {
                "patterns": [
                    r"YEAR\s+TO\s+DATE.*?Principal\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # In YEAR TO DATE section
                    r"YTD.*?Principal\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Year\s+to\s+Date\s+Principal\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "ytd_interest_paid": {
                "patterns": [
                    r"YEAR\s+TO\s+DATE.*?Interest\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # In YEAR TO DATE section
                    r"YTD.*?Interest\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Year\s+to\s+Date\s+Interest\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "interest_rate": {
                "patterns": [
                    r"Interest\s+Rate\s*:?\s*(\d+\.?\d*)\s*%",
                    r"Rate\s*:?\s*(\d+\.?\d*)\s*%",
                    r"(\d+\.?\d*)\s*%\s+Interest"
                ],
                "field_type": "percentage",
                "required": False
            },
            "maturity_date": {
                "patterns": [
                    r"Maturity\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
                    r"Final\s+Payment\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
                    r"Loan\s+Maturity\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})"
                ],
                "field_type": "date",
                "required": False
            },
            "borrower_name": {
                "patterns": [
                    r"Borrower\s*:?\s*(.+?)(?:\n|$)",
                    r"Account\s+Holder\s*:?\s*(.+?)(?:\n|$)"
                ],
                "field_type": "text",
                "required": False
            },
            "property_address": {
                "patterns": [
                    r"Property\s+Address\s*:?\s*(.+?)(?:\n|$)",
                    r"Collateral\s+Address\s*:?\s*(.+?)(?:\n|$)"
                ],
                "field_type": "text",
                "required": False
            }
        }


