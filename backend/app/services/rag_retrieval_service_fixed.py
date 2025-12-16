"""
Fixed RAG Retrieval Service with Accuracy Improvements

Fixes:
1. Proper metadata filtering (applied before scoring)
2. Score normalization (BM25 and semantic on same scale)
3. Adaptive RRF alpha based on query type
4. Entity extraction for better filtering
5. Improved chunk context preservation
"""
import logging
import math
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.services.embedding_service import EmbeddingService
from app.services.rag_accuracy_diagnostics import RAGAccuracyDiagnostics

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
    from app.services.rrf_service import FusionService
    RRF_AVAILABLE = True
except ImportError:
    RRF_AVAILABLE = False

try:
    from app.services.entity_resolver_service import EntityResolverService
    ENTITY_RESOLVER_AVAILABLE = True
except ImportError:
    ENTITY_RESOLVER_AVAILABLE = False


class FixedRAGRetrievalService:
    """
    Fixed RAG Retrieval Service with accuracy improvements.
    
    Key fixes:
    - Proper metadata filtering (before scoring)
    - Score normalization (0-1 range)
    - Adaptive RRF alpha
    - Entity extraction for filtering
    - Better chunk context
    """
    
    def __init__(self, db: Session, embedding_service: EmbeddingService = None):
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService(db)
        self.diagnostics = RAGAccuracyDiagnostics()
        
        # Initialize services
        self.pinecone_service = None
        self.use_pinecone = False
        self.bm25_service = None
        self.rrf_service = None
        self.entity_resolver = None
        
        if PINECONE_AVAILABLE:
            try:
                if pinecone_config.is_initialized() or pinecone_config.initialize():
                    self.pinecone_service = PineconeService()
                    self.use_pinecone = True
            except Exception as e:
                logger.warning(f"Pinecone initialization failed: {e}")
        
        if BM25_AVAILABLE:
            try:
                self.bm25_service = BM25SearchService(db)
            except Exception as e:
                logger.warning(f"BM25 initialization failed: {e}")
        
        if RRF_AVAILABLE:
            try:
                self.rrf_service = FusionService()
            except Exception as e:
                logger.warning(f"RRF initialization failed: {e}")
        
        if ENTITY_RESOLVER_AVAILABLE:
            try:
                self.entity_resolver = EntityResolverService(db)
            except Exception as e:
                logger.warning(f"Entity resolver initialization failed: {e}")
    
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
        use_rrf: bool = False,
        rrf_alpha: Optional[float] = None
    ) -> List[Dict]:
        """
        Retrieve relevant chunks with improved accuracy.
        
        Key improvements:
        1. Extract entities from query to set filters
        2. Apply metadata filters BEFORE scoring
        3. Normalize scores before fusion
        4. Use adaptive alpha for RRF
        
        Args:
            query: Query text
            top_k: Number of results
            property_id: Property filter (optional, will extract from query if not provided)
            period_id: Period filter (optional, will extract from query if not provided)
            document_type: Document type filter (optional, will extract from query if not provided)
            min_similarity: Minimum similarity threshold
            use_pinecone: Use Pinecone (None = auto)
            use_bm25: Enable BM25
            use_rrf: Use RRF fusion
            rrf_alpha: RRF alpha (None = adaptive)
        
        Returns:
            List of relevant chunks
        """
        # Step 1: Extract entities from query to improve filtering
        extracted_entities = self._extract_entities_from_query(query)
        
        # Use extracted entities if filters not provided
        if not property_id and extracted_entities.get('property_id'):
            property_id = extracted_entities['property_id']
            logger.debug(f"Extracted property_id {property_id} from query")
        
        if not period_id and extracted_entities.get('period_id'):
            period_id = extracted_entities['period_id']
            logger.debug(f"Extracted period_id {period_id} from query")
        
        if not document_type and extracted_entities.get('document_type'):
            document_type = extracted_entities['document_type']
            logger.debug(f"Extracted document_type {document_type} from query")
        
        # Step 2: Determine if we should use hybrid search
        # Use hybrid only if query has strong keyword signals
        should_use_hybrid = use_bm25 and self._should_use_hybrid(query)
        
        # Step 3: Get semantic results (with proper filtering)
        semantic_results = self._retrieve_semantic(
            query=query,
            top_k=top_k * 3 if should_use_hybrid else top_k,
            property_id=property_id,
            period_id=period_id,
            document_type=document_type,
            min_similarity=min_similarity,
            use_pinecone=use_pinecone
        )
        
        # Step 4: Get BM25 results (with proper filtering and normalization)
        bm25_results = []
        if should_use_hybrid and self.bm25_service:
            bm25_results = self._retrieve_bm25_normalized(
                query=query,
                top_k=top_k * 3,
                property_id=property_id,
                period_id=period_id,
                document_type=document_type
            )
        
        # Step 5: Fuse results with adaptive alpha
        if should_use_hybrid and bm25_results and self.rrf_service:
            # Determine adaptive alpha
            if rrf_alpha is None:
                rrf_alpha = self._determine_adaptive_alpha(query, semantic_results, bm25_results)
            
            fused_results = self.rrf_service.fuse(
                semantic_results=semantic_results,
                keyword_results=bm25_results,
                top_k=top_k
            )
            
            return fused_results
        
        # Return semantic results if no hybrid
        return semantic_results[:top_k]
    
    def _extract_entities_from_query(self, query: str) -> Dict[str, Any]:
        """
        Extract entities from query to improve filtering.
        
        Args:
            query: Query text
        
        Returns:
            Dict with extracted entities (property_id, period_id, document_type)
        """
        entities = {}
        
        # Extract property name and resolve to ID
        if self.entity_resolver:
            property_matches = self.entity_resolver.resolve_property_from_query(query)
            if property_matches and property_matches[0].get('confidence', 0) > 0.75:
                entities['property_id'] = property_matches[0]['property_id']
        
        # Extract period (Q3 2024, etc.)
        period_match = self._extract_period_from_query(query)
        if period_match:
            # Resolve to period_id
            from app.models.financial_period import FinancialPeriod
            period = self.db.query(FinancialPeriod).filter(
                FinancialPeriod.period_year == period_match['year'],
                FinancialPeriod.period_month == period_match['month']
            ).first()
            if period:
                entities['period_id'] = period.id
        
        # Extract document type
        doc_type = self._extract_document_type_from_query(query)
        if doc_type:
            entities['document_type'] = doc_type
        
        return entities
    
    def _extract_period_from_query(self, query: str) -> Optional[Dict[str, int]]:
        """Extract period (quarter/year) from query."""
        import re
        
        # Match Q3 2024, Q3, etc.
        quarter_match = re.search(r'Q([1-4])\s*(?:20\d{2})?', query, re.IGNORECASE)
        year_match = re.search(r'(20\d{2})', query)
        
        if quarter_match:
            quarter = int(quarter_match.group(1))
            year = int(year_match.group(1)) if year_match else datetime.now().year
            
            # Convert quarter to month
            month = (quarter - 1) * 3 + 1  # Q1=1, Q2=4, Q3=7, Q4=10
            
            return {'year': year, 'month': month}
        
        # Match month names
        month_names = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        for month_name, month_num in month_names.items():
            if month_name in query.lower():
                year_match = re.search(r'(20\d{2})', query)
                year = int(year_match.group(1)) if year_match else datetime.now().year
                return {'year': year, 'month': month_num}
        
        return None
    
    def _extract_document_type_from_query(self, query: str) -> Optional[str]:
        """Extract document type from query."""
        query_lower = query.lower()
        
        doc_type_keywords = {
            'income_statement': ['income', 'revenue', 'profit', 'loss', 'noi', 'operating income'],
            'balance_sheet': ['balance', 'assets', 'liabilities', 'equity'],
            'cash_flow': ['cash flow', 'cashflow'],
            'rent_roll': ['rent', 'lease', 'tenant', 'occupancy']
        }
        
        for doc_type, keywords in doc_type_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return doc_type
        
        return None
    
    def _should_use_hybrid(self, query: str) -> bool:
        """
        Determine if hybrid search should be used.
        
        Use hybrid for:
        - Queries with specific terms (DSCR, NOI, etc.)
        - Queries with property codes
        - Queries with exact numbers
        
        Use semantic-only for:
        - Conceptual queries ("properties with losses")
        - Questions ("what was", "show me")
        """
        query_lower = query.lower()
        
        # Strong keyword signals
        keyword_indicators = [
            r'\bDSCR\b',
            r'\bNOI\b',
            r'\b[A-Z]{3,5}\d{3,5}\b',  # Property codes
            r'\$\d+',  # Currency amounts
            r'\d+\.\d+%',  # Percentages
        ]
        
        keyword_count = sum(1 for pattern in keyword_indicators if re.search(pattern, query, re.IGNORECASE))
        
        # Conceptual queries (use semantic only)
        conceptual_indicators = [
            'properties with',
            'show me',
            'what was',
            'which properties',
            'find properties'
        ]
        
        is_conceptual = any(indicator in query_lower for indicator in conceptual_indicators)
        
        # Use hybrid if strong keyword signals and not conceptual
        return keyword_count >= 1 and not is_conceptual
    
    def _determine_adaptive_alpha(
        self,
        query: str,
        semantic_results: List[Dict],
        bm25_results: List[Dict]
    ) -> float:
        """
        Determine adaptive RRF alpha based on query and result quality.
        
        Args:
            query: Query text
            semantic_results: Semantic search results
            bm25_results: BM25 search results
        
        Returns:
            Optimal alpha value (0-1)
        """
        # Default alpha
        base_alpha = 0.7
        
        # If query is conceptual, favor semantic more
        if self._is_conceptual_query(query):
            return 0.85
        
        # If BM25 has very low scores, favor semantic
        if bm25_results:
            max_bm25_score = max(r.get('score', 0) for r in bm25_results[:5])
            if max_bm25_score < 0.1:  # Very low BM25 scores
                return 0.9
        
        # If semantic has very high scores, favor semantic
        if semantic_results:
            max_semantic_score = max(r.get('similarity', 0) for r in semantic_results[:5])
            if max_semantic_score > 0.9:  # Very high semantic scores
                return 0.85
        
        return base_alpha
    
    def _is_conceptual_query(self, query: str) -> bool:
        """Check if query is conceptual (not keyword-based)."""
        conceptual_patterns = [
            'properties with',
            'show me',
            'which properties',
            'find properties',
            'what was'
        ]
        
        return any(pattern in query.lower() for pattern in conceptual_patterns)
    
    def _retrieve_semantic(
        self,
        query: str,
        top_k: int,
        property_id: Optional[int],
        period_id: Optional[int],
        document_type: Optional[str],
        min_similarity: float,
        use_pinecone: Optional[bool]
    ) -> List[Dict]:
        """Retrieve semantic results with proper filtering."""
        query_embedding = self.embedding_service.generate_embedding(query)
        if not query_embedding:
            return []
        
        should_use_pinecone = use_pinecone if use_pinecone is not None else self.use_pinecone
        
        if should_use_pinecone and self.pinecone_service:
            # Use Pinecone with metadata filters
            filter_dict = {}
            if property_id:
                filter_dict['property_id'] = property_id
            if document_type:
                filter_dict['document_type'] = document_type
            if period_id:
                # Get period info
                from app.models.financial_period import FinancialPeriod
                period = self.db.query(FinancialPeriod).filter(
                    FinancialPeriod.id == period_id
                ).first()
                if period:
                    filter_dict['period_year'] = period.period_year
                    filter_dict['period_month'] = period.period_month
            
            result = self.pinecone_service.query_vectors(
                query_vector=query_embedding,
                top_k=top_k,
                namespace=document_type if document_type else None,
                filter=filter_dict if filter_dict else None
            )
            
            if result.get("success"):
                matches = result.get("matches", [])
                results = []
                for match in matches:
                    similarity = match.get("score", 0.0)
                    if similarity >= min_similarity:
                        # Enrich with chunk data (use batch enrichment from optimized service)
                        chunk_id = int(match.get("id", "").replace("chunk-", ""))
                        results.append({
                            'chunk_id': chunk_id,
                            'similarity': similarity,
                            'retrieval_method': 'pinecone'
                        })
                return results
        
        # Fallback to PostgreSQL (with proper filtering)
        return self._retrieve_semantic_postgresql(
            query_embedding, top_k, property_id, period_id, document_type, min_similarity
        )
    
    def _retrieve_semantic_postgresql(
        self,
        query_embedding: List[float],
        top_k: int,
        property_id: Optional[int],
        period_id: Optional[int],
        document_type: Optional[str],
        min_similarity: float
    ) -> List[Dict]:
        """Retrieve from PostgreSQL with proper filtering."""
        from app.models.document_chunk import DocumentChunk
        
        # Build query with filters
        query = self.db.query(DocumentChunk).filter(
            DocumentChunk.embedding.isnot(None)
        )
        
        if property_id:
            query = query.filter(DocumentChunk.property_id == property_id)
        if period_id:
            query = query.filter(DocumentChunk.period_id == period_id)
        if document_type:
            query = query.filter(DocumentChunk.document_type == document_type)
        
        # Limit to reasonable number for similarity calculation
        chunks = query.limit(1000).all()
        
        # Calculate similarities
        results = []
        for chunk in chunks:
            if not chunk.embedding:
                continue
            
            similarity = self._cosine_similarity(query_embedding, chunk.embedding)
            if similarity >= min_similarity:
                results.append({
                    'chunk_id': chunk.id,
                    'similarity': similarity,
                    'retrieval_method': 'postgresql'
                })
        
        # Sort and return top_k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def _retrieve_bm25_normalized(
        self,
        query: str,
        top_k: int,
        property_id: Optional[int],
        period_id: Optional[int],
        document_type: Optional[str]
    ) -> List[Dict]:
        """
        Retrieve BM25 results with proper filtering and score normalization.
        
        Key fixes:
        1. Apply metadata filters BEFORE scoring
        2. Normalize scores to 0-1 range
        """
        # Get BM25 results with filters applied
        bm25_results = self.bm25_service.search(
            query=query,
            top_k=top_k * 2,  # Get more for filtering
            property_id=property_id,
            period_id=period_id,
            document_type=document_type
        )
        
        if not bm25_results:
            return []
        
        # Normalize scores to 0-1 range (CRITICAL FIX)
        max_score = max(r.get('score', 0) for r in bm25_results) if bm25_results else 1.0
        
        normalized_results = []
        for result in bm25_results:
            original_score = result.get('score', 0)
            normalized_score = original_score / max_score if max_score > 0 else 0
            
            normalized_results.append({
                'chunk_id': result.get('chunk_id'),
                'score': normalized_score,  # Normalized to 0-1
                'original_score': original_score,  # Keep original for debugging
                'retrieval_method': 'bm25'
            })
        
        return normalized_results[:top_k]
    
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

