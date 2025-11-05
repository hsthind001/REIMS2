#!/usr/bin/env python3
"""
Test real Cash Flow PDF extraction
"""
import sys
import json
from app.utils.financial_table_parser import FinancialTableParser

def test_cash_flow_pdf(pdf_path):
    """Test Cash Flow extraction with real PDF"""
    print(f"Testing: {pdf_path}")
    print("=" * 80)
    
    try:
        with open(pdf_path, 'rb') as f:
            parser = FinancialTableParser()
            result = parser.extract_cash_flow_table(f.read())
        
        print(f"✅ Success: {result['success']}")
        print(f"📄 Total Pages: {result['total_pages']}")
        print(f"📊 Total Line Items: {result['total_items']}")
        print(f"🔄 Total Adjustments: {result['total_adjustments']}")
        print(f"💰 Total Cash Accounts: {result['total_cash_accounts']}")
        print(f"🔧 Extraction Method: {result['extraction_method']}")
        print()
        
        # Show header
        print("📋 HEADER METADATA:")
        print("-" * 80)
        header = result['header']
        print(f"  Property: {header.get('property_name', 'N/A')}")
        print(f"  Property Code: {header.get('property_code', 'N/A')}")
        print(f"  Period: {header.get('report_period_start', 'N/A')} to {header.get('report_period_end', 'N/A')}")
        print(f"  Accounting Basis: {header.get('accounting_basis', 'N/A')}")
        print(f"  Report Date: {header.get('report_generation_date', 'N/A')}")
        print()
        
        # Show sample line items by section
        print("📊 LINE ITEMS BY SECTION:")
        print("-" * 80)
        
        sections = {}
        for item in result['line_items']:
            section = item.get('line_section', 'UNKNOWN')
            if section not in sections:
                sections[section] = []
            sections[section].append(item)
        
        for section, items in sections.items():
            print(f"\n{section} ({len(items)} items):")
            for i, item in enumerate(items[:3]):  # Show first 3 per section
                category = item.get('line_category', 'N/A')
                subcategory = item.get('line_subcategory', 'N/A')
                amount = item.get('period_amount', 0)
                print(f"  {i+1}. {subcategory}: ${amount:,.2f}")
                if item.get('is_subtotal'):
                    print(f"     → [SUBTOTAL]")
                if item.get('is_total'):
                    print(f"     → [TOTAL]")
        
        # Show adjustments
        if result['adjustments']:
            print(f"\n🔄 ADJUSTMENTS ({len(result['adjustments'])} items):")
            print("-" * 80)
            for i, adj in enumerate(result['adjustments'][:5]):  # Show first 5
                category = adj.get('adjustment_category', 'N/A')
                name = adj.get('adjustment_name', 'N/A')
                amount = adj.get('amount', 0)
                sign = '+' if amount > 0 else '-'
                print(f"  {i+1}. [{category}] {name}: {sign}${abs(amount):,.2f}")
                if adj.get('related_property'):
                    print(f"     → Related Property: {adj['related_property']}")
                if adj.get('related_entity'):
                    print(f"     → Related Entity: {adj['related_entity']}")
        
        # Show cash accounts
        if result['cash_accounts']:
            print(f"\n💰 CASH ACCOUNT RECONCILIATION ({len(result['cash_accounts'])} accounts):")
            print("-" * 80)
            for i, acct in enumerate(result['cash_accounts']):
                name = acct.get('account_name', 'N/A')
                beginning = acct.get('beginning_balance', 0)
                ending = acct.get('ending_balance', 0)
                diff = acct.get('difference', 0)
                print(f"  {i+1}. {name}:")
                print(f"     Beginning: ${beginning:,.2f}")
                print(f"     Ending: ${ending:,.2f}")
                print(f"     Difference: ${diff:,.2f}")
                if acct.get('is_negative_balance'):
                    print(f"     ⚠️  WARNING: Negative balance!")
        
        print()
        print("=" * 80)
        print("✅ EXTRACTION TEST COMPLETE")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    pdf_path = "/home/gurpyar/REIMS_Uploaded/ESP 2024 Cash Flow Statement.pdf"
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    
    success = test_cash_flow_pdf(pdf_path)
    sys.exit(0 if success else 1)

