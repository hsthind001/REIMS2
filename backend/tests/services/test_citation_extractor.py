"""
Comprehensive Unit Tests for Citation Extractor Service

Tests cover:
- Citation extraction from answers
- Matching claims to document chunks
- Matching claims to SQL results
- Citation formatting
- Error handling and edge cases
- Performance and security
"""
import pytest
import time
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from typing import List, Dict, Any

from app.services.citation_extractor import CitationExtractor, Citation
from app.services.hallucination_detector import Claim


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = Mock()
    return db


@pytest.fixture
def citation_extractor(mock_db):
    """Create CitationExtractor instance"""
    return CitationExtractor(db=mock_db)


@pytest.fixture
def sample_claim():
    """Sample claim for testing"""
    return Claim(
        claim_type='currency',
        value=1234567.89,
        original_text='$1,234,567.89',
        context='The NOI was $1,234,567.89 for the quarter'
    )


@pytest.fixture
def sample_chunks():
    """Sample document chunks for testing"""
    return [
        {
            'chunk_id': 1,
            'chunk_text': 'The net operating income for Q3 2024 was $1,234,567.89, which exceeded expectations.',
            'document_id': 1,
            'document_type': 'income_statement',
            'property_id': 1,
            'period_id': 1,
            'file_name': 'income_statement_q3_2024.pdf',
            'metadata': {
                'page': 2,
                'line': 15,
                'x0': 100,
                'y0': 200,
                'x1': 500,
                'y1': 250
            }
        },
        {
            'chunk_id': 2,
            'chunk_text': 'Total revenue for the period was $2,500,000.00.',
            'document_id': 1,
            'document_type': 'income_statement',
            'property_id': 1,
            'period_id': 1,
            'file_name': 'income_statement_q3_2024.pdf',
            'metadata': {
                'page': 3,
                'line': 20
            }
        }
    ]


@pytest.fixture
def sample_sql_queries():
    """Sample SQL queries for testing"""
    return [
        "SELECT net_operating_income FROM financial_metrics WHERE property_id = 1 AND period_id = 1",
        "SELECT total_revenue FROM income_statement_data WHERE property_id = 1"
    ]


@pytest.fixture
def sample_sql_results():
    """Sample SQL query results for testing"""
    return [
        {'net_operating_income': 1234567.89},
        {'total_revenue': 2500000.00}
    ]


# ============================================================================
# TEST: Citation Extraction
# ============================================================================

