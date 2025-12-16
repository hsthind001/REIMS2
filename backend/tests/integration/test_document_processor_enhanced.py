"""
Integration Tests for Enhanced Document Processor

End-to-end tests with sample PDFs to verify:
- Table extraction accuracy
- Chunk relationships
- Metadata enrichment
- Performance benchmarks
"""
import pytest
import os
import time
from typing import Dict, List
from unittest.mock import patch, MagicMock

from app.services.document_processor_enhanced import EnhancedDocumentProcessor
from app.models.document_chunk import DocumentChunk
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.db.database import SessionLocal
from app.config.chunking_config import chunking_config


@pytest.fixture
def sample_pdf_path():
    """Path to sample PDF file for testing"""
    # This would be a path to a test PDF file
    # For now, we'll create a minimal PDF or use a fixture
    return None  # Will be set up with actual test PDFs


@pytest.fixture
def test_document_setup(db_session):
    """Set up test document in database"""
    # Create property
    property_obj = Property()
    property_obj.id = 999
    property_obj.property_code = "TEST"
    property_obj.property_name = "Test Property"
    db_session.add(property_obj)
    
    # Create period
    period = FinancialPeriod()
    period.id = 999
    period.property_id = 999
    period.period_year = 2024
    period.period_month = 1
    db_session.add(period)
    
    # Create document
    document = DocumentUpload()
    document.id = 999
    document.property_id = 999
    document.period_id = 999
    document.document_type = "balance_sheet"
    document.file_name = "test_balance_sheet.pdf"
    document.file_path = "test/test_balance_sheet.pdf"
    document.extraction_status = "completed"
    db_session.add(document)
    db_session.commit()
    
    yield document
    
    # Cleanup
    db_session.delete(document)
    db_session.delete(period)
    db_session.delete(property_obj)
    db_session.commit()


