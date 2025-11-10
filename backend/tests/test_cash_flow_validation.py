"""
Cash Flow Validation Tests - Template v1.0 Compliance

Tests for all cash flow validation rules including:
- Income validation
- Expense validation
- NOI validation
- Net Income validation
- Cash Flow validation
- Cash account validation
"""
import pytest
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.orm import Session

from app.services.validation_service import ValidationService
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload
from app.models.cash_flow_header import CashFlowHeader
from app.models.cash_flow_data import CashFlowData
from app.models.cash_flow_adjustments import CashFlowAdjustment
from app.models.cash_account_reconciliation import CashAccountReconciliation


@pytest.fixture
def setup_test_cash_flow(db_session: Session):
    """Create test cash flow data"""
    # Create property
    property = Property(
        property_code="TEST001",
        property_name="Test Property",
        status="active"
    )
    db_session.add(property)
    db_session.flush()
    
    # Create period
    period = FinancialPeriod(
        property_id=property.id,
        period_year=2024,
        period_month=12,
        period_start_date=date(2024, 12, 1),
        period_end_date=date(2024, 12, 31)
    )
    db_session.add(period)
    db_session.flush()
    
    # Create upload
    upload = DocumentUpload(
        property_id=property.id,
        period_id=period.id,
        document_type="cash_flow",
        file_name="test_cf.pdf",
        extraction_status="completed"
    )
    db_session.add(upload)
    db_session.flush()
    
    # Create header with proper calculations
    header = CashFlowHeader(
        property_id=property.id,
        period_id=period.id,
        upload_id=upload.id,
        property_name="Test Property",
        property_code="TEST001",
        report_period_start=date(2024, 12, 1),
        report_period_end=date(2024, 12, 31),
        accounting_basis="Accrual",
        # Income
        total_income=Decimal('1000000.00'),
        base_rentals=Decimal('750000.00'),  # 75% of total
        # Expenses
        total_operating_expenses=Decimal('300000.00'),
        total_additional_operating_expenses=Decimal('100000.00'),
        total_expenses=Decimal('400000.00'),
        # NOI
        net_operating_income=Decimal('600000.00'),  # 60% of income
        noi_percentage=Decimal('60.00'),
        # Other
        mortgage_interest=Decimal('200000.00'),
        depreciation=Decimal('150000.00'),
        amortization=Decimal('10000.00'),
        total_other_income_expense=Decimal('360000.00'),
        # Net Income
        net_income=Decimal('240000.00'),  # NOI - Other
        net_income_percentage=Decimal('24.00'),
        # Adjustments and Cash Flow
        total_adjustments=Decimal('50000.00'),
        cash_flow=Decimal('290000.00'),  # Net Income + Adjustments
        cash_flow_percentage=Decimal('29.00'),
        # Cash balances
        beginning_cash_balance=Decimal('100000.00'),
        ending_cash_balance=Decimal('390000.00'),
        extraction_confidence=Decimal('95.00')
    )
    db_session.add(header)
    db_session.flush()
    
    # Create line items
    line_items = [
        # Income
        CashFlowData(
            header_id=header.id,
            property_id=property.id,
            period_id=period.id,
            account_code="4010-0000",
            account_name="Base Rentals",
            period_amount=Decimal('750000.00'),
            line_section="INCOME",
            line_category="Base Rental Income",
            line_subcategory="Base Rentals",
            line_number=1,
            extraction_confidence=Decimal('96.00')
        ),
        CashFlowData(
            header_id=header.id,
            property_id=property.id,
            period_id=period.id,
            account_code="4020-0000",
            account_name="Tax Recovery",
            period_amount=Decimal('150000.00'),
            line_section="INCOME",
            line_category="Recovery Income",
            line_subcategory="Tax Recovery",
            line_number=2,
            extraction_confidence=Decimal('96.00')
        ),
        CashFlowData(
            header_id=header.id,
            property_id=property.id,
            account_code="4030-0000",
            account_name="CAM Recovery",
            period_amount=Decimal('100000.00'),
            line_section="INCOME",
            line_category="Recovery Income",
            line_subcategory="CAM Recovery",
            line_number=3,
            extraction_confidence=Decimal('96.00')
        ),
        # Operating Expenses
        CashFlowData(
            header_id=header.id,
            property_id=property.id,
            period_id=period.id,
            account_code="5010-0000",
            account_name="Property Tax",
            period_amount=Decimal('150000.00'),
            line_section="OPERATING_EXPENSE",
            line_category="Property Expenses",
            line_subcategory="Property Tax",
            line_number=10,
            extraction_confidence=Decimal('96.00')
        ),
        CashFlowData(
            header_id=header.id,
            property_id=property.id,
            period_id=period.id,
            account_code="5110-0000",
            account_name="Electricity",
            period_amount=Decimal('50000.00'),
            line_section="OPERATING_EXPENSE",
            line_category="Utility Expenses",
            line_subcategory="Electricity Service",
            line_number=11,
            is_subtotal=False,
            extraction_confidence=Decimal('96.00')
        ),
    ]
    
    for item in line_items:
        db_session.add(item)
    
    # Create adjustments
    adjustments = [
        CashFlowAdjustment(
            header_id=header.id,
            property_id=property.id,
            period_id=period.id,
            adjustment_category="ACCUMULATED_DEPRECIATION",
            adjustment_name="Accum. Depr. - Buildings",
            amount=Decimal('150000.00'),
            is_increase=True,
            line_number=1,
            extraction_confidence=Decimal('92.00')
        ),
        CashFlowAdjustment(
            header_id=header.id,
            property_id=property.id,
            period_id=period.id,
            adjustment_category="DISTRIBUTIONS",
            adjustment_name="Distribution",
            amount=Decimal('-100000.00'),
            is_increase=False,
            line_number=2,
            extraction_confidence=Decimal('92.00')
        ),
    ]
    
    for adj in adjustments:
        db_session.add(adj)
    
    # Create cash accounts
    cash_accounts = [
        CashAccountReconciliation(
            header_id=header.id,
            property_id=property.id,
            period_id=period.id,
            account_name="Cash - Operating",
            account_type="operating",
            beginning_balance=Decimal('100000.00'),
            ending_balance=Decimal('390000.00'),
            difference=Decimal('290000.00'),
            is_escrow_account=False,
            is_total_row=True,
            line_number=1,
            extraction_confidence=Decimal('95.00')
        )
    ]
    
    for acct in cash_accounts:
        db_session.add(acct)
    
    db_session.commit()
    
    return {
        "property": property,
        "period": period,
        "upload": upload,
        "header": header
    }