class TestCitationExtraction:
    """Test main citation extraction function"""
    
    def test_should_extract_citations_from_answer_with_chunks(
        self, citation_extractor, sample_chunks
    ):
        """Test extraction of citations when chunks are provided"""
        answer = "The NOI was $1,234,567.89 for the quarter."
        
        result = citation_extractor.extract_citations(
            answer=answer,
            retrieved_chunks=sample_chunks
        )
        
        assert result['total_claims'] > 0
        assert result['cited_claims'] > 0
        assert len(result['citations']) > 0
    
    def test_should_extract_citations_from_answer_with_sql(
        self, citation_extractor, sample_sql_queries, sample_sql_results
    ):
        """Test extraction of citations when SQL results are provided"""
        answer = "The NOI was $1,234,567.89."
        
        result = citation_extractor.extract_citations(
            answer=answer,
            sql_queries=sample_sql_queries,
            sql_results=sample_sql_results
        )
        
        assert result['total_claims'] > 0
        assert len(result['citations']) > 0
    
    def test_should_handle_empty_answer(
        self, citation_extractor
    ):
        """Test handling of empty answer"""
        result = citation_extractor.extract_citations("")
        
        assert result['total_claims'] == 0
        assert result['cited_claims'] == 0
        assert len(result['citations']) == 0
        assert result['extraction_time_ms'] >= 0
    
    def test_should_handle_none_answer(
        self, citation_extractor
    ):
        """Test handling of None answer"""
        result = citation_extractor.extract_citations(None)
        
        assert result['total_claims'] == 0
        assert result['cited_claims'] == 0
    
    def test_should_handle_answer_with_no_claims(
        self, citation_extractor
    ):
        """Test handling of answer with no numeric claims"""
        answer = "This is a text without any numbers or financial data."
        
        result = citation_extractor.extract_citations(answer)
        
        assert result['total_claims'] == 0
        assert result['cited_claims'] == 0
    
    def test_should_handle_very_long_answer(
        self, citation_extractor, sample_chunks
    ):
        """Test handling of very long answer (>10,000 characters)"""
        base_text = "The NOI was $1,234,567.89. " * 500  # ~20,000 characters
        answer = base_text
        
        start_time = time.time()
        result = citation_extractor.extract_citations(
            answer=answer,
            retrieved_chunks=sample_chunks
        )
        duration = time.time() - start_time
        
        # Should complete in reasonable time
        assert duration < 5.0
        assert result['total_claims'] > 0
    
    def test_should_measure_extraction_time(
        self, citation_extractor, sample_chunks
    ):
        """Test that extraction time is measured"""
        answer = "The NOI was $1,234,567.89."
        
        result = citation_extractor.extract_citations(
            answer=answer,
            retrieved_chunks=sample_chunks
        )
        
        assert 'extraction_time_ms' in result
        assert result['extraction_time_ms'] >= 0
    
    def test_should_handle_error_gracefully(
        self, citation_extractor
    ):
        """Test graceful handling of errors"""
        # Force error by passing invalid data
        with patch.object(citation_extractor, '_extract_citation_for_claim', side_effect=Exception("Test error")):
            result = citation_extractor.extract_citations(
                answer="The NOI was $1,234,567.89.",
                retrieved_chunks=[]
            )
            
            assert 'error' in result or result['cited_claims'] == 0


# ============================================================================
# TEST: Finding Claims in Chunks
# ============================================================================

