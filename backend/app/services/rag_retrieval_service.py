"""
RAG Retrieval Service

Semantic search over document chunks using vector similarity
"""
import logging
import math
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.document_chunk import DocumentChunk
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RAGRetrievalService:
    """Service for retrieving relevant document chunks using semantic search"""
    
    def __init__(self, db: Session, embedding_service: EmbeddingService = None):
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService(db)
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
        
        Returns:
            Similarity score between -1 and 1
        """
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: int = 5,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None,
        document_type: Optional[str] = None,
        min_similarity: float = 0.3
    ) -> List[Dict]:
        """
        Retrieve relevant document chunks for a query
        
        Args:
            query: User's query text
            top_k: Number of top results to return
            property_id: Filter by property (optional)
            period_id: Filter by period (optional)
            document_type: Filter by document type (optional)
            min_similarity: Minimum similarity threshold (0-1)
        
        Returns:
            List of relevant chunks with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)
            
            if not query_embedding:
                logger.warning("Could not generate query embedding, falling back to text search")
                return self._fallback_text_search(query, top_k, property_id, period_id, document_type)
            
            # Build query for chunks
            chunk_query = self.db.query(DocumentChunk).filter(
                DocumentChunk.embedding.isnot(None)
            )
            
            # Apply filters
            if property_id:
                chunk_query = chunk_query.filter(DocumentChunk.property_id == property_id)
            
            if period_id:
                chunk_query = chunk_query.filter(DocumentChunk.period_id == period_id)
            
            if document_type:
                chunk_query = chunk_query.filter(DocumentChunk.document_type == document_type)
            
            # Get all chunks (we'll calculate similarity in Python)
            chunks = chunk_query.all()
            
            if not chunks:
                logger.warning("No chunks found with embeddings")
                return []
            
            # Calculate similarities
            results = []
            for chunk in chunks:
                if not chunk.embedding:
                    continue
                
                similarity = self.cosine_similarity(query_embedding, chunk.embedding)
                
                if similarity >= min_similarity:
                    # Get document and property info
                    document = self.db.query(DocumentUpload).filter(
                        DocumentUpload.id == chunk.document_id
                    ).first()
                    
                    property_obj = None
                    period = None
                    if chunk.property_id:
                        property_obj = self.db.query(Property).filter(
                            Property.id == chunk.property_id
                        ).first()
                    if chunk.period_id:
                        period = self.db.query(FinancialPeriod).filter(
                            FinancialPeriod.id == chunk.period_id
                        ).first()
                    
                    results.append({
                        'chunk_id': chunk.id,
                        'document_id': chunk.document_id,
                        'chunk_index': chunk.chunk_index,
                        'chunk_text': chunk.chunk_text,
                        'similarity': similarity,
                        'property_code': property_obj.property_code if property_obj else None,
                        'property_name': property_obj.property_name if property_obj else None,
                        'period': f"{period.period_year}-{str(period.period_month).zfill(2)}" if period else None,
                        'document_type': chunk.document_type,
                        'file_name': document.file_name if document else None,
                        'metadata': chunk.chunk_metadata
                    })
            
            # Sort by similarity (descending)
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Return top_k
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {e}")
            return []
    
    def _fallback_text_search(
        self,
        query: str,
        top_k: int,
        property_id: Optional[int],
        period_id: Optional[int],
        document_type: Optional[str]
    ) -> List[Dict]:
        """
        Fallback text-based search when embeddings unavailable
        
        Uses simple text matching
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        chunk_query = self.db.query(DocumentChunk)
        
        if property_id:
            chunk_query = chunk_query.filter(DocumentChunk.property_id == property_id)
        if period_id:
            chunk_query = chunk_query.filter(DocumentChunk.period_id == period_id)
        if document_type:
            chunk_query = chunk_query.filter(DocumentChunk.document_type == document_type)
        
        chunks = chunk_query.all()
        
        results = []
        for chunk in chunks:
            chunk_text_lower = chunk.chunk_text.lower()
            chunk_words = set(chunk_text_lower.split())
            
            # Calculate simple word overlap score
            common_words = query_words.intersection(chunk_words)
            if common_words:
                score = len(common_words) / max(len(query_words), 1)
                
                if score > 0.1:  # At least 10% word overlap
                    document = self.db.query(DocumentUpload).filter(
                        DocumentUpload.id == chunk.document_id
                    ).first()
                    
                    property_obj = None
                    period = None
                    if chunk.property_id:
                        property_obj = self.db.query(Property).filter(
                            Property.id == chunk.property_id
                        ).first()
                    if chunk.period_id:
                        period = self.db.query(FinancialPeriod).filter(
                            FinancialPeriod.id == chunk.period_id
                        ).first()
                    
                    results.append({
                        'chunk_id': chunk.id,
                        'document_id': chunk.document_id,
                        'chunk_index': chunk.chunk_index,
                        'chunk_text': chunk.chunk_text,
                        'similarity': score,
                        'property_code': property_obj.property_code if property_obj else None,
                        'property_name': property_obj.property_name if property_obj else None,
                        'period': f"{period.period_year}-{str(period.period_month).zfill(2)}" if period else None,
                        'document_type': chunk.document_type,
                        'file_name': document.file_name if document else None,
                        'metadata': chunk.chunk_metadata
                    })
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def get_chunk_context(self, chunk_ids: List[int]) -> str:
        """
        Get combined context from multiple chunks
        
        Args:
            chunk_ids: List of chunk IDs
        
        Returns:
            Combined text context
        """
        chunks = self.db.query(DocumentChunk).filter(
            DocumentChunk.id.in_(chunk_ids)
        ).order_by(DocumentChunk.chunk_index).all()
        
        context_parts = []
        for chunk in chunks:
            context_parts.append(f"[Chunk {chunk.chunk_index} from {chunk.document_type}]\n{chunk.chunk_text}")
        
        return "\n\n---\n\n".join(context_parts)