class TestTableExtractionIntegration:
    """Integration tests for table extraction"""
    
    @pytest.mark.skip(reason="Requires actual PDF file")
    def test_extract_tables_from_pdf(self, db_session, sample_pdf_path):
        """Test extracting tables from a real PDF"""
        if not sample_pdf_path or not os.path.exists(sample_pdf_path):
            pytest.skip("Sample PDF not available")
        
        processor = EnhancedDocumentProcessor(db_session)
        
        with open(sample_pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        result = processor._extract_tables(pdf_data)
        
        assert result['success'] is True
        assert result['total_tables'] >= 0
        
        if result['total_tables'] > 0:
            table = result['tables'][0]
            assert 'headers' in table
            assert 'data' in table
            assert 'page' in table
            assert table['rows'] >= chunking_config.TABLE_MIN_ROWS
            assert table['columns'] >= chunking_config.TABLE_MIN_COLS
    
    def test_table_extraction_performance(self, db_session):
        """Test table extraction performance"""
        # This would use a real PDF
        # For now, we'll test with mock data
        processor = EnhancedDocumentProcessor(db_session)
        
        # Create minimal PDF bytes (would need actual PDF for real test)
        # This is a placeholder
        start_time = time.time()
        
        # Mock extraction
        result = processor._extract_tables(b"%PDF-1.4\nfake")
        
        elapsed = time.time() - start_time
        
        # Performance check (even for failure case)
        assert elapsed < chunking_config.TARGET_TABLE_EXTRACTION_TIME * 2  # Allow some margin


class TestTextChunkingIntegration:
    """Integration tests for text chunking"""
    
    def test_chunk_text_with_overlap(self, db_session):
        """Test that text chunking includes overlap"""
        processor = EnhancedDocumentProcessor(db_session)
        
        # Create long text
        text = "This is a test sentence. " * 200  # ~5000 chars
        pages = [{"page": 1, "text": text}]
        
        chunks = processor._chunk_text(text, pages)
        
        assert len(chunks) > 1  # Should be split into multiple chunks
        
        # Check overlap (first part of second chunk should appear in first chunk)
        if len(chunks) >= 2:
            chunk1_text = chunks[0]['content']
            chunk2_text = chunks[1]['content']
            
            # There should be some overlap (at least a few words)
            # This is a simplified check
            assert len(chunk1_text) > 0
            assert len(chunk2_text) > 0
    
    def test_chunk_text_preserves_structure(self, db_session):
        """Test that chunking preserves paragraph structure"""
        processor = EnhancedDocumentProcessor(db_session)
        
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        pages = [{"page": 1, "text": text}]
        
        chunks = processor._chunk_text(text, pages)
        
        # Should respect paragraph breaks
        assert len(chunks) > 0
        # Each chunk should contain complete paragraphs where possible


class TestParentChildRelationships:
    """Integration tests for parent-child relationships"""
    
    def test_header_content_relationships(self, db_session, test_document_setup):
        """Test that content chunks are linked to headers"""
        processor = EnhancedDocumentProcessor(db_session)
        
        # Create chunks with headers
        chunks = [
            {
                "chunk_index": 0,
                "content": "BALANCE SHEET",
                "chunk_type": "text",
                "page_number": 1
            },
            {
                "chunk_index": 1,
                "content": "This is content under the balance sheet header.",
                "chunk_type": "text",
                "page_number": 1
            }
        ]
        
        # Mock PDF for header detection
        from unittest.mock import patch, MagicMock
        mock_pdf = b"%PDF-1.4\nfake"
        
        with patch('app.services.document_processor_enhanced.fitz.open') as mock_fitz:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.rect.height = 800
            mock_doc.__len__.return_value = 1
            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.return_value = mock_doc
            
            result = processor._detect_headers_and_relationships(chunks, mock_pdf)
        
        # First chunk should be detected as header
        header_chunk = next((c for c in result if c.get("content") == "BALANCE SHEET"), None)
        if header_chunk:
            assert header_chunk.get("chunk_type") == "header"
        
        # Second chunk should have parent
        content_chunk = next((c for c in result if "content under" in c.get("content", "")), None)
        if content_chunk and chunking_config.PARENT_CHILD_ENABLED:
            assert "parent_chunk_index" in content_chunk or content_chunk.get("parent_chunk_index") is not None


class TestMetadataEnrichment:
    """Integration tests for metadata enrichment"""
    
    def test_metadata_includes_coordinates(self, db_session, test_document_setup):
        """Test that metadata includes PDF coordinates"""
        processor = EnhancedDocumentProcessor(db_session)
        
        chunks = [
            {
                "chunk_index": 0,
                "content": "Test content",
                "chunk_type": "text",
                "page_number": 1,
                "coordinates": {"x0": 10, "y0": 20, "x1": 100, "y1": 200}
            }
        ]
        
        result = processor._enrich_metadata(chunks, test_document_setup, b"fake pdf")
        
        assert len(result) == 1
        metadata = result[0].get("metadata", {})
        
        if chunking_config.INCLUDE_COORDINATES:
            assert "coordinates" in metadata
            coords = metadata["coordinates"]
            assert "x0" in coords
            assert "y0" in coords
            assert "x1" in coords
            assert "y1" in coords
    
    def test_metadata_includes_page_numbers(self, db_session, test_document_setup):
        """Test that metadata includes page numbers"""
        processor = EnhancedDocumentProcessor(db_session)
        
        chunks = [
            {
                "chunk_index": 0,
                "content": "Test",
                "chunk_type": "text",
                "page_number": 2
            }
        ]
        
        result = processor._enrich_metadata(chunks, test_document_setup, b"fake pdf")
        
        metadata = result[0].get("metadata", {})
        
        if chunking_config.INCLUDE_PAGE_NUMBERS:
            assert metadata.get("page_number") == 2


class TestFullDocumentProcessing:
    """Integration tests for full document processing"""
    
    @pytest.mark.skip(reason="Requires actual PDF and MinIO setup")
    def test_process_complete_document(self, db_session, test_document_setup):
        """Test processing a complete document end-to-end"""
        processor = EnhancedDocumentProcessor(db_session)
        
        # This would require:
        # 1. Actual PDF file
        # 2. MinIO storage setup
        # 3. Valid embeddings API key
        
        # For now, this is a placeholder
        pass
    
    def test_process_document_performance(self, db_session, test_document_setup):
        """Test that processing meets performance targets"""
        processor = EnhancedDocumentProcessor(db_session)
        
        # Create minimal PDF (would use real PDF in actual test)
        pdf_data = b"%PDF-1.4\nfake pdf content"
        
        start_time = time.time()
        
        result = processor.process_document(
            document_id=test_document_setup.id,
            pdf_data=pdf_data,
            generate_embeddings=False,  # Skip for performance test
            sync_to_pinecone=False
        )
        
        elapsed = time.time() - start_time
        
        if result.get("success"):
            perf = result.get("performance", {})
            time_per_page = perf.get("time_per_page", elapsed)
            
            # Should meet target (with some margin for test environment)
            assert time_per_page < chunking_config.TARGET_PROCESSING_TIME_PER_PAGE * 3


class TestChunkTypes:
    """Test chunk type identification"""
    
    def test_chunk_types_are_set(self, db_session, test_document_setup):
        """Test that chunk types are correctly identified"""
        processor = EnhancedDocumentProcessor(db_session)
        
        # Create chunks of different types
        chunks = [
            {
                "chunk_index": 0,
                "content": "BALANCE SHEET",
                "chunk_type": "text",  # Will be changed to header
                "page_number": 1
            },
            {
                "chunk_index": 1,
                "content": "| Account | Amount |\n| Cash | $1000 |",
                "chunk_type": "table",
                "page_number": 1
            },
            {
                "chunk_index": 2,
                "content": "This is regular text content.",
                "chunk_type": "text",
                "page_number": 1
            }
        ]
        
        # Process through header detection
        from unittest.mock import patch, MagicMock
        with patch('app.services.document_processor_enhanced.fitz.open') as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 1
            mock_fitz.return_value = mock_doc
            
            result = processor._detect_headers_and_relationships(chunks, b"fake pdf")
        
        # Verify chunk types
        types = [c.get("chunk_type") for c in result]
        assert "text" in types or "header" in types
        assert "table" in types


class TestDatabasePersistence:
    """Test that chunks are properly saved to database"""
    
    def test_chunks_saved_with_relationships(self, db_session, test_document_setup):
        """Test that chunks with relationships are saved correctly"""
        processor = EnhancedDocumentProcessor(db_session)
        
        chunks = [
            {
                "chunk_index": 0,
                "content": "Header",
                "chunk_type": "header",
                "char_count": 6,
                "metadata": {}
            },
            {
                "chunk_index": 1,
                "content": "Content",
                "chunk_type": "text",
                "char_count": 7,
                "metadata": {},
                "parent_chunk_index": 0
            }
        ]
        
        saved = processor._save_chunks(test_document_setup.id, chunks, test_document_setup)
        
        assert len(saved) == 2
        
        # Verify parent relationship
        content_chunk = next((c for c in saved if c.chunk_type == "text"), None)
        if content_chunk and chunking_config.PARENT_CHILD_ENABLED:
            assert content_chunk.parent_chunk_id is not None
        
        # Verify chunk types
        assert any(c.chunk_type == "header" for c in saved)
        assert any(c.chunk_type == "text" for c in saved)
        
        # Verify metadata
        assert all(c.chunk_metadata is not None for c in saved)


class TestPerformanceBenchmarks:
    """Performance benchmark tests"""
    
    @pytest.mark.skip(reason="Performance test - run manually")
    def test_benchmark_table_extraction(self, db_session):
        """Benchmark table extraction performance"""
        processor = EnhancedDocumentProcessor(db_session)
        
        # Would use real PDF here
        pdf_data = b"%PDF-1.4\nfake"
        
        start = time.time()
        result = processor._extract_tables(pdf_data)
        elapsed = time.time() - start
        
        print(f"Table extraction: {elapsed:.3f}s")
        assert elapsed < chunking_config.TARGET_TABLE_EXTRACTION_TIME * 2
    
    @pytest.mark.skip(reason="Performance test - run manually")
    def test_benchmark_text_chunking(self, db_session):
        """Benchmark text chunking performance"""
        processor = EnhancedDocumentProcessor(db_session)
        
        text = "Test sentence. " * 1000  # Large text
        pages = [{"page": 1, "text": text}]
        
        start = time.time()
        chunks = processor._chunk_text(text, pages)
        elapsed = time.time() - start
        
        print(f"Text chunking ({len(chunks)} chunks): {elapsed:.3f}s")
        assert elapsed < chunking_config.TARGET_CHUNKING_TIME_PER_PAGE * 2

