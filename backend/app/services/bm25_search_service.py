"""
BM25 Keyword Search Service

Provides BM25-based keyword search for document chunks to complement
semantic search. BM25 excels at exact term matching.
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
    logging.warning("rank_bm25 not available. Install with: pip install rank-bm25")

from app.models.document_chunk import DocumentChunk
from app.config.bm25_config import bm25_config

logger = logging.getLogger(__name__)


class BM25SearchService:
    """
    BM25 keyword search service for document chunks
    
    Features:
    - BM25Okapi algorithm for keyword matching
    - Index caching to disk for fast loading
    - Metadata filtering (property_id, document_type, period_id)
    - Auto-rebuild on threshold exceeded
    - Performance optimized (<100ms for top-20)
    """
    
    def __init__(self, db: Session):
        """
        Initialize BM25 search service
        
        Args:
            db: SQLAlchemy database session
        """
        if not BM25_AVAILABLE:
            raise ImportError("rank_bm25 library not available. Install with: pip install rank-bm25")
        
        self.db = db
        self.bm25_index: Optional[BM25Okapi] = None
        self.chunk_ids: List[int] = []
        self.chunk_metadata: Dict[int, Dict[str, Any]] = {}
        self.index_metadata: Dict[str, Any] = {
            'built_at': None,
            'chunk_count': 0,
            'version': bm25_config.CACHE_VERSION
        }
        
        # Try to load cached index
        self._load_cached_index()
    
    def build_index(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Build BM25 index from all document chunks
        
        Args:
            force_rebuild: Force rebuild even if cached index exists
        
        Returns:
            Dict with build statistics
        """
        start_time = time.time()
        logger.info("Building BM25 index from document chunks...")
        
        try:
            # Query all chunks from database
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.chunk_text.isnot(None),
                DocumentChunk.chunk_text != ''
            ).all()
            
            if not chunks:
                logger.warning("No document chunks found to index")
                return {
                    "success": False,
                    "error": "No chunks found",
                    "chunk_count": 0
                }
            
            # Prepare data for BM25
            tokenized_docs = []
            chunk_ids = []
            chunk_metadata = {}
            
            for chunk in chunks:
                # Tokenize chunk text
                tokens = self._tokenize(chunk.chunk_text)
                if tokens:  # Only add non-empty tokenized documents
                    tokenized_docs.append(tokens)
                    chunk_ids.append(chunk.id)
                    chunk_metadata[chunk.id] = {
                        'property_id': chunk.property_id,
                        'period_id': chunk.period_id,
                        'document_type': chunk.document_type,
                        'chunk_index': chunk.chunk_index,
                        'document_id': chunk.document_id
                    }
            
            if not tokenized_docs:
                logger.warning("No valid tokenized documents for indexing")
                return {
                    "success": False,
                    "error": "No valid documents to index",
                    "chunk_count": 0
                }
            
            # Build BM25 index
            self.bm25_index = BM25Okapi(
                tokenized_docs,
                k1=bm25_config.K1,
                b=bm25_config.B
            )
            
            # Store metadata
            self.chunk_ids = chunk_ids
            self.chunk_metadata = chunk_metadata
            self.index_metadata = {
                'built_at': datetime.now(),
                'chunk_count': len(chunk_ids),
                'version': bm25_config.CACHE_VERSION
            }
            
            # Save to cache
            self._save_index_to_cache()
            
            build_time = time.time() - start_time
            logger.info(f"BM25 index built successfully: {len(chunk_ids)} chunks in {build_time:.2f}s")
            
            return {
                "success": True,
                "chunk_count": len(chunk_ids),
                "build_time_seconds": build_time,
                "cache_path": str(bm25_config.get_cache_path())
            }
            
        except Exception as e:
            logger.error(f"Error building BM25 index: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def search(
        self,
        query: str,
        top_k: int = 20,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None,
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search document chunks using BM25
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            property_id: Filter by property ID (optional)
            period_id: Filter by period ID (optional)
            document_type: Filter by document type (optional)
        
        Returns:
            List of search results with scores
        """
        start_time = time.time()
        
        # Check if index exists
        if not self.bm25_index or not self.chunk_ids:
            logger.warning("BM25 index not built. Building now...")
            build_result = self.build_index()
            if not build_result.get("success"):
                logger.error("Failed to build BM25 index")
                return []
        
        # Check if rebuild needed (auto-rebuild)
        if bm25_config.AUTO_REBUILD:
            current_chunk_count = self.db.query(DocumentChunk).filter(
                DocumentChunk.chunk_text.isnot(None),
                DocumentChunk.chunk_text != ''
            ).count()
            
            if abs(current_chunk_count - self.index_metadata.get('chunk_count', 0)) >= bm25_config.REBUILD_THRESHOLD:
                logger.info(f"Chunk count changed by {abs(current_chunk_count - self.index_metadata.get('chunk_count', 0))}. Rebuilding index...")
                self.build_index(force_rebuild=True)
        
        try:
            # Tokenize query
            query_tokens = self._tokenize(query)
            if not query_tokens:
                logger.warning("Query tokenization resulted in empty tokens")
                return []
            
            # Get BM25 scores
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Create list of (score, chunk_id) pairs
            scored_chunks = list(zip(scores, self.chunk_ids))
            
            # Sort by score (descending)
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            
            # Apply metadata filters and build results
            results = []
            for score, chunk_id in scored_chunks:
                metadata = self.chunk_metadata.get(chunk_id, {})
                
                # Apply filters
                if property_id is not None and metadata.get('property_id') != property_id:
                    continue
                if period_id is not None and metadata.get('period_id') != period_id:
                    continue
                if document_type is not None and metadata.get('document_type') != document_type:
                    continue
                
                # Get chunk from database for full text
                chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
                if not chunk:
                    continue
                
                results.append({
                    'chunk_id': chunk_id,
                    'score': float(score),
                    'chunk_text': chunk.chunk_text,
                    'property_id': metadata.get('property_id'),
                    'period_id': metadata.get('period_id'),
                    'document_type': metadata.get('document_type'),
                    'chunk_index': metadata.get('chunk_index'),
                    'document_id': metadata.get('document_id'),
                    'metadata': chunk.chunk_metadata
                })
                
                # Stop when we have enough results
                if len(results) >= min(top_k, bm25_config.MAX_RESULTS):
                    break
            
            search_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Validate performance
            perf_validation = bm25_config.validate_performance(search_time, "bm25_search")
            if perf_validation.get('warning'):
                logger.warning(perf_validation['warning'])
            
            logger.debug(f"BM25 search completed: {len(results)} results in {search_time:.2f}ms")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in BM25 search: {e}", exc_info=True)
            return []
    
    def rebuild_index(self) -> Dict[str, Any]:
        """
        Force rebuild index from database
        
        Returns:
            Dict with rebuild statistics
        """
        logger.info("Force rebuilding BM25 index...")
        return self.build_index(force_rebuild=True)
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get index statistics
        
        Returns:
            Dict with index statistics
        """
        cache_path = bm25_config.get_cache_path()
        cache_exists = cache_path.exists()
        cache_size = cache_path.stat().st_size if cache_exists else 0
        
        return {
            'index_built': self.bm25_index is not None,
            'chunk_count': len(self.chunk_ids),
            'built_at': self.index_metadata.get('built_at').isoformat() if self.index_metadata.get('built_at') else None,
            'version': self.index_metadata.get('version'),
            'cache_exists': cache_exists,
            'cache_path': str(cache_path),
            'cache_size_bytes': cache_size,
            'cache_size_mb': round(cache_size / (1024 * 1024), 2) if cache_size > 0 else 0
        }
    
    def clear_cache(self) -> bool:
        """
        Clear cached index from disk
        
        Returns:
            True if cache cleared, False otherwise
        """
        try:
            cache_path = bm25_config.get_cache_path()
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cleared BM25 cache: {cache_path}")
                return True
            else:
                logger.info("No cache to clear")
                return False
        except Exception as e:
            logger.error(f"Error clearing cache: {e}", exc_info=True)
            return False
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text: lowercase, split on whitespace
        
        Args:
            text: Text to tokenize
        
        Returns:
            List of tokens
        """
        if not text:
            return []
        return text.lower().split()
    
    def _load_cached_index(self) -> bool:
        """
        Load cached index from disk
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            cache_path = bm25_config.get_cache_path()
            
            if not cache_path.exists():
                logger.debug("No cached BM25 index found")
                return False
            
            logger.info(f"Loading cached BM25 index from {cache_path}...")
            
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
            
            # Validate version
            if cached_data.get('version') != bm25_config.CACHE_VERSION:
                logger.warning(f"Cache version mismatch. Expected {bm25_config.CACHE_VERSION}, got {cached_data.get('version')}. Rebuilding...")
                return False
            
            # Load index components
            self.bm25_index = cached_data.get('bm25_index')
            self.chunk_ids = cached_data.get('chunk_ids', [])
            self.chunk_metadata = cached_data.get('chunk_metadata', {})
            self.index_metadata = cached_data.get('index_metadata', {})
            
            logger.info(f"Loaded BM25 index: {len(self.chunk_ids)} chunks (built at {self.index_metadata.get('built_at')})")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load cached BM25 index: {e}. Will rebuild on first search.")
            return False
    
    def _save_index_to_cache(self) -> bool:
        """
        Save index to disk cache
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if not self.bm25_index:
                logger.warning("No index to save")
                return False
            
            cache_path = bm25_config.get_cache_path()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Saving BM25 index to {cache_path}...")
            
            cached_data = {
                'bm25_index': self.bm25_index,
                'chunk_ids': self.chunk_ids,
                'chunk_metadata': self.chunk_metadata,
                'index_metadata': self.index_metadata,
                'version': bm25_config.CACHE_VERSION
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cached_data, f)
            
            logger.info(f"BM25 index saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save BM25 index to cache: {e}", exc_info=True)
            return False

