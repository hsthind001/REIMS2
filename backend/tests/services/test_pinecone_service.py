"""
Unit Tests for Pinecone Service

Tests vector operations, namespace management, and error handling
using mocked Pinecone client.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from typing import List, Dict, Any

from app.services.pinecone_service import PineconeService
from app.models.document_chunk import DocumentChunk


@pytest.fixture
def mock_pinecone_config():
    """Mock Pinecone configuration"""
    with patch('app.services.pinecone_service.pinecone_config') as mock_config:
        mock_config.is_initialized.return_value = True
        mock_config.index = MagicMock()
        yield mock_config


@pytest.fixture
def mock_index():
    """Mock Pinecone index"""
    index = MagicMock()
    
    # Mock describe_index_stats
    index.describe_index_stats.return_value = {
        'total_vector_count': 100,
        'namespaces': {
            'balance_sheet': {'vector_count': 50},
            'income_statement': {'vector_count': 30},
            '': {'vector_count': 20}  # Default namespace
        }
    }
    
    # Mock query
    index.query.return_value = {
        'matches': [
            {
                'id': 'chunk_1',
                'score': 0.95,
                'metadata': {'property_id': 1, 'document_type': 'balance_sheet'}
            },
            {
                'id': 'chunk_2',
                'score': 0.87,
                'metadata': {'property_id': 1, 'document_type': 'balance_sheet'}
            }
        ]
    }
    
    # Mock fetch
    index.fetch.return_value = {
        'vectors': {
            'chunk_1': {
                'id': 'chunk_1',
                'values': [0.1] * 1536,
                'metadata': {'property_id': 1}
            }
        }
    }
    
    # Mock upsert
    index.upsert.return_value = None
    
    # Mock delete
    index.delete.return_value = None
    
    return index


@pytest.fixture
def pinecone_service(mock_pinecone_config, mock_index, db_session):
    """Create PineconeService instance with mocked dependencies"""
    mock_pinecone_config.index = mock_index
    
    with patch('app.services.pinecone_service.pinecone_config', mock_pinecone_config):
        service = PineconeService(db=db_session)
        service.pinecone_config = mock_pinecone_config
        return service


class TestPineconeServiceInitialization:
    """Test Pinecone service initialization"""
    
    def test_service_initialization(self, pinecone_service):
        """Test service initializes correctly"""
        assert pinecone_service is not None
        assert pinecone_service.db is not None
    
    def test_namespace_mapping(self, pinecone_service):
        """Test document type to namespace mapping"""
        assert pinecone_service._get_namespace('balance_sheet') == 'balance_sheet'
        assert pinecone_service._get_namespace('income_statement') == 'income_statement'
        assert pinecone_service._get_namespace('cash_flow') == 'cash_flow'
        assert pinecone_service._get_namespace('rent_roll') == 'rent_roll'
        assert pinecone_service._get_namespace('unknown') == ''
        assert pinecone_service._get_namespace(None) == ''
    
    def test_vector_id_building(self, pinecone_service):
        """Test vector ID generation"""
        assert pinecone_service._build_vector_id(123) == 'chunk_123'
        assert pinecone_service._build_vector_id(0) == 'chunk_0'


class TestVectorUpsert:
    """Test vector upsert operations"""
    
    def test_upsert_single_vector(self, pinecone_service, mock_index):
        """Test upserting a single vector"""
        vector = {
            'id': 'chunk_1',
            'values': [0.1] * 1536,
            'metadata': {'property_id': 1}
        }
        
        result = pinecone_service.upsert_vectors([vector])
        
        assert result['success'] is True
        assert result['upserted'] == 1
        mock_index.upsert.assert_called_once()
    
    def test_upsert_batch_vectors(self, pinecone_service, mock_index):
        """Test batch upsert"""
        vectors = [
            {
                'id': f'chunk_{i}',
                'values': [0.1] * 1536,
                'metadata': {'property_id': 1}
            }
            for i in range(5)
        ]
        
        result = pinecone_service.upsert_vectors(vectors)
        
        assert result['success'] is True
        assert result['upserted'] == 5
        mock_index.upsert.assert_called_once()
    
    def test_upsert_with_namespace(self, pinecone_service, mock_index):
        """Test upsert with namespace"""
        vector = {
            'id': 'chunk_1',
            'values': [0.1] * 1536,
            'metadata': {'document_type': 'balance_sheet'}
        }
        
        result = pinecone_service.upsert_vectors([vector], namespace='balance_sheet')
        
        assert result['success'] is True
        assert result['namespace'] == 'balance_sheet'
        # Verify namespace was passed to upsert
        call_args = mock_index.upsert.call_args
        assert call_args[1]['namespace'] == 'balance_sheet'
    
    def test_upsert_invalid_vector(self, pinecone_service):
        """Test upsert with invalid vector (missing id or values)"""
        invalid_vectors = [
            {'id': 'chunk_1'},  # Missing values
            {'values': [0.1] * 1536},  # Missing id
        ]
        
        result = pinecone_service.upsert_vectors(invalid_vectors)
        
        assert result['success'] is False
        assert result['error'] == "No valid vectors to upsert"
    
    def test_upsert_empty_list(self, pinecone_service):
        """Test upsert with empty list"""
        result = pinecone_service.upsert_vectors([])
        
        assert result['success'] is True
        assert result['upserted'] == 0
        assert 'message' in result


class TestVectorQuery:
    """Test vector query operations"""
    
    def test_query_vectors(self, pinecone_service, mock_index):
        """Test querying vectors"""
        query_vector = [0.1] * 1536
        
        result = pinecone_service.query_vectors(
            query_vector=query_vector,
            top_k=5
        )
        
        assert result['success'] is True
        assert len(result['matches']) == 2
        assert result['matches'][0]['score'] == 0.95
        mock_index.query.assert_called_once()
    
    def test_query_with_filter(self, pinecone_service, mock_index):
        """Test query with metadata filter"""
        query_vector = [0.1] * 1536
        filter_dict = {'property_id': 1, 'document_type': 'balance_sheet'}
        
        result = pinecone_service.query_vectors(
            query_vector=query_vector,
            top_k=5,
            filter=filter_dict
        )
        
        assert result['success'] is True
        # Verify filter was passed
        call_args = mock_index.query.call_args
        assert call_args[1]['filter'] is not None
    
    def test_query_with_namespace(self, pinecone_service, mock_index):
        """Test query with namespace"""
        query_vector = [0.1] * 1536
        
        result = pinecone_service.query_vectors(
            query_vector=query_vector,
            top_k=5,
            namespace='balance_sheet'
        )
        
        assert result['success'] is True
        call_args = mock_index.query.call_args
        assert call_args[1]['namespace'] == 'balance_sheet'
    
    def test_query_include_metadata(self, pinecone_service, mock_index):
        """Test query with metadata included"""
        query_vector = [0.1] * 1536
        
        result = pinecone_service.query_vectors(
            query_vector=query_vector,
            top_k=5,
            include_metadata=True
        )
        
        assert result['success'] is True
        assert 'metadata' in result['matches'][0]
    
    def test_build_filter_expression(self, pinecone_service):
        """Test filter expression building"""
        filter_dict = {
            'property_id': 1,
            'document_type': 'balance_sheet',
            'period_year': [2023, 2024]
        }
        
        filter_expr = pinecone_service._build_filter_expression(filter_dict)
        
        assert filter_expr['property_id'] == {'$eq': 1}
        assert filter_expr['document_type'] == {'$eq': 'balance_sheet'}
        assert filter_expr['period_year'] == {'$in': [2023, 2024]}


class TestVectorDelete:
    """Test vector delete operations"""
    
    def test_delete_by_ids(self, pinecone_service, mock_index):
        """Test deleting vectors by IDs"""
        vector_ids = ['chunk_1', 'chunk_2']
        
        result = pinecone_service.delete_vectors(vector_ids=vector_ids)
        
        assert result['success'] is True
        assert result['deleted'] == 2
        mock_index.delete.assert_called_once_with(ids=vector_ids, namespace='')
    
    def test_delete_by_filter(self, pinecone_service, mock_index):
        """Test deleting vectors by metadata filter"""
        filter_dict = {'property_id': 1}
        
        result = pinecone_service.delete_vectors(filter=filter_dict)
        
        assert result['success'] is True
        assert result['deleted'] == 'filtered'
        call_args = mock_index.delete.call_args
        assert 'filter' in call_args[1]
    
    def test_delete_all_in_namespace(self, pinecone_service, mock_index):
        """Test deleting all vectors in namespace"""
        result = pinecone_service.delete_vectors(
            namespace='balance_sheet',
            delete_all=True
        )
        
        assert result['success'] is True
        assert result['deleted'] == 'all'
        call_args = mock_index.delete.call_args
        assert call_args[1]['delete_all'] is True
        assert call_args[1]['namespace'] == 'balance_sheet'
    
    def test_delete_all_requires_namespace(self, pinecone_service):
        """Test that delete_all requires a namespace"""
        result = pinecone_service.delete_vectors(delete_all=True)
        
        assert result['success'] is False
        assert 'namespace' in result['error']
    
    def test_delete_chunk(self, pinecone_service, mock_index):
        """Test deleting a chunk"""
        result = pinecone_service.delete_chunk(
            chunk_id=123,
            document_type='balance_sheet'
        )
        
        assert result['success'] is True
        call_args = mock_index.delete.call_args
        assert call_args[1]['ids'] == ['chunk_123']
        assert call_args[1]['namespace'] == 'balance_sheet'


class TestMetadataUpdate:
    """Test metadata update operations"""
    
    def test_update_metadata(self, pinecone_service, mock_index):
        """Test updating vector metadata"""
        vector_id = 'chunk_1'
        new_metadata = {'property_id': 2}
        
        result = pinecone_service.update_metadata(
            vector_id=vector_id,
            metadata=new_metadata
        )
        
        assert result['success'] is True
        # Verify fetch was called
        mock_index.fetch.assert_called_once()
        # Verify upsert was called with updated metadata
        mock_index.upsert.assert_called_once()
    
    def test_update_metadata_vector_not_found(self, pinecone_service, mock_index):
        """Test updating metadata for non-existent vector"""
        mock_index.fetch.return_value = {'vectors': {}}
        
        result = pinecone_service.update_metadata(
            vector_id='chunk_999',
            metadata={'property_id': 1}
        )
        
        assert result['success'] is False
        assert 'not found' in result['error'].lower()


class TestIndexStats:
    """Test index statistics"""
    
    def test_get_index_stats(self, pinecone_service, mock_index):
        """Test getting index statistics"""
        result = pinecone_service.get_index_stats()
        
        assert result['success'] is True
        assert result['total_vector_count'] == 100
        assert 'namespaces' in result
    
    def test_get_namespace_stats(self, pinecone_service, mock_index):
        """Test getting namespace-specific statistics"""
        result = pinecone_service.get_index_stats(namespace='balance_sheet')
        
        assert result['success'] is True
        assert result['namespace'] == 'balance_sheet'
        assert result['vector_count'] == 50


class TestChunkOperations:
    """Test chunk-specific operations"""
    
    def test_upsert_chunk(self, pinecone_service, mock_index):
        """Test upserting a single chunk"""
        result = pinecone_service.upsert_chunk(
            chunk_id=123,
            embedding=[0.1] * 1536,
            property_id=1,
            document_type='balance_sheet',
            period_year=2024,
            period_month=1,
            document_id=10,
            chunk_index=0
        )
        
        assert result['success'] is True
        assert result['upserted'] == 1
        # Verify upsert was called with correct namespace
        call_args = mock_index.upsert.call_args
        assert call_args[1]['namespace'] == 'balance_sheet'
    
    def test_upsert_chunks_batch(self, pinecone_service, mock_index, db_session):
        """Test batch upsert of chunks"""
        from app.models.financial_period import FinancialPeriod
        
        # Create mock chunks
        chunks = []
        embeddings = []
        for i in range(3):
            chunk = DocumentChunk()
            chunk.id = i + 1
            chunk.document_id = 1
            chunk.chunk_index = i
            chunk.chunk_text = f"Chunk {i}"
            chunk.property_id = 1
            chunk.document_type = 'balance_sheet'
            chunk.period_id = 1
            chunk.period = FinancialPeriod()
            chunk.period.period_year = 2024
            chunk.period.period_month = 1
            chunks.append(chunk)
            embeddings.append([0.1] * 1536)
        
        result = pinecone_service.upsert_chunks_batch(chunks, embeddings)
        
        assert result['success'] is True
        assert result['total_chunks'] == 3
        assert 'balance_sheet' in result['namespaces']


class TestErrorHandling:
    """Test error handling and retries"""
    
    def test_upsert_handles_exception(self, pinecone_service, mock_index):
        """Test upsert handles exceptions gracefully"""
        mock_index.upsert.side_effect = Exception("Connection error")
        
        vector = {
            'id': 'chunk_1',
            'values': [0.1] * 1536
        }
        
        result = pinecone_service.upsert_vectors([vector])
        
        assert result['success'] is False
        assert 'error' in result
    
    def test_query_handles_exception(self, pinecone_service, mock_index):
        """Test query handles exceptions gracefully"""
        mock_index.query.side_effect = Exception("Query error")
        
        result = pinecone_service.query_vectors(
            query_vector=[0.1] * 1536,
            top_k=5
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert result['matches'] == []
    
    def test_delete_handles_exception(self, pinecone_service, mock_index):
        """Test delete handles exceptions gracefully"""
        mock_index.delete.side_effect = Exception("Delete error")
        
        result = pinecone_service.delete_vectors(vector_ids=['chunk_1'])
        
        assert result['success'] is False
        assert 'error' in result


class TestMetadataBuilding:
    """Test metadata building utilities"""
    
    def test_build_metadata(self, pinecone_service):
        """Test building metadata dictionary"""
        metadata = pinecone_service._build_metadata(
            property_id=1,
            document_type='balance_sheet',
            period_year=2024,
            period_month=1,
            document_id=10,
            chunk_index=0
        )
        
        assert metadata['property_id'] == 1
        assert metadata['document_type'] == 'balance_sheet'
        assert metadata['period_year'] == 2024
        assert metadata['period_month'] == 1
        assert metadata['document_id'] == 10
        assert metadata['chunk_index'] == 0
    
    def test_build_metadata_with_additional(self, pinecone_service):
        """Test building metadata with additional fields"""
        additional = {'custom_field': 'value'}
        
        metadata = pinecone_service._build_metadata(
            property_id=1,
            additional_metadata=additional
        )
        
        assert metadata['property_id'] == 1
        assert metadata['custom_field'] == 'value'
    
    def test_build_metadata_handles_none(self, pinecone_service):
        """Test building metadata handles None values"""
        metadata = pinecone_service._build_metadata()
        
        # Should not include None values
        assert 'property_id' not in metadata
        assert 'document_type' not in metadata

