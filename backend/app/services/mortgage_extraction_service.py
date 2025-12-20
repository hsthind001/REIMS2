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
        
        Args:
            extracted_text: Raw text extracted from PDF
            pdf_data: Optional PDF bytes for coordinate extraction
            
        Returns:
            dict: Extracted mortgage data with all fields
        """
        try:
            # Load mortgage statement template
            template = self.db.query(ExtractionTemplate).filter(
                ExtractionTemplate.document_type == 'mortgage_statement',
                ExtractionTemplate.is_default == True
            ).first()
            
            if not template:
                return {
                    "success": False,
                    "error": "Mortgage statement extraction template not found"
                }
            
            # Get field patterns from template
            template_structure = template.template_structure or {}
            field_patterns = template_structure.get("field_patterns", {})
            
            # Extract all fields
            extracted_fields = {}
            extraction_coordinates = {}
            
            for field_name, field_config in field_patterns.items():
                patterns = field_config.get("patterns", [])
                field_type = field_config.get("field_type", "text")
                
                # Try each pattern
                value = None
                for pattern in patterns:
                    match = re.search(pattern, extracted_text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        value = match.group(1) if match.groups() else match.group(0)
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
            
            # Try to match lender name
            lender_id = self._match_lender(extracted_text)
            if lender_id:
                extracted_fields["lender_id"] = lender_id
            
            # Calculate derived fields
            extracted_fields = self._calculate_derived_fields(extracted_fields)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(extracted_fields, template_structure)
            
            return {
                "success": True,
                "mortgage_data": extracted_fields,
                "extraction_coordinates": extraction_coordinates,
                "confidence": confidence,
                "extraction_method": "template_patterns"
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
    
    def _parse_date(self, value: str) -> Optional[datetime]:
        """Parse date from string"""
        if not value:
            return None
        
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
                return datetime.strptime(value.strip(), fmt).date()
            except:
                continue
        
        return None
    
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


