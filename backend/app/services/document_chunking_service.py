"""
Document Chunking Service for RAG

Splits documents into manageable chunks for embedding and retrieval
"""
import re
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.document_upload import DocumentUpload
from app.models.extraction_log import ExtractionLog
from app.models.document_chunk import DocumentChunk
import logging

logger = logging.getLogger(__name__)


class DocumentChunkingService:
    """Service for chunking documents into manageable pieces"""
    
    # Default chunk size (characters)
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200
    
    def __init__(self, db: Session, chunk_size: int = None, chunk_overlap: int = None):
        self.db = db
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or self.DEFAULT_CHUNK_OVERLAP
    
    def chunk_document(self, document_id: int, force_rechunk: bool = False) -> Dict:
        """
        Chunk a document's extracted text
        
        Args:
            document_id: DocumentUpload ID
            force_rechunk: If True, delete existing chunks and re-chunk
        
        Returns:
            dict: Result with chunk count and status
        """
        try:
            # Get document
            document = self.db.query(DocumentUpload).filter(
                DocumentUpload.id == document_id
            ).first()
            
            if not document:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found"
                }
            
            # Check if already chunked
            existing_chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).count()
            
            if existing_chunks > 0 and not force_rechunk:
                return {
                    "success": True,
                    "message": f"Document already chunked ({existing_chunks} chunks)",
                    "chunk_count": existing_chunks,
                    "skipped": True
                }
            
            # Delete existing chunks if force_rechunk
            if force_rechunk and existing_chunks > 0:
                self.db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == document_id
                ).delete()
                self.db.commit()
            
            # Get extraction log with text
            extraction_log = None
            if document.extraction_id:
                extraction_log = self.db.query(ExtractionLog).filter(
                    ExtractionLog.id == document.extraction_id
                ).first()
            
            # Get text from extraction log
            text = None
            if extraction_log and extraction_log.extracted_text:
                text = extraction_log.extracted_text
            else:
                return {
                    "success": False,
                    "error": "No extracted text found for document. Please ensure extraction is complete."
                }
            
            # Chunk the text
            chunks = self._chunk_text(
                text=text,
                document_id=document_id,
                extraction_log_id=extraction_log.id if extraction_log else None,
                property_id=document.property_id,
                period_id=document.period_id,
                document_type=document.document_type
            )
            
            # Save chunks to database
            chunk_count = 0
            for chunk_data in chunks:
                chunk = DocumentChunk(
                    document_id=document_id,
                    extraction_log_id=chunk_data.get('extraction_log_id'),
                    chunk_index=chunk_data['chunk_index'],
                    chunk_text=chunk_data['chunk_text'],
                    chunk_size=len(chunk_data['chunk_text']),
                    chunk_metadata=chunk_data.get('metadata'),
                    property_id=chunk_data.get('property_id'),
                    period_id=chunk_data.get('period_id'),
                    document_type=chunk_data.get('document_type')
                )
                self.db.add(chunk)
                chunk_count += 1
            
            self.db.commit()
            
            logger.info(f"Chunked document {document_id} into {chunk_count} chunks")
            
            return {
                "success": True,
                "chunk_count": chunk_count,
                "document_id": document_id,
                "message": f"Successfully chunked document into {chunk_count} chunks"
            }
            
        except Exception as e:
            logger.error(f"Error chunking document {document_id}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _chunk_text(
        self,
        text: str,
        document_id: int,
        extraction_log_id: Optional[int] = None,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None,
        document_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Split text into chunks with overlap
        
        Args:
            text: Text to chunk
            document_id: Document ID
            extraction_log_id: Extraction log ID
            property_id: Property ID
            period_id: Period ID
            document_type: Document type
        
        Returns:
            List of chunk dictionaries
        """
        if not text or len(text.strip()) == 0:
            return []
        
        # Clean text
        text = text.strip()
        
        # Try to split by paragraphs first (better semantic boundaries)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If paragraph fits in current chunk, add it
            if len(current_chunk) + len(para) + 1 <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                # Save current chunk if it exists
                if current_chunk:
                    chunks.append({
                        'chunk_index': chunk_index,
                        'chunk_text': current_chunk,
                        'extraction_log_id': extraction_log_id,
                        'property_id': property_id,
                        'period_id': period_id,
                        'document_type': document_type,
                        'metadata': {
                            'chunk_method': 'paragraph',
                            'char_count': len(current_chunk)
                        }
                    })
                    chunk_index += 1
                
                # Start new chunk with overlap
                if chunk_index > 0 and self.chunk_overlap > 0:
                    # Add overlap from previous chunk
                    overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = para
                
                # If single paragraph is too large, split by sentences
                if len(current_chunk) > self.chunk_size:
                    chunks.extend(self._split_large_paragraph(
                        current_chunk,
                        chunk_index,
                        extraction_log_id,
                        property_id,
                        period_id,
                        document_type
                    ))
                    chunk_index += len(chunks) - chunk_index
                    current_chunk = ""
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                'chunk_index': chunk_index,
                'chunk_text': current_chunk,
                'extraction_log_id': extraction_log_id,
                'property_id': property_id,
                'period_id': period_id,
                'document_type': document_type,
                'metadata': {
                    'chunk_method': 'paragraph',
                    'char_count': len(current_chunk)
                }
            })
        
        return chunks
    
    def _split_large_paragraph(
        self,
        text: str,
        start_index: int,
        extraction_log_id: Optional[int],
        property_id: Optional[int],
        period_id: Optional[int],
        document_type: Optional[str]
    ) -> List[Dict]:
        """Split a large paragraph by sentences"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        chunk_index = start_index
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    chunks.append({
                        'chunk_index': chunk_index,
                        'chunk_text': current_chunk,
                        'extraction_log_id': extraction_log_id,
                        'property_id': property_id,
                        'period_id': period_id,
                        'document_type': document_type,
                        'metadata': {
                            'chunk_method': 'sentence',
                            'char_count': len(current_chunk)
                        }
                    })
                    chunk_index += 1
                
                # Add overlap
                if chunk_index > start_index and self.chunk_overlap > 0:
                    overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                else:
                    current_chunk = sentence
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                'chunk_index': chunk_index,
                'chunk_text': current_chunk,
                'extraction_log_id': extraction_log_id,
                'property_id': property_id,
                'period_id': period_id,
                'document_type': document_type,
                'metadata': {
                    'chunk_method': 'sentence',
                    'char_count': len(current_chunk)
                }
            })
        
        return chunks
    
    def chunk_all_documents(self, force_rechunk: bool = False) -> Dict:
        """
        Chunk all documents that have extracted text
        
        Args:
            force_rechunk: If True, re-chunk even if already chunked
        
        Returns:
            dict: Summary of chunking results
        """
        # Get all documents with completed extraction
        documents = self.db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == 'completed'
        ).all()
        
        results = {
            "total_documents": len(documents),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_chunks": 0,
            "errors": []
        }
        
        for doc in documents:
            result = self.chunk_document(doc.id, force_rechunk=force_rechunk)
            
            if result.get('success'):
                if result.get('skipped'):
                    results["skipped"] += 1
                else:
                    results["successful"] += 1
                    results["total_chunks"] += result.get('chunk_count', 0)
            else:
                results["failed"] += 1
                results["errors"].append({
                    "document_id": doc.id,
                    "file_name": doc.file_name,
                    "error": result.get('error')
                })
        
        return results

