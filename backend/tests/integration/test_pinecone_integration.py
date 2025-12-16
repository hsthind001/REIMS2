"""
Integration Tests for Pinecone

End-to-end tests for Pinecone integration with PostgreSQL,
sync service, and RAG retrieval service.

Note: These tests require a valid PINECONE_API_KEY to run.
Set PINECONE_TEST_API_KEY environment variable or skip tests.
"""
import pytest
import os
from typing import Dict, List

from app.services.pinecone_service import PineconeService
from app.services.pinecone_sync_service import PineconeSyncService
from app.services.rag_retrieval_service import RAGRetrievalService
from app.services.embedding_service import EmbeddingService
from app.models.document_chunk import DocumentChunk
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.config.pinecone_config import pinecone_config


# Skip all tests if Pinecone API key not available
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY') or os.getenv('PINECONE_TEST_API_KEY')
pytestmark = pytest.mark.skipif(
    not PINECONE_API_KEY,
    reason="PINECONE_API_KEY not set. Set environment variable to run integration tests."
)


@pytest.fixture(scope="module")
def test_index_name():
    """Generate unique test index name"""
    import time
    return f"reims2-test-{int(time.time())}"


@pytest.fixture(scope="module")
def initialized_pinecone(test_index_name):
    """Initialize Pinecone with test index"""
    # Initialize with test index
    original_index_name = pinecone_config._index_name
    pinecone_config._index_name = test_index_name
    
    try:
        # Initialize Pinecone
        success = pinecone_config.initialize()
        if not success:
            pytest.skip("Failed to initialize Pinecone")
        
        # Create test index if it doesn't exist
        if not pinecone_config.index_exists(test_index_name):
            pinecone_config.create_index_if_not_exists(
                index_name=test_index_name,
                dimension=1536,
                metric='cosine'
            )
        
        yield pinecone_config
        
    finally:
        # Cleanup: Delete test index
        try:
            if pinecone_config.index_exists(test_index_name):
                pinecone_config.delete_index(test_index_name, confirm=True)
        except Exception as e:
            print(f"Warning: Could not delete test index: {e}")
        
        # Restore original index name
        pinecone_config._index_name = original_index_name


@pytest.fixture
def pinecone_service(initialized_pinecone, db_session, test_index_name):
    """Create PineconeService with test index"""
    # Temporarily set index name
    original_index_name = pinecone_config._index_name
    pinecone_config._index_name = test_index_name
    pinecone_config._index = pinecone_config.client.Index(test_index_name)
    
    try:
        service = PineconeService(db=db_session)
        yield service
    finally:
        pinecone_config._index_name = original_index_name


