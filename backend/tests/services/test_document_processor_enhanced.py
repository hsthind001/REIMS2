"""
Unit Tests for Enhanced Document Processor

Tests table extraction, text chunking, parent-child relationships,
and metadata enrichment.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from typing import List, Dict, Any
import io

from app.services.document_processor_enhanced import EnhancedDocumentProcessor
from app.models.document_chunk import DocumentChunk
from app.models.document_upload import DocumentUpload


@pytest.fixture
def mock_pdf_data():
    """Mock PDF data"""
    return b"%PDF-1.4\nfake pdf content"


@pytest.fixture
def mock_document(db_session):
    """Create mock document"""
    from app.models.property import Property
    from app.models.financial_period import FinancialPeriod
    
    property_obj = Property()
    property_obj.id = 1
    property_obj.property_code = "TEST"
    property_obj.property_name = "Test Property"
    db_session.add(property_obj)
    
    period = FinancialPeriod()
    period.id = 1
    period.property_id = 1
    period.period_year = 2024
    period.period_month = 1
    db_session.add(period)
    
    document = DocumentUpload()
    document.id = 1
    document.property_id = 1
    document.period_id = 1
    document.document_type = "balance_sheet"
    document.file_name = "test.pdf"
    document.file_path = "test/test.pdf"
    document.extraction_status = "completed"
    db_session.add(document)
    db_session.commit()
    
    return document


@pytest.fixture
def processor(db_session):
    """Create processor instance"""
    return EnhancedDocumentProcessor(db_session)


class TestTableExtraction:
    """Test table extraction functionality"""
    
    @patch('app.services.document_processor_enhanced.camelot')
    @patch('tempfile.NamedTemporaryFile')
    def test_extract_tables_success(self, mock_tempfile, mock_camelot, processor, mock_pdf_data):
        """Test successful table extraction"""
        # Mock Camelot
        mock_table = MagicMock()
        mock_table.df = MagicMock()
        mock_table.df.values.tolist.return_value = [['Row1', 'Row2'], ['Data1', 'Data2']]
        mock_table.df.columns.tolist.return_value = ['Col1', 'Col2']
        mock_table.page = 1
        mock_table.parsing_report = {'accuracy': 95.0}
        mock_table._bbox = [10, 20, 100, 200]
        
        mock_camelot.read_pdf.return_value = [mock_table]
        
        # Mock temp file
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.pdf"
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        result = processor._extract_tables(mock_pdf_data)
        
        assert result['success'] is True
        assert result['total_tables'] == 1
        assert len(result['tables']) == 1
        assert result['tables'][0]['page'] == 1
        assert result['tables'][0]['rows'] == 2
        assert result['tables'][0]['columns'] == 2
    
    @patch('app.services.document_processor_enhanced.camelot')
    def test_extract_tables_filters_small_tables(self, mock_camelot, processor, mock_pdf_data):
        """Test that small tables are filtered out"""
        # Mock small table (1 row)
        mock_table = MagicMock()
        mock_table.df = MagicMock()
        mock_table.df.values.tolist.return_value = [['Data1']]
        mock_table.df.columns.tolist.return_value = ['Col1']
        mock_table.page = 1
        mock_table.parsing_report = {'accuracy': 95.0}
        mock_table._bbox = [10, 20, 100, 200]
        
        mock_camelot.read_pdf.return_value = [mock_table]
        
        with patch('tempfile.NamedTemporaryFile'):
            result = processor._extract_tables(mock_pdf_data)
        
        # Small table should be filtered out
        assert result['total_tables'] == 0
    
    def test_extract_tables_camelot_unavailable(self, processor, mock_pdf_data):
        """Test fallback when Camelot is unavailable"""
        with patch('app.services.document_processor_enhanced.CAMELOT_AVAILABLE', False):
            result = processor._extract_tables(mock_pdf_data)
        
        assert result['success'] is False
        assert 'Camelot not available' in result['error']


class TestTextChunking:
    """Test text chunking functionality"""
    
    def test_chunk_text_with_langchain(self, processor):
        """Test text chunking with LangChain"""
        text = "This is a test. " * 100  # Long text
        pages = [{"page": 1, "text": text}]
        
        result = processor._chunk_text(text, pages)
        
        assert len(result) > 0
        assert all(chunk['chunk_type'] == 'text' for chunk in result)
        assert all('content' in chunk for chunk in result)
        assert all('page_number' in chunk for chunk in result)
    
    def test_chunk_text_fallback(self, processor):
        """Test text chunking fallback when LangChain unavailable"""
        with patch('app.services.document_processor_enhanced.LANGCHAIN_AVAILABLE', False):
            processor.text_splitter = None
            
            text = "This is a test. " * 100
            pages = [{"page": 1, "text": text}]
            
            result = processor._chunk_text(text, pages)
            
            assert len(result) > 0
            assert all(chunk['chunk_type'] == 'text' for chunk in result)
    
    def test_chunk_text_empty(self, processor):
        """Test chunking empty text"""
        result = processor._chunk_text("", [])
        assert result == []


class TestTableToMarkdown:
    """Test table to markdown conversion"""
    
    def test_table_to_markdown(self, processor):
        """Test converting table to markdown"""
        table = {
            "headers": ["Account", "Amount"],
            "data": [["Cash", "$1000"], ["Revenue", "$5000"]],
            "rows": 2,
            "columns": 2
        }
        
        markdown = processor._table_to_markdown(table)
        
        assert "Account" in markdown
        assert "Amount" in markdown
        assert "Cash" in markdown
        assert "Revenue" in markdown
    
    def test_table_to_text_fallback(self, processor):
        """Test table to text conversion"""
        table = {
            "headers": ["Account", "Amount"],
            "data": [["Cash", "$1000"]],
            "rows": 1,
            "columns": 2
        }
        
        text = processor._table_to_text(table)
        
        assert "Account" in text
        assert "Amount" in text
        assert "Cash" in text


class TestHeaderDetection:
    """Test header detection and parent-child relationships"""
    
    @patch('fitz.open')
    def test_is_header_detection(self, mock_fitz, processor):
        """Test header detection logic"""
        # Mock PDF document
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.rect.height = 800
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.return_value = mock_doc
        
        # Test header (all caps, short)
        header_chunk = {
            "content": "BALANCE SHEET",
            "page_number": 1,
            "coordinates": {"y0": 50}  # Near top
        }
        
        assert processor._is_header(header_chunk, mock_doc) is True
        
        # Test non-header (long text)
        non_header = {
            "content": "This is a long paragraph that contains many words and should not be detected as a header.",
            "page_number": 1
        }
        
        assert processor._is_header(non_header, mock_doc) is False
    
    def test_determine_header_level(self, processor):
        """Test header level determination"""
        # Main section header
        main_header = {
            "content": "Balance Sheet"
        }
        
        level = processor._determine_header_level(main_header, MagicMock())
        assert level == 1
        
        # Regular header
        regular_header = {
            "content": "Current Assets"
        }
        
        level = processor._determine_header_level(regular_header, MagicMock())
        assert level == 2


class TestParentChildRelationships:
    """Test parent-child relationship logic"""
    
    def test_find_parent_header(self, processor):
        """Test finding parent header for a chunk"""
        header_chunks = [
            {
                "chunk_index": 0,
                "page_number": 1,
                "content": "BALANCE SHEET"
            },
            {
                "chunk_index": 5,
                "page_number": 1,
                "content": "ASSETS"
            }
        ]
        
        # Chunk that should have first header as parent
        chunk = {
            "chunk_index": 3,
            "page_number": 1,
            "content": "Some content here"
        }
        
        parent = processor._find_parent_header(chunk, header_chunks, MagicMock())
        
        assert parent is not None
        assert parent["content"] == "BALANCE SHEET"
    
    def test_find_parent_header_no_match(self, processor):
        """Test when no parent header is found"""
        header_chunks = []
        chunk = {
            "chunk_index": 5,
            "page_number": 1,
            "content": "Some content"
        }
        
        parent = processor._find_parent_header(chunk, header_chunks, MagicMock())
        
        assert parent is None


class TestMultiPageTables:
    """Test multi-page table detection"""
    
    def test_detect_multi_page_tables(self, processor):
        """Test detecting and merging multi-page tables"""
        tables = [
            {
                "table_index": 1,
                "page": 1,
                "headers": ["Account", "Amount"],
                "columns": 2,
                "data": [["Row1", "100"]]
            },
            {
                "table_index": 2,
                "page": 2,
                "headers": ["Account", "Amount"],
                "columns": 2,
                "data": [["Row2", "200"]]
            }
        ]
        
        result = processor._detect_multi_page_tables(tables)
        
        # Should merge into one table
        assert len(result) == 1
        assert result[0].get("multi_page") is True
    
    def test_tables_similar(self, processor):
        """Test table similarity check"""
        table1 = {
            "headers": ["Account", "Amount"],
            "columns": 2
        }
        
        table2 = {
            "headers": ["Account", "Amount"],
            "columns": 2
        }
        
        assert processor._tables_similar(table1, table2) is True
        
        table3 = {
            "headers": ["Different", "Headers"],
            "columns": 2
        }
        
        assert processor._tables_similar(table1, table3) is False


class TestMetadataEnrichment:
    """Test metadata enrichment"""
    
    @patch('fitz.open')
    def test_enrich_metadata(self, mock_fitz, processor, mock_document):
        """Test metadata enrichment"""
        chunks = [
            {
                "chunk_index": 0,
                "content": "Test content",
                "chunk_type": "text",
                "page_number": 1,
                "char_count": 12,
                "token_count": 3
            }
        ]
        
        # Mock PDF
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_fitz.return_value = mock_doc
        
        result = processor._enrich_metadata(chunks, mock_document, b"fake pdf")
        
        assert len(result) == 1
        assert "metadata" in result[0]
        metadata = result[0]["metadata"]
        assert metadata["chunk_type"] == "text"
        assert metadata["page_number"] == 1
        assert metadata["token_count"] == 3


class TestSaveChunks:
    """Test saving chunks to database"""
    
    def test_save_chunks(self, processor, db_session, mock_document):
        """Test saving chunks to database"""
        chunks = [
            {
                "chunk_index": 0,
                "content": "Test chunk 1",
                "chunk_type": "text",
                "char_count": 12,
                "metadata": {"page_number": 1}
            },
            {
                "chunk_index": 1,
                "content": "Test chunk 2",
                "chunk_type": "table",
                "char_count": 12,
                "metadata": {"page_number": 1, "table_index": 1}
            }
        ]
        
        saved = processor._save_chunks(mock_document.id, chunks, mock_document)
        
        assert len(saved) == 2
        assert all(isinstance(chunk, DocumentChunk) for chunk in saved)
        assert saved[0].chunk_type == "text"
        assert saved[1].chunk_type == "table"
        assert saved[0].document_id == mock_document.id
    
    def test_save_chunks_with_parent(self, processor, db_session, mock_document):
        """Test saving chunks with parent relationships"""
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
        
        saved = processor._save_chunks(mock_document.id, chunks, mock_document)
        
        assert len(saved) == 2
        assert saved[1].parent_chunk_id == saved[0].id


class TestProcessDocument:
    """Test full document processing"""
    
    @patch('app.services.document_processor_enhanced.download_file')
    @patch('app.services.document_processor_enhanced.fitz.open')
    def test_process_document_success(
        self,
        mock_fitz,
        mock_download,
        processor,
        db_session,
        mock_document,
        mock_pdf_data
    ):
        """Test successful document processing"""
        # Mock download
        mock_download.return_value = mock_pdf_data
        
        # Mock PDF
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Test PDF content " * 50
        mock_page.get_text.return_value = {"blocks": []}
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.return_value = mock_doc
        
        # Mock table extraction (no tables)
        with patch.object(processor, '_extract_tables', return_value={"tables": [], "success": True}):
            # Mock embedding generation
            with patch.object(processor.embedding_service, 'generate_embeddings_batch', return_value=[[0.1] * 1536]):
                result = processor.process_document(
                    document_id=mock_document.id,
                    pdf_data=mock_pdf_data,
                    generate_embeddings=False,  # Skip for faster test
                    sync_to_pinecone=False
                )
        
        assert result['success'] is True
        assert 'statistics' in result
        assert result['statistics']['total_chunks'] > 0
    
    def test_process_document_not_found(self, processor, db_session):
        """Test processing non-existent document"""
        result = processor.process_document(
            document_id=99999,
            pdf_data=b"fake",
            generate_embeddings=False,
            sync_to_pinecone=False
        )
        
        assert result['success'] is False
        assert 'not found' in result['error'].lower()


class TestErrorHandling:
    """Test error handling"""
    
    def test_process_document_handles_exceptions(self, processor, db_session, mock_document):
        """Test that exceptions are handled gracefully"""
        # Force an error by passing invalid PDF data
        result = processor.process_document(
            document_id=mock_document.id,
            pdf_data=b"invalid pdf",
            generate_embeddings=False,
            sync_to_pinecone=False
        )
        
        # Should return error result, not crash
        assert 'success' in result or 'error' in result

