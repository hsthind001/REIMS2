"""
Enhanced Document Processor

Table-aware document processor that preserves financial table structure,
uses semantic text chunking with overlap, and establishes parent-child
relationships for better RAG performance.
"""
import logging
import time
import tempfile
import os
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

import fitz  # PyMuPDF
import pdfplumber
import pandas as pd

# LangChain imports
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logging.warning("LangChain not available. Install with: pip install langchain")

# Camelot imports
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    logging.warning("Camelot not available. Install with: pip install camelot-py[cv]")

from app.models.document_chunk import DocumentChunk
from app.models.document_upload import DocumentUpload
from app.config.chunking_config import chunking_config
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_sync_service import PineconeSyncService

logger = logging.getLogger(__name__)


class EnhancedDocumentProcessor:
    """
    Enhanced document processor with table-aware chunking
    
    Features:
    - Table extraction using Camelot (stream + lattice)
    - Semantic text chunking with overlap
    - Parent-child relationships (headers → content)
    - Metadata enrichment (coordinates, page numbers, types)
    - Multi-page table support
    """
    
    def __init__(self, db: Session):
        """
        Initialize enhanced document processor
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.embedding_service = EmbeddingService(db)
        self.sync_service = PineconeSyncService(db) if hasattr(PineconeSyncService, '__init__') else None
        
        # Initialize text splitter
        if LANGCHAIN_AVAILABLE:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunking_config.get_chunk_size_chars(),
                chunk_overlap=chunking_config.get_overlap_size_chars(),
                separators=chunking_config.TEXT_SPLITTER_SEPARATORS,
                length_function=len
            )
        else:
            self.text_splitter = None
            logger.warning("LangChain not available. Text chunking will use simple splitting.")
    
    def process_document(
        self,
        document_id: int,
        pdf_data: bytes,
        generate_embeddings: bool = True,
        sync_to_pinecone: bool = True
    ) -> Dict[str, Any]:
        """
        Process a document: extract tables, chunk text, establish relationships
        
        Args:
            document_id: Document upload ID
            pdf_data: PDF file as bytes
            generate_embeddings: Whether to generate embeddings
            sync_to_pinecone: Whether to sync to Pinecone
        
        Returns:
            Dict with processing results and statistics
        """
        start_time = time.time()
        
        try:
            # Get document metadata
            document = self.db.query(DocumentUpload).filter(
                DocumentUpload.id == document_id
            ).first()
            
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }
            
            # Delete existing chunks for this document (if reprocessing)
            existing_chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            for chunk in existing_chunks:
                self.db.delete(chunk)
            self.db.commit()
            
            logger.info(f"Processing document {document_id}: {document.file_name}")
            
            # Step 1: Extract tables
            table_start = time.time()
            tables_result = self._extract_tables(pdf_data)
            table_time = time.time() - table_start
            
            # Step 2: Extract text
            text_start = time.time()
            text_result = self._extract_text(pdf_data)
            text_time = time.time() - text_start
            
            # Step 3: Chunk text with overlap
            chunk_start = time.time()
            text_chunks = self._chunk_text(text_result['text'], text_result.get('pages', []))
            chunk_time = time.time() - chunk_start
            
            # Step 4: Convert tables to markdown chunks
            table_chunks = self._convert_tables_to_chunks(tables_result.get('tables', []))
            
            # Step 5: Detect headers and establish relationships
            header_start = time.time()
            all_chunks = text_chunks + table_chunks
            all_chunks = self._detect_headers_and_relationships(all_chunks, pdf_data)
            header_time = time.time() - header_start
            
            # Step 6: Enrich metadata
            all_chunks = self._enrich_metadata(all_chunks, document, pdf_data)
            
            # Step 7: Save chunks to database
            save_start = time.time()
            saved_chunks = self._save_chunks(document_id, all_chunks, document)
            save_time = time.time() - save_start
            
            # Step 8: Generate embeddings
            embedding_time = 0
            if generate_embeddings and saved_chunks:
                embedding_start = time.time()
                self._generate_embeddings(saved_chunks)
                embedding_time = time.time() - embedding_start
                
                # Step 9: Sync to Pinecone
                if sync_to_pinecone and self.sync_service:
                    sync_start = time.time()
                    for chunk in saved_chunks:
                        if chunk.embedding:
                            self.sync_service.sync_chunk_to_pinecone(chunk.id)
                    sync_time = time.time() - sync_start
                else:
                    sync_time = 0
            
            total_time = time.time() - start_time
            pages = text_result.get('total_pages', 1)
            time_per_page = total_time / pages if pages > 0 else total_time
            
            # Performance validation
            perf_validation = chunking_config.validate_performance(
                time_per_page,
                chunking_config.TARGET_PROCESSING_TIME_PER_PAGE,
                "document_processing"
            )
            
            result = {
                "success": True,
                "document_id": document_id,
                "statistics": {
                    "total_chunks": len(saved_chunks),
                    "text_chunks": len([c for c in saved_chunks if c.chunk_type == 'text']),
                    "table_chunks": len([c for c in saved_chunks if c.chunk_type == 'table']),
                    "header_chunks": len([c for c in saved_chunks if c.chunk_type == 'header']),
                    "tables_extracted": len(tables_result.get('tables', [])),
                    "pages_processed": pages
                },
                "performance": {
                    "total_time": round(total_time, 2),
                    "time_per_page": round(time_per_page, 2),
                    "table_extraction_time": round(table_time, 2),
                    "text_extraction_time": round(text_time, 2),
                    "chunking_time": round(chunk_time, 2),
                    "header_detection_time": round(header_time, 2),
                    "save_time": round(save_time, 2),
                    "embedding_time": round(embedding_time, 2),
                    "validation": perf_validation
                }
            }
            
            if perf_validation.get('warning'):
                logger.warning(perf_validation['warning'])
            
            logger.info(f"Document {document_id} processed: {len(saved_chunks)} chunks in {total_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }
    
    def _extract_tables(self, pdf_data: bytes) -> Dict[str, Any]:
        """
        Extract tables from PDF using Camelot
        
        Args:
            pdf_data: PDF file as bytes
        
        Returns:
            Dict with extracted tables
        """
        if not CAMELOT_AVAILABLE:
            logger.warning("Camelot not available. Skipping table extraction.")
            return {"tables": [], "success": False, "error": "Camelot not available"}
        
        try:
            # Save to temporary file (Camelot requires file path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(pdf_data)
                tmp_path = tmp_file.name
            
            all_tables = []
            
            # Try both lattice and stream modes
            for flavor in chunking_config.TABLE_EXTRACTION_MODES:
                try:
                    tables = camelot.read_pdf(tmp_path, flavor=flavor, pages="all")
                    
                    for table_num, table in enumerate(tables, 1):
                        # Filter by minimum size
                        if len(table.df) < chunking_config.TABLE_MIN_ROWS:
                            continue
                        if len(table.df.columns) < chunking_config.TABLE_MIN_COLS:
                            continue
                        
                        # Get table data
                        data = table.df.values.tolist()
                        headers = table.df.columns.tolist()
                        
                        # Get table coordinates
                        bbox = table._bbox if hasattr(table, '_bbox') else None
                        coordinates = None
                        if bbox:
                            coordinates = {
                                "x0": float(bbox[0]),
                                "y0": float(bbox[1]),
                                "x1": float(bbox[2]),
                                "y1": float(bbox[3])
                            }
                        
                        table_data = {
                            "table_index": len(all_tables) + 1,
                            "page": table.page,
                            "flavor": flavor,
                            "headers": headers,
                            "data": data,
                            "rows": len(data),
                            "columns": len(headers),
                            "accuracy": table.parsing_report.get("accuracy", 0),
                            "coordinates": coordinates,
                            "raw_table": table  # Keep for markdown conversion
                        }
                        
                        all_tables.append(table_data)
                
                except Exception as e:
                    logger.warning(f"Camelot {flavor} extraction failed: {str(e)}")
                    continue
            
            # Cleanup
            os.unlink(tmp_path)
            
            # Detect multi-page tables
            if chunking_config.MULTI_PAGE_TABLE_DETECTION:
                all_tables = self._detect_multi_page_tables(all_tables)
            
            return {
                "tables": all_tables,
                "total_tables": len(all_tables),
                "success": True
            }
            
        except Exception as e:
            # Cleanup on error
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            logger.error(f"Table extraction failed: {str(e)}", exc_info=True)
            return {
                "tables": [],
                "success": False,
                "error": str(e)
            }
    
    def _extract_text(self, pdf_data: bytes) -> Dict[str, Any]:
        """
        Extract text from PDF with page information
        
        Args:
            pdf_data: PDF file as bytes
        
        Returns:
            Dict with extracted text and page information
        """
        try:
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            pages_text = []
            full_text_parts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Get text blocks with coordinates
                blocks = page.get_text("dict")
                
                pages_text.append({
                    "page": page_num + 1,
                    "text": text,
                    "char_count": len(text),
                    "word_count": len(text.split()),
                    "blocks": blocks.get("blocks", [])
                })
                
                full_text_parts.append(text)
            
            doc.close()
            
            full_text = "\n\n--- Page Break ---\n\n".join(full_text_parts)
            
            return {
                "text": full_text,
                "pages": pages_text,
                "total_pages": len(pages_text),
                "total_chars": len(full_text),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}", exc_info=True)
            return {
                "text": "",
                "pages": [],
                "total_pages": 0,
                "success": False,
                "error": str(e)
            }
    
    def _chunk_text(self, text: str, pages: List[Dict]) -> List[Dict[str, Any]]:
        """
        Chunk text using RecursiveCharacterTextSplitter with overlap
        
        Args:
            text: Full text to chunk
            pages: Page information for metadata
        
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        if not text or len(text.strip()) == 0:
            return chunks
        
        if self.text_splitter:
            # Use LangChain splitter
            text_chunks = self.text_splitter.split_text(text)
        else:
            # Fallback: Simple splitting
            chunk_size = chunking_config.get_chunk_size_chars()
            overlap_size = chunking_config.get_overlap_size_chars()
            text_chunks = []
            
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunk_text = text[start:end]
                text_chunks.append(chunk_text)
                start = end - overlap_size
        
        # Create chunk dictionaries with metadata
        for idx, chunk_text in enumerate(text_chunks):
            # Determine page number (approximate)
            page_num = self._determine_page_for_text(chunk_text, pages)
            
            chunks.append({
                "chunk_index": idx,
                "content": chunk_text,
                "chunk_type": chunking_config.CHUNK_TYPE_TEXT,
                "page_number": page_num,
                "char_count": len(chunk_text),
                "token_count": int(len(chunk_text) * chunking_config.TOKENS_PER_CHAR)
            })
        
        return chunks
    
    def _convert_tables_to_chunks(self, tables: List[Dict]) -> List[Dict[str, Any]]:
        """
        Convert extracted tables to markdown format chunks
        
        Args:
            tables: List of extracted table dictionaries
        
        Returns:
            List of table chunk dictionaries
        """
        chunks = []
        
        for table in tables:
            if chunking_config.TABLE_MARKDOWN_FORMAT:
                # Convert to markdown
                markdown = self._table_to_markdown(table)
            else:
                # Use plain text representation
                markdown = self._table_to_text(table)
            
            chunks.append({
                "chunk_index": len(chunks),  # Will be reindexed later
                "content": markdown,
                "chunk_type": chunking_config.CHUNK_TYPE_TABLE,
                "page_number": table.get("page", 1),
                "table_index": table.get("table_index", 0),
                "coordinates": table.get("coordinates"),
                "char_count": len(markdown),
                "token_count": int(len(markdown) * chunking_config.TOKENS_PER_CHAR),
                "table_metadata": {
                    "rows": table.get("rows", 0),
                    "columns": table.get("columns", 0),
                    "accuracy": table.get("accuracy", 0),
                    "flavor": table.get("flavor", "unknown")
                }
            })
        
        return chunks
    
    def _table_to_markdown(self, table: Dict) -> str:
        """
        Convert table to markdown format
        
        Args:
            table: Table dictionary with headers and data
        
        Returns:
            Markdown string
        """
        try:
            headers = table.get("headers", [])
            data = table.get("data", [])
            
            if not headers and not data:
                return ""
            
            # Create DataFrame for easier markdown conversion
            if headers:
                df = pd.DataFrame(data, columns=headers)
            else:
                df = pd.DataFrame(data)
            
            # Convert to markdown
            markdown = df.to_markdown(index=False)
            
            return markdown
            
        except Exception as e:
            logger.warning(f"Failed to convert table to markdown: {str(e)}")
            # Fallback to text
            return self._table_to_text(table)
    
    def _table_to_text(self, table: Dict) -> str:
        """
        Convert table to plain text format
        
        Args:
            table: Table dictionary
        
        Returns:
            Plain text string
        """
        headers = table.get("headers", [])
        data = table.get("data", [])
        
        lines = []
        
        if headers:
            lines.append(" | ".join(str(h) for h in headers))
            lines.append("-" * (sum(len(str(h)) for h in headers) + len(headers) * 3))
        
        for row in data:
            lines.append(" | ".join(str(cell) for cell in row))
        
        return "\n".join(lines)
    
    def _detect_headers_and_relationships(
        self,
        chunks: List[Dict[str, Any]],
        pdf_data: bytes
    ) -> List[Dict[str, Any]]:
        """
        Detect headers and establish parent-child relationships
        
        Args:
            chunks: List of chunk dictionaries
            pdf_data: PDF file as bytes (for coordinate extraction)
        
        Returns:
            List of chunks with parent relationships established
        """
        if not chunking_config.PARENT_CHILD_ENABLED:
            return chunks
        
        try:
            # Open PDF for coordinate extraction
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            # Detect headers
            header_chunks = []
            for chunk in chunks:
                if self._is_header(chunk, doc):
                    chunk["chunk_type"] = chunking_config.CHUNK_TYPE_HEADER
                    chunk["header_level"] = self._determine_header_level(chunk, doc)
                    header_chunks.append(chunk)
            
            # Establish parent-child relationships
            for chunk in chunks:
                if chunk["chunk_type"] != chunking_config.CHUNK_TYPE_HEADER:
                    parent = self._find_parent_header(chunk, header_chunks, doc)
                    if parent:
                        chunk["parent_chunk_index"] = parent["chunk_index"]
            
            doc.close()
            
            # Add header chunks to list
            for header in header_chunks:
                if header not in chunks:
                    chunks.append(header)
            
            # Reindex chunks
            chunks.sort(key=lambda x: (x.get("page_number", 0), x.get("chunk_index", 0)))
            for idx, chunk in enumerate(chunks):
                chunk["chunk_index"] = idx
            
            return chunks
            
        except Exception as e:
            logger.warning(f"Header detection failed: {str(e)}")
            return chunks
    
    def _is_header(self, chunk: Dict[str, Any], doc: fitz.Document) -> bool:
        """
        Determine if a chunk is a header
        
        Args:
            chunk: Chunk dictionary
            doc: PyMuPDF document
        
        Returns:
            True if chunk appears to be a header
        """
        if not chunking_config.HEADER_DETECTION_ENABLED:
            return False
        
        content = chunk.get("content", "")
        
        # Simple heuristics for header detection
        # 1. Short text (typically headers are short)
        if len(content) > 200:
            return False
        
        # 2. All caps or title case
        if content.isupper() or content.istitle():
            return True
        
        # 3. Contains common header patterns
        header_patterns = [
            "balance sheet",
            "income statement",
            "cash flow",
            "rent roll",
            "assets",
            "liabilities",
            "revenue",
            "expenses"
        ]
        
        content_lower = content.lower()
        if any(pattern in content_lower for pattern in header_patterns):
            return True
        
        # 4. Check position on page (headers are typically at top)
        page_num = chunk.get("page_number", 1)
        if page_num <= len(doc):
            try:
                page = doc[page_num - 1]
                # If coordinates available, check if near top
                coords = chunk.get("coordinates")
                if coords:
                    page_height = page.rect.height
                    y0 = coords.get("y0", 0)
                    if y0 / page_height < chunking_config.HEADER_POSITION_TOP_THRESHOLD:
                        return True
            except:
                pass
        
        return False
    
    def _determine_header_level(self, chunk: Dict[str, Any], doc: fitz.Document) -> int:
        """
        Determine header hierarchy level (1-3)
        
        Args:
            chunk: Header chunk dictionary
            doc: PyMuPDF document
        
        Returns:
            Header level (1-3)
        """
        # Simple heuristic: use font size or position
        # Level 1: Main sections (typically larger, at top)
        # Level 2: Subsections
        # Level 3: Sub-subsections
        
        content = chunk.get("content", "")
        
        # Check if it's a main section header
        main_sections = ["balance sheet", "income statement", "cash flow", "rent roll"]
        if any(section in content.lower() for section in main_sections):
            return 1
        
        # Default to level 2
        return 2
    
    def _find_parent_header(
        self,
        chunk: Dict[str, Any],
        header_chunks: List[Dict[str, Any]],
        doc: fitz.Document
    ) -> Optional[Dict[str, Any]]:
        """
        Find the parent header for a chunk
        
        Args:
            chunk: Chunk to find parent for
            header_chunks: List of header chunks
            doc: PyMuPDF document
        
        Returns:
            Parent header chunk or None
        """
        if not header_chunks:
            return None
        
        chunk_page = chunk.get("page_number", 1)
        chunk_index = chunk.get("chunk_index", 0)
        
        # Find nearest header before this chunk
        candidates = []
        for header in header_chunks:
            header_page = header.get("page_number", 1)
            header_index = header.get("chunk_index", 0)
            
            # Header must be before chunk
            if header_page < chunk_page or (header_page == chunk_page and header_index < chunk_index):
                distance = (chunk_page - header_page) * 1000 + (chunk_index - header_index)
                if distance <= chunking_config.MAX_DISTANCE_FOR_PARENT:
                    candidates.append((distance, header))
        
        if candidates:
            # Return closest header
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        
        return None
    
    def _detect_multi_page_tables(self, tables: List[Dict]) -> List[Dict]:
        """
        Detect and merge multi-page tables
        
        Args:
            tables: List of extracted tables
        
        Returns:
            List of tables with multi-page tables merged
        """
        if not tables:
            return tables
        
        # Group tables by similarity and page proximity
        merged_tables = []
        processed = set()
        
        for i, table1 in enumerate(tables):
            if i in processed:
                continue
            
            current_group = [table1]
            processed.add(i)
            
            # Look for continuation tables
            for j, table2 in enumerate(tables[i+1:], start=i+1):
                if j in processed:
                    continue
                
                # Check if tables are on consecutive pages
                if table2.get("page") == table1.get("page") + len(current_group):
                    # Check similarity (same column count, similar headers)
                    if (table2.get("columns") == table1.get("columns") and
                        self._tables_similar(table1, table2)):
                        current_group.append(table2)
                        processed.add(j)
            
            # Merge multi-page tables
            if len(current_group) > 1:
                merged = self._merge_tables(current_group)
                merged_tables.append(merged)
            else:
                merged_tables.append(table1)
        
        return merged_tables
    
    def _tables_similar(self, table1: Dict, table2: Dict) -> bool:
        """Check if two tables are similar (likely continuation)"""
        headers1 = table1.get("headers", [])
        headers2 = table2.get("headers", [])
        
        if len(headers1) != len(headers2):
            return False
        
        # Check header similarity
        matches = sum(1 for h1, h2 in zip(headers1, headers2) if str(h1).lower() == str(h2).lower())
        similarity = matches / len(headers1) if headers1 else 0
        
        return similarity >= chunking_config.TABLE_CONTINUATION_THRESHOLD
    
    def _merge_tables(self, tables: List[Dict]) -> Dict:
        """Merge multiple tables into one"""
        if not tables:
            return {}
        
        if len(tables) == 1:
            return tables[0]
        
        # Combine all data
        all_data = []
        headers = tables[0].get("headers", [])
        
        for table in tables:
            all_data.extend(table.get("data", []))
        
        # Create merged table
        merged = tables[0].copy()
        merged["data"] = all_data
        merged["rows"] = len(all_data)
        merged["pages"] = [t.get("page") for t in tables]
        merged["multi_page"] = True
        
        return merged
    
    def _determine_page_for_text(self, text: str, pages: List[Dict]) -> int:
        """Determine which page a text chunk belongs to"""
        if not pages:
            return 1
        
        # Simple heuristic: find page with most matching text
        for page_info in pages:
            page_text = page_info.get("text", "")
            # Check if chunk text appears in page
            if text[:100] in page_text:  # Check first 100 chars
                return page_info.get("page", 1)
        
        # Default to first page
        return 1
    
    def _enrich_metadata(
        self,
        chunks: List[Dict[str, Any]],
        document: DocumentUpload,
        pdf_data: bytes
    ) -> List[Dict[str, Any]]:
        """
        Enrich chunks with metadata (coordinates, page numbers, etc.)
        
        Args:
            chunks: List of chunk dictionaries
            document: Document upload object
            pdf_data: PDF file as bytes
        
        Returns:
            List of chunks with enriched metadata
        """
        try:
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            for chunk in chunks:
                metadata = chunk.get("metadata", {})
                
                # Add chunk type
                metadata["chunk_type"] = chunk.get("chunk_type", "text")
                
                # Add page number
                if chunking_config.INCLUDE_PAGE_NUMBERS:
                    metadata["page_number"] = chunk.get("page_number", 1)
                
                # Add coordinates if available
                if chunking_config.INCLUDE_COORDINATES:
                    coords = chunk.get("coordinates")
                    if coords:
                        metadata["coordinates"] = coords
                    else:
                        # Try to extract from PDF
                        page_num = chunk.get("page_number", 1)
                        if page_num <= len(doc):
                            # Approximate coordinates (would need more sophisticated extraction)
                            metadata["coordinates"] = {
                                "x0": 0.0,
                                "y0": 0.0,
                                "x1": 0.0,
                                "y1": 0.0
                            }
                
                # Add token count
                if chunking_config.INCLUDE_TOKEN_COUNT:
                    metadata["token_count"] = chunk.get("token_count", 0)
                
                # Add table metadata if applicable
                if chunk.get("chunk_type") == "table":
                    table_meta = chunk.get("table_metadata", {})
                    metadata.update(table_meta)
                    metadata["table_index"] = chunk.get("table_index", 0)
                
                # Add header level if applicable
                if chunk.get("chunk_type") == "header":
                    metadata["header_level"] = chunk.get("header_level", 1)
                
                chunk["metadata"] = metadata
            
            doc.close()
            
        except Exception as e:
            logger.warning(f"Metadata enrichment failed: {str(e)}")
        
        return chunks
    
    def _save_chunks(
        self,
        document_id: int,
        chunks: List[Dict[str, Any]],
        document: DocumentUpload
    ) -> List[DocumentChunk]:
        """
        Save chunks to database
        
        Args:
            document_id: Document upload ID
            chunks: List of chunk dictionaries
            document: Document upload object
        
        Returns:
            List of saved DocumentChunk objects
        """
        saved_chunks = []
        
        try:
            for chunk_data in chunks:
                # Find parent chunk if parent_chunk_index is set
                parent_chunk_id = None
                if "parent_chunk_index" in chunk_data:
                    parent_index = chunk_data["parent_chunk_index"]
                    # Find parent in already saved chunks
                    for saved in saved_chunks:
                        if saved.chunk_index == parent_index:
                            parent_chunk_id = saved.id
                            break
                
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk_data.get("chunk_index", 0),
                    chunk_text=chunk_data.get("content", ""),
                    chunk_size=chunk_data.get("char_count", 0),
                    chunk_type=chunk_data.get("chunk_type"),
                    parent_chunk_id=parent_chunk_id,
                    chunk_metadata=chunk_data.get("metadata", {}),
                    property_id=document.property_id,
                    period_id=document.period_id,
                    document_type=document.document_type
                )
                
                self.db.add(chunk)
                saved_chunks.append(chunk)
            
            self.db.commit()
            
            # Refresh to get IDs for parent relationships
            for chunk in saved_chunks:
                self.db.refresh(chunk)
            
            # Update parent relationships now that we have IDs
            for i, chunk_data in enumerate(chunks):
                if "parent_chunk_index" in chunk_data and not saved_chunks[i].parent_chunk_id:
                    parent_index = chunk_data["parent_chunk_index"]
                    for saved in saved_chunks:
                        if saved.chunk_index == parent_index:
                            saved_chunks[i].parent_chunk_id = saved.id
                            break
            
            self.db.commit()
            
            logger.info(f"Saved {len(saved_chunks)} chunks for document {document_id}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save chunks: {str(e)}", exc_info=True)
            raise
        
        return saved_chunks
    
    def _generate_embeddings(self, chunks: List[DocumentChunk]) -> None:
        """
        Generate embeddings for chunks
        
        Args:
            chunks: List of DocumentChunk objects
        """
        try:
            # Filter chunks that need embeddings
            chunks_to_embed = [c for c in chunks if not c.embedding]
            
            if not chunks_to_embed:
                return
            
            # Generate embeddings in batch
            texts = [chunk.chunk_text for chunk in chunks_to_embed]
            embeddings = self.embedding_service.generate_embeddings_batch(texts)
            
            # Store embeddings
            for chunk, embedding in zip(chunks_to_embed, embeddings):
                if embedding:
                    chunk.embedding = embedding
                    chunk.embedding_model = self.embedding_service.OPENAI_MODEL
                    chunk.embedding_dimension = len(embedding)
            
            self.db.commit()
            
            logger.info(f"Generated embeddings for {len([e for e in embeddings if e])} chunks")
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}", exc_info=True)
            # Don't raise - embeddings are optional