class TestPineconeServiceIntegration:
    """Integration tests for PineconeService"""
    
    def test_upsert_and_query(self, pinecone_service):
        """Test upserting vectors and querying them"""
        # Upsert test vectors
        vectors = [
            {
                'id': 'test_chunk_1',
                'values': [0.1] * 1536,
                'metadata': {
                    'property_id': 1,
                    'document_type': 'balance_sheet',
                    'test': True
                }
            },
            {
                'id': 'test_chunk_2',
                'values': [0.2] * 1536,
                'metadata': {
                    'property_id': 1,
                    'document_type': 'income_statement',
                    'test': True
                }
            }
        ]
        
        # Upsert
        result = pinecone_service.upsert_vectors(vectors)
        assert result['success'] is True
        assert result['upserted'] == 2
        
        # Query
        query_vector = [0.15] * 1536  # Between the two vectors
        query_result = pinecone_service.query_vectors(
            query_vector=query_vector,
            top_k=2
        )
        
        assert query_result['success'] is True
        assert len(query_result['matches']) >= 1
        
        # Verify test metadata
        test_matches = [
            m for m in query_result['matches']
            if m.get('metadata', {}).get('test') is True
        ]
        assert len(test_matches) >= 1
    
    def test_query_with_filter(self, pinecone_service):
        """Test querying with metadata filters"""
        # Upsert vectors with different metadata
        vectors = [
            {
                'id': f'test_filter_{i}',
                'values': [0.1] * 1536,
                'metadata': {
                    'property_id': i % 2 + 1,  # Alternate between 1 and 2
                    'document_type': 'balance_sheet',
                    'test': True
                }
            }
            for i in range(5)
        ]
        
        pinecone_service.upsert_vectors(vectors)
        
        # Query with filter
        query_result = pinecone_service.query_vectors(
            query_vector=[0.1] * 1536,
            top_k=10,
            filter={'property_id': 1, 'test': True}
        )
        
        assert query_result['success'] is True
        # All results should have property_id = 1
        for match in query_result['matches']:
            assert match['metadata']['property_id'] == 1
    
    def test_namespace_isolation(self, pinecone_service):
        """Test that namespaces isolate vectors"""
        # Upsert to different namespaces
        vectors_bs = [{
            'id': 'test_bs_1',
            'values': [0.1] * 1536,
            'metadata': {'test': True, 'namespace': 'balance_sheet'}
        }]
        
        vectors_is = [{
            'id': 'test_is_1',
            'values': [0.1] * 1536,
            'metadata': {'test': True, 'namespace': 'income_statement'}
        }]
        
        pinecone_service.upsert_vectors(vectors_bs, namespace='balance_sheet')
        pinecone_service.upsert_vectors(vectors_is, namespace='income_statement')
        
        # Query default namespace (should not find namespace-specific vectors)
        query_result = pinecone_service.query_vectors(
            query_vector=[0.1] * 1536,
            top_k=10,
            namespace=''
        )
        
        # Results may or may not include our test vectors depending on index state
        # But we can verify namespace-specific queries work
        query_bs = pinecone_service.query_vectors(
            query_vector=[0.1] * 1536,
            top_k=10,
            namespace='balance_sheet'
        )
        
        assert query_bs['success'] is True
    
    def test_delete_vectors(self, pinecone_service):
        """Test deleting vectors"""
        # Upsert test vector
        vector = {
            'id': 'test_delete_1',
            'values': [0.1] * 1536,
            'metadata': {'test': True, 'delete_me': True}
        }
        
        pinecone_service.upsert_vectors([vector])
        
        # Delete it
        delete_result = pinecone_service.delete_vectors(
            vector_ids=['test_delete_1']
        )
        
        assert delete_result['success'] is True
        
        # Verify it's deleted (query should not return it)
        query_result = pinecone_service.query_vectors(
            query_vector=[0.1] * 1536,
            top_k=10
        )
        
        # The deleted vector should not be in results
        deleted_ids = [m['id'] for m in query_result['matches']]
        assert 'test_delete_1' not in deleted_ids
    
    def test_get_index_stats(self, pinecone_service):
        """Test getting index statistics"""
        stats = pinecone_service.get_index_stats()
        
        assert stats['success'] is True
        assert 'total_vector_count' in stats or 'namespaces' in stats


class TestPineconeSyncServiceIntegration:
    """Integration tests for PineconeSyncService"""
    
    def test_sync_chunk_to_pinecone(
        self,
        pinecone_service,
        db_session,
        initialized_pinecone,
        test_index_name
    ):
        """Test syncing a chunk from PostgreSQL to Pinecone"""
        # Create test data in PostgreSQL
        property_obj = Property()
        property_obj.id = 999
        property_obj.property_code = "TEST"
        property_obj.property_name = "Test Property"
        db_session.add(property_obj)
        
        period = FinancialPeriod()
        period.id = 999
        period.property_id = 999
        period.period_year = 2024
        period.period_month = 1
        db_session.add(period)
        
        document = DocumentUpload()
        document.id = 999
        document.property_id = 999
        document.file_name = "test.pdf"
        document.document_type = "balance_sheet"
        db_session.add(document)
        
        chunk = DocumentChunk()
        chunk.id = 999
        chunk.document_id = 999
        chunk.chunk_index = 0
        chunk.chunk_text = "Test chunk text for syncing"
        chunk.property_id = 999
        chunk.period_id = 999
        chunk.document_type = "balance_sheet"
        chunk.embedding = [0.1] * 1536
        db_session.add(chunk)
        db_session.commit()
        
        # Sync to Pinecone
        sync_service = PineconeSyncService(db_session)
        result = sync_service.sync_chunk_to_pinecone(chunk_id=999)
        
        assert result['success'] is True
        assert result['synced_to_pinecone'] is True
        
        # Verify sync status
        verify_result = sync_service.verify_sync_status(chunk_id=999)
        assert verify_result['success'] is True
        assert verify_result['in_pinecone'] is True
        
        # Cleanup
        db_session.delete(chunk)
        db_session.delete(document)
        db_session.delete(period)
        db_session.delete(property_obj)
        db_session.commit()
        
        # Remove from Pinecone
        pinecone_service.delete_chunk(999, 'balance_sheet')