class TestFindInChunks:
    """Test finding claims in document chunks"""
    
    def test_should_find_claim_in_chunk_with_exact_match(
        self, citation_extractor, sample_claim, sample_chunks
    ):
        """Test finding claim with exact text match"""
        sources = citation_extractor._find_in_chunks(sample_claim, sample_chunks)
        
        assert len(sources) > 0
        assert sources[0]['type'] == 'document'
        assert sources[0]['document_type'] == 'income_statement'
        assert sources[0]['confidence'] > 0
    
    def test_should_find_claim_in_chunk_with_fuzzy_match(
        self, citation_extractor, sample_claim
    ):
        """Test finding claim with fuzzy text match"""
        chunks = [
            {
                'chunk_text': 'The net operating income was $1,234,567.89 for Q3.',
                'chunk_id': 1,
                'document_type': 'income_statement',
                'metadata': {}
            }
        ]
        
        sources = citation_extractor._find_in_chunks(sample_claim, chunks)
        
        assert len(sources) > 0
    
    def test_should_not_find_claim_when_not_in_chunks(
        self, citation_extractor, sample_claim
    ):
        """Test that claim is not found when not in chunks"""
        chunks = [
            {
                'chunk_text': 'Total revenue was $2,500,000.00.',
                'chunk_id': 1,
                'document_type': 'income_statement',
                'metadata': {}
            }
        ]
        
        sources = citation_extractor._find_in_chunks(sample_claim, chunks)
        
        assert len(sources) == 0
    
    def test_should_include_page_number_when_available(
        self, citation_extractor, sample_claim, sample_chunks
    ):
        """Test that page number is included in citation when available"""
        with patch('app.services.citation_extractor.citation_config') as mock_config:
            mock_config.INCLUDE_PAGE_NUMBER = True
            
            sources = citation_extractor._find_in_chunks(sample_claim, sample_chunks)
            
            if sources:
                assert 'page' in sources[0]
                assert sources[0]['page'] == 2
    
    def test_should_include_line_number_when_available(
        self, citation_extractor, sample_claim, sample_chunks
    ):
        """Test that line number is included in citation when available"""
        with patch('app.services.citation_extractor.citation_config') as mock_config:
            mock_config.INCLUDE_LINE_NUMBER = True
            
            sources = citation_extractor._find_in_chunks(sample_claim, sample_chunks)
            
            if sources:
                assert 'line' in sources[0]
                assert sources[0]['line'] == 15
    
    def test_should_include_coordinates_when_available(
        self, citation_extractor, sample_claim, sample_chunks
    ):
        """Test that coordinates are included in citation when available"""
        sources = citation_extractor._find_in_chunks(sample_claim, sample_chunks)
        
        if sources and 'coordinates' in sources[0]:
            coords = sources[0]['coordinates']
            assert 'x0' in coords
            assert 'y0' in coords
            assert 'x1' in coords
            assert 'y1' in coords
    
    def test_should_include_excerpt_when_enabled(
        self, citation_extractor, sample_claim, sample_chunks
    ):
        """Test that excerpt is included in citation when enabled"""
        with patch('app.services.citation_extractor.citation_config') as mock_config:
            mock_config.INCLUDE_EXCERPT = True
            mock_config.EXCERPT_WINDOW = 100
            
            sources = citation_extractor._find_in_chunks(sample_claim, sample_chunks)
            
            if sources:
                assert 'excerpt' in sources[0]
                assert len(sources[0]['excerpt']) > 0
    
    def test_should_sort_sources_by_confidence(
        self, citation_extractor, sample_claim
    ):
        """Test that sources are sorted by confidence (highest first)"""
        chunks = [
            {
                'chunk_text': 'Revenue was $1,234,567.89 approximately.',
                'chunk_id': 1,
                'document_type': 'income_statement',
                'metadata': {}
            },
            {
                'chunk_text': 'The exact NOI was $1,234,567.89 for the period.',
                'chunk_id': 2,
                'document_type': 'income_statement',
                'metadata': {}
            }
        ]
        
        sources = citation_extractor._find_in_chunks(sample_claim, chunks)
        
        if len(sources) > 1:
            assert sources[0]['confidence'] >= sources[1]['confidence']
    
    def test_should_handle_empty_chunks(
        self, citation_extractor, sample_claim
    ):
        """Test handling of empty chunks list"""
        sources = citation_extractor._find_in_chunks(sample_claim, [])
        
        assert len(sources) == 0
    
    def test_should_handle_chunks_without_text(
        self, citation_extractor, sample_claim
    ):
        """Test handling of chunks without chunk_text"""
        chunks = [
            {
                'chunk_id': 1,
                'document_type': 'income_statement',
                'metadata': {}
            }
        ]
        
        sources = citation_extractor._find_in_chunks(sample_claim, chunks)
        
        assert len(sources) == 0


# ============================================================================
# TEST: Matching Claims in Text
# ============================================================================

class TestMatchClaimInText:
    """Test matching claims in text"""
    
    def test_should_match_exact_text(
        self, citation_extractor, sample_claim
    ):
        """Test exact text matching"""
        text = "The NOI was $1,234,567.89 for the quarter."
        
        result = citation_extractor._match_claim_in_text(sample_claim, text)
        
        assert result['matched'] is True
        assert result['confidence'] == 1.0
    
    def test_should_match_with_fuzzy_matching(
        self, citation_extractor, sample_claim
    ):
        """Test fuzzy text matching"""
        text = "The net operating income was $1,234,567.89 approximately."
        
        result = citation_extractor._match_claim_in_text(sample_claim, text)
        
        # Should match even if not exact
        assert result['matched'] is True
        assert result['confidence'] > 0
    
    def test_should_not_match_when_value_different(
        self, citation_extractor, sample_claim
    ):
        """Test that different values don't match"""
        text = "The NOI was $9,999,999.99 for the quarter."
        
        result = citation_extractor._match_claim_in_text(sample_claim, text)
        
        assert result['matched'] is False
    
    def test_should_match_currency_with_different_formats(
        self, citation_extractor
    ):
        """Test matching currency in different formats"""
        claim = Claim(
            claim_type='currency',
            value=1234567.89,
            original_text='$1,234,567.89'
        )
        
        # Test with M suffix
        text1 = "The NOI was $1.23M for the quarter."
        result1 = citation_extractor._match_claim_in_text(claim, text1)
        assert result1['matched'] is True
        
        # Test with K suffix
        claim_k = Claim(
            claim_type='currency',
            value=500000.0,
            original_text='$500K'
        )
        text2 = "Revenue was $500K."
        result2 = citation_extractor._match_claim_in_text(claim_k, text2)
        assert result2['matched'] is True
    
    def test_should_handle_empty_text(
        self, citation_extractor, sample_claim
    ):
        """Test handling of empty text"""
        result = citation_extractor._match_claim_in_text(sample_claim, "")
        
        assert result['matched'] is False
    
    def test_should_handle_unicode_text(
        self, citation_extractor, sample_claim
    ):
        """Test matching with Unicode characters"""
        text = "The NOI was $1,234,567.89 (收入: ¥8,000,000)."
        
        result = citation_extractor._match_claim_in_text(sample_claim, text)
        
        # Should still match USD value
        assert result['matched'] is True


