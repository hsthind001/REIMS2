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
from datetime import datetime


class FinancialTableParser:
    """
    Parse financial statements with table structure preservation
    
    Designed for 100% data extraction accuracy with zero data loss
    """
    
    def __init__(self):
        # Multiple account code patterns for flexibility
        self.account_code_patterns = [
            re.compile(r'\b\d{4}-\d{4}\b'),      # ####-#### format (primary)
            re.compile(r'\b\d{4}\b'),             # #### format
            re.compile(r'\b\d{3,5}-\d{3,5}\b'),   # Flexible digits
        ]
        self.account_code_pattern = self.account_code_patterns[0]  # Keep for backward compat
        # More specific amount pattern - requires comma OR decimal point to avoid matching account codes
        self.amount_pattern = re.compile(r'[\(\-]?\$?\s*(?:\d{1,3},(?:\d{3},)*\d{3}(?:\.\d{2})?|\d+\.\d{2})\)?')
        
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
        
        Template v2.0 Implementation - Extracts all 24 fields including:
        - Basic: property, unit, tenant, lease type
        - Dates: lease_from, lease_to, term_months, tenancy_years  
        - Financials: monthly/annual rent, rent per SF, recoveries, misc, deposits
        - Special: gross rent rows, vacant units, multi-unit leases
        
        Returns:
            dict: {
                "report_date": "2025-04-30",
                "property_name": "Hammond Aire Plaza",
                "property_code": "HMND",
                "line_items": [...],  # All 24 fields per record
                "success": True
            }
        """
        try:
            pdf = pdfplumber.open(io.BytesIO(pdf_data))
            all_line_items = []
            report_date = None
            property_name = None
            property_code = None
            
            # Extract report date from first page
            first_page = pdf.pages[0]
            first_page_text = first_page.extract_text()
            report_date = self._extract_report_date(first_page_text)
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                tables = page.extract_tables()
                
                # Extract property name from page
                page_property_name, page_property_code = self._extract_property_info(text)
                if page_property_name and not property_name:
                    property_name = page_property_name
                    property_code = page_property_code
                
                if tables:
                    for table in tables:
                        items = self._parse_rent_roll_table(table, page_num, report_date, property_name, property_code)
                        all_line_items.extend(items)
                else:
                    items = self._parse_rent_roll_text(text, page_num, report_date, property_name, property_code)
                    all_line_items.extend(items)
            
            pdf.close()
            
            return {
                "success": True,
                "report_date": report_date,
                "property_name": property_name,
                "property_code": property_code,
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
            
            # Skip header rows - only if entire row is just the header
            row_text = ' '.join([str(c) for c in row if c]).strip().upper()
            if row_text in ['ACCOUNT CODE', 'ACCOUNT NAME', 'AMOUNT', 'DESCRIPTION', 'BALANCE']:
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
            
            # Validate we have minimum data - accept if has name OR code
            if (account_name and len(account_name) > 2) or account_code:
                # Default amount to 0 if missing
                if amount is None:
                    amount = 0.0
                
                # Skip generic totals without codes
                if account_name and 'TOTAL' in account_name.upper() and not account_code:
                    continue
                
                line_items.append({
                    "account_code": account_code or "",
                    "account_name": account_name or "Unnamed Account",
                    "amount": float(amount),
                    "confidence": 95.0 if account_code else 80.0,
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
    
    def _parse_rent_roll_table(self, table: List[List], page_num: int, report_date: str = None, 
                               property_name: str = None, property_code: str = None) -> List[Dict]:
        """
        Parse rent roll table - Template v2.0 implementation
        
        Extracts all 24 fields including gross rent rows, tenant IDs, recoveries
        """
        line_items = []
        header_row = None
        header_map = {}
        
        # Identify header row and map columns
        for row_idx, row in enumerate(table):
            if not row:
                continue
            row_str = ' '.join([str(cell) or '' for cell in row]).upper()
            
            # Look for header row with key columns
            if 'UNIT' in row_str and ('TENANT' in row_str or 'LEASE' in row_str):
                header_row = row_idx
                # Map column positions
                for col_idx, cell in enumerate(row):
                    if cell:
                        col_name = str(cell).strip().lower()
                        # Be more specific with matching to avoid conflicts
                        if col_name in ['unit', 'unit(s)', 'units']:
                            header_map['unit'] = col_idx
                        elif col_name in ['lease', 'tenant', 'lessee', 'tenant name']:
                            header_map['tenant'] = col_idx
                        elif 'lease type' in col_name:
                            header_map['lease_type'] = col_idx
                        elif col_name in ['area', 'sq ft', 'sqft', 'square feet']:
                            header_map['area'] = col_idx
                        elif 'lease from' in col_name or col_name in ['from', 'start date', 'lease start']:
                            header_map['lease_from'] = col_idx
                        elif 'lease to' in col_name or col_name in ['to', 'end date', 'lease end', 'expiration']:
                            header_map['lease_to'] = col_idx
                        elif col_name in ['term', 'term (months)', 'lease term']:
                            header_map['term'] = col_idx
                        elif 'tenancy' in col_name or 'years' in col_name:
                            if 'remaining' not in col_name:
                                header_map['tenancy'] = col_idx
                        elif 'monthly rent/area' in col_name:
                            header_map['monthly_per_sf'] = col_idx
                        elif 'monthly rent' in col_name:
                            header_map['monthly_rent'] = col_idx
                        elif 'annual rent/area' in col_name:
                            header_map['annual_per_sf'] = col_idx
                        elif 'annual rent' in col_name:
                            header_map['annual_rent'] = col_idx
                        elif 'annual rec' in col_name or 'recoveries' in col_name:
                            header_map['recoveries'] = col_idx
                        elif 'annual misc' in col_name:
                            header_map['misc'] = col_idx
                        elif 'security' in col_name or (col_name.startswith('deposit') and 'security' not in col_name):
                            header_map['security'] = col_idx
                        elif 'loc' in col_name or 'bank guarantee' in col_name or 'letter of credit' in col_name:
                            header_map['loc'] = col_idx
                break
        
        if header_row is None:
            # No header found, use default positions
            return []
        
        # Process data rows
        for row_idx in range(header_row + 1, len(table)):
            row = table[row_idx]
            if not row or len(row) < 3:
                continue
            
            # Check if this is a summary row
            row_text = ' '.join([str(cell) or '' for cell in row]).upper()
            if 'OCCUPANCY' in row_text or 'TOTAL' in row_text or 'SUMMARY' in row_text:
                break  # Reached summary section
            
            record = self._parse_rent_roll_row(row, header_map, report_date, property_name, property_code)
            if record:
                record['page'] = page_num
                line_items.append(record)
        
        return line_items
    
    def _parse_balance_sheet_text(self, text: str, page_num: int) -> List[Dict]:
        """Fallback: Parse balance sheet from plain text - AGGRESSIVE EXTRACTION"""
        line_items = []
        lines = text.split('\n')
        
        # Skip lines that are clearly headers or page markers
        skip_patterns = [
            r'^Page \d+',
            r'^Balance Sheet',
            r'^Period =',
            r'^Book =',
            r'^Current Balance',
            r'^\s*$'
        ]
        
        for line in lines:
            # Skip empty or header lines
            if any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
                continue
            
            # Try to find account code (try all patterns)
            account_code = None
            code_match = None
            for pattern in self.account_code_patterns:
                code_match = pattern.search(line)
                if code_match:
                    account_code = code_match.group()
                    break
            
            # Try to find amount
            amount_match = self.amount_pattern.search(line)
            amount = None
            if amount_match:
                amount = self._parse_amount(amount_match.group())
            
            # Extract account name
            account_name = None
            if code_match and amount_match:
                # Account name is between code and amount
                start = code_match.end()
                end = amount_match.start()
                account_name = line[start:end].strip()
            elif code_match:
                # Has code but no amount - take rest of line as name
                account_name = line[code_match.end():].strip()
                amount = 0.0  # Default to 0 if no amount found
            elif amount_match:
                # Has amount but no code - take beginning as name
                account_name = line[:amount_match.start()].strip()
                account_code = ""  # Empty code
            
            # Add item if we have at least a name or code
            if (account_name and len(account_name) > 2) or account_code:
                # Skip generic section headers that don't have amounts
                if account_name and account_name.upper() in ['ASSETS', 'LIABILITIES', 'EQUITY', 'CURRENT ASSETS', 'CURRENT LIABILITIES']:
                    if not amount_match:
                        continue
                
                # Skip "Total" lines without codes (but keep if they have codes)
                if account_name and 'TOTAL' in account_name.upper() and not account_code:
                    continue
                
                # Skip if account code looks like a year (2020-2030) or page number
                if account_code and account_code.isdigit():
                    code_num = int(account_code)
                    if 2000 <= code_num <= 2100 or code_num < 100:  # Years or page numbers
                        continue
                
                line_items.append({
                    "account_code": account_code or "",
                    "account_name": account_name or "Unnamed Account",
                    "amount": float(amount) if amount is not None else 0.0,
                    "confidence": 90.0 if account_code else 75.0,
                    "page": page_num
                })
        
        return line_items
    
    def _parse_income_statement_text(self, text: str, page_num: int) -> List[Dict]:
        """Fallback: Parse income statement from plain text - AGGRESSIVE EXTRACTION"""
        line_items = []
        lines = text.split('\n')
        
        skip_patterns = [
            r'^Page \d+',
            r'^Income Statement',
            r'^Period =',
            r'^Book =',
            r'^\s*$'
        ]
        
        for line in lines:
            if any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
                continue
            
            # Find account code
            account_code = None
            code_match = None
            for pattern in self.account_code_patterns:
                code_match = pattern.search(line)
                if code_match:
                    account_code = code_match.group()
                    break
            
            # Find all amounts (income statements typically have multiple columns)
            amount_matches = self.amount_pattern.findall(line)
            amounts = [self._parse_amount(amt) for amt in amount_matches if self._parse_amount(amt) is not None]
            
            # Extract account name
            account_name = None
            if code_match and amount_matches:
                # Between code and first amount
                first_amt_idx = line.find(amount_matches[0])
                account_name = line[code_match.end():first_amt_idx].strip()
            elif code_match:
                account_name = line[code_match.end():].strip()
            elif amount_matches:
                # Take beginning up to first amount
                first_amt_idx = line.find(amount_matches[0])
                account_name = line[:first_amt_idx].strip()
            
            if (account_name and len(account_name) > 2) or account_code:
                # Skip section headers without amounts
                if account_name and account_name.upper() in ['REVENUE', 'INCOME', 'EXPENSES', 'NET INCOME']:
                    if not amounts:
                        continue
                
                # Skip totals without codes
                if account_name and 'TOTAL' in account_name.upper() and not account_code:
                    continue
                
                # Skip if account code looks like a year or page number
                if account_code and account_code.isdigit():
                    code_num = int(account_code)
                    if 2000 <= code_num <= 2100 or code_num < 100:
                        continue
                
                line_items.append({
                    "account_code": account_code or "",
                    "account_name": account_name or "Unnamed Account",
                    "period_amount": float(amounts[0]) if len(amounts) > 0 else 0.0,
                    "ytd_amount": float(amounts[1]) if len(amounts) > 1 else None,
                    "period_percentage": None,
                    "ytd_percentage": None,
                    "confidence": 90.0 if account_code else 75.0,
                    "page": page_num
                })
        
        return line_items
    
    def _parse_cash_flow_text(self, text: str, page_num: int, category: str) -> List[Dict]:
        """Fallback: Parse cash flow from plain text - AGGRESSIVE EXTRACTION"""
        line_items = []
        lines = text.split('\n')
        
        skip_patterns = [
            r'^Page \d+',
            r'^Cash Flow',
            r'^Period =',
            r'^Book =',
            r'^\s*$'
        ]
        
        for line in lines:
            if any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
                continue
            
            # Update category based on section headers
            if "INVESTING ACTIVITIES" in line.upper():
                category = "investing"
                continue
            elif "FINANCING ACTIVITIES" in line.upper():
                category = "financing"
                continue
            elif "OPERATING ACTIVITIES" in line.upper():
                category = "operating"
                continue
            
            # Find account code
            account_code = None
            code_match = None
            for pattern in self.account_code_patterns:
                code_match = pattern.search(line)
                if code_match:
                    account_code = code_match.group()
                    break
            
            # Find amount
            amount_match = self.amount_pattern.search(line)
            amount = None
            if amount_match:
                amount = self._parse_amount(amount_match.group())
            
            # Extract account name
            account_name = None
            if code_match and amount_match:
                start = code_match.end()
                end = amount_match.start()
                account_name = line[start:end].strip()
            elif code_match:
                account_name = line[code_match.end():].strip()
                amount = 0.0
            elif amount_match:
                account_name = line[:amount_match.start()].strip()
                account_code = ""
            
            if (account_name and len(account_name) > 2) or account_code:
                # Skip totals without codes
                if account_name and 'TOTAL' in account_name.upper() and not account_code:
                    continue
                
                # Skip if account code looks like a year or page number
                if account_code and account_code.isdigit():
                    code_num = int(account_code)
                    if 2000 <= code_num <= 2100 or code_num < 100:
                        continue
                
                line_items.append({
                    "account_code": account_code or "",
                    "account_name": account_name or "Unnamed Account",
                    "amount": float(amount) if amount is not None else 0.0,
                    "cash_flow_category": category,
                    "is_inflow": (amount or 0) > 0,
                    "confidence": 90.0 if account_code else 75.0,
                    "page": page_num
                })
        
        return line_items
    
    def _parse_rent_roll_text(self, text: str, page_num: int, report_date: str = None,
                              property_name: str = None, property_code: str = None) -> List[Dict]:
        """
        Fallback: Parse rent roll from plain text
        
        Less accurate than table-based extraction, but handles non-tabular layouts
        """
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
                        is_vacant = tenant_name.upper() in ["VACANT", "AVAILABLE"]
                        
                        record = {
                            "property_name": property_name,
                            "property_code": property_code,
                            "report_date": report_date,
                            "unit_number": unit_number,
                            "tenant_name": tenant_name,
                            "monthly_rent": float(amounts[0]) if len(amounts) > 0 else None,
                            "annual_rent": float(amounts[1]) if len(amounts) > 1 else None,
                            "occupancy_status": "vacant" if is_vacant else "occupied",
                            "is_vacant": is_vacant,
                            "is_gross_rent_row": False,
                            "confidence": 75.0,
                            "page": page_num
                        }
                        line_items.append(record)
        
        return line_items
    
    def _extract_report_date(self, text: str) -> Optional[str]:
        """
        Extract report date from text
        
        Looks for "As of Date: MM/DD/YYYY" and converts to ISO format
        """
        match = re.search(r'As of Date:\s*(\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            try:
                dt = datetime.strptime(date_str, '%m/%d/%Y')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass
        return None
    
    def _extract_property_info(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract property name and code from text
        
        Looks for format: "Property Name (code)" or "Property Name(code)"
        Returns: (property_name, property_code)
        """
        # Pattern: Text followed by (code) where code is 2-5 letters
        match = re.search(r'([A-Z][^(]+?)\s*\(([A-Z]{2,5})\)', text, re.IGNORECASE)
        if match:
            prop_name = match.group(1).strip()
            prop_code = match.group(2).upper()
            # Verify it looks like a property name (not just any parenthesized text)
            if len(prop_name) > 5 and any(word in prop_name.lower() for word in ['plaza', 'commons', 'crossing', 'center', 'mall', 'shore']):
                return prop_name, prop_code
        return None, None
    
    def _parse_rent_roll_row(self, row: List, header_map: Dict, report_date: str = None, 
                             property_name: str = None, property_code: str = None) -> Optional[Dict]:
        """
        Parse a single rent roll row extracting all 24 fields
        
        Template v2.0 fields:
        - property_name, property_code, report_date  
        - unit_number, tenant_name, tenant_id
        - lease_type, area_sqft
        - lease_from_date, lease_to_date, term_months, tenancy_years
        - monthly_rent, monthly_rent_per_sf, annual_rent, annual_rent_per_sf
        - annual_recoveries_per_sf, annual_misc_per_sf
        - security_deposit, loc_amount
        - is_vacant, is_gross_rent_row, notes
        """
        record = {
            'property_name': property_name,
            'property_code': property_code,
            'report_date': report_date,
            'is_vacant': False,
            'is_gross_rent_row': False,
            'tenant_id': None,
            'notes': None
        }
        
        # Helper to safely get cell value
        def get_cell(col_name):
            if col_name in header_map:
                idx = header_map[col_name]
                if idx < len(row) and row[idx]:
                    return str(row[idx]).strip()
            return None
        
        # Extract unit number (required)
        unit = get_cell('unit')
        if not unit:
            return None
        record['unit_number'] = unit
        
        # Extract tenant/lease name
        tenant = get_cell('tenant')
        if not tenant:
            return None
        
        # Validate tenant name - should not be a date or number
        # If it looks like a date (MM/DD/YYYY), column mapping is likely wrong
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', tenant.strip()):
            # This is a date, not a tenant name - column misalignment
            return None
        
        # Check for "Gross Rent" row (special row type)
        if 'gross rent' in tenant.lower():
            record['is_gross_rent_row'] = True
            record['tenant_name'] = 'Gross Rent'
            # For gross rent rows, only extract financial amounts
            monthly_val = get_cell('monthly_rent')
            if monthly_val:
                record['monthly_rent'] = float(self._parse_amount(monthly_val) or 0)
            annual_val = get_cell('annual_rent')
            if annual_val:
                record['annual_rent'] = float(self._parse_amount(annual_val) or 0)
            monthly_per_sf_val = get_cell('monthly_per_sf')
            if monthly_per_sf_val:
                record['monthly_rent_per_sqft'] = float(self._parse_amount(monthly_per_sf_val) or 0)
            annual_per_sf_val = get_cell('annual_per_sf')
            if annual_per_sf_val:
                record['annual_rent_per_sqft'] = float(self._parse_amount(annual_per_sf_val) or 0)
            return record
        
        # Check for VACANT unit
        if tenant.upper() in ['VACANT', 'AVAILABLE']:
            record['is_vacant'] = True
            record['occupancy_status'] = 'vacant'
            record['tenant_name'] = 'VACANT'
            # Extract area for vacant units
            area_val = get_cell('area')
            if area_val:
                record['unit_area_sqft'] = float(self._parse_amount(area_val) or 0)
            return record
        
        # Extract tenant name and ID
        tenant_match = re.match(r'(.+?)\s*\(t(\d+)\)', tenant)
        if tenant_match:
            record['tenant_name'] = tenant_match.group(1).strip()
            record['tenant_id'] = f"t{tenant_match.group(2)}"
        else:
            record['tenant_name'] = tenant
        
        # Extract lease type
        lease_type = get_cell('lease_type')
        if lease_type:
            record['lease_type'] = lease_type
        
        # Extract area
        area_val = get_cell('area')
        if area_val:
            parsed_area = self._parse_amount(area_val)
            if parsed_area is not None:
                record['unit_area_sqft'] = float(parsed_area)
        
        # Extract dates
        lease_from = get_cell('lease_from')
        if lease_from:
            record['lease_start_date'] = self._parse_rent_roll_date(lease_from)
        
        lease_to = get_cell('lease_to')
        if lease_to:
            record['lease_end_date'] = self._parse_rent_roll_date(lease_to)
        
        # Extract term months
        term_val = get_cell('term')
        if term_val:
            try:
                record['lease_term_months'] = int(float(self._parse_amount(term_val) or 0))
            except:
                pass
        
        # Extract tenancy years
        tenancy_val = get_cell('tenancy')
        if tenancy_val:
            parsed_tenancy = self._parse_amount(tenancy_val)
            if parsed_tenancy:
                record['tenancy_years'] = float(parsed_tenancy)
        
        # Calculate tenancy years if not provided
        if not record.get('tenancy_years') and record.get('lease_start_date') and report_date:
            try:
                start_dt = datetime.strptime(record['lease_start_date'], '%Y-%m-%d')
                report_dt = datetime.strptime(report_date, '%Y-%m-%d')
                days_diff = (report_dt - start_dt).days
                record['tenancy_years'] = round(days_diff / 365.25, 2)
            except:
                pass
        
        # Extract monthly rent
        monthly_val = get_cell('monthly_rent')
        if monthly_val:
            parsed_monthly = self._parse_amount(monthly_val)
            if parsed_monthly is not None:
                record['monthly_rent'] = float(parsed_monthly)
        
        # Extract monthly rent per SF
        monthly_per_sf_val = get_cell('monthly_per_sf')
        if monthly_per_sf_val:
            parsed_per_sf = self._parse_amount(monthly_per_sf_val)
            if parsed_per_sf is not None:
                # Sanity check: rent per SF should be < $50/month for retail
                if float(parsed_per_sf) < 50.0:
                    record['monthly_rent_per_sqft'] = float(parsed_per_sf)
        
        # Calculate monthly per SF if missing
        if not record.get('monthly_rent_per_sqft') and record.get('monthly_rent') and record.get('unit_area_sqft'):
            if record['unit_area_sqft'] > 0:
                calculated = record['monthly_rent'] / record['unit_area_sqft']
                # Sanity check
                if calculated < 50.0:
                    record['monthly_rent_per_sqft'] = round(calculated, 4)
        
        # Extract annual rent
        annual_val = get_cell('annual_rent')
        if annual_val:
            parsed_annual = self._parse_amount(annual_val)
            if parsed_annual is not None:
                record['annual_rent'] = float(parsed_annual)
        
        # Calculate annual rent if missing
        if not record.get('annual_rent') and record.get('monthly_rent'):
            record['annual_rent'] = round(record['monthly_rent'] * 12, 2)
        
        # Extract annual rent per SF
        annual_per_sf_val = get_cell('annual_per_sf')
        if annual_per_sf_val:
            parsed_annual_sf = self._parse_amount(annual_per_sf_val)
            if parsed_annual_sf is not None:
                # Sanity check: annual rent per SF should be < $600/year for retail
                if float(parsed_annual_sf) < 600.0:
                    record['annual_rent_per_sqft'] = float(parsed_annual_sf)
        
        # Calculate annual per SF if missing
        if not record.get('annual_rent_per_sqft') and record.get('monthly_rent_per_sqft'):
            calculated = record['monthly_rent_per_sqft'] * 12
            # Sanity check
            if calculated < 600.0:
                record['annual_rent_per_sqft'] = round(calculated, 2)
        
        # Extract recoveries per SF
        recoveries_val = get_cell('recoveries')
        if recoveries_val:
            parsed_recoveries = self._parse_amount(recoveries_val)
            if parsed_recoveries is not None:
                record['annual_recoveries_per_sf'] = float(parsed_recoveries)
        
        # Extract misc per SF
        misc_val = get_cell('misc')
        if misc_val:
            parsed_misc = self._parse_amount(misc_val)
            if parsed_misc is not None:
                record['annual_misc_per_sf'] = float(parsed_misc)
        
        # Extract security deposit
        security_val = get_cell('security')
        if security_val:
            parsed_security = self._parse_amount(security_val)
            if parsed_security is not None:
                record['security_deposit'] = float(parsed_security)
        
        # Extract LOC
        loc_val = get_cell('loc')
        if loc_val:
            parsed_loc = self._parse_amount(loc_val)
            if parsed_loc is not None:
                record['loc_amount'] = float(parsed_loc)
        
        # Set occupancy status
        if not record.get('occupancy_status'):
            record['occupancy_status'] = 'occupied' if not record['is_vacant'] else 'vacant'
        
        # Set confidence
        record['confidence'] = 95.0
        
        return record
    
    def _parse_rent_roll_date(self, date_str: str) -> Optional[str]:
        """
        Parse rent roll date and return in ISO format (YYYY-MM-DD)
        
        Handles formats: MM/DD/YYYY, MM/DD/YY
        """
        if not date_str or not isinstance(date_str, str):
            return None
        
        date_str = date_str.strip()
        if not date_str or date_str == '-':
            return None
        
        # Try different formats
        formats = ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d']
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return None
    
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

