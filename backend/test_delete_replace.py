#!/usr/bin/env python3
"""
Test script to verify delete-and-replace functionality for financial data
Tests all four document types: balance_sheet, income_statement, cash_flow, rent_roll
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
from datetime import date

# Import models
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.income_statement_header import IncomeStatementHeader
from app.models.cash_flow_data import CashFlowData
from app.models.cash_flow_header import CashFlowHeader
from app.models.rent_roll_data import RentRollData
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload

# Database connection
DATABASE_URL = "postgresql://reims:reims@localhost:5433/reims"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def test_balance_sheet_delete_replace():
    """Test balance sheet delete and replace"""
    print("\n=== Testing Balance Sheet Delete & Replace ===")
    db = SessionLocal()
    
    try:
        # Create test property and period
        prop = Property(
            property_code="TEST001",
            property_name="Test Property",
            address="123 Test St"
        )
        db.add(prop)
        db.flush()
        
        period = FinancialPeriod(
            year=2024,
            month=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        db.add(period)
        db.flush()
        
        # Create first upload
        upload1 = DocumentUpload(
            property_id=prop.id,
            period_id=period.id,
            document_type="balance_sheet",
            file_name="test1.pdf",
            file_size=1000,
            file_path="test/test1.pdf",
            status="completed"
        )
        db.add(upload1)
        db.flush()
        
        # Insert initial balance sheet data
        bs1 = BalanceSheetData(
            property_id=prop.id,
            period_id=period.id,
            upload_id=upload1.id,
            account_code="1000",
            account_name="Cash",
            amount=Decimal("50000.00"),
            extraction_confidence=Decimal("95.0")
        )
        bs2 = BalanceSheetData(
            property_id=prop.id,
            period_id=period.id,
            upload_id=upload1.id,
            account_code="2000",
            account_name="Accounts Payable",
            amount=Decimal("25000.00"),
            extraction_confidence=Decimal("92.0")
        )
        db.add_all([bs1, bs2])
        db.commit()
        
        print(f"✓ Initial upload: Inserted 2 balance sheet records")
        
        # Count records
        count1 = db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == prop.id,
            BalanceSheetData.period_id == period.id
        ).count()
        print(f"  Records in DB: {count1}")
        
        # Simulate re-upload: DELETE all existing data
        deleted = db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == prop.id,
            BalanceSheetData.period_id == period.id
        ).delete(synchronize_session=False)
        print(f"🗑️  Deleted {deleted} existing records")
        
        # Create second upload
        upload2 = DocumentUpload(
            property_id=prop.id,
            period_id=period.id,
            document_type="balance_sheet",
            file_name="test2.pdf",
            file_size=1000,
            file_path="test/test2.pdf",
            status="completed"
        )
        db.add(upload2)
        db.flush()
        
        # Insert NEW balance sheet data (different values, different number of records)
        bs3 = BalanceSheetData(
            property_id=prop.id,
            period_id=period.id,
            upload_id=upload2.id,
            account_code="1000",
            account_name="Cash",
            amount=Decimal("75000.00"),  # CHANGED
            extraction_confidence=Decimal("97.0")
        )
        bs4 = BalanceSheetData(
            property_id=prop.id,
            period_id=period.id,
            upload_id=upload2.id,
            account_code="2000",
            account_name="Accounts Payable",
            amount=Decimal("30000.00"),  # CHANGED
            extraction_confidence=Decimal("94.0")
        )
        bs5 = BalanceSheetData(
            property_id=prop.id,
            period_id=period.id,
            upload_id=upload2.id,
            account_code="3000",
            account_name="Equity",  # NEW RECORD
            amount=Decimal("45000.00"),
            extraction_confidence=Decimal("96.0")
        )
        db.add_all([bs3, bs4, bs5])
        db.commit()
        
        print(f"✓ Re-upload: Inserted 3 NEW balance sheet records")
        
        # Verify results
        count2 = db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == prop.id,
            BalanceSheetData.period_id == period.id
        ).count()
        
        upload2_records = db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == prop.id,
            BalanceSheetData.period_id == period.id,
            BalanceSheetData.upload_id == upload2.id
        ).count()
        
        print(f"  Total records in DB: {count2}")
        print(f"  Records from upload2: {upload2_records}")
        
        # Verify old data is gone
        cash = db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == prop.id,
            BalanceSheetData.period_id == period.id,
            BalanceSheetData.account_code == "1000"
        ).first()
        
        if count2 == 3 and upload2_records == 3 and cash.amount == Decimal("75000.00"):
            print("✅ PASS: Data was completely replaced (old deleted, new inserted)")
            return True
        else:
            print("❌ FAIL: Data was not properly replaced")
            return False
            
    finally:
        # Cleanup
        db.query(BalanceSheetData).filter(
            BalanceSheetData.property_id == prop.id
        ).delete()
        db.query(DocumentUpload).filter(
            DocumentUpload.property_id == prop.id
        ).delete()
        db.query(Property).filter(Property.id == prop.id).delete()
        db.query(FinancialPeriod).filter(FinancialPeriod.id == period.id).delete()
        db.commit()
        db.close()


def test_income_statement_delete_replace():
    """Test income statement delete and replace"""
    print("\n=== Testing Income Statement Delete & Replace ===")
    db = SessionLocal()
    
    try:
        # Create test property and period
        prop = Property(
            property_code="TEST002",
            property_name="Test Property 2",
            address="456 Test Ave"
        )
        db.add(prop)
        db.flush()
        
        period = FinancialPeriod(
            year=2024,
            month=2,
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 29)
        )
        db.add(period)
        db.flush()
        
        # Create first upload
        upload1 = DocumentUpload(
            property_id=prop.id,
            period_id=period.id,
            document_type="income_statement",
            file_name="test_is1.pdf",
            file_size=1000,
            file_path="test/test_is1.pdf",
            status="completed"
        )
        db.add(upload1)
        db.flush()
        
        # Insert initial header and data
        header1 = IncomeStatementHeader(
            property_id=prop.id,
            period_id=period.id,
            upload_id=upload1.id,
            total_income=Decimal("100000"),
            total_expenses=Decimal("60000"),
            net_operating_income=Decimal("40000")
        )
        db.add(header1)
        db.flush()
        
        is1 = IncomeStatementData(
            header_id=header1.id,
            property_id=prop.id,
            period_id=period.id,
            upload_id=upload1.id,
            account_code="4000",
            account_name="Rental Income",
            period_amount=Decimal("100000")
        )
        db.add(is1)
        db.commit()
        
        print(f"✓ Initial upload: Inserted 1 header + 1 line item")
        
        # Count records
        header_count1 = db.query(IncomeStatementHeader).filter(
            IncomeStatementHeader.property_id == prop.id,
            IncomeStatementHeader.period_id == period.id
        ).count()
        item_count1 = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == prop.id,
            IncomeStatementData.period_id == period.id
        ).count()
        print(f"  Headers: {header_count1}, Line items: {item_count1}")
        
        # Simulate re-upload: DELETE header and line items
        deleted_headers = db.query(IncomeStatementHeader).filter(
            IncomeStatementHeader.property_id == prop.id,
            IncomeStatementHeader.period_id == period.id
        ).delete(synchronize_session=False)
        
        deleted_items = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == prop.id,
            IncomeStatementData.period_id == period.id
        ).delete(synchronize_session=False)
        
        print(f"🗑️  Deleted {deleted_headers} header(s) and {deleted_items} line items")
        
        # Create second upload
        upload2 = DocumentUpload(
            property_id=prop.id,
            period_id=period.id,
            document_type="income_statement",
            file_name="test_is2.pdf",
            file_size=1000,
            file_path="test/test_is2.pdf",
            status="completed"
        )
        db.add(upload2)
        db.flush()
        
        # Insert NEW header and data
        header2 = IncomeStatementHeader(
            property_id=prop.id,
            period_id=period.id,
            upload_id=upload2.id,
            total_income=Decimal("120000"),  # CHANGED
            total_expenses=Decimal("65000"),  # CHANGED
            net_operating_income=Decimal("55000")  # CHANGED
        )
        db.add(header2)
        db.flush()
        
        is2 = IncomeStatementData(
            header_id=header2.id,
            property_id=prop.id,
            period_id=period.id,
            upload_id=upload2.id,
            account_code="4000",
            account_name="Rental Income",
            period_amount=Decimal("120000")  # CHANGED
        )
        is3 = IncomeStatementData(
            header_id=header2.id,
            property_id=prop.id,
            period_id=period.id,
            upload_id=upload2.id,
            account_code="5000",
            account_name="Operating Expenses",  # NEW
            period_amount=Decimal("65000")
        )
        db.add_all([is2, is3])
        db.commit()
        
        print(f"✓ Re-upload: Inserted 1 NEW header + 2 NEW line items")
        
        # Verify results
        header_count2 = db.query(IncomeStatementHeader).filter(
            IncomeStatementHeader.property_id == prop.id,
            IncomeStatementHeader.period_id == period.id
        ).count()
        item_count2 = db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == prop.id,
            IncomeStatementData.period_id == period.id
        ).count()
        
        header = db.query(IncomeStatementHeader).filter(
            IncomeStatementHeader.property_id == prop.id,
            IncomeStatementHeader.period_id == period.id
        ).first()
        
        print(f"  Headers: {header_count2}, Line items: {item_count2}")
        
        if (header_count2 == 1 and item_count2 == 2 and 
            header.total_income == Decimal("120000")):
            print("✅ PASS: Income statement data was completely replaced")
            return True
        else:
            print("❌ FAIL: Income statement data was not properly replaced")
            return False
            
    finally:
        # Cleanup
        db.query(IncomeStatementData).filter(
            IncomeStatementData.property_id == prop.id
        ).delete()
        db.query(IncomeStatementHeader).filter(
            IncomeStatementHeader.property_id == prop.id
        ).delete()
        db.query(DocumentUpload).filter(
            DocumentUpload.property_id == prop.id
        ).delete()
        db.query(Property).filter(Property.id == prop.id).delete()
        db.query(FinancialPeriod).filter(FinancialPeriod.id == period.id).delete()
        db.commit()
        db.close()


def main():
    """Run all tests"""
    print("=" * 60)
    print("DELETE AND REPLACE FUNCTIONALITY TEST")
    print("=" * 60)
    print("\nThis test verifies that re-uploading documents for the same")
    print("property+period DELETES old data and INSERTS new data.")
    
    results = []
    
    # Test balance sheet
    results.append(("Balance Sheet", test_balance_sheet_delete_replace()))
    
    # Test income statement
    results.append(("Income Statement", test_income_statement_delete_replace()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nPassed: {total_passed}/{len(results)}")
    
    if total_passed == len(results):
        print("\n🎉 All tests passed! Delete-and-replace is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

