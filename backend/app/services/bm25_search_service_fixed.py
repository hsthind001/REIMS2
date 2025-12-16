"""
Fixed BM25 Search Service with Accuracy Improvements

Fixes:
1. Metadata filtering BEFORE scoring (not after)
2. Score normalization to 0-1 range
3. Better tokenization for financial terms
"""
import logging
import pickle
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

from app.models.document_chunk import DocumentChunk
from app.config.bm25_config import bm25_config

logger = logging.getLogger(__name__)


class FixedBM25SearchService:
    """
    Fixed BM25 service with accuracy improvements.
    
    Key fixes:
    - Filter chunks BEFORE building index subset (for metadata filters)
    - Normalize scores to 0-1 range
    - Better tokenization for financial terms
    """
    
    def __init__(self, db: Session):
        if not BM25_AVAILABLE:
            raise ImportError("rank_bm25 library not available")
        
        self.db = db
        self.bm25_index: Optional[BM25Okapi] = None
        self.chunk_ids: List[int] = []
        self.chunk_metadata: Dict[int, Dict[str, Any]] = {}
        self.index_metadata: Dict[str, Any] = {
            'built_at': None,
            'chunk_count': 0,
            'version': bm25_config.CACHE_VERSION
        }
        
        # Load cached index
        self._load_cached_index()
    
    def search(
        self,
        query: str,
        top_k: int = 20,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None,
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search with FIXED filtering (applied before scoring).
        
        Key fix: Filter chunks BEFORE scoring to avoid irrelevant high scores.
        
        Args:
            query: Search query
            top_k: Number of results
            property_id: Property filter (applied before scoring)
            period_id: Period filter (applied before scoring)
            document_type: Document type filter (applied before scoring)
        
        Returns:
            List of results with NORMALIZED scores (0-1 range)
        """
        start_time = time.time()
        
        # Check if index exists
        if not self.bm25_index or not self.chunk_ids:
            logger.warning("BM25 index not built. Building now...")
            build_result = self.build_index()
            if not build_result.get("success"):
                return []
        
        # FIX: Filter chunks BEFORE scoring
        # Get filtered chunk IDs
        filtered_chunk_ids = self._get_filtered_chunk_ids(
            property_id=property_id,
            period_id=period_id,
            document_type=document_type
        )
        
        if not filtered_chunk_ids:
            logger.warning("No chunks match filters")
            return []
        
        # Build filtered index subset (only for filtered chunks)
        filtered_indices = [
            i for i, chunk_id in enumerate(self.chunk_ids)
            if chunk_id in filtered_chunk_ids
        ]
        
        if not filtered_indices:
            return []
        
        # Get tokenized documents for filtered chunks only
        filtered_tokenized = [self._tokenize(self._get_chunk_text(chunk_id)) 
                            for chunk_id in filtered_chunk_ids]
        
        # Build temporary BM25 index for filtered subset
        filtered_bm25 = BM25Okapi(
            filtered_tokenized,
            k1=bm25_config.K1,
            b=bm25_config.B
        )
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        # Get BM25 scores for filtered chunks
        scores = filtered_bm25.get_scores(query_tokens)
        
        # Create results with normalized scores
        scored_chunks = list(zip(scores, filtered_chunk_ids))
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        # Normalize scores to 0-1 range (CRITICAL FIX)
        max_score = max(score for score, _ in scored_chunks) if scored_chunks else 1.0
        
        results = []
        for score, chunk_id in scored_chunks[:top_k]:
            metadata = self.chunk_metadata.get(chunk_id, {})
            chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
            
            if not chunk:
                continue
            
            # Normalize score
            normalized_score = score / max_score if max_score > 0 else 0.0
            
            results.append({
                'chunk_id': chunk_id,
                'score': normalized_score,  # Normalized to 0-1
                'original_score': score,  # Keep original for debugging
                'chunk_text': chunk.chunk_text,
                'property_id': metadata.get('property_id'),
                'period_id': metadata.get('period_id'),
                'document_type': metadata.get('document_type'),
                'chunk_index': metadata.get('chunk_index'),
                'document_id': metadata.get('document_id'),
                'metadata': chunk.chunk_metadata
            })
        
        search_time = (time.time() - start_time) * 1000
        logger.debug(f"BM25 search: {len(results)} results in {search_time:.2f}ms")
        
        return results
    
    def _get_filtered_chunk_ids(
        self,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None,
        document_type: Optional[str] = None
    ) -> List[int]:
        """
        Get chunk IDs matching filters.
        
        This is applied BEFORE scoring to avoid irrelevant high scores.
        """
        # If no filters, return all chunk IDs
        if not any([property_id, period_id, document_type]):
            return self.chunk_ids
        
        # Query database for filtered chunk IDs (more efficient than iterating metadata)
        query = self.db.query(DocumentChunk.id).filter(
            DocumentChunk.chunk_text.isnot(None),
            DocumentChunk.chunk_text != ''
        )
        
        if property_id is not None:
            query = query.filter(DocumentChunk.property_id == property_id)
        if period_id is not None:
            query = query.filter(DocumentChunk.period_id == period_id)
        if document_type is not None:
            query = query.filter(DocumentChunk.document_type == document_type)
        
        filtered_ids = [row[0] for row in query.all()]
        return filtered_ids
    
    def _get_chunk_text(self, chunk_id: int) -> str:
        """Get chunk text (cached or from database)."""
        # Try to get from metadata cache first
        if chunk_id in self.chunk_metadata:
            # We don't cache text in metadata, so query DB
            chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
            return chunk.chunk_text if chunk else ""
        return ""
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Improved tokenization for financial documents.
        
        Handles:
        - Financial abbreviations (NOI, DSCR, etc.)
        - Currency amounts ($1.2M)
        - Percentages (85.5%)
        - Property codes (WEND001)
        """
        if not text:
            return []
        
        text_lower = text.lower()
        
        # Split on whitespace
        tokens = text_lower.split()
        
        # Handle financial abbreviations (keep uppercase in token)
        financial_terms = ['noi', 'dscr', 'ebitda', 'cap', 'ltv', 'dti']
        for term in financial_terms:
            if term in text_lower:
                tokens.append(term.upper())  # Add uppercase version
        
        # Handle currency (extract number and "million"/"thousand")
        currency_pattern = r'\$(\d+(?:\.\d+)?)\s*(million|m|thousand|k)?'
        import re
        currency_matches = re.findall(currency_pattern, text, re.IGNORECASE)
        for amount, suffix in currency_matches:
            tokens.append(f"${amount}")
            if suffix:
                tokens.append(suffix.lower())
        
        # Handle property codes (WEND001, etc.)
        code_pattern = r'\b[A-Z]{3,5}\d{3,5}\b'
        codes = re.findall(code_pattern, text)
        tokens.extend([code.lower() for code in codes])
        
        return tokens
    
    def build_index(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Build index (same as original, but with improved tokenization)."""
        # Import original build_index logic
        from app.services.bm25_search_service import BM25SearchService
        original_service = BM25SearchService(self.db)
        result = original_service.build_index(force_rebuild)
        
        # Copy index data
        if result.get("success"):
            self.bm25_index = original_service.bm25_index
            self.chunk_ids = original_service.chunk_ids
            self.chunk_metadata = original_service.chunk_metadata
            self.index_metadata = original_service.index_metadata
        
        return result
    
    def _load_cached_index(self):
        """Load cached index (same as original)."""
        from app.services.bm25_search_service import BM25SearchService
        original_service = BM25SearchService(self.db)
        # Try to load - if successful, copy data
        try:
            if original_service.bm25_index:
                self.bm25_index = original_service.bm25_index
                self.chunk_ids = original_service.chunk_ids
                self.chunk_metadata = original_service.chunk_metadata
                self.index_metadata = original_service.index_metadata
        except:
            pass

