"""
Vector Store Manager for NLQ System with Temporal Support

Manages Qdrant vector store with:
- Document embeddings (reconciliation rules, formulas, etc.)
- Query embeddings (semantic caching)
- Temporal metadata for time-aware retrieval
- Hybrid search (vector + BM25)
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import hashlib
import json

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, Range, Match
SearchParams, MatchValue
)
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from loguru import logger

from app.config.nlq_config import nlq_config


class VectorStoreManager:
    """
    Manages vector store operations with temporal awareness

    Features:
    - Temporal metadata tagging
    - Hybrid vector + BM25 search
    - Time-based filtering
    - Automatic reranking
    """

    def __init__(self):
        """Initialize vector store manager"""
        self.client = self._init_qdrant_client()
        self.embedder = self._init_embedder()
        self.bm25_index = None  # Lazy loaded
        self.bm25_corpus = []
        self._ensure_collections()

    def _init_qdrant_client(self) -> QdrantClient:
        """Initialize Qdrant client"""
        try:
            if nlq_config.QDRANT_API_KEY:
                # Cloud deployment
                client = QdrantClient(
                    url=f"https://{nlq_config.QDRANT_HOST}",
                    api_key=nlq_config.QDRANT_API_KEY
                )
            else:
                # Local deployment
                client = QdrantClient(
                    host=nlq_config.QDRANT_HOST,
                    port=nlq_config.QDRANT_PORT
                )
            logger.info(f"✅ Connected to Qdrant at {nlq_config.QDRANT_HOST}:{nlq_config.QDRANT_PORT}")
            return client
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            raise

    def _init_embedder(self) -> SentenceTransformer:
        """Initialize embedding model"""
        try:
            if nlq_config.EMBEDDING_PROVIDER == "huggingface":
                model = SentenceTransformer(nlq_config.HUGGINGFACE_MODEL)
                logger.info(f"✅ Loaded HuggingFace embedder: {nlq_config.HUGGINGFACE_MODEL}")
            else:
                # Default to BGE large
                model = SentenceTransformer("BAAI/bge-large-en-v1.5")
                logger.info("✅ Loaded BGE-large embedder")
            return model
        except Exception as e:
            logger.error(f"❌ Failed to load embedder: {e}")
            raise

    def _ensure_collections(self):
        """Ensure all required collections exist"""
        collections = [
            nlq_config.QDRANT_DOCUMENTS_COLLECTION,
            nlq_config.QDRANT_RULES_COLLECTION,
            nlq_config.QDRANT_FORMULAS_COLLECTION,
            nlq_config.QDRANT_QUERIES_COLLECTION
        ]

        vector_size = self.embedder.get_sentence_embedding_dimension()

        for collection_name in collections:
            try:
                self.client.get_collection(collection_name)
                logger.debug(f"Collection {collection_name} already exists")
            except:
                # Create collection
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created collection: {collection_name}")

    def add_document(
        self,
        text: str,
        metadata: Dict[str, Any],
        collection_name: Optional[str] = None
    ) -> str:
        """
        Add a document to the vector store with temporal metadata

        Args:
            text: Document text content
            metadata: Metadata including temporal information
                {
                    "source": str,
                    "category": str,
                    "year": int (optional),
                    "month": int (optional),
                    "period_start": str (optional),
                    "period_end": str (optional),
                    "statement_type": str (optional)
                }
            collection_name: Target collection (default: documents)

        Returns:
            Document ID
        """
        if collection_name is None:
            collection_name = nlq_config.QDRANT_DOCUMENTS_COLLECTION

        # Generate embedding
        embedding = self.embedder.encode(text).tolist()

        # Generate unique ID
        doc_id = hashlib.md5(
            f"{text[:100]}{metadata.get('source', '')}{datetime.now().isoformat()}".encode()
        ).hexdigest()

        # Add temporal metadata
        payload = {
            "text": text,
            **metadata,
            "created_at": datetime.now().isoformat(),
            "text_length": len(text)
        }

        # Insert into Qdrant
        self.client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=doc_id,
                    vector=embedding,
                    payload=payload
                )
            ]
        )

        logger.debug(f"Added document {doc_id} to {collection_name}")
        return doc_id

    def add_documents_batch(
        self,
        documents: List[Dict[str, Any]],
        collection_name: Optional[str] = None
    ) -> List[str]:
        """
        Add multiple documents in batch

        Args:
            documents: List of dicts with 'text' and 'metadata' keys
            collection_name: Target collection

        Returns:
            List of document IDs
        """
        if collection_name is None:
            collection_name = nlq_config.QDRANT_DOCUMENTS_COLLECTION

        # Generate embeddings for all documents
        texts = [doc["text"] for doc in documents]
        embeddings = self.embedder.encode(texts, show_progress_bar=True)

        # Prepare points
        points = []
        doc_ids = []

        for i, doc in enumerate(documents):
            doc_id = hashlib.md5(
                f"{doc['text'][:100]}{doc.get('metadata', {}).get('source', '')}{i}".encode()
            ).hexdigest()
            doc_ids.append(doc_id)

            payload = {
                "text": doc["text"],
                **doc.get("metadata", {}),
                "created_at": datetime.now().isoformat(),
                "text_length": len(doc["text"])
            }

            points.append(
                PointStruct(
                    id=doc_id,
                    vector=embeddings[i].tolist(),
                    payload=payload
                )
            )

        # Batch insert
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )

        logger.info(f"✅ Added {len(doc_ids)} documents to {collection_name}")
        return doc_ids

    def search(
        self,
        query: str,
        collection_name: Optional[str] = None,
        temporal_filters: Optional[Dict[str, Any]] = None,
        top_k: int = None,
        score_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Vector search with optional temporal filtering

        Args:
            query: Search query text
            collection_name: Collection to search
            temporal_filters: Temporal constraints
                {
                    "year": int,
                    "month": int,
                    "start_date": str,
                    "end_date": str
                }
            top_k: Number of results
            score_threshold: Minimum similarity score

        Returns:
            List of search results with scores
        """
        if collection_name is None:
            collection_name = nlq_config.QDRANT_DOCUMENTS_COLLECTION

        if top_k is None:
            top_k = nlq_config.VECTOR_SEARCH_TOP_K

        if score_threshold is None:
            score_threshold = nlq_config.VECTOR_SEARCH_SCORE_THRESHOLD

        # Generate query embedding
        query_embedding = self.embedder.encode(query).tolist()

        # Build filters
        filter_conditions = []

        if temporal_filters:
            if "year" in temporal_filters:
                filter_conditions.append(
                    FieldCondition(
                        key="year",
                        match=Match(value=temporal_filters["year"])
                    )
                )

            if "month" in temporal_filters:
                filter_conditions.append(
                    FieldCondition(
                        key="month",
                        match=Match(value=temporal_filters["month"])
                    )
                )

            # Date range filter
            if "start_date" in temporal_filters and "end_date" in temporal_filters:
                # This requires period_start and period_end fields in metadata
                filter_conditions.append(
                    FieldCondition(
                        key="period_end",
                        range=Range(gte=temporal_filters["start_date"])
                    )
                )
                filter_conditions.append(
                    FieldCondition(
                        key="period_start",
                        range=Range(lte=temporal_filters["end_date"])
                    )
                )

        query_filter = Filter(must=filter_conditions) if filter_conditions else None

        # Perform search
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=top_k,
            score_threshold=score_threshold
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "text": result.payload.get("text", ""),
                "metadata": {k: v for k, v in result.payload.items() if k != "text"},
                "score": result.score
            })

        logger.debug(f"Vector search returned {len(formatted_results)} results")
        return formatted_results

    def hybrid_search(
        self,
        query: str,
        collection_name: Optional[str] = None,
        temporal_filters: Optional[Dict[str, Any]] = None,
        alpha: float = None,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector and BM25

        Args:
            query: Search query
            collection_name: Collection to search
            temporal_filters: Temporal constraints
            alpha: Weight for vector vs BM25 (0=BM25 only, 1=vector only)
            top_k: Number of final results

        Returns:
            Ranked search results
        """
        if alpha is None:
            alpha = nlq_config.HYBRID_ALPHA

        if top_k is None:
            top_k = nlq_config.RERANKER_TOP_K

        # 1. Vector search
        vector_results = self.search(
            query=query,
            collection_name=collection_name,
            temporal_filters=temporal_filters,
            top_k=top_k * 2  # Get more candidates for fusion
        )

        # 2. BM25 search (if enabled)
        if nlq_config.ENABLE_HYBRID_SEARCH and alpha < 1.0:
            bm25_results = self._bm25_search(query, collection_name, temporal_filters, top_k * 2)

            # 3. Reciprocal Rank Fusion
            fused_results = self._reciprocal_rank_fusion(
                [vector_results, bm25_results],
                [alpha, 1 - alpha]
            )
        else:
            fused_results = vector_results

        # 4. Rerank (if enabled)
        if nlq_config.ENABLE_RERANKING:
            final_results = self._rerank(query, fused_results, top_k)
        else:
            final_results = fused_results[:top_k]

        return final_results

    def _bm25_search(
        self,
        query: str,
        collection_name: str,
        temporal_filters: Optional[Dict],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """BM25 keyword search"""
        # For simplicity, retrieve all documents and apply BM25
        # In production, this should use a dedicated BM25 index

        # Get all documents from collection (cached)
        if not hasattr(self, '_corpus_cache') or self._corpus_cache_collection != collection_name:
            all_docs = self.client.scroll(
                collection_name=collection_name,
                limit=10000  # Adjust based on collection size
            )[0]

            self._corpus_cache = all_docs
            self._corpus_cache_collection = collection_name
            self._bm25_texts = [doc.payload.get("text", "") for doc in all_docs]
            self._bm25_index = BM25Okapi([text.split() for text in self._bm25_texts])

        # Apply temporal filters
        filtered_docs = self._apply_temporal_filters(self._corpus_cache, temporal_filters)

        # BM25 scoring
        query_tokens = query.split()
        doc_scores = self._bm25_index.get_scores(query_tokens)

        # Get indices of filtered docs
        filtered_indices = [self._corpus_cache.index(doc) for doc in filtered_docs]
        filtered_scores = [(i, doc_scores[i]) for i in filtered_indices]

        # Sort and get top k
        top_results = sorted(filtered_scores, key=lambda x: x[1], reverse=True)[:top_k]

        # Format results
        bm25_results = []
        for idx, score in top_results:
            doc = self._corpus_cache[idx]
            bm25_results.append({
                "id": doc.id,
                "text": doc.payload.get("text", ""),
                "metadata": {k: v for k, v in doc.payload.items() if k != "text"},
                "score": score
            })

        return bm25_results

    def _apply_temporal_filters(self, docs: List, filters: Optional[Dict]) -> List:
        """Apply temporal filters to document list"""
        if not filters:
            return docs

        filtered = []
        for doc in docs:
            payload = doc.payload
            match = True

            if "year" in filters and payload.get("year") != filters["year"]:
                match = False

            if "month" in filters and payload.get("month") != filters["month"]:
                match = False

            # Add more filter logic as needed

            if match:
                filtered.append(doc)

        return filtered

    def _reciprocal_rank_fusion(
        self,
        results_lists: List[List[Dict]],
        weights: List[float],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion algorithm

        Args:
            results_lists: List of search result lists
            weights: Weights for each result list
            k: RRF constant (typically 60)

        Returns:
            Fused and ranked results
        """
        # Combine scores using RRF
        doc_scores = {}

        for results, weight in zip(results_lists, weights):
            for rank, result in enumerate(results, start=1):
                doc_id = result["id"]
                rrf_score = weight / (k + rank)

                if doc_id in doc_scores:
                    doc_scores[doc_id]["score"] += rrf_score
                else:
                    doc_scores[doc_id] = {
                        **result,
                        "score": rrf_score
                    }

        # Sort by combined score
        fused_results = sorted(
            doc_scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )

        return fused_results

    def _rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using cross-encoder

        Args:
            query: Original query
            results: Search results to rerank
            top_k: Number of final results

        Returns:
            Reranked results
        """
        try:
            from FlagEmbedding import FlagReranker

            # Lazy load reranker
            if not hasattr(self, '_reranker'):
                self._reranker = FlagReranker(
                    nlq_config.RERANKER_MODEL,
                    use_fp16=True
                )

            # Prepare pairs for reranking
            pairs = [[query, result["text"]] for result in results]

            # Get reranking scores
            scores = self._reranker.compute_score(pairs, normalize=True)

            # Update scores
            for i, result in enumerate(results):
                result["rerank_score"] = scores[i] if isinstance(scores, list) else scores
                result["original_score"] = result["score"]
                result["score"] = scores[i] if isinstance(scores, list) else scores

            # Sort by rerank score
            reranked = sorted(results, key=lambda x: x["score"], reverse=True)

            return reranked[:top_k]

        except Exception as e:
            logger.warning(f"Reranking failed: {e}. Returning original results.")
            return results[:top_k]

    def delete_collection(self, collection_name: str):
        """Delete a collection"""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vector_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}


# Singleton instance
vector_store_manager = VectorStoreManager()
