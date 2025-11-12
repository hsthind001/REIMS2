"""
Unit tests for Ensemble Voting Engine
Tests weighted voting, conflict resolution, and confidence calculation.
"""
import pytest
from decimal import Decimal

from app.services.ensemble_engine import EnsembleEngine, NumericNormalizer, FieldResult
from app.utils.engines.base_extractor import ExtractionResult


class TestNumericNormalizer:
    """Test numeric normalization utility."""
    
    def test_normalize_currency(self):
        """Test currency normalization."""
        normalizer = NumericNormalizer()
        
        assert normalizer.normalize("$1,234.56") == "1234.56"
        assert normalizer.normalize("1234.56") == "1234.56"
        assert normalizer.normalize("$1,234.5600") == "1234.56"
    
    def test_normalize_negative(self):
        """Test negative number normalization."""
        normalizer = NumericNormalizer()
        
        assert normalizer.normalize("($1,234.56)") == "-1234.56"
        assert normalizer.normalize("-1234.56") == "-1234.56"
    
    def test_normalize_text(self):
        """Test text normalization."""
        normalizer = NumericNormalizer()
        
        assert normalizer.normalize("  Eastern  Shore  Plaza  ") == "eastern shore plaza"
        assert normalizer.normalize(None) == "NULL"


class TestEnsembleEngine:
    """Test ensemble voting engine."""
    
    def test_single_engine_result(self):
        """Test with single engine result."""
        engine = EnsembleEngine()
        
        results = [
            ExtractionResult(
                engine_name='pymupdf',
                confidence=0.95,
                data={'total_assets': '1000000'},
                metadata={}
            )
        ]
        
        ensemble_result = engine.combine_results(results)
        
        assert ensemble_result.overall_confidence == 0.95
        assert len(ensemble_result.fields) == 1
        assert ensemble_result.fields['total_assets'].final_value == '1000000'
        assert ensemble_result.fields['total_assets'].resolution_method == 'single_engine'
    
    def test_consensus_voting(self):
        """Test consensus detection and bonus."""
        engine = EnsembleEngine()
        
        results = [
            ExtractionResult('pymupdf', 0.90, {'total_assets': '1000000'}, {}),
            ExtractionResult('pdfplumber', 0.85, {'total_assets': '1000000'}, {}),
            ExtractionResult('camelot', 0.95, {'total_assets': '1000000'}, {})
        ]
        
        ensemble_result = engine.combine_results(results)
        
        # All engines agree = consensus
        field_result = ensemble_result.fields['total_assets']
        assert field_result.resolution_method == 'consensus'
        assert field_result.final_value == '1000000'
        # Should have consensus bonus (10%)
        assert ensemble_result.overall_confidence > 0.90
    
    def test_conflict_resolution(self):
        """Test weighted voting with conflicts."""
        engine = EnsembleEngine()
        
        results = [
            ExtractionResult('pymupdf', 0.70, {'total_assets': '1000000'}, {}),
            ExtractionResult('pdfplumber', 0.90, {'total_assets': '2000000'}, {}),
            ExtractionResult('camelot', 0.95, {'total_assets': '2000000'}, {})
        ]
        
        ensemble_result = engine.combine_results(results)
        
        # Higher weighted votes win
        field_result = ensemble_result.fields['total_assets']
        assert field_result.final_value == '2000000'  # pdfplumber + camelot win
        assert field_result.conflicting_values is not None
        assert field_result.resolution_method == 'weighted_vote'
    
    def test_numeric_normalization_voting(self):
        """Test that numeric values are normalized for comparison."""
        engine = EnsembleEngine()
        
        results = [
            ExtractionResult('pymupdf', 0.90, {'total_assets': '$1,000,000.00'}, {}),
            ExtractionResult('pdfplumber', 0.85, {'total_assets': '1000000'}, {}),
            ExtractionResult('camelot', 0.95, {'total_assets': '$1,000,000'}, {})
        ]
        
        ensemble_result = engine.combine_results(results)
        
        # All should be recognized as same value (normalized to 1000000.00)
        field_result = ensemble_result.fields['total_assets']
        assert field_result.resolution_method == 'consensus'
        assert ensemble_result.consensus_fields == 1
    
    def test_needs_review_flag(self):
        """Test low confidence triggers review flag."""
        engine = EnsembleEngine()
        
        results = [
            ExtractionResult('easyocr', 0.60, {'total_assets': '500000'}, {})  # Low confidence
        ]
        
        ensemble_result = engine.combine_results(results)
        
        field_result = ensemble_result.fields['total_assets']
        assert field_result.needs_review == True  # Below 0.70 threshold

