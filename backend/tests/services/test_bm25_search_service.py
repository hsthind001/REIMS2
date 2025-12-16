"""
Unit Tests for BM25 Search Service

Tests index building, search accuracy, metadata filtering,
cache operations, and performance.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import os
from pathlib import Path

from app.services.bm25_search_service import BM25SearchService
from app.models.document_chunk import DocumentChunk
from app.config.bm25_config import bm25_config


@pytest.fixture
def mock_bm25_index():
    """Mock BM25Okapi index"""
    mock_index = MagicMock()
    mock_index.get_scores.return_value = [2.5, 1.8, 1.2, 0.9, 0.5]
    return mock_index


@pytest.fixture
def cache_service(db_session):
    """Create BM25 service instance"""
    # Use temporary cache directory for tests
    with patch('app.config.bm25_config.bm25_config.CACHE_DIR', tempfile.mkdtemp()):
        service = BM25SearchService(db_session)
        return service


class TestIndexBuilding:
    """Test index building functionality"""
    
    def test_build_index_from_chunks(self, cache_service, db_session):
        """Test building index from document chunks"""
        # Create test chunks
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=0,
                chunk_text="DSCR below 1.25 indicates financial risk",
                property_id=1,
                period_id=1,
                document_type="income_statement"
            ),
            DocumentChunk(
                document_id=1,
                chunk_index=1,
                chunk_text="Net operating income increased by 10%",
                property_id=1,
                period_id=1,
                document_type="income_statement"
            ),
            DocumentChunk(
                document_id=2,
                chunk_index=0,
                chunk_text="Property revenue reached $1 million",
                property_id=2,
                period_id=2,
                document_type="income_statement"
            )
        ]
        
        for chunk in chunks:
            db_session.add(chunk)
        db_session.commit()
        
        # Build index
        result = cache_service.build_index()
        
        assert result['success'] is True
        assert result['chunk_count'] == 3
        assert cache_service.bm25_index is not None
        assert len(cache_service.chunk_ids) == 3
    
    def test_build_index_empty_chunks(self, cache_service, db_session):
        """Test building index with no chunks"""
        result = cache_service.build_index()
        
        assert result['success'] is False
        assert 'No chunks found' in result.get('error', '')
    
    def test_build_index_skips_empty_text(self, cache_service, db_session):
        """Test that chunks with empty text are skipped"""
        chunk = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="",  # Empty text
            property_id=1
        )
        db_session.add(chunk)
        db_session.commit()
        
        result = cache_service.build_index()
        
        assert result['success'] is False or result['chunk_count'] == 0


class TestSearch:
    """Test search functionality"""
    
    def test_search_exact_term_match(self, cache_service, db_session):
        """Test that exact term matches get higher scores"""
        # Create chunks
        chunk1 = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="DSCR below 1.25 indicates financial risk",
            property_id=1,
            document_type="income_statement"
        )
        chunk2 = DocumentChunk(
            document_id=1,
            chunk_index=1,
            chunk_text="Net operating income increased",
            property_id=1,
            document_type="income_statement"
        )
        db_session.add_all([chunk1, chunk2])
        db_session.commit()
        
        # Build index
        cache_service.build_index()
        
        # Search for exact term
        results = cache_service.search("DSCR below 1.25", top_k=5)
        
        assert len(results) > 0
        assert results[0]['chunk_id'] == chunk1.id
        assert 'DSCR' in results[0]['chunk_text']
        assert results[0]['score'] > 0
    
    def test_search_metadata_filtering(self, cache_service, db_session):
        """Test metadata filtering (property_id, document_type)"""
        # Create chunks for different properties
        chunk1 = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="Property revenue increased",
            property_id=1,
            document_type="income_statement"
        )
        chunk2 = DocumentChunk(
            document_id=2,
            chunk_index=0,
            chunk_text="Property revenue increased",
            property_id=2,
            document_type="income_statement"
        )
        db_session.add_all([chunk1, chunk2])
        db_session.commit()
        
        # Build index
        cache_service.build_index()
        
        # Search with property filter
        results = cache_service.search(
            "revenue",
            top_k=5,
            property_id=1
        )
        
        assert len(results) > 0
        assert all(r['property_id'] == 1 for r in results)
    
    def test_search_document_type_filter(self, cache_service, db_session):
        """Test filtering by document type"""
        chunk1 = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="Balance sheet assets",
            property_id=1,
            document_type="balance_sheet"
        )
        chunk2 = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="Income statement revenue",
            property_id=1,
            document_type="income_statement"
        )
        db_session.add_all([chunk1, chunk2])
        db_session.commit()
        
        cache_service.build_index()
        
        results = cache_service.search(
            "revenue",
            top_k=5,
            document_type="income_statement"
        )
        
        assert len(results) > 0
        assert all(r['document_type'] == 'income_statement' for r in results)
    
    def test_search_returns_top_k(self, cache_service, db_session):
        """Test that search returns top-k results"""
        # Create multiple chunks
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Test chunk {i} with revenue data",
                property_id=1
            )
            for i in range(10)
        ]
        db_session.add_all(chunks)
        db_session.commit()
        
        cache_service.build_index()
        
        results = cache_service.search("revenue", top_k=5)
        
        assert len(results) <= 5
        # Results should be sorted by score (descending)
        scores = [r['score'] for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_search_no_matches(self, cache_service, db_session):
        """Test search with no matching chunks"""
        chunk = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="Some unrelated text",
            property_id=1
        )
        db_session.add(chunk)
        db_session.commit()
        
        cache_service.build_index()
        
        results = cache_service.search("nonexistent term xyz123", top_k=5)
        
        # Should return empty or very low scoring results
        assert isinstance(results, list)


class TestCacheOperations:
    """Test cache loading and saving"""
    
    def test_save_index_to_cache(self, cache_service, db_session):
        """Test saving index to cache"""
        # Create and build index
        chunk = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="Test chunk",
            property_id=1
        )
        db_session.add(chunk)
        db_session.commit()
        
        cache_service.build_index()
        
        # Save to cache
        result = cache_service._save_index_to_cache()
        
        assert result is True
        cache_path = bm25_config.get_cache_path()
        assert cache_path.exists()
    
    def test_load_cached_index(self, cache_service, db_session):
        """Test loading index from cache"""
        # Create and build index
        chunk = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="Test chunk",
            property_id=1
        )
        db_session.add(chunk)
        db_session.commit()
        
        cache_service.build_index()
        cache_service._save_index_to_cache()
        
        # Create new service instance (should load from cache)
        new_service = BM25SearchService(db_session)
        
        assert new_service.bm25_index is not None
        assert len(new_service.chunk_ids) > 0
    
    def test_load_cache_version_mismatch(self, cache_service, db_session):
        """Test that version mismatch triggers rebuild"""
        # Create and save index with old version
        chunk = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="Test chunk",
            property_id=1
        )
        db_session.add(chunk)
        db_session.commit()
        
        cache_service.build_index()
        cache_service.index_metadata['version'] = 999  # Wrong version
        cache_service._save_index_to_cache()
        
        # Try to load (should fail and return False)
        new_service = BM25SearchService(db_session)
        # Should rebuild or have empty index
        assert new_service.bm25_index is None or len(new_service.chunk_ids) == 0
    
    def test_clear_cache(self, cache_service, db_session):
        """Test clearing cache"""
        # Create and save index
        chunk = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="Test chunk",
            property_id=1
        )
        db_session.add(chunk)
        db_session.commit()
        
        cache_service.build_index()
        cache_service._save_index_to_cache()
        
        # Clear cache
        result = cache_service.clear_cache()
        
        assert result is True
        cache_path = bm25_config.get_cache_path()
        assert not cache_path.exists()


class TestIndexStats:
    """Test index statistics"""
    
    def test_get_index_stats(self, cache_service, db_session):
        """Test getting index statistics"""
        # Create and build index
        chunk = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="Test chunk",
            property_id=1
        )
        db_session.add(chunk)
        db_session.commit()
        
        cache_service.build_index()
        
        stats = cache_service.get_index_stats()
        
        assert stats['index_built'] is True
        assert stats['chunk_count'] == 1
        assert stats['built_at'] is not None
        assert stats['version'] == bm25_config.CACHE_VERSION
    
    def test_get_index_stats_not_built(self, cache_service):
        """Test stats when index not built"""
        stats = cache_service.get_index_stats()
        
        assert stats['index_built'] is False
        assert stats['chunk_count'] == 0


class TestTokenization:
    """Test tokenization function"""
    
    def test_tokenize_lowercase(self, cache_service):
        """Test that tokenization converts to lowercase"""
        tokens = cache_service._tokenize("DSCR Below 1.25")
        
        assert all(token.islower() for token in tokens)
        assert 'dscr' in tokens
        assert 'below' in tokens
    
    def test_tokenize_whitespace_split(self, cache_service):
        """Test that tokenization splits on whitespace"""
        tokens = cache_service._tokenize("DSCR below 1.25")
        
        assert len(tokens) == 3
        assert 'dscr' in tokens
        assert 'below' in tokens
        assert '1.25' in tokens
    
    def test_tokenize_empty_string(self, cache_service):
        """Test tokenization of empty string"""
        tokens = cache_service._tokenize("")
        
        assert tokens == []
    
    def test_tokenize_special_characters(self, cache_service):
        """Test tokenization with special characters"""
        tokens = cache_service._tokenize("DSCR: 1.25 (below threshold)")
        
        # Should handle special characters gracefully
        assert isinstance(tokens, list)
        assert len(tokens) > 0


class TestAutoRebuild:
    """Test auto-rebuild functionality"""
    
    def test_auto_rebuild_on_threshold(self, cache_service, db_session):
        """Test that index rebuilds when threshold exceeded"""
        # Create initial chunks
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Chunk {i}",
                property_id=1
            )
            for i in range(50)
        ]
        db_session.add_all(chunks)
        db_session.commit()
        
        cache_service.build_index()
        initial_count = len(cache_service.chunk_ids)
        
        # Add more chunks to exceed threshold
        with patch('app.config.bm25_config.bm25_config.AUTO_REBUILD', True):
            with patch('app.config.bm25_config.bm25_config.REBUILD_THRESHOLD', 10):
                new_chunks = [
                    DocumentChunk(
                        document_id=1,
                        chunk_index=50 + i,
                        chunk_text=f"New chunk {i}",
                        property_id=1
                    )
                    for i in range(20)  # Exceeds threshold of 10
                ]
                db_session.add_all(new_chunks)
                db_session.commit()
                
                # Search should trigger rebuild
                results = cache_service.search("chunk", top_k=5)
                
                # Index should have been rebuilt
                assert len(cache_service.chunk_ids) > initial_count


class TestPerformance:
    """Test performance requirements"""
    
    def test_search_performance(self, cache_service, db_session):
        """Test that search meets performance target (<100ms)"""
        import time
        
        # Create test chunks
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Test chunk {i} with revenue data and financial information",
                property_id=1
            )
            for i in range(100)
        ]
        db_session.add_all(chunks)
        db_session.commit()
        
        cache_service.build_index()
        
        # Measure search time
        start = time.time()
        results = cache_service.search("revenue", top_k=20)
        elapsed_ms = (time.time() - start) * 1000
        
        # Should be under 100ms (with margin for test environment)
        assert elapsed_ms < 200  # Allow margin for test environment
        assert len(results) <= 20


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_search_without_index(self, cache_service):
        """Test search when index not built"""
        # Should auto-build on first search
        results = cache_service.search("test", top_k=5)
        
        # Should return empty results or auto-build
        assert isinstance(results, list)
    
    def test_rebuild_index(self, cache_service, db_session):
        """Test force rebuild"""
        # Create initial index
        chunk = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="Initial chunk",
            property_id=1
        )
        db_session.add(chunk)
        db_session.commit()
        
        cache_service.build_index()
        initial_count = len(cache_service.chunk_ids)
        
        # Add more chunks
        new_chunk = DocumentChunk(
            document_id=1,
            chunk_index=1,
            chunk_text="New chunk",
            property_id=1
        )
        db_session.add(new_chunk)
        db_session.commit()
        
        # Force rebuild
        result = cache_service.rebuild_index()
        
        assert result['success'] is True
        assert len(cache_service.chunk_ids) > initial_count
    
    def test_search_empty_query(self, cache_service, db_session):
        """Test search with empty query"""
        chunk = DocumentChunk(
            document_id=1,
            chunk_index=0,
            chunk_text="Test chunk",
            property_id=1
        )
        db_session.add(chunk)
        db_session.commit()
        
        cache_service.build_index()
        
        results = cache_service.search("", top_k=5)
        
        assert isinstance(results, list)
        assert len(results) == 0  # Empty query should return no results

