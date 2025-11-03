"""
Validation Rules Seed Data

Comprehensive business logic validation rules for financial statements
20 rules covering balance sheets, income statements, cash flow, and rent rolls
"""
from app.db.database import SessionLocal
from app.models.validation_rule import ValidationRule


def seed_validation_rules():
    """Seed all validation rules into database"""
    db = SessionLocal()
    
    try:
        # Clear existing rules (optional - for fresh seed)
        # db.query(ValidationRule).delete()
        
        rules = [
            # ==================== BALANCE SHEET RULES ====================
            {
                "rule_name": "balance_sheet_equation",
                "rule_description": "Balance Sheet Equation: Assets = Liabilities + Equity",
                "document_type": "balance_sheet",
                "rule_type": "balance_check",
                "rule_formula": "total_assets = total_liabilities + total_equity",
                "error_message": "Assets must equal Liabilities plus Equity",
                "severity": "error",
                "is_active": True
            },
            {
                "rule_name": "balance_sheet_current_assets",
                "rule_description": "Current Assets sum correctly",
                "document_type": "balance_sheet",
                "rule_type": "sum_check",
                "rule_formula": "sum(current_asset_accounts) = total_current_assets",
                "error_message": "Sum of current asset accounts doesn't match total",
                "severity": "warning",
                "is_active": True
            },
            {
                "rule_name": "balance_sheet_fixed_assets",
                "rule_description": "Fixed Assets sum correctly",
                "document_type": "balance_sheet",
                "rule_type": "sum_check",
                "rule_formula": "sum(fixed_asset_accounts) = total_fixed_assets",
                "error_message": "Sum of fixed asset accounts doesn't match total",
                "severity": "warning",
                "is_active": True
            },
            {
                "rule_name": "balance_sheet_no_negative_cash",
                "rule_description": "Cash accounts should not be negative",
                "document_type": "balance_sheet",
                "rule_type": "range_check",
                "rule_formula": "cash >= 0",
                "error_message": "Cash balance is negative",
                "severity": "warning",
                "is_active": True
            },
            {
                "rule_name": "balance_sheet_no_negative_equity",
                "rule_description": "Total Equity should not be negative (warning for distressed properties)",
                "document_type": "balance_sheet",
                "rule_type": "range_check",
                "rule_formula": "total_equity >= 0",
                "error_message": "Total Equity is negative (property may be underwater)",
                "severity": "warning",
                "is_active": True
            },
            
            # ==================== INCOME STATEMENT RULES ====================
            {
                "rule_name": "income_statement_total_revenue",
                "rule_description": "Revenue accounts sum to Total Revenue",
                "document_type": "income_statement",
                "rule_type": "sum_check",
                "rule_formula": "sum(revenue_accounts) = total_revenue",
                "error_message": "Sum of revenue accounts doesn't match total revenue",
                "severity": "error",
                "is_active": True
            },
            {
                "rule_name": "income_statement_total_expenses",
                "rule_description": "Expense accounts sum to Total Expenses",
                "document_type": "income_statement",
                "rule_type": "sum_check",
                "rule_formula": "sum(expense_accounts) = total_expenses",
                "error_message": "Sum of expense accounts doesn't match total expenses",
                "severity": "error",
                "is_active": True
            },
            {
                "rule_name": "income_statement_net_income",
                "rule_description": "Net Income = Total Revenue - Total Expenses",
                "document_type": "income_statement",
                "rule_type": "balance_check",
                "rule_formula": "net_income = total_revenue - total_expenses",
                "error_message": "Net Income calculation is incorrect",
                "severity": "error",
                "is_active": True
            },
            {
                "rule_name": "income_statement_percentages",
                "rule_description": "Period and YTD percentages should be reasonable",
                "document_type": "income_statement",
                "rule_type": "range_check",
                "rule_formula": "-100 <= percentage <= 200",
                "error_message": "Percentage values are out of reasonable range",
                "severity": "warning",
                "is_active": True
            },
            {
                "rule_name": "income_statement_ytd_consistency",
                "rule_description": "YTD amounts should be >= Period amounts",
                "document_type": "income_statement",
                "rule_type": "range_check",
                "rule_formula": "ytd_amount >= period_amount",
                "error_message": "YTD amount is less than Period amount",
                "severity": "warning",
                "is_active": True
            },
            {
                "rule_name": "income_statement_no_negative_revenue",
                "rule_description": "Revenue accounts should not be negative",
                "document_type": "income_statement",
                "rule_type": "range_check",
                "rule_formula": "revenue >= 0",
                "error_message": "Revenue account has negative amount",
                "severity": "warning",
                "is_active": True
            },
            
            # ==================== CASH FLOW RULES ====================
            {
                "rule_name": "cash_flow_categories_sum",
                "rule_description": "Operating + Investing + Financing = Net Change in Cash",
                "document_type": "cash_flow",
                "rule_type": "balance_check",
                "rule_formula": "operating + investing + financing = net_change",
                "error_message": "Cash flow categories don't sum to net change",
                "severity": "error",
                "is_active": True
            },
            {
                "rule_name": "cash_flow_beginning_ending",
                "rule_description": "Beginning Cash + Net Change = Ending Cash",
                "document_type": "cash_flow",
                "rule_type": "balance_check",
                "rule_formula": "beginning_cash + net_change = ending_cash",
                "error_message": "Beginning + Net Change doesn't equal Ending Cash",
                "severity": "error",
                "is_active": True
            },
            {
                "rule_name": "cash_flow_cross_check_balance_sheet",
                "rule_description": "Ending Cash (CF) should match Cash (BS)",
                "document_type": "cash_flow",
                "rule_type": "cross_statement_check",
                "rule_formula": "ending_cash_cf = cash_bs",
                "error_message": "Ending Cash on Cash Flow doesn't match Cash on Balance Sheet",
                "severity": "warning",
                "is_active": True
            },
            
            # ==================== RENT ROLL RULES ====================
            {
                "rule_name": "rent_roll_occupancy_rate",
                "rule_description": "Occupancy rate should be between 0-100%",
                "document_type": "rent_roll",
                "rule_type": "range_check",
                "rule_formula": "0 <= occupancy_rate <= 100",
                "error_message": "Occupancy rate is out of valid range (0-100%)",
                "severity": "error",
                "is_active": True
            },
            {
                "rule_name": "rent_roll_total_rent",
                "rule_description": "Sum of tenant rents should match total",
                "document_type": "rent_roll",
                "rule_type": "sum_check",
                "rule_formula": "sum(monthly_rent) = total_monthly_rent",
                "error_message": "Sum of individual tenant rents doesn't match total",
                "severity": "warning",
                "is_active": True
            },
            {
                "rule_name": "rent_roll_no_duplicate_units",
                "rule_description": "Each unit should appear only once",
                "document_type": "rent_roll",
                "rule_type": "uniqueness_check",
                "rule_formula": "unit_number unique per period",
                "error_message": "Duplicate unit numbers found in rent roll",
                "severity": "error",
                "is_active": True
            },
            {
                "rule_name": "rent_roll_valid_lease_dates",
                "rule_description": "Lease start date must be before end date",
                "document_type": "rent_roll",
                "rule_type": "date_check",
                "rule_formula": "lease_start_date < lease_end_date",
                "error_message": "Lease start date is not before end date",
                "severity": "warning",
                "is_active": True
            },
            {
                "rule_name": "rent_roll_annual_equals_monthly",
                "rule_description": "Annual rent should equal monthly rent * 12",
                "document_type": "rent_roll",
                "rule_type": "calculation_check",
                "rule_formula": "annual_rent = monthly_rent * 12",
                "error_message": "Annual rent doesn't equal monthly rent * 12",
                "severity": "info",
                "is_active": True
            },
            
            # ==================== CROSS-STATEMENT RULES ====================
            {
                "rule_name": "cross_net_income_consistency",
                "rule_description": "Net Income should be consistent across Income Statement and Cash Flow",
                "document_type": "cross_statement",
                "rule_type": "cross_statement_check",
                "rule_formula": "net_income_is = net_income_cf",
                "error_message": "Net Income differs between Income Statement and Cash Flow",
                "severity": "warning",
                "is_active": True
            },
            {
                "rule_name": "cross_cash_consistency",
                "rule_description": "Cash balance should match across Balance Sheet and Cash Flow",
                "document_type": "cross_statement",
                "rule_type": "cross_statement_check",
                "rule_formula": "cash_bs = ending_cash_cf",
                "error_message": "Cash balance differs between Balance Sheet and Cash Flow",
                "severity": "warning",
                "is_active": True
            },
        ]
        
        # Insert rules
        inserted_count = 0
        for rule_data in rules:
            # Check if rule already exists
            existing = db.query(ValidationRule).filter(
                ValidationRule.rule_name == rule_data["rule_name"]
            ).first()
            
            if not existing:
                rule = ValidationRule(**rule_data)
                db.add(rule)
                inserted_count += 1
        
        db.commit()
        
        print(f"✓ Validation rules seeded successfully")
        print(f"  Total rules in spec: {len(rules)}")
        print(f"  New rules inserted: {inserted_count}")
        print(f"  Total rules in DB: {db.query(ValidationRule).count()}")
        
        # Print summary by document type
        for doc_type in ["balance_sheet", "income_statement", "cash_flow", "rent_roll", "cross_statement"]:
            count = db.query(ValidationRule).filter(
                ValidationRule.document_type == doc_type
            ).count()
            print(f"  {doc_type}: {count} rules")
        
        return True
    
    except Exception as e:
        db.rollback()
        print(f"✗ Error seeding validation rules: {e}")
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding validation rules...")
    success = seed_validation_rules()
    exit(0 if success else 1)

