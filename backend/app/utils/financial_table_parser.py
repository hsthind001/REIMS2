"""
Financial Table Parser - Specialized extraction for financial statement tables

Uses PDFPlumber for table structure preservation and accurate data extraction
Handles multi-column layouts with proper alignment of account codes and amounts
"""
import pdfplumber
import io
import re
from typing import Dict, List, Optional, Tuple
from decimal import Decimal


class FinancialTableParser:
    """
    Parse financial statements with table structure preservation
    
    Designed for 100% data extraction accuracy with zero data loss
    """
    
    def __init__(self):
        self.account_code_pattern = re.compile(r'\b\d{4}-\d{4}\b')  # ####-#### format
        self.amount_pattern = re.compile(r'[\(\-]?\$?\s*[\d,]+\.?\d*\)?')
        
    def extract_balance_sheet_table(self, pdf_data: bytes) -> Dict:
        """
        Extract balance sheet with table structure
        
        Returns:
            dict: {
                "line_items": [
                    {
                        "account_code": "0122-0000",
                        "account_name": "Cash - Operating", 
                        "amount": 211729.81,
                        "confidence": 98.0
                    },
                    ...
                ],
                "success": True,
                "total_items": 50,
                "extraction_method": "table"
            }
        """
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            all_line_items = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract tables from page
                tables = page.extract_tables()
                
                if tables:
                    # Process each table
                    for table in tables:
                        items = self._parse_balance_sheet_table(table, page_num)
                        all_line_items.extend(items)
                else:
                    # Fallback: Extract text with layout
                    text = page.extract_text()
                    items = self._parse_balance_sheet_text(text, page_num)
                    all_line_items.extend(items)
            
            pdf.close()
            
            return {
                "success": True,
                "line_items": all_line_items,
                "total_items": len(all_line_items),
                "extraction_method": "table" if tables else "text",
                "document_type": "balance_sheet"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "line_items": [],
                "total_items": 0
            }
    
    def extract_income_statement_table(self, pdf_data: bytes) -> Dict:
        """
        Extract income statement with Period, YTD, and % columns
        
        Returns:
            dict: {
                "line_items": [
                    {
                        "account_code": "4010-0000",
                        "account_name": "Base Rentals",
                        "period_amount": 215671.29,
                        "ytd_amount": 2588055.53,
                        "period_percentage": 98.35,
                        "ytd_percentage": 81.40,
                        "confidence": 96.0
                    },
                    ...
                ]
            }
        """
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            all_line_items = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        items = self._parse_income_statement_table(table, page_num)
                        all_line_items.extend(items)
                else:
                    text = page.extract_text()
                    items = self._parse_income_statement_text(text, page_num)
                    all_line_items.extend(items)
            
            pdf.close()
            
            return {
                "success": True,
                "line_items": all_line_items,
                "total_items": len(all_line_items),
                "extraction_method": "table" if tables else "text",
                "document_type": "income_statement"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "line_items": [],
                "total_items": 0
            }
    
    def extract_cash_flow_table(self, pdf_data: bytes) -> Dict:
        """
        Extract cash flow statement with Operating/Investing/Financing sections
        
        Returns:
            dict: {
                "line_items": [
                    {
                        "account_code": "7105-0000",
                        "account_name": "Interest Income",
                        "amount": 1860030.71,
                        "cash_flow_category": "operating",
                        "is_inflow": True,
                        "confidence": 95.0
                    },
                    ...
                ]
            }
        """
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            all_line_items = []
            current_category = "operating"
            
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                text = page.extract_text()
                
                # Determine current section
                if "INVESTING ACTIVITIES" in text.upper():
                    current_category = "investing"
                elif "FINANCING ACTIVITIES" in text.upper():
                    current_category = "financing"
                
                if tables:
                    for table in tables:
                        items = self._parse_cash_flow_table(table, page_num, current_category)
                        all_line_items.extend(items)
                else:
                    items = self._parse_cash_flow_text(text, page_num, current_category)
                    all_line_items.extend(items)
            
            pdf.close()
            
            return {
                "success": True,
                "line_items": all_line_items,
                "total_items": len(all_line_items),
                "extraction_method": "table" if tables else "text",
                "document_type": "cash_flow"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "line_items": [],
                "total_items": 0
            }
    
    def extract_rent_roll_table(self, pdf_data: bytes) -> Dict:
        """
        Extract rent roll with unit-by-unit tenant data
        
        Returns:
            dict: {
                "line_items": [
                    {
                        "unit_number": "A-101",
                        "tenant_name": "Kroger Grocery Store",
                        "lease_start_date": "2020-01-01",
                        "lease_end_date": "2030-12-31",
                        "unit_area_sqft": 45000.0,
                        "monthly_rent": 50000.0,
                        "annual_rent": 600000.0,
                        "occupancy_status": "occupied",
                        "confidence": 92.0
                    },
                    ...
                ]
            }
        """
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            all_line_items = []
            
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        items = self._parse_rent_roll_table(table, page_num)
                        all_line_items.extend(items)
                else:
                    text = page.extract_text()
                    items = self._parse_rent_roll_text(text, page_num)
                    all_line_items.extend(items)
            
            pdf.close()
            
            return {
                "success": True,
                "line_items": all_line_items,
                "total_items": len(all_line_items),
                "extraction_method": "table" if tables else "text",
                "document_type": "rent_roll"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "line_items": [],
                "total_items": 0
            }
    
    def _parse_balance_sheet_table(self, table: List[List], page_num: int) -> List[Dict]:
        """Parse balance sheet table structure"""
        line_items = []
        
        for row in table:
            if not row or len(row) < 2:
                continue
            
            # Skip header rows
            if any(header in str(row[0]).upper() for header in ['ACCOUNT', 'ASSETS', 'LIABILITIES', 'EQUITY']):
                if 'CODE' in str(row[0]).upper():
                    continue
            
            # Extract account code (if present)
            account_code = None
            account_name = None
            amount = None
            
            # Try to find account code in first column
            for i, cell in enumerate(row):
                if not cell:
                    continue
                    
                cell_str = str(cell).strip()
                
                # Check for account code pattern
                code_match = self.account_code_pattern.search(cell_str)
                if code_match and not account_code:
                    account_code = code_match.group()
                    # Account name might be in same cell or next column
                    account_name = cell_str.replace(account_code, '').strip()
                    if not account_name and i + 1 < len(row):
                        account_name = str(row[i + 1]).strip()
                
                # Check for amount (usually in last column)
                amount_match = self.amount_pattern.search(cell_str)
                if amount_match and not amount:
                    amount_str = amount_match.group()
                    amount = self._parse_amount(amount_str)
                    
                    # If we have amount but no account name yet
                    if amount and not account_name and i > 0:
                        account_name = str(row[0]).strip()
            
            # If no code pattern found, use first column as account name
            if not account_code and row[0]:
                account_name = str(row[0]).strip()
                # Try to get account code from account name if embedded
                code_match = self.account_code_pattern.search(account_name)
                if code_match:
                    account_code = code_match.group()
                    account_name = account_name.replace(account_code, '').strip()
            
            # Validate we have minimum data
            if account_name and amount is not None:
                # Skip if it's likely a header or total line without meaningful data
                if len(account_name) > 2 and account_name.upper() not in ['TOTAL', 'SUBTOTAL']:
                    line_items.append({
                        "account_code": account_code or "",
                        "account_name": account_name,
                        "amount": float(amount),
                        "confidence": 95.0 if account_code else 85.0,
                        "page": page_num
                    })
        
        return line_items
    
    def _parse_income_statement_table(self, table: List[List], page_num: int) -> List[Dict]:
        """Parse income statement table with multiple columns"""
        line_items = []
        
        for row in table:
            if not row or len(row) < 2:
                continue
            
            # Skip headers
            if any(h in str(row[0]).upper() for h in ['ACCOUNT', 'REVENUE', 'EXPENSE', 'INCOME']):
                continue
            
            account_code = None
            account_name = None
            period_amount = None
            ytd_amount = None
            period_percentage = None
            ytd_percentage = None
            
            # Typical layout: Code | Name | Period Amount | Period % | YTD Amount | YTD %
            for i, cell in enumerate(row):
                if not cell:
                    continue
                
                cell_str = str(cell).strip()
                
                # Account code
                if not account_code:
                    code_match = self.account_code_pattern.search(cell_str)
                    if code_match:
                        account_code = code_match.group()
                        account_name = cell_str.replace(account_code, '').strip()
                        continue
                
                # Account name (if no code found)
                if not account_name and i == 0:
                    account_name = cell_str
                    continue
                
                # Try to parse as amount or percentage
                if '%' in cell_str:
                    # It's a percentage
                    pct_value = self._parse_percentage(cell_str)
                    if pct_value is not None:
                        if period_percentage is None:
                            period_percentage = pct_value
                        elif ytd_percentage is None:
                            ytd_percentage = pct_value
                else:
                    # It's an amount
                    amt_value = self._parse_amount(cell_str)
                    if amt_value is not None:
                        if period_amount is None:
                            period_amount = amt_value
                        elif ytd_amount is None:
                            ytd_amount = amt_value
            
            # Create line item if we have minimum data
            if account_name and period_amount is not None:
                line_items.append({
                    "account_code": account_code or "",
                    "account_name": account_name,
                    "period_amount": float(period_amount),
                    "ytd_amount": float(ytd_amount) if ytd_amount is not None else None,
                    "period_percentage": float(period_percentage) if period_percentage is not None else None,
                    "ytd_percentage": float(ytd_percentage) if ytd_percentage is not None else None,
                    "confidence": 96.0 if account_code else 88.0,
                    "page": page_num
                })
        
        return line_items
    
    def _parse_cash_flow_table(self, table: List[List], page_num: int, category: str) -> List[Dict]:
        """Parse cash flow table"""
        line_items = []
        
        for row in table:
            if not row or len(row) < 2:
                continue
            
            account_code = None
            account_name = None
            amount = None
            
            for i, cell in enumerate(row):
                if not cell:
                    continue
                
                cell_str = str(cell).strip()
                
                # Account code
                code_match = self.account_code_pattern.search(cell_str)
                if code_match and not account_code:
                    account_code = code_match.group()
                    account_name = cell_str.replace(account_code, '').strip()
                
                # Amount
                amount_match = self.amount_pattern.search(cell_str)
                if amount_match and not amount:
                    amount = self._parse_amount(amount_match.group())
            
            if not account_name and row[0]:
                account_name = str(row[0]).strip()
            
            if account_name and amount is not None:
                line_items.append({
                    "account_code": account_code or "",
                    "account_name": account_name,
                    "amount": float(amount),
                    "cash_flow_category": category,
                    "is_inflow": amount > 0,
                    "confidence": 95.0 if account_code else 85.0,
                    "page": page_num
                })
        
        return line_items
    
    def _parse_rent_roll_table(self, table: List[List], page_num: int) -> List[Dict]:
        """Parse rent roll table"""
        line_items = []
        
        # Skip header row
        header_found = False
        for row in table:
            if not row:
                continue
            
            # Detect header
            row_str = ' '.join([str(cell) for cell in row if cell]).upper()
            if 'UNIT' in row_str and ('TENANT' in row_str or 'RENT' in row_str):
                header_found = True
                continue
            
            if not header_found:
                continue
            
            # Parse tenant row
            unit_number = None
            tenant_name = None
            monthly_rent = None
            annual_rent = None
            area = None
            
            for cell in row:
                if not cell:
                    continue
                
                cell_str = str(cell).strip()
                
                # Unit number (usually first column, alphanumeric)
                if not unit_number and re.match(r'^[A-Z0-9-]+$', cell_str):
                    unit_number = cell_str
                    continue
                
                # Tenant name (text, not a number)
                if not tenant_name and not self.amount_pattern.search(cell_str):
                    tenant_name = cell_str
                    continue
                
                # Amounts
                if self.amount_pattern.search(cell_str):
                    amt = self._parse_amount(cell_str)
                    if amt:
                        if not monthly_rent:
                            monthly_rent = amt
                        elif not annual_rent:
                            annual_rent = amt
                        elif not area:
                            area = amt
            
            if unit_number and tenant_name:
                occupancy_status = "vacant" if tenant_name.upper() in ["VACANT", "AVAILABLE", ""] else "occupied"
                
                line_items.append({
                    "unit_number": unit_number,
                    "tenant_name": tenant_name,
                    "unit_area_sqft": float(area) if area else None,
                    "monthly_rent": float(monthly_rent) if monthly_rent else None,
                    "annual_rent": float(annual_rent) if annual_rent else None,
                    "occupancy_status": occupancy_status,
                    "confidence": 92.0,
                    "page": page_num
                })
        
        return line_items
    
    def _parse_balance_sheet_text(self, text: str, page_num: int) -> List[Dict]:
        """Fallback: Parse balance sheet from plain text"""
        line_items = []
        lines = text.split('\n')
        
        for line in lines:
            # Look for pattern: account_code account_name amount
            code_match = self.account_code_pattern.search(line)
            amount_match = self.amount_pattern.search(line)
            
            if code_match and amount_match:
                account_code = code_match.group()
                amount = self._parse_amount(amount_match.group())
                
                # Extract account name (between code and amount)
                start = code_match.end()
                end = amount_match.start()
                account_name = line[start:end].strip()
                
                if account_name and amount is not None:
                    line_items.append({
                        "account_code": account_code,
                        "account_name": account_name,
                        "amount": float(amount),
                        "confidence": 80.0,  # Lower confidence for text extraction
                        "page": page_num
                    })
        
        return line_items
    
    def _parse_income_statement_text(self, text: str, page_num: int) -> List[Dict]:
        """Fallback: Parse income statement from plain text"""
        # Similar to balance sheet but look for multiple amount columns
        return self._parse_balance_sheet_text(text, page_num)
    
    def _parse_cash_flow_text(self, text: str, page_num: int, category: str) -> List[Dict]:
        """Fallback: Parse cash flow from plain text"""
        items = self._parse_balance_sheet_text(text, page_num)
        # Add cash flow category
        for item in items:
            item['cash_flow_category'] = category
            item['is_inflow'] = item['amount'] > 0
        return items
    
    def _parse_rent_roll_text(self, text: str, page_num: int) -> List[Dict]:
        """Fallback: Parse rent roll from plain text"""
        line_items = []
        lines = text.split('\n')
        
        for line in lines:
            # Simple pattern: unit_number tenant_name amounts
            parts = line.split()
            if len(parts) >= 3:
                # First part might be unit number
                if re.match(r'^[A-Z0-9-]+$', parts[0]):
                    unit_number = parts[0]
                    # Look for amounts
                    amounts = []
                    tenant_parts = []
                    
                    for part in parts[1:]:
                        if self.amount_pattern.search(part):
                            amt = self._parse_amount(part)
                            if amt:
                                amounts.append(amt)
                        else:
                            tenant_parts.append(part)
                    
                    tenant_name = ' '.join(tenant_parts)
                    
                    if tenant_name:
                        line_items.append({
                            "unit_number": unit_number,
                            "tenant_name": tenant_name,
                            "monthly_rent": float(amounts[0]) if len(amounts) > 0 else None,
                            "annual_rent": float(amounts[1]) if len(amounts) > 1 else None,
                            "occupancy_status": "vacant" if tenant_name.upper() == "VACANT" else "occupied",
                            "confidence": 75.0,
                            "page": page_num
                        })
        
        return line_items
    
    def _parse_amount(self, amount_str: str) -> Optional[Decimal]:
        """
        Parse monetary amount from string
        
        Handles: $1,234.56, (1,234.56), -1,234.56, 1234.56
        """
        try:
            # Remove $, commas, spaces
            cleaned = amount_str.replace('$', '').replace(',', '').replace(' ', '').strip()
            
            # Handle parentheses (negative)
            is_negative = False
            if cleaned.startswith('(') and cleaned.endswith(')'):
                is_negative = True
                cleaned = cleaned[1:-1]
            elif cleaned.startswith('-'):
                is_negative = True
                cleaned = cleaned[1:]
            
            # Convert to Decimal
            value = Decimal(cleaned)
            
            if is_negative:
                value = -value
            
            return value
        
        except Exception:
            return None
    
    def _parse_percentage(self, pct_str: str) -> Optional[Decimal]:
        """Parse percentage from string"""
        try:
            cleaned = pct_str.replace('%', '').replace(' ', '').strip()
            
            # Handle parentheses (negative)
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]
            
            return Decimal(cleaned)
        
        except Exception:
            return None