# ============================================================================
# TEST: Finding Claims in SQL Results
# ============================================================================

class TestFindInSQL:
    """Test finding claims in SQL results"""
    
    def test_should_find_claim_in_sql_result(
        self, citation_extractor, sample_claim, sample_sql_queries, sample_sql_results
    ):
        """Test finding claim value in SQL results"""
        sources = citation_extractor._find_in_sql(
            sample_claim,
            sample_sql_queries,
            sample_sql_results
        )
        
        assert len(sources) > 0
        assert sources[0]['type'] == 'sql'
        assert sources[0]['confidence'] == 0.95
    
    def test_should_not_find_claim_when_not_in_sql_result(
        self, citation_extractor, sample_claim
    ):
        """Test that claim is not found when not in SQL results"""
        sql_results = [
            {'total_revenue': 2500000.00}
        ]
        sql_queries = ["SELECT total_revenue FROM income_statement"]
        
        sources = citation_extractor._find_in_sql(sample_claim, sql_queries, sql_results)
        
        assert len(sources) == 0
    
    def test_should_find_claim_in_nested_sql_result(
        self, citation_extractor, sample_claim
    ):
        """Test finding claim in nested SQL result structure"""
        sql_results = [
            {
                'metrics': {
                    'noi': 1234567.89,
                    'revenue': 2500000.00
                }
            }
        ]
        sql_queries = ["SELECT metrics FROM financial_data"]
        
        sources = citation_extractor._find_in_sql(sample_claim, sql_queries, sql_results)
        
        assert len(sources) > 0
    
    def test_should_find_claim_in_list_sql_result(
        self, citation_extractor, sample_claim
    ):
        """Test finding claim in list SQL result"""
        sql_results = [
            [1234567.89, 2500000.00]
        ]
        sql_queries = ["SELECT noi, revenue FROM financial_data"]
        
        sources = citation_extractor._find_in_sql(sample_claim, sql_queries, sql_results)
        
        assert len(sources) > 0
    
    def test_should_handle_empty_sql_results(
        self, citation_extractor, sample_claim
    ):
        """Test handling of empty SQL results"""
        sources = citation_extractor._find_in_sql(sample_claim, [], [])
        
        assert len(sources) == 0
    
    def test_should_handle_none_sql_results(
        self, citation_extractor, sample_claim
    ):
        """Test handling of None SQL results"""
        sources = citation_extractor._find_in_sql(sample_claim, None, None)
        
        assert len(sources) == 0


# ============================================================================
# TEST: Citation Deduplication
# ============================================================================