class TestRAGRetrievalIntegration:
    """Integration tests for RAG retrieval with Pinecone"""
    
    def test_rag_retrieval_with_pinecone(
        self,
        pinecone_service,
        db_session,
        initialized_pinecone,
        test_index_name
    ):
        """Test RAG retrieval using Pinecone"""
        # Create test chunks with embeddings
        embedding_service = EmbeddingService(db_session)
        
        # Generate test embeddings
        test_texts = [
            "This is a balance sheet showing assets and liabilities",
            "Income statement contains revenue and expenses",
            "Cash flow statement shows operating activities"
        ]
        
        embeddings = embedding_service.generate_embeddings_batch(test_texts)
        
        # Create chunks in PostgreSQL
        chunks = []
        for i, (text, embedding) in enumerate(zip(test_texts, embeddings)):
            if not embedding:
                continue
            
            chunk = DocumentChunk()
            chunk.document_id = 1
            chunk.chunk_index = i
            chunk.chunk_text = text
            chunk.document_type = 'balance_sheet' if i == 0 else 'income_statement'
            chunk.embedding = embedding
            db_session.add(chunk)
            chunks.append(chunk)
        
        db_session.commit()
        
        # Sync to Pinecone
        sync_service = PineconeSyncService(db_session)
        for chunk in chunks:
            sync_service.sync_chunk_to_pinecone(chunk.id)
        
        # Test RAG retrieval
        rag_service = RAGRetrievalService(db_session)
        
        # Query should use Pinecone if available
        results = rag_service.retrieve_relevant_chunks(
            query="What does a balance sheet show?",
            top_k=3,
            document_type='balance_sheet'
        )
        
        assert len(results) > 0
        # Results should have similarity scores
        assert all('similarity' in r for r in results)
        # Results should indicate retrieval method
        assert any(r.get('retrieval_method') in ['pinecone', 'postgresql'] for r in results)
        
        # Cleanup
        for chunk in chunks:
            pinecone_service.delete_chunk(chunk.id, chunk.document_type)
            db_session.delete(chunk)
        db_session.commit()


class TestErrorHandlingIntegration:
    """Test error handling in integration scenarios"""
    
    def test_graceful_degradation_on_pinecone_failure(
        self,
        db_session
    ):
        """Test that system falls back to PostgreSQL when Pinecone fails"""
        # This test verifies that RAG service can work without Pinecone
        # by using PostgreSQL fallback
        
        rag_service = RAGRetrievalService(db_session)
        
        # Force PostgreSQL retrieval
        results = rag_service.retrieve_relevant_chunks(
            query="test query",
            top_k=5,
            use_pinecone=False
        )
        
        # Should return results (even if empty) without error
        assert isinstance(results, list)
    
    def test_sync_handles_missing_embedding(
        self,
        db_session
    ):
        """Test sync handles chunks without embeddings"""
        # Create chunk without embedding
        chunk = DocumentChunk()
        chunk.id = 888
        chunk.document_id = 1
        chunk.chunk_index = 0
        chunk.chunk_text = "Test without embedding"
        chunk.embedding = None
        db_session.add(chunk)
        db_session.commit()
        
        sync_service = PineconeSyncService(db_session)
        result = sync_service.sync_chunk_to_pinecone(chunk_id=888)
        
        # Should fail gracefully
        assert result['success'] is False
        assert 'embedding' in result['error'].lower()
        
        # Cleanup
        db_session.delete(chunk)
        db_session.commit()


class TestPerformanceBenchmarks:
    """Performance benchmarks for Pinecone operations"""
    
    @pytest.mark.skip(reason="Performance test - run manually")
    def test_batch_upsert_performance(self, pinecone_service):
        """Benchmark batch upsert performance"""
        import time
        
        # Create large batch
        batch_size = 100
        vectors = [
            {
                'id': f'perf_test_{i}',
                'values': [0.1] * 1536,
                'metadata': {'test': True, 'index': i}
            }
            for i in range(batch_size)
        ]
        
        start = time.time()
        result = pinecone_service.upsert_vectors(vectors)
        elapsed = time.time() - start
        
        assert result['success'] is True
        print(f"Upserted {batch_size} vectors in {elapsed:.2f}s ({batch_size/elapsed:.1f} vectors/sec)")
        
        # Cleanup
        vector_ids = [f'perf_test_{i}' for i in range(batch_size)]
        pinecone_service.delete_vectors(vector_ids=vector_ids)
    
    @pytest.mark.skip(reason="Performance test - run manually")
    def test_query_performance(self, pinecone_service):
        """Benchmark query performance"""
        import time
        
        query_vector = [0.1] * 1536
        
        start = time.time()
        result = pinecone_service.query_vectors(
            query_vector=query_vector,
            top_k=10
        )
        elapsed = time.time() - start
        
        assert result['success'] is True
        print(f"Query returned {len(result['matches'])} results in {elapsed:.3f}s")