class TestIncomeValidation:
    """Test income validation rules"""
    
    def test_total_income_sum_validation(self, db_session, setup_test_cash_flow):
        """Test total income equals sum of income items"""
        data = setup_test_cash_flow
        validator = ValidationService(db_session)
        
        result = validator.validate_cf_total_income(
            data["upload"].id,
            data["property"].id,
            data["period"].id
        )
        
        assert result["passed"] == True
    
    def test_base_rental_percentage_validation(self, db, setup_test_cash_flow):
        """Test base rentals are 70-85% of total income"""
        data = setup_test_cash_flow
        validator = ValidationService(db_session)
        
        result = validator.validate_cf_base_rental_percentage(
            data["upload"].id,
            data["property"].id,
            data["period"].id
        )
        
        # Base rentals are 75%, which is in range
        assert result["passed"] == True


class TestExpenseValidation:
    """Test expense validation rules"""
    
    def test_total_expenses_sum_validation(self, db, setup_test_cash_flow):
        """Test total expenses equals operating + additional"""
        data = setup_test_cash_flow
        validator = ValidationService(db_session)
        
        result = validator.validate_cf_total_expenses(
            data["upload"].id,
            data["property"].id,
            data["period"].id
        )
        
        assert result["passed"] == True


class TestNOIValidation:
    """Test NOI validation rules"""
    
    def test_noi_calculation_validation(self, db, setup_test_cash_flow):
        """Test NOI = Total Income - Total Expenses"""
        data = setup_test_cash_flow
        validator = ValidationService(db_session)
        
        result = validator.validate_cf_noi_calculation(
            data["upload"].id,
            data["property"].id,
            data["period"].id
        )
        
        assert result["passed"] == True
    
    def test_noi_percentage_validation(self, db, setup_test_cash_flow):
        """Test NOI is 60-80% of Total Income"""
        data = setup_test_cash_flow
        validator = ValidationService(db_session)
        
        result = validator.validate_cf_noi_percentage(
            data["upload"].id,
            data["property"].id,
            data["period"].id
        )
        
        # NOI is 60%, which is in range
        assert result["passed"] == True
    
    def test_noi_positive_validation(self, db, setup_test_cash_flow):
        """Test NOI is positive"""
        data = setup_test_cash_flow
        validator = ValidationService(db_session)
        
        result = validator.validate_cf_noi_positive(
            data["upload"].id,
            data["property"].id,
            data["period"].id
        )
        
        assert result["passed"] == True