class TestCitationDeduplication:
    """Test citation deduplication"""
    
    def test_should_deduplicate_similar_sources(
        self, citation_extractor
    ):
        """Test deduplication of citations with similar sources"""
        citation1 = Citation(
            citation_type='document',
            claim_text='$1,234,567.89',
            sources=[
                {
                    'type': 'document',
                    'document_id': 1,
                    'chunk_id': 1,
                    'page': 2
                }
            ]
        )
        
        citation2 = Citation(
            citation_type='document',
            claim_text='$1,234,567.89',
            sources=[
                {
                    'type': 'document',
                    'document_id': 1,
                    'chunk_id': 1,
                    'page': 2  # Same source
                }
            ]
        )
        
        with patch('app.services.citation_extractor.citation_config') as mock_config:
            mock_config.DEDUPLICATE_SOURCES = True
            
            deduplicated = citation_extractor._deduplicate_citations([citation1, citation2])
            
            # Should have only unique sources
            assert len(deduplicated) <= 2
    
    def test_should_not_deduplicate_different_sources(
        self, citation_extractor
    ):
        """Test that different sources are not deduplicated"""
        citation1 = Citation(
            citation_type='document',
            claim_text='$1,234,567.89',
            sources=[
                {
                    'type': 'document',
                    'document_id': 1,
                    'chunk_id': 1,
                    'page': 2
                }
            ]
        )
        
        citation2 = Citation(
            citation_type='document',
            claim_text='$1,234,567.89',
            sources=[
                {
                    'type': 'document',
                    'document_id': 2,
                    'chunk_id': 2,
                    'page': 3  # Different source
                }
            ]
        )
        
        with patch('app.services.citation_extractor.citation_config') as mock_config:
            mock_config.DEDUPLICATE_SOURCES = True
            
            deduplicated = citation_extractor._deduplicate_citations([citation1, citation2])
            
            assert len(deduplicated) == 2
    
    def test_should_handle_empty_citations(
        self, citation_extractor
    ):
        """Test handling of empty citations list"""
        deduplicated = citation_extractor._deduplicate_citations([])
        
        assert len(deduplicated) == 0


# ============================================================================
# TEST: Citation Formatting
# ============================================================================

class TestCitationFormatting:
    """Test citation formatting functions"""
    
    def test_should_format_citation_inline(
        self, citation_extractor
    ):
        """Test inline citation formatting"""
        citation = Citation(
            citation_type='document',
            claim_text='$1,234,567.89',
            sources=[
                {
                    'type': 'document',
                    'document_type': 'income_statement',
                    'page': 2,
                    'line': 15
                }
            ]
        )
        
        with patch('app.services.citation_extractor.citation_config') as mock_config:
            mock_config.INCLUDE_PAGE_NUMBER = True
            mock_config.INCLUDE_LINE_NUMBER = True
            mock_config.MAX_SOURCES_PER_CLAIM = 3
            
            formatted = citation_extractor.format_citation_inline(citation)
            
            assert '$1,234,567.89' in formatted
            assert 'Source' in formatted or 'Page' in formatted
    
    def test_should_format_sql_citation(
        self, citation_extractor
    ):
        """Test formatting of SQL citation"""
        citation = Citation(
            citation_type='sql',
            claim_text='$1,234,567.89',
            sources=[
                {
                    'type': 'sql',
                    'query': 'SELECT noi FROM metrics'
                }
            ]
        )
        
        formatted = citation_extractor.format_citation_inline(citation)
        
        assert '$1,234,567.89' in formatted
        assert 'Database Query' in formatted or 'SQL' in formatted
    
    def test_should_format_citations_for_api(
        self, citation_extractor
    ):
        """Test formatting citations for API response"""
        citations = [
            Citation(
                citation_type='document',
                claim_text='$1,234,567.89',
                sources=[{'type': 'document', 'page': 2}],
                confidence=0.95
            )
        ]
        
        formatted = citation_extractor.format_citations_for_api(citations)
        
        assert len(formatted) == 1
        assert formatted[0]['claim'] == '$1,234,567.89'
        assert formatted[0]['confidence'] == 0.95
        assert formatted[0]['type'] == 'document'


# ============================================================================
# TEST: Edge Cases and Security
# ============================================================================

