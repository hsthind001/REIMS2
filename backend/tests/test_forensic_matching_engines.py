"""
Unit tests for forensic reconciliation matching engines

Tests for:
- ExactMatchEngine
- FuzzyMatchEngine
- CalculatedMatchEngine
- InferredMatchEngine
- ConfidenceScorer
"""

import pytest
from decimal import Decimal
from app.services.matching_engines import (
    ExactMatchEngine,
    FuzzyMatchEngine,
    CalculatedMatchEngine,
    InferredMatchEngine,
    ConfidenceScorer
)


class TestConfidenceScorer:
    """Test confidence score calculation"""
    
    def test_perfect_match(self):
        scorer = ConfidenceScorer()
        score = scorer.calculate_score(100.0, 100.0, 100.0, 100.0)
        assert score == Decimal('100.00')
    
    def test_weighted_calculation(self):
        scorer = ConfidenceScorer()
        # Account (40%) + Amount (40%) + Date (10%) + Context (10%)
        score = scorer.calculate_score(80.0, 90.0, 100.0, 100.0)
        expected = (80.0 * 0.4) + (90.0 * 0.4) + (100.0 * 0.1) + (100.0 * 0.1)
        assert float(score) == pytest.approx(expected, rel=0.01)
    
    def test_low_confidence(self):
        scorer = ConfidenceScorer()
        score = scorer.calculate_score(50.0, 50.0, 50.0, 50.0)
        assert score == Decimal('50.00')
    
    def test_bounds_clamping(self):
        scorer = ConfidenceScorer()
        # Test that scores are clamped to 0-100
        score_negative = scorer.calculate_score(-10.0, 100.0, 100.0, 100.0)
        assert score_negative >= Decimal('0.00')
        
        score_over_100 = scorer.calculate_score(150.0, 100.0, 100.0, 100.0)
        assert score_over_100 <= Decimal('100.00')


class TestExactMatchEngine:
    """Test exact matching engine"""
    
    def test_exact_match_same_account_code(self):
        engine = ExactMatchEngine()
        source_data = {
            1: {'account_code': '0122-0000', 'amount': Decimal('100000.00')}
        }
        target_data = {
            1: {'account_code': '0122-0000', 'amount': Decimal('100000.00')}
        }
        matches = engine.find_matches(source_data, target_data)
        assert len(matches) == 1
        assert matches[0]['match_type'] == 'exact'
        assert matches[0]['confidence_score'] == Decimal('100.00')
        assert matches[0]['amount_difference'] == Decimal('0.00')
    
    def test_exact_match_within_tolerance(self):
        engine = ExactMatchEngine()
        source_data = {
            1: {'account_code': '0122-0000', 'amount': Decimal('100000.00')}
        }
        target_data = {
            1: {'account_code': '0122-0000', 'amount': Decimal('100000.01')}
        }
        matches = engine.find_matches(source_data, target_data, tolerance=Decimal('0.01'))
        assert len(matches) == 1
        assert matches[0]['match_type'] == 'exact'
    
    def test_no_match_different_account_code(self):
        engine = ExactMatchEngine()
        source_data = {
            1: {'account_code': '0122-0000', 'amount': Decimal('100000.00')}
        }
        target_data = {
            1: {'account_code': '0123-0000', 'amount': Decimal('100000.00')}
        }
        matches = engine.find_matches(source_data, target_data)
        assert len(matches) == 0
    
    def test_no_match_amount_outside_tolerance(self):
        engine = ExactMatchEngine()
        source_data = {
            1: {'account_code': '0122-0000', 'amount': Decimal('100000.00')}
        }
        target_data = {
            1: {'account_code': '0122-0000', 'amount': Decimal('100000.10')}
        }
        matches = engine.find_matches(source_data, target_data, tolerance=Decimal('0.01'))
        assert len(matches) == 0
    
    def test_multiple_matches(self):
        engine = ExactMatchEngine()
        source_data = {
            1: {'account_code': '0122-0000', 'amount': Decimal('100000.00')},
            2: {'account_code': '0123-0000', 'amount': Decimal('50000.00')}
        }
        target_data = {
            1: {'account_code': '0122-0000', 'amount': Decimal('100000.00')},
            2: {'account_code': '0123-0000', 'amount': Decimal('50000.00')}
        }
        matches = engine.find_matches(source_data, target_data)
        assert len(matches) == 2


