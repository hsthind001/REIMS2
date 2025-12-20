"""
Seed Budget Data

Creates sample budget data for testing variance analysis
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import SessionLocal
from app.models.budget import Budget, BudgetStatus
from datetime import datetime

def seed_budget_data():
    """Create sample budget data for Eastern Shore Plaza (property_id=1)"""
    db = SessionLocal()

    try:
        # Check if budgets already exist
        existing = db.query(Budget).filter(
            Budget.property_id == 1,
            Budget.financial_period_id == 3  # December 2025
        ).first()

        if existing:
            print("✅ Budget data already exists")
            return

        # Sample budget accounts for a property
        budget_accounts = [
            # Revenue accounts
            {"account_code": "40000", "account_name": "Rental Income", "category": "Revenue", "amount": 100000},
            {"account_code": "41000", "account_name": "Parking Income", "category": "Revenue", "amount": 5000},
            {"account_code": "42000", "account_name": "Other Income", "category": "Revenue", "amount": 2000},

            # Operating Expenses
            {"account_code": "50000", "account_name": "Property Management Fees", "category": "Operating Expenses", "amount": 5000},
            {"account_code": "51000", "account_name": "Repairs & Maintenance", "category": "Operating Expenses", "amount": 8000},
            {"account_code": "52000", "account_name": "Utilities", "category": "Operating Expenses", "amount": 12000},
            {"account_code": "53000", "account_name": "Insurance", "category": "Operating Expenses", "amount": 3000},
            {"account_code": "54000", "account_name": "Property Taxes", "category": "Operating Expenses", "amount": 15000},
            {"account_code": "55000", "account_name": "Legal & Professional", "category": "Operating Expenses", "amount": 2500},
            {"account_code": "56000", "account_name": "Marketing & Advertising", "category": "Operating Expenses", "amount": 1500},
        ]

        budgets_created = 0

        for account in budget_accounts:
            budget = Budget(
                property_id=1,
                financial_period_id=3,  # December 2025
                budget_name="2025 Annual Budget",
                budget_year=2025,
                budget_period_type="monthly",
                status=BudgetStatus.ACTIVE,
                account_code=account["account_code"],
                account_name=account["account_name"],
                account_category=account["category"],
                budgeted_amount=account["amount"],
                tolerance_percentage=10.0,  # 10% tolerance
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(budget)
            budgets_created += 1

        db.commit()
        print(f"✅ Created {budgets_created} budget records for Eastern Shore Plaza")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding budget data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_budget_data()