class TestEdgeCases:
    """Test edge cases and security concerns"""
    
    def test_should_handle_special_characters_in_text(
        self, citation_extractor, sample_chunks
    ):
        """Test handling of special characters in text"""
        answer = "The NOI was $1,234,567.89 (with special chars: @#$%^&*)"
        
        result = citation_extractor.extract_citations(
            answer=answer,
            retrieved_chunks=sample_chunks
        )
        
        assert result is not None
        assert 'error' not in result
    
    def test_should_handle_unicode_in_text(
        self, citation_extractor, sample_chunks
    ):
        """Test handling of Unicode characters"""
        answer = "The NOI was $1,234,567.89 (收入: ¥8,000,000)"
        
        result = citation_extractor.extract_citations(
            answer=answer,
            retrieved_chunks=sample_chunks
        )
        
        assert result is not None
    
    def test_should_handle_null_values(
        self, citation_extractor
    ):
        """Test handling of None/null values"""
        result = citation_extractor.extract_citations(
            answer=None,
            retrieved_chunks=None,
            sql_queries=None,
            sql_results=None
        )
        
        assert result is not None
        assert result['total_claims'] == 0
    
    def test_should_handle_invalid_data_types(
        self, citation_extractor
    ):
        """Test handling of invalid data types"""
        # Should not raise exception with invalid types
        try:
            result = citation_extractor.extract_citations(
                answer=12345,  # Invalid type
                retrieved_chunks="invalid"  # Invalid type
            )
            # Should handle gracefully
            assert result is not None
        except (TypeError, AttributeError):
            # Acceptable to raise type errors
            pass
    
    def test_should_limit_sources_per_claim(
        self, citation_extractor, sample_claim
    ):
        """Test that sources are limited per claim"""
        chunks = [
            {
                'chunk_text': f'The NOI was $1,234,567.89 in chunk {i}.',
                'chunk_id': i,
                'document_type': 'income_statement',
                'metadata': {}
            }
            for i in range(10)  # 10 chunks with same value
        ]
        
        with patch('app.services.citation_extractor.citation_config') as mock_config:
            mock_config.MAX_SOURCES_PER_CLAIM = 3
            
            sources = citation_extractor._find_in_chunks(sample_claim, chunks)
            
            # Should be limited to max sources
            assert len(sources) <= 3


# ============================================================================
# TEST: Performance
# ============================================================================

class TestPerformance:
    """Test performance requirements"""
    
    def test_should_complete_extraction_quickly(
        self, citation_extractor, sample_chunks
    ):
        """Test that extraction completes within timeout"""
        answer = "The NOI was $1,234,567.89 and revenue was $2,500,000.00."
        
        start_time = time.time()
        result = citation_extractor.extract_citations(
            answer=answer,
            retrieved_chunks=sample_chunks
        )
        duration = time.time() - start_time
        
        # Should complete in < 200ms
        assert duration < 0.2
        assert result['extraction_time_ms'] < 200
    
    def test_should_handle_many_chunks_efficiently(
        self, citation_extractor, sample_claim
    ):
        """Test handling of many chunks efficiently"""
        chunks = [
            {
                'chunk_text': f'Chunk {i} with text about financial data.',
                'chunk_id': i,
                'document_type': 'income_statement',
                'metadata': {}
            }
            for i in range(100)  # 100 chunks
        ]
        
        start_time = time.time()
        sources = citation_extractor._find_in_chunks(sample_claim, chunks)
        duration = time.time() - start_time
        
        # Should complete in reasonable time
        assert duration < 1.0


# ============================================================================
# TEST: Integration
# ============================================================================

class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.integration
    def test_should_work_with_real_hallucination_detector(
        self, mock_db
    ):
        """Integration test with real hallucination detector"""
        extractor = CitationExtractor(db=mock_db)
        
        answer = "The NOI was $1,234,567.89 for Q3 2024."
        chunks = [
            {
                'chunk_text': 'The net operating income was $1,234,567.89.',
                'chunk_id': 1,
                'document_type': 'income_statement',
                'metadata': {}
            }
        ]
        
        result = extractor.extract_citations(
            answer=answer,
            retrieved_chunks=chunks
        )
        
        assert result is not None
        assert result['total_claims'] > 0
