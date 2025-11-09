import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime

from app.services.metadata_storage_service import MetadataStorageService
from app.services.confidence_engine import ConfidenceEngine
from app.models.extraction_field_metadata import ExtractionFieldMetadata
from app.utils.engines.base_extractor import ExtractionResult


class TestMetadataStorageService:
    """Test suite for MetadataStorageService error handling"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.query = Mock()
        return session
    
    @pytest.fixture
    def mock_confidence_engine(self):
        """Create mock confidence engine"""
        engine = Mock(spec=ConfidenceEngine)
        engine.calculate_field_confidence = Mock(
            return_value=(Decimal('0.85'), 'consensus', None)
        )
        engine.should_flag_for_review = Mock(
            return_value=(False, None, None)
        )
        return engine
    
    @pytest.fixture
    def sample_extraction_results(self):
        """Create sample extraction results"""
        return [
            ExtractionResult(
                engine_name="pymupdf",
                extracted_data={"text": "Sample text"},
                success=True,
                confidence_score=Decimal('0.85'),
                processing_time_ms=100.0
            ),
            ExtractionResult(
                engine_name="pdfplumber",
                extracted_data={"tables": []},
                success=True,
                confidence_score=Decimal('0.90'),
                processing_time_ms=150.0
            )
        ]
    
    def test_save_field_metadata_success(self, mock_db_session, mock_confidence_engine, sample_extraction_results):
        """Test successful field metadata save"""
        service = MetadataStorageService(mock_db_session, mock_confidence_engine)
        
        metadata = service.save_field_metadata(
            document_id=1,
            table_name="balance_sheet_data",
            record_id=100,
            field_name="total_assets",
            extraction_results=sample_extraction_results,
            field_values=[1000, 1000]
        )
        
        assert metadata is not None
        assert metadata.document_id == 1
        assert metadata.field_name == "total_assets"
        assert mock_db_session.add.called
    
    def test_save_document_metadata_with_rollback(self, mock_db_session, mock_confidence_engine):
        """Test rollback on database error during document metadata save"""
        # Setup: Make commit raise an error
        mock_db_session.commit.side_effect = IntegrityError("mock", "params", "orig")
        
        service = MetadataStorageService(mock_db_session, mock_confidence_engine)
        
        field_metadata_list = [
            {
                'table_name': 'test_table',
                'record_id': 1,
                'field_name': 'test_field',
                'extraction_results': [],
                'field_values': []
            }
        ]
        
        # Should raise the error after rollback
        with pytest.raises(SQLAlchemyError):
            service.save_document_metadata(1, field_metadata_list)
        
        # Verify rollback was called
        assert mock_db_session.rollback.called
    
    def test_save_extraction_result_with_connection_failure(self, mock_db_session, mock_confidence_engine, sample_extraction_results):
        """Test handling of database connection failure"""
        # Setup: Make commit raise connection error
        mock_db_session.commit.side_effect = SQLAlchemyError("Connection failed")
        
        service = MetadataStorageService(mock_db_session, mock_confidence_engine)
        
        result = service.save_extraction_result_metadata(
            document_id=1,
            extraction_results=sample_extraction_results,
            extracted_records={'test_table': [{'id': 1, 'field': 'value'}]}
        )
        
        # Should return error result
        assert result["success"] == False
        assert "error" in result
        assert mock_db_session.rollback.called
    
    def test_flag_low_confidence_fields_rollback(self, mock_db_session, mock_confidence_engine):
        """Test rollback when flagging low confidence fields fails"""
        # Setup: Make commit raise an error
        mock_db_session.commit.side_effect = SQLAlchemyError("Update failed")
        
        # Mock query to return empty list
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        service = MetadataStorageService(mock_db_session, mock_confidence_engine)
        
        # Should raise error and trigger rollback
        with pytest.raises(SQLAlchemyError):
            service.flag_low_confidence_fields(document_id=1)
        
        assert mock_db_session.rollback.called
    
    def test_bulk_save_with_invalid_data(self, mock_db_session, mock_confidence_engine):
        """Test bulk save with invalid data triggers rollback"""
        # Setup: Make bulk_save_objects raise error
        mock_db_session.bulk_save_objects.side_effect = IntegrityError("mock", "params", "orig")
        
        service = MetadataStorageService(mock_db_session, mock_confidence_engine)
        
        # Create mock metadata records
        records = [Mock(spec=ExtractionFieldMetadata) for _ in range(5)]
        
        result = service.bulk_save_metadata(records)
        
        # Should return failure result
        assert result["success"] == False
        assert result["total_saved"] == 0
        assert "error" in result
        assert mock_db_session.rollback.called
    
    def test_multiple_operations_rollback_on_last_failure(self, mock_db_session, mock_confidence_engine, sample_extraction_results):
        """Test that rollback reverts all operations if last one fails"""
        # Setup: Commit fails after multiple adds
        call_count = [0]
        
        def commit_side_effect():
            call_count[0] += 1
            if call_count[0] >= 1:  # Fail on first commit
                raise SQLAlchemyError("Commit failed")
        
        mock_db_session.commit.side_effect = commit_side_effect
        
        service = MetadataStorageService(mock_db_session, mock_confidence_engine)
        
        field_metadata_list = [
            {
                'table_name': f'table_{i}',
                'record_id': i,
                'field_name': f'field_{i}',
                'extraction_results': sample_extraction_results,
                'field_values': [f'value_{i}', f'value_{i}']
            }
            for i in range(3)
        ]
        
        # Should raise error and rollback all 3 operations
        with pytest.raises(SQLAlchemyError):
            service.save_document_metadata(1, field_metadata_list)
        
        # Verify rollback called
        assert mock_db_session.rollback.called
        # Verify multiple add calls were made before failure
        assert mock_db_session.add.call_count == 3
    
    def test_get_review_statistics_error_handling(self, mock_db_session, mock_confidence_engine):
        """Test error handling in get_review_statistics"""
        # Setup: Make query raise error
        mock_db_session.query.side_effect = SQLAlchemyError("Query failed")
        
        service = MetadataStorageService(mock_db_session, mock_confidence_engine)
        
        result = service.get_review_statistics(document_id=1)
        
        # Should return error dict
        assert "error" in result
    
    def test_save_with_null_document_id(self, mock_db_session, mock_confidence_engine, sample_extraction_results):
        """Test handling of null/invalid document ID"""
        # This should eventually fail at the database level
        mock_db_session.commit.side_effect = IntegrityError("mock", "params", "orig")
        
        service = MetadataStorageService(mock_db_session, mock_confidence_engine)
        
        field_metadata_list = [
            {
                'table_name': 'test_table',
                'record_id': 1,
                'field_name': 'test_field',
                'extraction_results': sample_extraction_results,
                'field_values': ['value1', 'value2']
            }
        ]
        
        with pytest.raises(SQLAlchemyError):
            service.save_document_metadata(None, field_metadata_list)
        
        assert mock_db_session.rollback.called


# Additional integration tests would go here
# These would require a real test database

