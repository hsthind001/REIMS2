"""
Template-based PDF extraction system

Matches extracted text to predefined templates for structured data extraction
"""
from typing import Dict, List, Optional
import re
from fuzzywuzzy import fuzz
from app.models.extraction_template import ExtractionTemplate
from app.models.chart_of_accounts import ChartOfAccounts
from sqlalchemy.orm import Session


class TemplateExtractor:
    """Extract structured financial data using templates"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def extract_using_template(
        self,
        extracted_text: str,
        document_type: str,
        template_name: Optional[str] = None
    ) -> Dict:
        """
        Extract structured data using template matching
        
        Args:
            extracted_text: Raw text from PDF
            document_type: balance_sheet, income_statement, cash_flow, rent_roll
            template_name: Specific template to use (None = use default)
        
        Returns:
            dict: Structured extraction results
        """
        try:
            # Load template
            if template_name:
                template = self.db.query(ExtractionTemplate).filter(
                    ExtractionTemplate.template_name == template_name
                ).first()
            else:
                template = self.db.query(ExtractionTemplate).filter(
                    ExtractionTemplate.document_type == document_type,
                    ExtractionTemplate.is_default == True
                ).first()
            
            if not template:
                return {
                    "success": False,
                    "error": f"No template found for {document_type}"
                }
            
            # Load chart of accounts for this document type
            accounts = self.db.query(ChartOfAccounts).filter(
                ChartOfAccounts.document_types.contains([document_type]),
                ChartOfAccounts.is_active == True
            ).order_by(ChartOfAccounts.display_order).all()
            
            # Extract line items based on template
            line_items = self._extract_line_items(
                extracted_text,
                template,
                accounts
            )
            
            return {
                "document_type": document_type,
                "template_used": template.template_name,
                "line_items": line_items,
                "total_items_extracted": len(line_items),
                "success": True
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_line_items(
        self,
        text: str,
        template: ExtractionTemplate,
        accounts: List[ChartOfAccounts]
    ) -> List[Dict]:
        """Extract individual line items from text"""
        
        line_items = []
        
        # Split text into lines
        lines = text.split('\n')
        
        for account in accounts:
            # Try to find this account in the text
            match_result = self._find_account_in_text(
                account,
                lines,
                template
            )
            
            if match_result:
                line_items.append(match_result)
        
        return line_items
    
    def _find_account_in_text(
        self,
        account: ChartOfAccounts,
        lines: List[str],
        template: ExtractionTemplate
    ) -> Optional[Dict]:
        """
        Find and extract value for specific account
        
        Uses fuzzy matching to handle OCR errors and variations
        """
        account_name = account.account_name.lower()
        account_variations = self._generate_name_variations(account_name)
        
        for line in lines:
            line_lower = line.lower()
            
            # Try fuzzy matching
            for variation in account_variations:
                similarity = fuzz.ratio(variation, line_lower)
                
                if similarity > 80:  # 80% similarity threshold
                    # Extract monetary value from this line
                    value = self._extract_monetary_value(line)
                    
                    if value is not None:
                        return {
                            "account_code": account.account_code,
                            "account_name": account.account_name,
                            "value": value,
                            "matched_text": line.strip(),
                            "confidence": similarity,
                            "is_calculated": account.is_calculated
                        }
        
        return None
    
    def _generate_name_variations(self, name: str) -> List[str]:
        """Generate common variations of account name"""
        variations = [name]
        
        # Remove common words
        without_common = re.sub(r'\b(and|or|the|a|an)\b', '', name).strip()
        if without_common != name:
            variations.append(without_common)
        
        # Remove punctuation
        without_punct = re.sub(r'[^\w\s]', '', name)
        if without_punct != name:
            variations.append(without_punct)
        
        # Abbreviations
        if 'accounts receivable' in name:
            variations.append('a/r')
            variations.append('ar')
        if 'accounts payable' in name:
            variations.append('a/p')
            variations.append('ap')
        
        return list(set(variations))
    
    def _extract_monetary_value(self, text: str) -> Optional[float]:
        """
        Extract monetary value from text line
        
        Handles formats: $1,234.56  (1,234.56)  1234.56
        """
        # Remove currency symbols and whitespace
        text = text.replace('$', '').replace(',', '').strip()
        
        # Pattern for monetary values
        # Handles: 1234.56, (1234.56), -1234.56
        pattern = r'[-]?\(?\d+(?:\.\d{1,2})?\)?'
        
        matches = re.findall(pattern, text)
        
        if matches:
            # Take the last number (usually the total on the right)
            value_str = matches[-1]
            
            # Handle parentheses (negative values)
            is_negative = '(' in value_str
            value_str = value_str.replace('(', '').replace(')', '')
            
            try:
                value = float(value_str)
                return -value if is_negative else value
            except ValueError:
                return None
        
        return None

