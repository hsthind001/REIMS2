import sys
from sqlalchemy import select, text, func, desc
from decimal import Decimal

# Add /app to path
sys.path.append('/app')

from app.db.database import SessionLocal
from app.models.extraction_log import ExtractionLog
from app.models.income_statement_data import IncomeStatementData

def main():
    db = SessionLocal()
    try:
        property_id = 11
        period_id = 169
        
        print(f"Checking Extraction Logs for Property {property_id}, Period {period_id}...")
        print("=" * 80)
        
        # Find the most recent income statement extraction for this property/period
        recent_log = db.query(ExtractionLog).filter(
            ExtractionLog.document_type == "income_statement"
        ).order_by(desc(ExtractionLog.created_at)).first()
        
        if recent_log:
            print(f"\n1. MOST RECENT INCOME STATEMENT EXTRACTION:")
            print(f"   - File: {recent_log.filename}")
            print(f"   - Uploaded: {recent_log.created_at}")
            print(f"   - Strategy: {recent_log.strategy_used}")
            print(f"   - Confidence: {recent_log.confidence_score}")
            print(f"   - Needs Review: {recent_log.needs_review}")
            print(f"   - Recommendations: {recent_log.recommendations}")
        
        # Now let's manually calculate what the totals SHOULD be
        print(f"\n\n2. MANUAL CALCULATION OF TOTALS:")
        print("-" * 80)
        
        # Income total (4010-4091, exclude is_calculated=True to avoid NOI)
        income_sum = db.query(func.sum(IncomeStatementData.period_amount)).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code >= '4010-0000',
            IncomeStatementData.account_code < '4990-0000',
            IncomeStatementData.is_calculated == False
        ).scalar() or Decimal('0')
        print(f"Total Income (4010-4091): ${income_sum:,.2f}")
        
        # Operating expenses (5010-5989)
        opex_sum = db.query(func.sum(IncomeStatementData.period_amount)).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code >= '5010-0000',
            IncomeStatementData.account_code < '5990-0000',
            IncomeStatementData.is_calculated == False
        ).scalar() or Decimal('0')
        print(f"Total Operating Expenses (5010-5989): ${opex_sum:,.2f}")
        
        # Additional expenses (6010-6189)
        addl_sum = db.query(func.sum(IncomeStatementData.period_amount)).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.account_code >= '6010-0000',
            IncomeStatementData.account_code < '6190-0000',
            IncomeStatementData.is_calculated == False
        ).scalar() or Decimal('0')
        print(f"Total Additional Expenses (6010-6189): ${addl_sum:,.2f}")
        
        # Total expenses
        total_expenses = opex_sum + addl_sum
        print(f"Total Expenses (OpEx + Additional): ${total_expenses:,.2f}")
        
        # NOI
        noi = income_sum - total_expenses
        print(f"NOI (Income - Total Expenses): ${noi:,.2f}")
        
        # Now check if calculated NOI rows exist (with is_calculated=True)
        print(f"\n\n3. CHECKING FOR is_calculated=TRUE ROWS:")
        print("-" * 80)
        
        calculated_rows = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == property_id,
            IncomeStatementData.period_id == period_id,
            IncomeStatementData.is_calculated == True
        ).all()
        
        if calculated_rows:
            print(f"Found {len(calculated_rows)} calculated rows:")
            for row in calculated_rows:
                print(f"  {row.account_code} - {row.account_name}: ${row.period_amount:,.2f} [is_total={row.is_total}]")
        else:
            print("NO CALCULATED ROWS FOUND!")
            print("This means _insert_synthetic_total_rows was NOT executed or failed.")
        
        # Check income statement header to see what totals were stored there
        print(f"\n\n4. INCOME STATEMENT HEADER TOTALS:")
        print("-" * 80)
        from app.models.income_statement_header import IncomeStatementHeader
        
        header = db.query(IncomeStatementHeader).filter(
            IncomeStatementHeader.property_id == property_id,
            IncomeStatementHeader.period_id == period_id
        ).first()
        
        if header:
            print(f"Total Income (Header): ${header.total_income:,.2f}")
            print(f"Total Operating Expenses (Header): ${header.total_operating_expenses:,.2f}")
            print(f"Total Additional Expenses (Header): ${header.total_additional_operating_expenses:,.2f}")
            print(f"Total Expenses (Header): ${header.total_expenses:,.2f}")
            print(f"NOI (Header): ${header.net_operating_income:,.2f}")
            print(f"Net Income (Header): ${header.net_income:,.2f}")
        else:
            print("NO HEADER FOUND!")

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
