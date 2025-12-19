"""
Unit tests for DeduplicationService

Tests the intelligent deduplication logic that prevents unique constraint violations.
"""

import pytest
from app.services.deduplication_service import DeduplicationService


class TestDeduplicationService:
    """Test suite for DeduplicationService"""
    
    @pytest.fixture
    def dedup_service(self):
        """Create DeduplicationService instance"""
        return DeduplicationService()
    
    def test_deduplicate_single_column_no_duplicates(self, dedup_service):
        """Test deduplication with no duplicates"""
        items = [
            {'account_code': '4010-0000', 'account_name': 'Base Rentals', 'amount': 1000.0, 'confidence': 95.0},
            {'account_code': '4020-0000', 'account_name': 'Tax', 'amount': 500.0, 'confidence': 90.0},
            {'account_code': '4030-0000', 'account_name': 'Insurance', 'amount': 300.0, 'confidence': 85.0}
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code']
        )
        
        assert result['statistics']['total_items'] == 3
        assert result['statistics']['duplicates_removed'] == 0
        assert result['statistics']['final_count'] == 3
        assert len(result['deduplicated_items']) == 3
    
    def test_deduplicate_single_column_with_duplicates(self, dedup_service):
        """Test deduplication with duplicate account_codes"""
        items = [
            {'account_code': '4010-0000', 'account_name': 'Base Rentals', 'amount': 1000.0, 'confidence': 90.0},
            {'account_code': '4010-0000', 'account_name': 'Base Rentals', 'amount': 1200.0, 'confidence': 95.0},  # Duplicate, higher confidence
            {'account_code': '4020-0000', 'account_name': 'Tax', 'amount': 500.0, 'confidence': 85.0}
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code'],
            selection_strategy='confidence'
        )
        
        assert result['statistics']['total_items'] == 3
        assert result['statistics']['duplicates_removed'] == 1
        assert result['statistics']['final_count'] == 2
        assert len(result['deduplicated_items']) == 2
        # Should keep the one with higher confidence
        assert result['deduplicated_items'][0]['confidence'] == 95.0
    
    def test_deduplicate_multi_column_constraint(self, dedup_service):
        """Test deduplication with multiple constraint columns (account_code + account_name)"""
        items = [
            {'account_code': '4010-0000', 'account_name': 'Base Rentals', 'amount': 1000.0, 'confidence': 90.0},
            {'account_code': '4010-0000', 'account_name': 'Base Rentals - Retail', 'amount': 800.0, 'confidence': 85.0},  # Different name, should keep both
            {'account_code': '4010-0000', 'account_name': 'Base Rentals', 'amount': 1200.0, 'confidence': 95.0}  # Duplicate code+name, should deduplicate
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code', 'account_name'],
            selection_strategy='confidence'
        )
        
        assert result['statistics']['total_items'] == 3
        assert result['statistics']['duplicates_removed'] == 1
        assert result['statistics']['final_count'] == 2
        # Should have both "Base Rentals" and "Base Rentals - Retail"
        names = [item['account_name'] for item in result['deduplicated_items']]
        assert 'Base Rentals' in names
        assert 'Base Rentals - Retail' in names
    
    def test_selection_strategy_confidence(self, dedup_service):
        """Test confidence-based selection strategy"""
        items = [
            {'account_code': '4010-0000', 'amount': 1000.0, 'confidence': 80.0},
            {'account_code': '4010-0000', 'amount': 1200.0, 'confidence': 95.0}  # Higher confidence
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code'],
            selection_strategy='confidence'
        )
        
        assert result['statistics']['duplicates_removed'] == 1
        assert result['deduplicated_items'][0]['confidence'] == 95.0
        assert result['deduplicated_items'][0]['amount'] == 1200.0
    
    def test_selection_strategy_amount(self, dedup_service):
        """Test amount-based selection strategy"""
        items = [
            {'account_code': '4010-0000', 'amount': 1000.0, 'confidence': 95.0},
            {'account_code': '4010-0000', 'amount': 1200.0, 'confidence': 80.0}  # Higher amount
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code'],
            selection_strategy='amount'
        )
        
        assert result['statistics']['duplicates_removed'] == 1
        assert result['deduplicated_items'][0]['amount'] == 1200.0
        assert result['deduplicated_items'][0]['confidence'] == 80.0
    
    def test_totals_use_amount_strategy(self, dedup_service):
        """Test that totals/subtotals use amount strategy automatically"""
        items = [
            {'account_code': '4990-0000', 'amount': 1000.0, 'confidence': 80.0, 'is_total': True},
            {'account_code': '4990-0000', 'amount': 1200.0, 'confidence': 95.0, 'is_total': True}  # Higher amount
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code'],
            selection_strategy='confidence',  # Default, but should use 'amount' for totals
            is_total_or_subtotal=lambda item: item.get('is_total', False) or item.get('is_subtotal', False)
        )
        
        assert result['statistics']['duplicates_removed'] == 1
        # Should keep higher amount (1200) even though confidence is higher in first
        assert result['deduplicated_items'][0]['amount'] == 1200.0
    
    def test_details_use_confidence_strategy(self, dedup_service):
        """Test that detail lines use confidence strategy"""
        items = [
            {'account_code': '4010-0000', 'amount': 1000.0, 'confidence': 80.0, 'is_total': False},
            {'account_code': '4010-0000', 'amount': 1200.0, 'confidence': 95.0, 'is_total': False}  # Higher confidence
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code'],
            selection_strategy='confidence',
            is_total_or_subtotal=lambda item: item.get('is_total', False) or item.get('is_subtotal', False)
        )
        
        assert result['statistics']['duplicates_removed'] == 1
        # Should keep higher confidence (95) even though amount is higher in second
        assert result['deduplicated_items'][0]['confidence'] == 95.0
    
    def test_tie_breaker_higher_amount(self, dedup_service):
        """Test tie-breaker when confidence is equal"""
        items = [
            {'account_code': '4010-0000', 'amount': 1000.0, 'confidence': 90.0},
            {'account_code': '4010-0000', 'amount': 1200.0, 'confidence': 90.0}  # Same confidence, higher amount
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code'],
            selection_strategy='confidence'
        )
        
        assert result['statistics']['duplicates_removed'] == 1
        assert result['deduplicated_items'][0]['amount'] == 1200.0
    
    def test_missing_constraint_column(self, dedup_service):
        """Test handling of missing constraint columns"""
        items = [
            {'account_code': '4010-0000', 'account_name': 'Base Rentals', 'amount': 1000.0},
            {'account_code': None, 'account_name': 'Tax', 'amount': 500.0},  # Missing account_code
            {'account_code': '4030-0000', 'account_name': None, 'amount': 300.0}  # Missing account_name
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code', 'account_name']
        )
        
        # Items with missing constraint columns should be skipped
        assert result['statistics']['final_count'] == 1
        assert result['deduplicated_items'][0]['account_code'] == '4010-0000'
    
    def test_unmatched_account_code(self, dedup_service):
        """Test handling of UNMATCHED account codes"""
        items = [
            {'account_code': 'UNMATCHED', 'account_name': 'Unknown Account 1', 'amount': 100.0},
            {'account_code': 'UNMATCHED', 'account_name': 'Unknown Account 2', 'amount': 200.0}  # Different names
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code', 'account_name']
        )
        
        # Should keep both since account_names differ
        assert result['statistics']['final_count'] == 2
        assert result['statistics']['duplicates_removed'] == 0
    
    def test_validate_no_duplicates_passes(self, dedup_service):
        """Test validation when no duplicates exist"""
        items = [
            {'account_code': '4010-0000', 'account_name': 'Base Rentals'},
            {'account_code': '4020-0000', 'account_name': 'Tax'},
            {'account_code': '4030-0000', 'account_name': 'Insurance'}
        ]
        
        is_valid, error_msg = dedup_service.validate_no_duplicates(
            items=items,
            constraint_columns=['account_code', 'account_name']
        )
        
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_no_duplicates_fails(self, dedup_service):
        """Test validation when duplicates exist"""
        items = [
            {'account_code': '4010-0000', 'account_name': 'Base Rentals'},
            {'account_code': '4010-0000', 'account_name': 'Base Rentals'},  # Duplicate
            {'account_code': '4020-0000', 'account_name': 'Tax'}
        ]
        
        is_valid, error_msg = dedup_service.validate_no_duplicates(
            items=items,
            constraint_columns=['account_code', 'account_name'],
            context="test validation"
        )
        
        assert is_valid is False
        assert error_msg is not None
        assert "Duplicate constraint key" in error_msg
        assert "test validation" in error_msg
    
    def test_empty_items_list(self, dedup_service):
        """Test handling of empty items list"""
        result = dedup_service.deduplicate_items(
            items=[],
            constraint_columns=['account_code']
        )
        
        assert result['statistics']['total_items'] == 0
        assert result['statistics']['duplicates_removed'] == 0
        assert result['statistics']['final_count'] == 0
        assert len(result['deduplicated_items']) == 0
    
    def test_completeness_strategy(self, dedup_service):
        """Test completeness-based selection strategy"""
        items = [
            {'account_code': '4010-0000', 'amount': 1000.0, 'confidence': 90.0},  # Fewer fields
            {'account_code': '4010-0000', 'amount': 1000.0, 'confidence': 90.0, 'line_number': 1, 'page_number': 1}  # More fields
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code'],
            selection_strategy='completeness'
        )
        
        assert result['statistics']['duplicates_removed'] == 1
        # Should keep the more complete record
        assert 'line_number' in result['deduplicated_items'][0]
        assert 'page_number' in result['deduplicated_items'][0]
    
    def test_duplicate_details_logging(self, dedup_service):
        """Test that duplicate details are captured for logging"""
        items = [
            {'account_code': '4010-0000', 'amount': 1000.0, 'confidence': 80.0},
            {'account_code': '4010-0000', 'amount': 1200.0, 'confidence': 95.0}
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code'],
            selection_strategy='confidence'
        )
        
        assert len(result['duplicate_details']) == 1
        assert result['duplicate_details'][0]['action'] in ['replaced', 'kept_existing']
        assert result['duplicate_details'][0]['constraint_key'] == '4010-0000'
        assert 'reason' in result['duplicate_details'][0]
    
    def test_cash_flow_constraint_with_line_number(self, dedup_service):
        """Test cash flow constraint with account_code + account_name + line_number"""
        items = [
            {'account_code': '4010-0000', 'account_name': 'Base Rentals', 'line_number': 1, 'amount': 1000.0},
            {'account_code': '4010-0000', 'account_name': 'Base Rentals', 'line_number': 1, 'amount': 1200.0},  # Duplicate (same code+name+line)
            {'account_code': '4010-0000', 'account_name': 'Base Rentals', 'line_number': 2, 'amount': 800.0}  # Different line_number, should keep
        ]
        
        result = dedup_service.deduplicate_items(
            items=items,
            constraint_columns=['account_code', 'account_name', 'line_number'],
            selection_strategy='confidence'
        )
        
        assert result['statistics']['duplicates_removed'] == 1
        assert result['statistics']['final_count'] == 2
        # Should have both line_number 1 (deduplicated) and line_number 2
        line_numbers = [item['line_number'] for item in result['deduplicated_items']]
        assert 1 in line_numbers
        assert 2 in line_numbers

