"""
PDF Generator Service - Generate PDF reports from database data matching original format

This service recreates PDF documents (income statements, balance sheets, etc.) 
using extracted data from the database, allowing verification of extraction accuracy.
"""
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date
from io import BytesIO
from weasyprint import HTML, CSS
from sqlalchemy.orm import Session
import logging

from app.models.income_statement_data import IncomeStatementData
from app.models.income_statement_header import IncomeStatementHeader
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

logger = logging.getLogger(__name__)


class PDFGeneratorService:
    """Generate PDF reports from database data matching original format"""
    
    def generate_income_statement_pdf(
        self,
        upload_id: int,
        db: Session
    ) -> BytesIO:
        """
        Generate income statement PDF matching original format
        
        Args:
            upload_id: Document upload ID
            db: Database session
            
        Returns:
            BytesIO: PDF file as bytes
        """
        try:
            # Get header with property and period info
            header = db.query(IncomeStatementHeader).filter(
                IncomeStatementHeader.upload_id == upload_id
            ).first()
            
            if not header:
                raise ValueError(f"No income statement header found for upload_id {upload_id}")
            
            # Get property info for full name
            property_info = db.query(Property).filter(
                Property.id == header.property_id
            ).first()
            
            # Get period info for date formatting
            period_info = db.query(FinancialPeriod).filter(
                FinancialPeriod.id == header.period_id
            ).first()
            
            # Get line items ordered by line_number
            items = db.query(IncomeStatementData).filter(
                IncomeStatementData.upload_id == upload_id
            ).order_by(
                IncomeStatementData.line_number.asc().nulls_last()
            ).all()
            
            if not items:
                raise ValueError(f"No income statement data found for upload_id {upload_id}")
            
            # Generate HTML
            html = self._generate_income_statement_html(header, items, property_info, period_info)
            
            # Convert to PDF
            pdf_bytes = HTML(string=html).write_pdf()
            
            logger.info(f"Generated PDF for upload_id {upload_id} with {len(items)} line items")
            
            return BytesIO(pdf_bytes)
        
        except Exception as e:
            logger.error(f"Error generating income statement PDF: {str(e)}")
            raise
    
    def _generate_income_statement_html(
        self,
        header: IncomeStatementHeader,
        items: List[IncomeStatementData],
        property_info: Optional[Property] = None,
        period_info: Optional[FinancialPeriod] = None
    ) -> str:
        """Generate HTML matching original PDF format"""
        
        # Format property name
        property_name = property_info.property_name if property_info else header.property_name
        
        # Format period - try to match original format
        if period_info:
            # Format like "Dec 2023"
            period_str = period_info.period_end_date.strftime("%b %Y") if period_info.period_end_date else "N/A"
        elif header.period_end_date:
            period_str = header.period_end_date.strftime("%b %Y")
        else:
            period_str = "N/A"
        
        # Format accounting basis
        accounting_basis = header.accounting_basis or "Accrual"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: letter;
            margin: 0.75in;
        }}
        body {{
            font-family: Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.2;
            color: #000;
        }}
        .header {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .property-name {{
            font-size: 14pt;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .report-title {{
            font-size: 12pt;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .period-info {{
            font-size: 9pt;
            margin-bottom: 3px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        thead {{
            display: table-header-group;
        }}
        th {{
            text-align: left;
            font-weight: bold;
            border-bottom: 2px solid #000;
            padding: 5px 3px;
            font-size: 9pt;
        }}
        td {{
            padding: 3px;
            border-bottom: 1px solid #ddd;
            font-size: 9pt;
        }}
        .account-code {{
            width: 12%;
            font-family: 'Courier New', monospace;
        }}
        .account-name {{
            width: 38%;
        }}
        .period-col {{
            width: 25%;
            text-align: right;
        }}
        .ytd-col {{
            width: 25%;
            text-align: right;
        }}
        .section-header {{
            font-weight: bold;
            font-size: 11pt;
            background-color: #f0f0f0;
            padding: 5px 3px;
            margin-top: 10px;
        }}
        .subtotal {{
            font-weight: bold;
            border-top: 1px solid #000;
        }}
        .total {{
            font-weight: bold;
            font-size: 11pt;
            border-top: 2px solid #000;
            background-color: #e8e8e8;
        }}
        .amount {{
            text-align: right;
            white-space: nowrap;
        }}
        .percentage {{
            font-size: 8pt;
            color: #666;
            margin-left: 5px;
        }}
        .negative {{
            color: #000;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="property-name">{property_name}</div>
        <div class="report-title">Income Statement</div>
        <div class="period-info">Period = {period_str}</div>
        <div class="period-info">Book = {accounting_basis}</div>
    </div>
    
    <table>
        <thead>
            <tr>
                <th class="account-code">Account</th>
                <th class="account-name">Description</th>
                <th class="period-col">Period to Date</th>
                <th class="ytd-col">Year to Date</th>
            </tr>
        </thead>
        <tbody>
"""
        
        current_category = None
        
        for item in items:
            # Add section header if category changed
            if item.line_category and item.line_category != current_category:
                if current_category is not None:
                    html += "</tbody></table><table><tbody>"
                # Format category name (e.g., "OPERATING_EXPENSE" -> "EXPENSES")
                category_display = item.line_category.replace("_", " ").title()
                if category_display == "Operating Expense":
                    category_display = "EXPENSES"
                elif category_display == "Income":
                    category_display = "INCOME"
                html += f'<tr><td colspan="4" class="section-header">{category_display}</td></tr>'
                current_category = item.line_category
            
            # Format amounts - match original format (no commas, 2 decimal places)
            period_amt = float(item.period_amount) if item.period_amount else 0.0
            # Format without commas to match original PDF format
            period_amt_str = f"{period_amt:,.2f}".replace(",", "")
            period_pct = float(item.period_percentage) if item.period_percentage else None
            period_pct_str = f"({period_pct:.2f}%)" if period_pct is not None else ""
            
            ytd_amt = float(item.ytd_amount) if item.ytd_amount else 0.0
            # Format without commas to match original PDF format
            ytd_amt_str = f"{ytd_amt:,.2f}".replace(",", "")
            ytd_pct = float(item.ytd_percentage) if item.ytd_percentage else None
            ytd_pct_str = f"({ytd_pct:.2f}%)" if ytd_pct is not None else ""
            
            # Determine row class
            row_class = ""
            if item.is_total:
                row_class = "total"
            elif item.is_subtotal:
                row_class = "subtotal"
            
            # Handle negative amounts
            period_class = "negative" if period_amt < 0 else ""
            ytd_class = "negative" if ytd_amt < 0 else ""
            
            html += f"""
                    <tr class="{row_class}">
                        <td class="account-code">{item.account_code or ""}</td>
                        <td class="account-name">{item.account_name or ""}</td>
                        <td class="amount {period_class}">
                            {period_amt_str}
                            <span class="percentage">{period_pct_str}</span>
                        </td>
                        <td class="amount {ytd_class}">
                            {ytd_amt_str}
                            <span class="percentage">{ytd_pct_str}</span>
                        </td>
                    </tr>
            """
        
        html += """
        </tbody>
    </table>
</body>
</html>
"""
        
        return html

