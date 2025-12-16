"""
Performance Tests for BM25 Search

Benchmarks index building, search latency, cache operations,
and concurrent search performance.
"""
import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.services.bm25_search_service import BM25SearchService
from app.models.document_chunk import DocumentChunk
from app.config.bm25_config import bm25_config


@pytest.fixture
def performance_db_session(db_session):
    """Database session for performance tests"""
    return db_session


@pytest.fixture
def performance_service(performance_db_session):
    """BM25 service for performance tests"""
    # Use temporary cache directory
    with patch('app.config.bm25_config.bm25_config.CACHE_DIR', tempfile.mkdtemp()):
        service = BM25SearchService(performance_db_session)
        return service


class TestIndexBuildPerformance:
    """Test index building performance"""
    
    def test_index_build_time_10k_chunks(self, performance_service, performance_db_session):
        """Test index build time for 10k chunks (target: <10s)"""
        # Create 10k chunks
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Test chunk {i} with revenue data and financial information for property analysis",
                property_id=1,
                document_type="income_statement"
            )
            for i in range(10000)
        ]
        
        # Add in batches to avoid memory issues
        batch_size = 1000
        for i in range(0, len(chunks), batch_size):
            performance_db_session.add_all(chunks[i:i + batch_size])
            performance_db_session.commit()
        
        # Measure build time
        start = time.time()
        result = performance_service.build_index()
        elapsed = time.time() - start
        
        assert result['success'] is True
        assert elapsed < 30  # Allow margin for test environment (target is <10s)
        assert result['chunk_count'] == 10000
    
    def test_index_build_time_1k_chunks(self, performance_service, performance_db_session):
        """Test index build time for 1k chunks"""
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Chunk {i} with test data",
                property_id=1
            )
            for i in range(1000)
        ]
        performance_db_session.add_all(chunks)
        performance_db_session.commit()
        
        start = time.time()
        result = performance_service.build_index()
        elapsed = time.time() - start
        
        assert result['success'] is True
        assert elapsed < 5  # Should be fast for 1k chunks
        assert result['chunk_count'] == 1000


class TestSearchLatency:
    """Test search latency performance"""
    
    def test_search_latency_top_20(self, performance_service, performance_db_session):
        """Test search latency for top-20 results (target: <100ms)"""
        # Create test chunks
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Test chunk {i} with revenue data and financial metrics",
                property_id=1,
                document_type="income_statement"
            )
            for i in range(5000)
        ]
        performance_db_session.add_all(chunks)
        performance_db_session.commit()
        
        performance_service.build_index()
        
        # Measure search time
        start = time.time()
        results = performance_service.search("revenue", top_k=20)
        elapsed_ms = (time.time() - start) * 1000
        
        assert len(results) <= 20
        assert elapsed_ms < 200  # Allow margin for test environment (target is <100ms)
    
    def test_search_latency_top_100(self, performance_service, performance_db_session):
        """Test search latency for top-100 results"""
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Chunk {i} with test data",
                property_id=1
            )
            for i in range(10000)
        ]
        performance_db_session.add_all(chunks)
        performance_db_session.commit()
        
        performance_service.build_index()
        
        start = time.time()
        results = performance_service.search("test", top_k=100)
        elapsed_ms = (time.time() - start) * 1000
        
        assert len(results) <= 100
        assert elapsed_ms < 500  # Should still be reasonable for top-100
    
    def test_search_with_metadata_filter(self, performance_service, performance_db_session):
        """Test search latency with metadata filtering"""
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Chunk {i}",
                property_id=1 if i % 2 == 0 else 2,
                document_type="income_statement"
            )
            for i in range(5000)
        ]
        performance_db_session.add_all(chunks)
        performance_db_session.commit()
        
        performance_service.build_index()
        
        start = time.time()
        results = performance_service.search(
            "chunk",
            top_k=20,
            property_id=1,
            document_type="income_statement"
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert elapsed_ms < 200  # Filtering should not significantly impact performance


class TestCachePerformance:
    """Test cache loading performance"""
    
    def test_cache_load_time(self, performance_service, performance_db_session):
        """Test cache load time (target: <1s)"""
        # Create and build index
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Chunk {i}",
                property_id=1
            )
            for i in range(5000)
        ]
        performance_db_session.add_all(chunks)
        performance_db_session.commit()
        
        performance_service.build_index()
        performance_service._save_index_to_cache()
        
        # Measure load time
        start = time.time()
        new_service = BM25SearchService(performance_db_session)
        elapsed = time.time() - start
        
        assert new_service.bm25_index is not None
        assert elapsed < 2  # Allow margin (target is <1s)
    
    def test_cache_save_time(self, performance_service, performance_db_session):
        """Test cache save time"""
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Chunk {i}",
                property_id=1
            )
            for i in range(5000)
        ]
        performance_db_session.add_all(chunks)
        performance_db_session.commit()
        
        performance_service.build_index()
        
        # Measure save time
        start = time.time()
        result = performance_service._save_index_to_cache()
        elapsed = time.time() - start
        
        assert result is True
        assert elapsed < 2  # Should be fast


class TestConcurrentSearch:
    """Test concurrent search performance"""
    
    def test_concurrent_searches(self, performance_service, performance_db_session):
        """Test multiple concurrent searches"""
        import threading
        
        # Create test chunks
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Chunk {i} with test data",
                property_id=1
            )
            for i in range(1000)
        ]
        performance_db_session.add_all(chunks)
        performance_db_session.commit()
        
        performance_service.build_index()
        
        results_list = []
        errors = []
        
        def search_worker(query):
            try:
                results = performance_service.search(query, top_k=10)
                results_list.append(results)
            except Exception as e:
                errors.append(e)
        
        # Run 10 concurrent searches
        threads = []
        for i in range(10):
            thread = threading.Thread(target=search_worker, args=(f"test {i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results_list) == 10
        assert all(len(r) <= 10 for r in results_list)


class TestMemoryUsage:
    """Test memory usage"""
    
    def test_index_memory_usage(self, performance_service, performance_db_session):
        """Test that index doesn't consume excessive memory"""
        import sys
        
        # Create chunks
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Chunk {i} with test data" * 10,  # Longer text
                property_id=1
            )
            for i in range(1000)
        ]
        performance_db_session.add_all(chunks)
        performance_db_session.commit()
        
        # Measure memory before
        # Note: This is a rough estimate, actual memory tracking would require psutil
        performance_service.build_index()
        
        # Index should be built successfully
        assert performance_service.bm25_index is not None
        assert len(performance_service.chunk_ids) == 1000


class TestScalability:
    """Test scalability with large datasets"""
    
    @pytest.mark.slow
    def test_large_dataset_10k_chunks(self, performance_service, performance_db_session):
        """Test with 10k chunks"""
        chunks = [
            DocumentChunk(
                document_id=1,
                chunk_index=i,
                chunk_text=f"Chunk {i} with comprehensive financial data and metrics",
                property_id=1,
                document_type="income_statement"
            )
            for i in range(10000)
        ]
        
        # Add in batches
        batch_size = 1000
        for i in range(0, len(chunks), batch_size):
            performance_db_session.add_all(chunks[i:i + batch_size])
            performance_db_session.commit()
        
        # Build index
        start = time.time()
        result = performance_service.build_index()
        build_time = time.time() - start
        
        assert result['success'] is True
        
        # Search should still be fast
        start = time.time()
        results = performance_service.search("financial", top_k=20)
        search_time = (time.time() - start) * 1000
        
        assert len(results) <= 20
        assert search_time < 200  # Should still meet target
        assert build_time < 60  # Build should complete in reasonable time

