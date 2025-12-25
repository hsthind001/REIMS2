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
            default_patterns = self._get_default_field_patterns()
            if template:
                template_structure = template.template_structure or {}
                field_patterns = template_structure.get("field_patterns", {}) or {}
            else:
                logger.warning("Mortgage statement template not found, using default patterns")
                field_patterns = {}

            # Merge in robust default patterns to ensure full coverage (especially for balances, YTD, and payment breakdowns)
            merged_patterns = {}
            for field_name, default_cfg in default_patterns.items():
                existing_cfg = field_patterns.get(field_name, {})
                existing_patterns = existing_cfg.get("patterns", [])
                merged_cfg = {
                    "patterns": default_cfg.get("patterns", []) + [p for p in existing_patterns if p not in default_cfg.get("patterns", [])],
                    "field_type": existing_cfg.get("field_type", default_cfg.get("field_type", "text")),
                    "required": existing_cfg.get("required", default_cfg.get("required", False))
                }
                merged_patterns[field_name] = merged_cfg

            # Include any extra fields from template not in defaults
            for field_name, cfg in field_patterns.items():
                if field_name not in merged_patterns:
                    merged_patterns[field_name] = cfg

            field_patterns = merged_patterns
            
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

            # Structured parsing fallback for table-style statements (fills gaps left by regex-only extraction)
            self._apply_structured_table_parsing(extracted_text, extracted_fields)
            
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

    def _apply_structured_table_parsing(self, extracted_text: str, fields: Dict) -> None:
        """
        Fallback parser for tabular mortgage statements (e.g., Wells Fargo layout)
        where text extraction separates labels from values into column blocks.
        """
        currency_re = r"([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})"

        # BALANCES block
        balances_block = re.search(
            r"BALANCES\s*(.*?)(?:YEAR\s+TO\s+DATE|PAYMENT\s+INFORMATION)",
            extracted_text,
            re.IGNORECASE | re.DOTALL
        )
        if balances_block:
            balance_nums = re.findall(currency_re, balances_block.group(1))
            if len(balance_nums) >= 6:
                balance_mapping = [
                    ("principal_balance", 0),
                    ("tax_escrow_balance", 1),
                    ("insurance_escrow_balance", 2),
                    ("reserve_balance", 3),
                    ("other_escrow_balance", 4),
                    ("suspense_balance", 5),
                ]
                for field_name, idx in balance_mapping:
                    if fields.get(field_name) is None:
                        fields[field_name] = self._parse_currency(balance_nums[idx])

        # YEAR TO DATE block
        ytd_block = re.search(
            r"YEAR\s+TO\s+DATE\s*(.*?)(?:PAYMENT\s+INFORMATION|Loan\s+Number)",
            extracted_text,
            re.IGNORECASE | re.DOTALL
        )
        if ytd_block:
            ytd_nums = re.findall(currency_re, ytd_block.group(1))
            if len(ytd_nums) >= 2:
                if fields.get("ytd_principal_paid") is None:
                    fields["ytd_principal_paid"] = self._parse_currency(ytd_nums[0])
                if fields.get("ytd_interest_paid") is None:
                    fields["ytd_interest_paid"] = self._parse_currency(ytd_nums[1])
            if len(ytd_nums) >= 5:
                if fields.get("ytd_taxes_disbursed") is None:
                    fields["ytd_taxes_disbursed"] = self._parse_currency(ytd_nums[2])
                if fields.get("ytd_insurance_disbursed") is None:
                    fields["ytd_insurance_disbursed"] = self._parse_currency(ytd_nums[3])
                if fields.get("ytd_reserve_disbursed") is None:
                    fields["ytd_reserve_disbursed"] = self._parse_currency(ytd_nums[4])

        # PAYMENT INFORMATION block
        payment_block = re.search(
            r"PAYMENT\s+INFORMATION.*?(?=Late\s+Charges|Total\s+Payment\s+Due)",
            extracted_text,
            re.IGNORECASE | re.DOTALL
        )
        if payment_block:
            pay_nums = re.findall(currency_re, payment_block.group(0))
            # First 11 values = past due rows, next 11 = current rows (Wells Fargo layout)
            if len(pay_nums) >= 22:
                past_due = pay_nums[:11]
                current = pay_nums[11:22]

                current_mapping = [
                    ("principal_due", 0),
                    ("interest_due", 1),
                    ("tax_escrow_due", 2),
                    ("insurance_escrow_due", 3),
                    ("reserve_due", 4),
                ]
                for field_name, idx in current_mapping:
                    if fields.get(field_name) is None:
                        fields[field_name] = self._parse_currency(current[idx])

                # Late and misc fees (use past due values first, then current if present)
                if fields.get("late_fees") is None and len(past_due) > 7:
                    fields["late_fees"] = self._parse_currency(past_due[7])
                if fields.get("late_fees") is None and len(current) > 7:
                    fields["late_fees"] = self._parse_currency(current[7])

                if fields.get("other_fees") is None:
                    misc_candidates = []
                    if len(past_due) > 8:
                        misc_candidates.append(past_due[8])
                    if len(current) > 8:
                        misc_candidates.append(current[8])
                    for candidate in misc_candidates:
                        parsed = self._parse_currency(candidate)
                        if parsed is not None:
                            fields["other_fees"] = parsed
                            break

                if fields.get("total_payment_due") is None:
                    fields["total_payment_due"] = self._parse_currency(current[-1])

        # Coupon/footer "Total Payment Due" (includes late charge warning) as final fallback
        if fields.get("total_payment_due") is None:
            total_due_match = re.search(
                r"Total\s+Payment\s+Due\s*[\s\$]*([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})",
                extracted_text,
                re.IGNORECASE | re.DOTALL
            )
            if total_due_match:
                coupon_total = self._parse_currency(total_due_match.group(1))
                if coupon_total is not None:
                    fields["total_payment_due"] = coupon_total
        else:
            # Upgrade to coupon total if it exists and is larger (captures late-charge inclusive amount)
            total_due_match = re.search(
                r"Total\s+Payment\s+Due\s*[\s\$]*([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})",
                extracted_text,
                re.IGNORECASE | re.DOTALL
            )
            if total_due_match:
                coupon_total = self._parse_currency(total_due_match.group(1))
                if coupon_total is not None and fields.get("total_payment_due") is not None:
                    try:
                        if coupon_total > Decimal(str(fields["total_payment_due"])):
                            fields["total_payment_due"] = coupon_total
                    except Exception:
                        pass
    
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
        suspense = fields.get("suspense_balance") or Decimal('0')
        
        fields["total_loan_balance"] = principal + tax_escrow + insurance_escrow + reserve + other_escrow + suspense
        
        # Calculate ytd_total_paid
        ytd_principal = fields.get("ytd_principal_paid") or Decimal('0')
        ytd_interest = fields.get("ytd_interest_paid") or Decimal('0')
        fields["ytd_total_paid"] = ytd_principal + ytd_interest
        
        # Calculate monthly_debt_service
        if fields.get("total_payment_due") is not None:
            fields["monthly_debt_service"] = fields.get("total_payment_due")
        else:
            principal_due = fields.get("principal_due") or Decimal('0')
            interest_due = fields.get("interest_due") or Decimal('0')
            tax_due = fields.get("tax_escrow_due") or Decimal('0')
            insurance_due = fields.get("insurance_escrow_due") or Decimal('0')
            reserve_due = fields.get("reserve_due") or Decimal('0')
            late_fees = fields.get("late_fees") or Decimal('0')
            other_fees = fields.get("other_fees") or Decimal('0')
            fields["monthly_debt_service"] = principal_due + interest_due + tax_due + insurance_due + reserve_due + late_fees + other_fees
        
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
                    r"Principal\s+Balance[\s\$\n\r]*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",  # Wells Fargo wide-spacing: "Principal Balance                    $   22,199,562.43"
                    r"BALANCES.*?Principal\s+Balance\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",  # Section-specific
                    r"Outstanding\s+Principal\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Current\s+Principal\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Unpaid\s+Principal\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
                ],
                "field_type": "currency",
                "required": True
            },
            "payment_due_date": {
                "patterns": [
                    r"Payment\s+Due\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
                    r"Due\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})",
                    r"Payment\s+Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})"
                ],
                "field_type": "date",
                "required": False
            },
            "principal_due": {
                "patterns": [
                    r"Current\s+Principal\s+Due\s+\$?\s*([\d,]+\.?\d*)",  # Wells Fargo wide-spacing: "Current Principal Due                $   34,253.84"
                    r"PAYMENT\s+INFORMATION.*?Current\s+Principal\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Principal\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Principal\s+Payment\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "interest_due": {
                "patterns": [
                    r"Current\s+Interest\s+Due\s+\$?\s*([\d,]+\.?\d*)",  # Wells Fargo wide-spacing: "Current Interest Due                 $   91,375.87"
                    r"PAYMENT\s+INFORMATION.*?Current\s+Interest\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Interest\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Interest\s+Payment\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "total_payment_due": {
                "patterns": [
                    r"Total\s+Payment\s+Due[^\d]{0,40}\$?\s*([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})",  # Wells Fargo wide-spacing: "Total Payment Due                    $   176,836.34"
                    r"TOTAL\s+PAYMENT\s+DUE[^\d]{0,40}([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})",  # Uppercase rows
                    r"TOTAL.*?Payment\s+Due[^\d]{0,40}\$?\s*([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})",  # Total row near payment section
                    r"Amount\s+Due\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})",
                    r"Payment\s+Amount\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2})"
                ],
                "field_type": "currency",
                "required": False
            },
            "tax_escrow_balance": {
                "patterns": [
                    r"Tax\s+Escrow\s+Balance[\s\$\n\r]*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",  # Wells Fargo wide-spacing: "Tax Escrow Balance                   $   204,650.95"
                    r"BALANCES.*?Tax\s+Escrow\s+Balance\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Escrow\s+for\s+Taxes\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
                ],
                "field_type": "currency",
                "required": False
            },
            "insurance_escrow_balance": {
                "patterns": [
                    r"Insurance\s+Escrow\s+Balance[\s\$\n\r]*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",  # Wells Fargo wide-spacing: "Insurance Escrow Balance             $   205,315.30"
                    r"BALANCES.*?Insurance\s+Escrow\s+Balance\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Escrow\s+for\s+Insurance\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
                ],
                "field_type": "currency",
                "required": False
            },
            "reserve_balance": {
                "patterns": [
                    r"Reserve\s+Balance[\s\$\n\r]*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",  # Wells Fargo wide-spacing: "Reserve Balance                      $   433,239.75"
                    r"BALANCES.*?Reserve\s+Balance\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Reserve\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
                ],
                "field_type": "currency",
                "required": False
            },
            "suspense_balance": {
                "patterns": [
                    r"Suspense\s+Balance[\s\$\n\r]*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Suspense\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
                ],
                "field_type": "currency",
                "required": False
            },
            "other_escrow_balance": {
                "patterns": [
                    r"FHA\s+Mtg\s+Ins\s+Prem.*?\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Other\s+Escrow\s+Balance\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Misc\s+Escrow\s+Balance\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
                ],
                "field_type": "currency",
                "required": False
            },
            "tax_escrow_due": {
                "patterns": [
                    r"Current\s+Tax\s+Due[\s\$\n\r]*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",  # Wells Fargo wide-spacing: "Current Tax Due                      $   16,048.79"
                    r"PAYMENT\s+INFORMATION.*?Current\s+Tax\s+Due\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Tax\s+Escrow\s+Due\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Tax\s+Due\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
                ],
                "field_type": "currency",
                "required": False
            },
            "insurance_escrow_due": {
                "patterns": [
                    r"Current\s+Insurance\s+Due[\s\$\n\r]*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",  # Wells Fargo wide-spacing: "Current Insurance Due                $   20,531.53"
                    r"PAYMENT\s+INFORMATION.*?Current\s+Insurance\s+Due\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Insurance\s+Escrow\s+Due\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Insurance\s+Due\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
                ],
                "field_type": "currency",
                "required": False
            },
            "reserve_due": {
                "patterns": [
                    r"Current\s+Reserves\s+Due[\s\$\n\r]*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",  # Wells Fargo wide-spacing: "Current Reserves Due                 $   14,626.31"
                    r"PAYMENT\s+INFORMATION.*?Current\s+Reserves\s+Due\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Reserve\s+Due\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
                ],
                "field_type": "currency",
                "required": False
            },
            "late_fees": {
                "patterns": [
                    r"Past\s+Due\s+Late\s+Charges\s+\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Late\s+Charge\s+Due\s+From\s+Last\s+Month\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Late\s+Charges?\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
                ],
                "field_type": "currency",
                "required": False
            },
            "other_fees": {
                "patterns": [
                    r"Past\s+Due\s+Misc\s+Amount\s+-\s*(?:Fees|Other)\s+\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Misc\s+Amount\s+-\s*Fees\s+\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
                    r"Misc\s+Fees\s*:?\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
                ],
                "field_type": "currency",
                "required": False
            },
            "ytd_principal_paid": {
                "patterns": [
                    r"Principal\s+Paid\s+\$?\s*([\d,]+\.?\d*)",  # Wells Fargo wide-spacing format: "Principal Paid                    $   250,454.78"
                    r"YEAR\s+TO\s+DATE.*?Principal\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # Traditional format with section
                    r"YTD.*?Principal\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Year\s+to\s+Date\s+Principal\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "ytd_interest_paid": {
                "patterns": [
                    r"Interest\s+Paid\s+\$?\s*([\d,]+\.?\d*)",  # Wells Fargo wide-spacing format: "Interest Paid                     $   628,953.19"
                    r"YEAR\s+TO\s+DATE.*?Interest\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",  # Traditional format with section
                    r"YTD.*?Interest\s+Paid\s*:?\s*\$?\s*([\d,]+\.?\d*)",
                    r"Year\s+to\s+Date\s+Interest\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "ytd_taxes_disbursed": {
                "patterns": [
                    r"Taxes\s+Disbursed\s+\$?\s*([\d,]+\.?\d*)",  # Wells Fargo wide-spacing: "Taxes Disbursed                      $   0.00"
                    r"YTD.*?Taxes\s+Disbursed\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "ytd_insurance_disbursed": {
                "patterns": [
                    r"Insurance\s+Disbursed\s+\$?\s*([\d,]+\.?\d*)",  # Wells Fargo wide-spacing: "Insurance Disbursed                  $   0.00"
                    r"YTD.*?Insurance\s+Disbursed\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "ytd_reserve_disbursed": {
                "patterns": [
                    r"Reserve\s+(?:Escrow\s+)?Disbursed\s+\$?\s*([\d,]+\.?\d*)",  # Wells Fargo wide-spacing: "Reserve Escrow Disbursed             $   100,391.77"
                    r"YTD.*?Reserve\s+(?:Escrow\s+)?Disbursed\s*:?\s*\$?\s*([\d,]+\.?\d*)"
                ],
                "field_type": "currency",
                "required": False
            },
            "interest_rate": {
                "patterns": [
                    r"Interest\s+Rate\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*%?",  # Allow long decimal without trailing % sign
                    r"Rate\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*%?",
                    r"([0-9]+(?:\.[0-9]+)?)\s*%\s+Interest"
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