class TestNetIncomeValidation:
    """Test net income validation rules"""
    
    def test_net_income_calculation_validation(self, db, setup_test_cash_flow):
        """Test Net Income = NOI - (Mortgage + Depreciation + Amortization)"""
        data = setup_test_cash_flow
        validator = ValidationService(db_session)
        
        result = validator.validate_cf_net_income_calculation(
            data["upload"].id,
            data["property"].id,
            data["period"].id
        )
        
        assert result["passed"] == True


class TestCashFlowValidation:
    """Test cash flow validation rules"""
    
    def test_cash_flow_calculation_validation(self, db, setup_test_cash_flow):
        """Test Cash Flow = Net Income + Total Adjustments"""
        data = setup_test_cash_flow
        validator = ValidationService(db_session)
        
        result = validator.validate_cf_cash_flow_calculation(
            data["upload"].id,
            data["property"].id,
            data["period"].id
        )
        
        assert result["passed"] == True
    
    def test_cash_account_differences_validation(self, db, setup_test_cash_flow):
        """Test cash account differences = ending - beginning"""
        data = setup_test_cash_flow
        validator = ValidationService(db_session)
        
        result = validator.validate_cf_cash_account_differences(
            data["upload"].id,
            data["property"].id,
            data["period"].id
        )
        
        assert result["passed"] == True
    
    def test_total_cash_balance_validation(self, db, setup_test_cash_flow):
        """Test total cash equals sum of all cash accounts"""
        data = setup_test_cash_flow
        validator = ValidationService(db_session)
        
        result = validator.validate_cf_total_cash_balance(
            data["upload"].id,
            data["property"].id,
            data["period"].id
        )
        
        assert result["passed"] == True


class TestEdgeCases:
    """Test edge cases and special scenarios"""
    
    def test_negative_noi_warning(self, db_session):
        """Test that negative NOI triggers warning"""
        # Create minimal test data with negative NOI
        property = Property(property_code="NEG001", property_name="Negative NOI Property", status="active")
        db.add(property)
        db.flush()
        
        period = FinancialPeriod(
            property_id=property.id,
            period_year=2024,
            period_month=12,
            period_start_date=date(2024, 12, 1),
            period_end_date=date(2024, 12, 31)
        )
        db.add(period)
        db.flush()
        
        upload = DocumentUpload(
            property_id=property.id,
            period_id=period.id,
            document_type="cash_flow",
            file_name="test.pdf",
            extraction_status="completed"
        )
        db.add(upload)
        db.flush()
        
        header = CashFlowHeader(
            property_id=property.id,
            period_id=period.id,
            upload_id=upload.id,
            property_name="Test Property",
            property_code="NEG001",
            report_period_start=date(2024, 12, 1),
            report_period_end=date(2024, 12, 31),
            accounting_basis="Accrual",
            total_income=Decimal('100000.00'),
            total_expenses=Decimal('150000.00'),
            net_operating_income=Decimal('-50000.00'),  # Negative NOI
            net_income=Decimal('-50000.00'),
            cash_flow=Decimal('-50000.00'),
            extraction_confidence=Decimal('95.00')
        )
        db_session.add(header)
        db_session.commit()
        
        validator = ValidationService(db_session)
        result = validator.validate_cf_noi_positive(upload.id, property.id, period.id)
        
        # Should fail but with warning severity
        assert result["passed"] == False
        assert result["severity"] == "warning"
    
    def test_zero_total_income_handling(self, db_session):
        """Test handling of zero total income"""
        # This should be caught by completeness checks
        # Percentage calculations should handle division by zero gracefully
        pass  # Placeholder for future implementation


class TestCrossPropertyValidation:
    """Test cross-property validation rules"""
    
    @pytest.mark.skip(reason="Requires multiple properties with inter-property transfers")
    def test_inter_property_balance_reconciliation(self):
        """Test A/R from Property A = A/P to Property A in Property A's statements"""
        # This is an advanced validation that requires multiple property data
        pass