class TestFuzzyMatchEngine:
    """Test fuzzy matching engine"""
    
    def test_fuzzy_match_similar_names(self):
        engine = FuzzyMatchEngine()
        source_data = {
            1: {'account_name': 'Cash Operating Account', 'amount': Decimal('100000.00')}
        }
        target_data = {
            1: {'account_name': 'Operating Cash', 'amount': Decimal('100500.00')}
        }
        matches = engine.find_matches(source_data, target_data, name_threshold=70)
        assert len(matches) >= 1
        assert matches[0]['match_type'] == 'fuzzy'
        assert matches[0]['confidence_score'] >= Decimal('70.00')
    
    def test_fuzzy_match_exact_name_different_amount(self):
        engine = FuzzyMatchEngine()
        source_data = {
            1: {'account_name': 'Cash Operating Account', 'amount': Decimal('100000.00')}
        }
        target_data = {
            1: {'account_name': 'Cash Operating Account', 'amount': Decimal('105000.00')}
        }
        matches = engine.find_matches(source_data, target_data, name_threshold=80)
        # Should still match but with lower confidence due to amount difference
        assert len(matches) >= 1
        assert matches[0]['match_type'] == 'fuzzy'
    
    def test_fuzzy_match_below_threshold(self):
        engine = FuzzyMatchEngine()
        source_data = {
            1: {'account_name': 'Cash Operating Account', 'amount': Decimal('100000.00')}
        }
        target_data = {
            1: {'account_name': 'Accounts Payable', 'amount': Decimal('100000.00')}
        }
        matches = engine.find_matches(source_data, target_data, name_threshold=80)
        # Should not match - names too different
        assert len(matches) == 0
    
    def test_fuzzy_match_no_account_name(self):
        engine = FuzzyMatchEngine()
        source_data = {
            1: {'account_code': '0122-0000', 'amount': Decimal('100000.00')}
        }
        target_data = {
            1: {'account_code': '0122-0000', 'amount': Decimal('100000.00')}
        }
        matches = engine.find_matches(source_data, target_data)
        # Without account names, fuzzy matching can't work
        assert len(matches) == 0


class TestCalculatedMatchEngine:
    """Test calculated matching engine"""
    
    def test_calculated_match_rule_function(self):
        engine = CalculatedMatchEngine()
        
        def test_rule(source_data, target_data):
            """Simple test rule: sum of source equals target"""
            source_sum = sum(Decimal(str(r.get('amount', 0))) for r in source_data.values())
            target_sum = sum(Decimal(str(r.get('amount', 0))) for r in target_data.values())
            
            if abs(source_sum - target_sum) <= Decimal('0.01'):
                return {
                    'source_record': list(source_data.values())[0],
                    'target_record': list(target_data.values())[0],
                    'source_value': source_sum,
                    'target_value': target_sum,
                    'relationship_type': 'equality',
                    'relationship_formula': 'SUM(source) = SUM(target)',
                    'confidence_score': Decimal('95.00')
                }
            return None
        
        source_data = {
            1: {'amount': Decimal('50000.00')},
            2: {'amount': Decimal('50000.00')}
        }
        target_data = {
            1: {'amount': Decimal('100000.00')}
        }
        
        matches = engine.find_matches(source_data, target_data, test_rule, 'test_rule')
        assert len(matches) == 1
        assert matches[0]['match_type'] == 'calculated'
        assert matches[0]['confidence_score'] == Decimal('95.00')
        assert matches[0]['relationship_type'] == 'equality'
    
    def test_calculated_match_rule_fails(self):
        engine = CalculatedMatchEngine()
        
        def failing_rule(source_data, target_data):
            return None
        
        source_data = {1: {'amount': Decimal('100000.00')}}
        target_data = {1: {'amount': Decimal('200000.00')}}
        
        matches = engine.find_matches(source_data, target_data, failing_rule, 'failing_rule')
        assert len(matches) == 0
    
    def test_calculated_match_rule_exception(self):
        engine = CalculatedMatchEngine()
        
        def exception_rule(source_data, target_data):
            raise ValueError("Test exception")
        
        source_data = {1: {'amount': Decimal('100000.00')}}
        target_data = {1: {'amount': Decimal('100000.00')}}
        
        # Should handle exception gracefully
        matches = engine.find_matches(source_data, target_data, exception_rule, 'exception_rule')
        assert len(matches) == 0


class TestInferredMatchEngine:
    """Test inferred matching engine (placeholder)"""
    
    def test_inferred_match_placeholder(self):
        engine = InferredMatchEngine()
        source_data = {1: {'amount': Decimal('100000.00')}}
        target_data = {1: {'amount': Decimal('100000.00')}}
        
        # Currently returns empty list (placeholder)
        matches = engine.find_matches(source_data, target_data)
        assert len(matches) == 0
    
    def test_inferred_match_engine_initialized(self):
        engine = InferredMatchEngine()
        assert engine.scorer is not None
        assert engine.model is None  # ML model not yet implemented

