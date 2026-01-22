"""
Database Repair Script: Fix Missing Income Statement Total Rows

This script repairs the income statement data for Property 11, Period 169 by:
1. Calculating totals from existing line items
2. Updating the income_statement_header with correct totals
3. Inserting missing synthetic total rows (4990-0000, 5990-0000, etc.)
"""
import sys
from decimal import Decimal
from datetime import datetime

sys.path.append('/app')

from app.db.database import SessionLocal
from app.models.income_statement_data import IncomeStatementData
from app.models.income_statement_header import IncomeStatementHeader

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print("=" * 80)
        print("INCOME STATEMENT REPAIR SCRIPT")
        print("=" * 80)
        print(f"Property ID: {property_id}")
        print(f"Period ID: {period_id}")
        print()
        
        # Step 1: Calculate totals from existing line items
        print("Step 1: Calculating totals from line items...")
        print("-" * 80)
        
        all_items = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.is_calculated == False  # Only detail items
        ).all()
        
        print(f"Found {len(all_items)} detail line items")
        
        # Calculate totals
        totals = {
            "total_income": Decimal('0'),
            "base_rentals": Decimal('0'),
            "total_recovery_income": Decimal('0'),
            "total_other_income": Decimal('0'),
            "total_operating_expenses": Decimal('0'),
            "total_property_expenses": Decimal('0'),
            "total_utility_expenses": Decimal('0'),
            "total_contracted_expenses": Decimal('0'),
            "total_rm_expenses": Decimal('0'),
            "total_admin_expenses": Decimal('0'),
            "total_additional_expenses": Decimal('0'),
            "total_management_fees": Decimal('0'),
            "total_leasing_costs": Decimal('0'),
            "total_ll_expenses": Decimal('0'),
            "total_expenses": Decimal('0'),
            "noi": Decimal('0'),
            "mortgage_interest": Decimal('0'),
            "depreciation": Decimal('0'),
            "amortization": Decimal('0'),
            "net_income": Decimal('0')
        }
        
        for item in all_items:
            amount = item.period_amount or Decimal('0')
            code = item.account_code or ""
            
            if not code or '-' not in code:
                continue
            
            try:
                code_num = int(code.split('-')[0])
            except:
                continue
            
            # Income (4000-4999)
            if 4000 <= code_num < 4990:
                totals["total_income"] += amount
                if code_num == 4010:
                    totals["base_rentals"] = amount
                elif code_num in [4020, 4030, 4040, 4055, 4060]:
                    totals["total_recovery_income"] += amount
                elif code_num in [4018, 4050, 4090, 4091]:
                    totals["total_other_income"] += amount
            
            # Operating Expenses (5000-5999)
            elif 5000 <= code_num < 5990:
                totals["total_operating_expenses"] += amount
                if 5010 <= code_num <= 5014:
                    totals["total_property_expenses"] += amount
                elif 5100 <= code_num < 5199:
                    totals["total_utility_expenses"] += amount
                elif 5200 <= code_num < 5299:
                    totals["total_contracted_expenses"] += amount
                elif 5300 <= code_num < 5399:
                    totals["total_rm_expenses"] += amount
                elif 5400 <= code_num < 5499:
                    totals["total_admin_expenses"] += amount
            
            # Additional Expenses (6000-6189)
            elif 6000 <= code_num < 6190:
                totals["total_additional_expenses"] += amount
                if 6010 <= code_num <= 6020:
                    totals["total_management_fees"] += amount
                elif code_num in [6014, 6016]:
                    totals["total_leasing_costs"] += amount
            
            # Below the line (7000-7999)
            elif 7000 <= code_num < 8000:
                if code_num == 7010:
                    totals["mortgage_interest"] = amount
                elif code_num == 7020:
                    totals["depreciation"] = amount
                elif code_num == 7030:
                    totals["amortization"] = amount
        
        # Calculate derived totals
        totals["total_expenses"] = totals["total_operating_expenses"] + totals["total_additional_expenses"]
        totals["noi"] = totals["total_income"] - totals["total_expenses"]
        total_other = totals["mortgage_interest"] + totals["depreciation"] + totals["amortization"]
        totals["net_income"] = totals["noi"] - total_other
        
        print("\nCalculated Totals:")
        for key, value in totals.items():
            if value != 0:
                print(f"  {key}: ${value:,.2f}")
        
        # Step 2: Update income_statement_header
        print("\n\nStep 2: Updating income_statement_header...")
        print("-" * 80)
        
        header = db.query(IncomeStatementHeader).filter(
            IncomeStatementHeader.property_id == property_id,
            IncomeStatementHeader.period_id == period_id
        ).first()
        
        if not header:
            print("ERROR: No header found! Cannot proceed.")
            return
        
        # Update header with calculated totals
        header.total_income = totals["total_income"]
        header.base_rentals = totals["base_rentals"]
        header.total_recovery_income = totals["total_recovery_income"]
        header.total_other_income = totals["total_other_income"]
        header.total_operating_expenses = totals["total_operating_expenses"]
        header.total_property_expenses = totals["total_property_expenses"]
        header.total_utility_expenses = totals["total_utility_expenses"]
        header.total_contracted_expenses = totals["total_contracted_expenses"]
        header.total_rm_expenses = totals["total_rm_expenses"]
        header.total_admin_expenses = totals["total_admin_expenses"]
        header.total_additional_operating_expenses = totals["total_additional_expenses"]
        header.total_management_fees = totals["total_management_fees"]
        header.total_leasing_costs = totals["total_leasing_costs"]
        header.total_ll_expenses = totals["total_ll_expenses"]
        header.total_expenses = totals["total_expenses"]
        header.net_operating_income = totals["noi"]
        header.mortgage_interest = totals["mortgage_interest"]
        header.depreciation = totals["depreciation"]
        header.amortization = totals["amortization"]
        header.net_income = totals["net_income"]
        
        # Calculate percentages
        if totals["total_income"] > 0:
            header.noi_percentage = (totals["noi"] / totals["total_income"]) * Decimal('100')
            header.net_income_percentage = (totals["net_income"] / totals["total_income"]) * Decimal('100')
        
        print("✅ Header updated with calculated totals")
        
        # Step 3: Insert synthetic total rows
        print("\n\nStep 3: Inserting missing total rows...")
        print("-" * 80)
        
        synthetic_rows = [
            ("4990-0000", "TOTAL INCOME", totals["total_income"], 100),
            ("5990-0000", "TOTAL OPERATING EXPENSES", totals["total_operating_expenses"], 200),
            ("6190-0000", "TOTAL ADDITIONAL OPERATING EXPENSES", totals["total_additional_expenses"], 300),
            ("6199-0000", "TOTAL EXPENSES", totals["total_expenses"], 400),
            ("6299-0000", "NET OPERATING INCOME", totals["noi"], 500),
            ("9090-0000", "NET INCOME", totals["net_income"], 900),
        ]
        
        rows_added = 0
        for account_code, account_name, amount, line_num in synthetic_rows:
            # Check if already exists
            existing = db.query(IncomeStatementData).filter(
                IncomeStatementData.property_id == property_id,
                IncomeStatementData.period_id == period_id,
                IncomeStatementData.account_code == account_code
            ).first()
            
            if existing:
                print(f"  ⏭️  {account_code} already exists, skipping")
                continue
            
            # Only insert if amount is non-zero
            if amount == 0:
                print(f"  ⏭️  {account_code} is $0, skipping")
                continue
            
            # Create synthetic row
            new_row = IncomeStatementData(
                header_id=header.id,
                property_id=property_id,
                period_id=period_id,
                upload_id=header.upload_id,
                account_id=None,
                account_code=account_code,
                account_name=account_name,
                period_amount=amount,
                ytd_amount=None,
                period_percentage=None,
                ytd_percentage=None,
                is_subtotal=False,
                is_total=True,
                is_calculated=True,
                line_category=None,
                line_subcategory=None,
                line_number=line_num,
                account_level=1,
                is_below_the_line=False,
                extraction_confidence=Decimal('100.0'),
                match_confidence=None,
                extraction_method="repair_script",
                needs_review=False,
                period_type=header.period_type,
                accounting_basis=header.accounting_basis,
                report_generation_date=header.report_generation_date,
                page_number=None,
                extraction_x0=None,
                extraction_y0=None,
                extraction_x1=None,
                extraction_y1=None
            )
            
            db.add(new_row)
            rows_added += 1
            print(f"  ➕ Added {account_code} {account_name} = ${amount:,.2f}")
        
        # Commit all changes
        db.commit()
        
        print("\n" + "=" * 80)
        print("REPAIR COMPLETE!")
        print("=" * 80)
        print(f"✅ Header updated")
        print(f"✅ {rows_added} synthetic total rows inserted")
        print("\nYou can now re-run validations to verify all checks pass.")
        
    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
