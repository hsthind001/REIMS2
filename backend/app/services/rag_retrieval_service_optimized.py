"""
Optimized RAG Retrieval Service

Performance optimizations:
1. Batch enrichment with eager loading (eliminates N+1 queries)
2. PostgreSQL vector similarity using pgvector (if available)
3. Parallel hybrid search execution
4. Embedding caching
5. Optimized database queries with proper indexes
"""
import logging
import math
import time
import hashlib
import json
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, func, text
from app.models.document_chunk import DocumentChunk
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Try to import services
try:
    from app.services.bm25_search_service import BM25SearchService
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

try:
    from app.services.pinecone_service import PineconeService
    from app.config.pinecone_config import pinecone_config
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

try:
    from app.services.rrf_service import RRFService
    RRF_AVAILABLE = True
except ImportError:
    RRF_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
except ImportError:
    REDIS_AVAILABLE = False
    redis_client = None


class OptimizedRAGRetrievalService:
    """
    Optimized RAG Retrieval Service with performance improvements.
    
    Key optimizations:
    - Batch enrichment (eliminates N+1 queries)
    - Parallel hybrid search
    - Embedding caching
    - Optimized database queries
    """
    
    def __init__(self, db: Session, embedding_service: EmbeddingService = None):
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService(db)
        
        # Initialize services
        self.pinecone_service = None
        self.use_pinecone = False
        self.bm25_service = None
        self.rrf_service = None
        
        if PINECONE_AVAILABLE:
            try:
                if pinecone_config.is_initialized() or pinecone_config.initialize():
                    self.pinecone_service = PineconeService()
                    self.use_pinecone = True
                    logger.info("OptimizedRAGRetrievalService initialized with Pinecone")
            except Exception as e:
                logger.warning(f"Pinecone initialization failed: {e}")
        
        if BM25_AVAILABLE:
            try:
                self.bm25_service = BM25SearchService(db)
                logger.info("OptimizedRAGRetrievalService initialized with BM25")
            except Exception as e:
                logger.warning(f"BM25 initialization failed: {e}")
        
        if RRF_AVAILABLE:
            try:
                self.rrf_service = RRFService()
                logger.info("OptimizedRAGRetrievalService initialized with RRF")
            except Exception as e:
                logger.warning(f"RRF initialization failed: {e}")
        
        # Check if pgvector is available
        self.pgvector_available = self._check_pgvector()
    
    def _check_pgvector(self) -> bool:
        """Check if pgvector extension is available."""
        try:
            result = self.db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            return result.scalar() is not None
        except Exception:
            return False
    
    def _get_cached_embedding(self, query: str) -> Optional[List[float]]:
        """
        Get cached embedding if available.
        
        Args:
            query: Query text
        
        Returns:
            Cached embedding or None
        """
        if not REDIS_AVAILABLE or not redis_client:
            return None
        
        try:
            query_hash = hashlib.md5(query.encode()).hexdigest()
            cached = redis_client.get(f"embedding:{query_hash}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.debug(f"Cache lookup failed: {e}")
        
        return None
    
    def _cache_embedding(self, query: str, embedding: List[float]):
        """
        Cache embedding for future use.
        
        Args:
            query: Query text
            embedding: Embedding vector
        """
        if not REDIS_AVAILABLE or not redis_client:
            return
        
        try:
            query_hash = hashlib.md5(query.encode()).hexdigest()
            redis_client.setex(
                f"embedding:{query_hash}",
                3600,  # 1 hour TTL
                json.dumps(embedding)
            )
        except Exception as e:
            logger.debug(f"Cache store failed: {e}")
    
    def _generate_embedding_cached(self, query: str) -> List[float]:
        """
        Generate embedding with caching.
        
        Args:
            query: Query text
        
        Returns:
            Embedding vector
        """
        # Check cache first
        cached = self._get_cached_embedding(query)
        if cached:
            return cached
        
        # Generate new embedding
        embedding = self.embedding_service.generate_embedding(query)
        
        # Cache it
        if embedding:
            self._cache_embedding(query, embedding)
        
        return embedding
    
    def _enrich_chunks_batch(
        self,
        chunk_ids: List[int]
    ) -> Dict[int, Dict]:
        """
        Batch enrich chunks with related data using eager loading.
        
        Eliminates N+1 query problem by loading all related data in single query.
        
        Args:
            chunk_ids: List of chunk IDs to enrich
        
        Returns:
            Dict mapping chunk_id to enriched data:
            {
                chunk_id: {
                    'chunk': DocumentChunk,
                    'document': DocumentUpload,
                    'property': Property,
                    'period': FinancialPeriod
                }
            }
        """
        if not chunk_ids:
            return {}
        
        # Single query with eager loading
        chunks = self.db.query(DocumentChunk)\
            .options(
                joinedload(DocumentChunk.document),
                joinedload(DocumentChunk.property),
                joinedload(DocumentChunk.period)
            )\
            .filter(DocumentChunk.id.in_(chunk_ids))\
            .all()
        
        # Build enrichment map
        enrichment_map = {}
        for chunk in chunks:
            enrichment_map[chunk.id] = {
                'chunk': chunk,
                'document': chunk.document if hasattr(chunk, 'document') else None,
                'property': chunk.property if hasattr(chunk, 'property') else None,
                'period': chunk.period if hasattr(chunk, 'period') else None
            }
        
        return enrichment_map
    
    def _format_enriched_result(
        self,
        chunk_id: int,
        similarity: float,
        enrichment: Dict,
        retrieval_method: str,
        additional_data: Optional[Dict] = None
    ) -> Dict:
        """
        Format enriched chunk data into result dictionary.
        
        Args:
            chunk_id: Chunk ID
            similarity: Similarity score
            enrichment: Enrichment data from _enrich_chunks_batch
            retrieval_method: Method used ('pinecone', 'postgresql', 'bm25', 'hybrid')
            additional_data: Additional data to include
        
        Returns:
            Formatted result dictionary
        """
        chunk = enrichment.get('chunk')
        document = enrichment.get('document')
        property_obj = enrichment.get('property')
        period = enrichment.get('period')
        
        result = {
            'chunk_id': chunk_id,
            'document_id': chunk.document_id if chunk else None,
            'chunk_index': chunk.chunk_index if chunk else None,
            'chunk_text': chunk.chunk_text if chunk else None,
            'similarity': similarity,
            'property_code': property_obj.property_code if property_obj else None,
            'property_name': property_obj.property_name if property_obj else None,
            'period': f"{period.period_year}-{str(period.period_month).zfill(2)}" if period else None,
            'document_type': chunk.document_type if chunk else None,
            'file_name': document.file_name if document else None,
            'metadata': chunk.chunk_metadata if chunk and chunk.chunk_metadata else {},
            'retrieval_method': retrieval_method
        }
        
        if additional_data:
            result.update(additional_data)
        
        return result
    
    def _retrieve_with_pinecone_optimized(
        self,
        query: str,
        top_k: int,
        property_id: Optional[int],
        period_id: Optional[int],
        document_type: Optional[str],
        min_similarity: float
    ) -> List[Dict]:
        """
        Optimized Pinecone retrieval with batch enrichment.
        
        Args:
            query: Query text
            top_k: Number of results
            property_id: Property filter
            period_id: Period filter
            document_type: Document type filter
            min_similarity: Minimum similarity
        
        Returns:
            List of enriched results
        """
        start_time = time.time()
        
        # Generate embedding (with cache)
        query_embedding = self._generate_embedding_cached(query)
        if not query_embedding:
            raise ValueError("Could not generate query embedding")
        
        # Build metadata filter
        filter_dict = {}
        if property_id:
            filter_dict['property_id'] = property_id
        if document_type:
            filter_dict['document_type'] = document_type
        if period_id:
            # Get period info (cache this too if needed)
            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.id == period_id
            ).first()
            if period:
                filter_dict['period_year'] = period.period_year
                filter_dict['period_month'] = period.period_month
        
        # Query Pinecone
        query_top_k = max(top_k * 2, 20)
        result = self.pinecone_service.query_vectors(
            query_vector=query_embedding,
            top_k=query_top_k,
            namespace=document_type if document_type else None,
            filter=filter_dict if filter_dict else None
        )
        
        if not result.get("success"):
            raise Exception(f"Pinecone query failed: {result.get('error')}")
        
        # Extract chunk IDs
        matches = result.get("matches", [])
        chunk_ids = []
        match_data = {}  # chunk_id -> {score, vector_id}
        
        for match in matches:
            similarity = match.get("score", 0.0)
            if similarity < min_similarity:
                continue
            
            vector_id = match.get("id", "")
            try:
                chunk_id = int(vector_id.replace("chunk-", ""))
                chunk_ids.append(chunk_id)
                match_data[chunk_id] = {
                    'score': similarity,
                    'vector_id': vector_id
                }
            except (ValueError, AttributeError):
                continue
        
        if not chunk_ids:
            return []
        
        # Batch enrich all chunks
        enrichment_map = self._enrich_chunks_batch(chunk_ids)
        
        # Format results
        results = []
        for chunk_id in chunk_ids:
            if chunk_id not in enrichment_map:
                continue
            
            enrichment = enrichment_map[chunk_id]
            similarity = match_data[chunk_id]['score']
            
            results.append(self._format_enriched_result(
                chunk_id=chunk_id,
                similarity=similarity,
                enrichment=enrichment,
                retrieval_method='pinecone'
            ))
        
        # Sort and return top_k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        elapsed = time.time() - start_time
        logger.debug(f"Pinecone retrieval: {len(results)} results in {elapsed:.3f}s")
        
        return results[:top_k]
    
    def _retrieve_with_postgresql_optimized(
        self,
        query: str,
        top_k: int,
        property_id: Optional[int],
        period_id: Optional[int],
        document_type: Optional[str],
        min_similarity: float
    ) -> List[Dict]:
        """
        Optimized PostgreSQL retrieval using pgvector if available.
        
        Args:
            query: Query text
            top_k: Number of results
            property_id: Property filter
            period_id: Period filter
            document_type: Document type filter
            min_similarity: Minimum similarity
        
        Returns:
            List of enriched results
        """
        start_time = time.time()
        
        # Generate embedding (with cache)
        query_embedding = self._generate_embedding_cached(query)
        if not query_embedding:
            logger.warning("Could not generate embedding, falling back to text search")
            return []
        
        # Use pgvector if available (much faster)
        if self.pgvector_available:
            return self._retrieve_with_pgvector(
                query_embedding, top_k, property_id, period_id, document_type, min_similarity
            )
        
        # Fallback to Python-based similarity (slower but works)
        return self._retrieve_with_postgresql_python(
            query_embedding, top_k, property_id, period_id, document_type, min_similarity
        )
    
    def _retrieve_with_pgvector(
        self,
        query_embedding: List[float],
        top_k: int,
        property_id: Optional[int],
        period_id: Optional[int],
        document_type: Optional[str],
        min_similarity: float
    ) -> List[Dict]:
        """
        Retrieve using pgvector extension (fast vector similarity).
        
        Requires: pgvector extension and embedding_vector column.
        """
        # Build WHERE clause
        where_clauses = ["dc.embedding_vector IS NOT NULL"]
        params = {'embedding': str(query_embedding)}
        
        if property_id:
            where_clauses.append("dc.property_id = :property_id")
            params['property_id'] = property_id
        
        if period_id:
            where_clauses.append("dc.period_id = :period_id")
            params['period_id'] = period_id
        
        if document_type:
            where_clauses.append("dc.document_type = :document_type")
            params['document_type'] = document_type
        
        where_sql = " AND ".join(where_clauses)
        
        # SQL query with pgvector cosine similarity
        sql = f"""
        SELECT 
            dc.id,
            1 - (dc.embedding_vector <=> :embedding::vector) as similarity
        FROM document_chunks dc
        WHERE {where_sql}
        ORDER BY dc.embedding_vector <=> :embedding::vector
        LIMIT :limit
        """
        
        params['limit'] = top_k * 2  # Get more for filtering
        
        try:
            result = self.db.execute(text(sql), params)
            rows = result.fetchall()
            
            # Extract chunk IDs and similarities
            chunk_data = {}
            for row in rows:
                chunk_id, similarity = row
                if similarity >= min_similarity:
                    chunk_data[chunk_id] = similarity
            
            if not chunk_data:
                return []
            
            # Batch enrich
            enrichment_map = self._enrich_chunks_batch(list(chunk_data.keys()))
            
            # Format results
            results = []
            for chunk_id, similarity in chunk_data.items():
                if chunk_id not in enrichment_map:
                    continue
                
                results.append(self._format_enriched_result(
                    chunk_id=chunk_id,
                    similarity=similarity,
                    enrichment=enrichment_map[chunk_id],
                    retrieval_method='postgresql_pgvector'
                ))
            
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"pgvector query failed: {e}, falling back to Python")
            return self._retrieve_with_postgresql_python(
                query_embedding, top_k, property_id, period_id, document_type, min_similarity
            )
    
    def _retrieve_with_postgresql_python(
        self,
        query_embedding: List[float],
        top_k: int,
        property_id: Optional[int],
        period_id: Optional[int],
        document_type: Optional[str],
        min_similarity: float
    ) -> List[Dict]:
        """
        Fallback: Python-based similarity calculation.
        
        Note: This is slower but works without pgvector.
        For better performance, use pgvector or limit chunk count.
        """
        # Build query with filters
        chunk_query = self.db.query(DocumentChunk).filter(
            DocumentChunk.embedding.isnot(None)
        )
        
        if property_id:
            chunk_query = chunk_query.filter(DocumentChunk.property_id == property_id)
        if period_id:
            chunk_query = chunk_query.filter(DocumentChunk.period_id == period_id)
        if document_type:
            chunk_query = chunk_query.filter(DocumentChunk.document_type == document_type)
        
        # Limit to reasonable number for Python calculation
        # If too many chunks, consider using pgvector or Pinecone
        chunks = chunk_query.limit(1000).all()  # Limit for performance
        
        if not chunks:
            return []
        
        # Calculate similarities
        chunk_scores = {}
        for chunk in chunks:
            if not chunk.embedding:
                continue
            
            similarity = self._cosine_similarity(query_embedding, chunk.embedding)
            if similarity >= min_similarity:
                chunk_scores[chunk.id] = similarity
        
        if not chunk_scores:
            return []
        
        # Get top-k chunk IDs
        sorted_chunk_ids = sorted(
            chunk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        chunk_ids = [chunk_id for chunk_id, _ in sorted_chunk_ids]
        
        # Batch enrich
        enrichment_map = self._enrich_chunks_batch(chunk_ids)
        
        # Format results
        results = []
        for chunk_id, similarity in sorted_chunk_ids:
            if chunk_id not in enrichment_map:
                continue
            
            results.append(self._format_enriched_result(
                chunk_id=chunk_id,
                similarity=similarity,
                enrichment=enrichment_map[chunk_id],
                retrieval_method='postgresql_python'
            ))
        
        return results
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _retrieve_hybrid_parallel(
        self,
        query: str,
        top_k: int,
        property_id: Optional[int],
        period_id: Optional[int],
        document_type: Optional[str],
        min_similarity: float,
        bm25_weight: float,
        use_pinecone: Optional[bool]
    ) -> List[Dict]:
        """
        Parallel hybrid search combining BM25 and semantic results.
        
        Executes both searches in parallel for better performance.
        
        Args:
            query: Query text
            top_k: Number of results
            property_id: Property filter
            period_id: Period filter
            document_type: Document type filter
            min_similarity: Minimum similarity
            bm25_weight: Weight for BM25 (0-1)
            use_pinecone: Use Pinecone for semantic search
        
        Returns:
            Combined results with weighted scores
        """
        start_time = time.time()
        
        # Execute searches in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit BM25 search
            bm25_future = None
            if self.bm25_service:
                bm25_future = executor.submit(
                    self._retrieve_with_bm25_optimized,
                    query, top_k * 2, property_id, period_id, document_type
                )
            
            # Submit semantic search
            semantic_future = executor.submit(
                self._retrieve_with_pinecone_optimized if use_pinecone else self._retrieve_with_postgresql_optimized,
                query, top_k * 2, property_id, period_id, document_type, min_similarity
            )
            
            # Wait for results
            bm25_results = []
            semantic_results = []
            
            if bm25_future:
                try:
                    bm25_results = bm25_future.result(timeout=2.0)
                except Exception as e:
                    logger.warning(f"BM25 search failed: {e}")
            
            try:
                semantic_results = semantic_future.result(timeout=3.0)
            except Exception as e:
                logger.warning(f"Semantic search failed: {e}")
        
        # Combine results
        combined = self._combine_hybrid_results(
            bm25_results, semantic_results, bm25_weight
        )
        
        elapsed = time.time() - start_time
        logger.debug(f"Parallel hybrid search: {len(combined)} results in {elapsed:.3f}s")
        
        return combined[:top_k]
    
    def _retrieve_with_bm25_optimized(
        self,
        query: str,
        top_k: int,
        property_id: Optional[int],
        period_id: Optional[int],
        document_type: Optional[str]
    ) -> List[Dict]:
        """
        Optimized BM25 retrieval with batch enrichment.
        """
        if not self.bm25_service:
            return []
        
        # Get BM25 results
        bm25_results = self.bm25_service.search(
            query=query,
            top_k=top_k * 2,
            property_id=property_id,
            period_id=period_id,
            document_type=document_type
        )
        
        if not bm25_results:
            return []
        
        # Extract chunk IDs
        chunk_ids = [r['chunk_id'] for r in bm25_results]
        
        # Batch enrich
        enrichment_map = self._enrich_chunks_batch(chunk_ids)
        
        # Normalize scores
        max_score = max(r['score'] for r in bm25_results) if bm25_results else 1.0
        
        # Format results
        results = []
        for bm25_result in bm25_results:
            chunk_id = bm25_result['chunk_id']
            if chunk_id not in enrichment_map:
                continue
            
            normalized_score = bm25_result['score'] / max_score if max_score > 0 else 0
            
            results.append(self._format_enriched_result(
                chunk_id=chunk_id,
                similarity=normalized_score,
                enrichment=enrichment_map[chunk_id],
                retrieval_method='bm25',
                additional_data={'bm25_score': bm25_result['score']}
            ))
        
        return results
    
    def _combine_hybrid_results(
        self,
        bm25_results: List[Dict],
        semantic_results: List[Dict],
        bm25_weight: float
    ) -> List[Dict]:
        """
        Combine BM25 and semantic results with weighted scoring.
        
        Args:
            bm25_results: BM25 search results
            semantic_results: Semantic search results
            bm25_weight: Weight for BM25 (0-1)
        
        Returns:
            Combined and sorted results
        """
        # Build score map
        chunk_scores = {}
        
        # Add BM25 results
        for result in bm25_results:
            chunk_id = result['chunk_id']
            chunk_scores[chunk_id] = {
                'bm25_score': result.get('bm25_score', result.get('similarity', 0)),
                'semantic_score': 0,
                'data': result
            }
        
        # Add semantic results
        for result in semantic_results:
            chunk_id = result['chunk_id']
            semantic_score = result.get('similarity', 0)
            
            if chunk_id in chunk_scores:
                chunk_scores[chunk_id]['semantic_score'] = semantic_score
                # Merge data (prefer semantic for metadata)
                chunk_scores[chunk_id]['data'].update(result)
            else:
                chunk_scores[chunk_id] = {
                    'bm25_score': 0,
                    'semantic_score': semantic_score,
                    'data': result
                }
        
        # Calculate combined scores
        combined_results = []
        for chunk_id, scores in chunk_scores.items():
            combined_score = (
                bm25_weight * scores['bm25_score'] +
                (1 - bm25_weight) * scores['semantic_score']
            )
            
            result = scores['data'].copy()
            result['similarity'] = combined_score
            result['bm25_score'] = scores['bm25_score']
            result['semantic_score'] = scores['semantic_score']
            result['retrieval_method'] = 'hybrid'
            
            combined_results.append(result)
        
        # Sort by combined score
        combined_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return combined_results
    
    def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: int = 5,
        property_id: Optional[int] = None,
        period_id: Optional[int] = None,
        document_type: Optional[str] = None,
        min_similarity: float = 0.3,
        use_pinecone: Optional[bool] = None,
        use_bm25: bool = False,
        bm25_weight: float = 0.5,
        use_rrf: bool = False
    ) -> List[Dict]:
        """
        Optimized retrieval with all performance improvements.
        
        Args:
            query: Query text
            top_k: Number of results
            property_id: Property filter
            period_id: Period filter
            document_type: Document type filter
            min_similarity: Minimum similarity
            use_pinecone: Use Pinecone (None = auto)
            use_bm25: Enable BM25
            bm25_weight: BM25 weight for hybrid (0-1)
            use_rrf: Use RRF fusion
        
        Returns:
            List of enriched results
        """
        start_time = time.time()
        
        try:
            # Hybrid search with parallel execution
            if use_bm25 and self.bm25_service:
                results = self._retrieve_hybrid_parallel(
                    query=query,
                    top_k=top_k,
                    property_id=property_id,
                    period_id=period_id,
                    document_type=document_type,
                    min_similarity=min_similarity,
                    bm25_weight=bm25_weight,
                    use_pinecone=use_pinecone if use_pinecone is not None else self.use_pinecone
                )
            # Semantic search only
            else:
                should_use_pinecone = use_pinecone if use_pinecone is not None else self.use_pinecone
                if should_use_pinecone and self.pinecone_service:
                    results = self._retrieve_with_pinecone_optimized(
                        query=query,
                        top_k=top_k,
                        property_id=property_id,
                        period_id=period_id,
                        document_type=document_type,
                        min_similarity=min_similarity
                    )
                else:
                    results = self._retrieve_with_postgresql_optimized(
                        query=query,
                        top_k=top_k,
                        property_id=property_id,
                        period_id=period_id,
                        document_type=document_type,
                        min_similarity=min_similarity
                    )
            
            elapsed = time.time() - start_time
            logger.info(f"Retrieval completed: {len(results)} results in {elapsed:.3f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            return []

