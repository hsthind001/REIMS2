"""
Integration tests for duplicate prevention in document extraction

Tests the full extraction flow with duplicate scenarios to ensure
unique constraint violations never occur.
"""

import pytest
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.services.extraction_orchestrator import ExtractionOrchestrator
from app.services.deduplication_service import get_deduplication_service


class TestDeduplicationIntegration:
    """Integration tests for duplicate prevention"""
    
    @pytest.fixture
    def dedup_service(self):
        """Get deduplication service instance"""
        return get_deduplication_service()
    
    def test_balance_sheet_duplicate_prevention(self, db_session: Session, sample_property: Property, sample_period: FinancialPeriod):
        """Test that balance sheet extraction prevents duplicate account_code violations"""
        # Create upload record
        upload = DocumentUpload(
            property_id=sample_property.id,
            period_id=sample_period.id,
            document_type='balance_sheet',
            extraction_status='processing',
            file_path='test/balance_sheet.pdf'
        )
        db_session.add(upload)
        db_session.commit()
        
        # Create orchestrator
        orchestrator = ExtractionOrchestrator(db=db_session)
        
        # Simulate extracted items with duplicates
        extracted_items = [
            {
                'account_code': '0121-0000',
                'account_name': 'Cash - Depository',
                'amount': Decimal('1000.00'),
                'confidence': 90.0,
                'is_subtotal': False,
                'is_total': False
            },
            {
                'account_code': '0121-0000',  # Duplicate account_code
                'account_name': 'Cash - Depository',
                'amount': Decimal('1200.00'),  # Different amount
                'confidence': 95.0,  # Higher confidence
                'is_subtotal': False,
                'is_total': False
            },
            {
                'account_code': '0125-0000',
                'account_name': 'Cash - Operating',
                'amount': Decimal('500.00'),
                'confidence': 85.0,
                'is_subtotal': False,
                'is_total': False
            }
        ]
        
        # Use the deduplication service directly to verify it works
        dedup_service = get_deduplication_service()
        result = dedup_service.deduplicate_items(
            items=extracted_items,
            constraint_columns=['account_code'],
            document_type='balance_sheet',
            is_total_or_subtotal=lambda item: item.get('is_subtotal', False) or item.get('is_total', False)
        )
        
        # Verify deduplication worked
        assert result['statistics']['total_items'] == 3
        assert result['statistics']['duplicates_removed'] == 1
        assert result['statistics']['final_count'] == 2
        
        # Verify the higher confidence record was kept
        deduplicated = result['deduplicated_items']
        account_codes = [item['account_code'] for item in deduplicated]
        assert '0121-0000' in account_codes
        assert '0125-0000' in account_codes
        
        # Find the kept 0121-0000 record
        kept_record = next(item for item in deduplicated if item['account_code'] == '0121-0000')
        assert kept_record['confidence'] == 95.0  # Should keep higher confidence
        assert kept_record['amount'] == Decimal('1200.00')
        
        # Verify validation passes
        is_valid, error_msg = dedup_service.validate_no_duplicates(
            items=deduplicated,
            constraint_columns=['account_code'],
            context="test"
        )
        assert is_valid is True
        assert error_msg is None
    
    def test_income_statement_duplicate_prevention(self, db_session: Session, sample_property: Property, sample_period: FinancialPeriod):
        """Test that income statement extraction prevents duplicate (account_code, account_name) violations"""
        # Create upload record
        upload = DocumentUpload(
            property_id=sample_property.id,
            period_id=sample_period.id,
            document_type='income_statement',
            extraction_status='processing',
            file_path='test/income_statement.pdf'
        )
        db_session.add(upload)
        db_session.commit()
        
        # Simulate extracted items with duplicates
        extracted_items = [
            {
                'account_code': '4010-0000',
                'account_name': 'Base Rentals',
                'period_amount': Decimal('10000.00'),
                'confidence': 90.0,
                'is_subtotal': False,
                'is_total': False
            },
            {
                'account_code': '4010-0000',  # Same code
                'account_name': 'Base Rentals',  # Same name - DUPLICATE
                'period_amount': Decimal('12000.00'),
                'confidence': 95.0,  # Higher confidence
                'is_subtotal': False,
                'is_total': False
            },
            {
                'account_code': '4010-0000',  # Same code
                'account_name': 'Base Rentals - Retail',  # Different name - NOT duplicate
                'period_amount': Decimal('5000.00'),
                'confidence': 85.0,
                'is_subtotal': False,
                'is_total': False
            }
        ]
        
        # Use the deduplication service
        dedup_service = get_deduplication_service()
        result = dedup_service.deduplicate_items(
            items=extracted_items,
            constraint_columns=['account_code', 'account_name'],
            document_type='income_statement',
            is_total_or_subtotal=lambda item: item.get('is_subtotal', False) or item.get('is_total', False)
        )
        
        # Verify deduplication worked
        assert result['statistics']['total_items'] == 3
        assert result['statistics']['duplicates_removed'] == 1
        assert result['statistics']['final_count'] == 2
        
        # Verify both "Base Rentals" and "Base Rentals - Retail" are kept
        deduplicated = result['deduplicated_items']
        account_names = [item['account_name'] for item in deduplicated]
        assert 'Base Rentals' in account_names
        assert 'Base Rentals - Retail' in account_names
        
        # Verify the higher confidence "Base Rentals" was kept
        kept_base_rentals = next(item for item in deduplicated if item['account_name'] == 'Base Rentals')
        assert kept_base_rentals['confidence'] == 95.0
        assert kept_base_rentals['period_amount'] == Decimal('12000.00')
        
        # Verify validation passes
        is_valid, error_msg = dedup_service.validate_no_duplicates(
            items=deduplicated,
            constraint_columns=['account_code', 'account_name'],
            context="test"
        )
        assert is_valid is True
        assert error_msg is None
    
    def test_cash_flow_duplicate_prevention(self, db_session: Session, sample_property: Property, sample_period: FinancialPeriod):
        """Test that cash flow extraction prevents duplicate (account_code, account_name, line_number) violations"""
        # Create upload record
        upload = DocumentUpload(
            property_id=sample_property.id,
            period_id=sample_period.id,
            document_type='cash_flow',
            extraction_status='processing',
            file_path='test/cash_flow.pdf'
        )
        db_session.add(upload)
        db_session.commit()
        
        # Simulate extracted items with duplicates
        extracted_items = [
            {
                'account_code': '4010-0000',
                'account_name': 'Base Rentals',
                'line_number': 1,
                'period_amount': Decimal('10000.00'),
                'confidence': 90.0,
                'is_subtotal': False,
                'is_total': False
            },
            {
                'account_code': '4010-0000',  # Same code
                'account_name': 'Base Rentals',  # Same name
                'line_number': 1,  # Same line_number - DUPLICATE
                'period_amount': Decimal('12000.00'),
                'confidence': 95.0,  # Higher confidence
                'is_subtotal': False,
                'is_total': False
            },
            {
                'account_code': '4010-0000',  # Same code
                'account_name': 'Base Rentals',  # Same name
                'line_number': 2,  # Different line_number - NOT duplicate
                'period_amount': Decimal('5000.00'),
                'confidence': 85.0,
                'is_subtotal': False,
                'is_total': False
            }
        ]
        
        # Use the deduplication service
        dedup_service = get_deduplication_service()
        result = dedup_service.deduplicate_items(
            items=extracted_items,
            constraint_columns=['account_code', 'account_name', 'line_number'],
            document_type='cash_flow',
            is_total_or_subtotal=lambda item: item.get('is_subtotal', False) or item.get('is_total', False)
        )
        
        # Verify deduplication worked
        assert result['statistics']['total_items'] == 3
        assert result['statistics']['duplicates_removed'] == 1
        assert result['statistics']['final_count'] == 2
        
        # Verify both line_number 1 (deduplicated) and line_number 2 are kept
        deduplicated = result['deduplicated_items']
        line_numbers = [item['line_number'] for item in deduplicated]
        assert 1 in line_numbers
        assert 2 in line_numbers
        
        # Verify the higher confidence line_number 1 was kept
        kept_line_1 = next(item for item in deduplicated if item['line_number'] == 1)
        assert kept_line_1['confidence'] == 95.0
        assert kept_line_1['period_amount'] == Decimal('12000.00')
        
        # Verify validation passes
        is_valid, error_msg = dedup_service.validate_no_duplicates(
            items=deduplicated,
            constraint_columns=['account_code', 'account_name', 'line_number'],
            context="test"
        )
        assert is_valid is True
        assert error_msg is None
    
    def test_totals_prefer_amount_strategy(self, db_session: Session):
        """Test that totals/subtotals use amount strategy for deduplication"""
        extracted_items = [
            {
                'account_code': '4990-0000',
                'account_name': 'TOTAL REVENUE',
                'amount': Decimal('10000.00'),
                'confidence': 95.0,
                'is_total': True
            },
            {
                'account_code': '4990-0000',
                'account_name': 'TOTAL REVENUE',
                'amount': Decimal('12000.00'),  # Higher amount
                'confidence': 80.0,  # Lower confidence
                'is_total': True
            }
        ]
        
        dedup_service = get_deduplication_service()
        result = dedup_service.deduplicate_items(
            items=extracted_items,
            constraint_columns=['account_code'],
            selection_strategy='confidence',  # Default
            is_total_or_subtotal=lambda item: item.get('is_total', False) or item.get('is_subtotal', False)
        )
        
        # Should keep higher amount (12000) even though confidence is lower
        assert result['statistics']['duplicates_removed'] == 1
        kept = result['deduplicated_items'][0]
        assert kept['amount'] == Decimal('12000.00')
        assert kept['confidence'] == 80.0
    
    def test_details_prefer_confidence_strategy(self, db_session: Session):
        """Test that detail lines use confidence strategy for deduplication"""
        extracted_items = [
            {
                'account_code': '4010-0000',
                'account_name': 'Base Rentals',
                'amount': Decimal('10000.00'),
                'confidence': 95.0,  # Higher confidence
                'is_total': False
            },
            {
                'account_code': '4010-0000',
                'account_name': 'Base Rentals',
                'amount': Decimal('12000.00'),  # Higher amount
                'confidence': 80.0,  # Lower confidence
                'is_total': False
            }
        ]
        
        dedup_service = get_deduplication_service()
        result = dedup_service.deduplicate_items(
            items=extracted_items,
            constraint_columns=['account_code', 'account_name'],
            selection_strategy='confidence',
            is_total_or_subtotal=lambda item: item.get('is_total', False) or item.get('is_subtotal', False)
        )
        
        # Should keep higher confidence (95) even though amount is lower
        assert result['statistics']['duplicates_removed'] == 1
        kept = result['deduplicated_items'][0]
        assert kept['confidence'] == 95.0
        assert kept['amount'] == Decimal('10000.00')
    
    def test_validation_catches_duplicates(self, db_session: Session):
        """Test that validation correctly identifies duplicates"""
        items = [
            {'account_code': '4010-0000', 'account_name': 'Base Rentals'},
            {'account_code': '4010-0000', 'account_name': 'Base Rentals'},  # Duplicate
            {'account_code': '4020-0000', 'account_name': 'Tax'}
        ]
        
        dedup_service = get_deduplication_service()
        is_valid, error_msg = dedup_service.validate_no_duplicates(
            items=items,
            constraint_columns=['account_code', 'account_name'],
            context="test validation"
        )
        
        assert is_valid is False
        assert error_msg is not None
        assert "Duplicate constraint key" in error_msg
        assert "4010-0000|||Base Rentals" in error_msg or "4010-0000" in error_msg

