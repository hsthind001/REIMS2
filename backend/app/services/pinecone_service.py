"""
Pinecone Vector Operations Service

Handles vector operations (upsert, query, delete, update) with namespace management,
metadata filtering, and batch processing utilities.
"""
import logging
from typing import List, Dict, Optional, Any, Union
from sqlalchemy.orm import Session

from app.config.pinecone_config import pinecone_config, retry_with_backoff
from app.models.document_chunk import DocumentChunk

logger = logging.getLogger(__name__)


class PineconeService:
    """
    Service for Pinecone vector database operations
    
    Handles upsert, query, delete, and metadata update operations
    with proper namespace management and error handling.
    """
    
    # Document type to namespace mapping
    DOCUMENT_TYPE_NAMESPACES = {
        'balance_sheet': 'balance_sheet',
        'income_statement': 'income_statement',
        'cash_flow': 'cash_flow',
        'rent_roll': 'rent_roll'
    }
    
    def __init__(self, db: Session = None):
        """
        Initialize Pinecone service
        
        Args:
            db: SQLAlchemy database session (optional, for metadata lookups)
        """
        self.db = db
        self._ensure_initialized()
    
    def _ensure_initialized(self):
        """Ensure Pinecone is initialized"""
        if not pinecone_config.is_initialized():
            if not pinecone_config.initialize():
                raise RuntimeError("Failed to initialize Pinecone. Check configuration.")
    
    def _get_namespace(self, document_type: Optional[str] = None) -> str:
        """
        Get namespace for document type
        
        Args:
            document_type: Document type (balance_sheet, income_statement, etc.)
        
        Returns:
            Namespace string (defaults to empty string for default namespace)
        """
        if document_type and document_type in self.DOCUMENT_TYPE_NAMESPACES:
            return self.DOCUMENT_TYPE_NAMESPACES[document_type]
        return ""  # Default namespace
    
    def _build_metadata(
        self,
        property_id: Optional[int] = None,
        document_type: Optional[str] = None,
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        document_id: Optional[int] = None,
        chunk_index: Optional[int] = None,
        additional_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Build metadata dictionary for Pinecone vectors
        
        Args:
            property_id: Property ID
            document_type: Document type
            period_year: Financial period year
            period_month: Financial period month
            document_id: Document upload ID
            chunk_index: Chunk index within document
            additional_metadata: Additional metadata to include
        
        Returns:
            Metadata dictionary
        """
        metadata = {}
        
        if property_id is not None:
            metadata['property_id'] = property_id
        if document_type:
            metadata['document_type'] = document_type
        if period_year is not None:
            metadata['period_year'] = period_year
        if period_month is not None:
            metadata['period_month'] = period_month
        if document_id is not None:
            metadata['document_id'] = document_id
        if chunk_index is not None:
            metadata['chunk_index'] = chunk_index
        
        # Merge additional metadata
        if additional_metadata:
            metadata.update(additional_metadata)
        
        return metadata
    
    def _build_vector_id(self, chunk_id: int) -> str:
        """
        Build vector ID from chunk ID
        
        Args:
            chunk_id: Document chunk ID
        
        Returns:
            Vector ID string
        """
        return f"chunk_{chunk_id}"
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
    def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upsert vectors to Pinecone index
        
        Args:
            vectors: List of vector dictionaries with keys:
                - 'id': Vector ID (string)
                - 'values': Embedding vector (list of floats)
                - 'metadata': Metadata dictionary (optional)
            namespace: Namespace to upsert to (optional)
        
        Returns:
            Dict with success status and upserted count
        """
        if not vectors:
            return {"success": True, "upserted": 0, "message": "No vectors to upsert"}
        
        try:
            index = pinecone_config.index
            namespace = namespace or ""
            
            # Prepare vectors for upsert
            upsert_vectors = []
            for vec in vectors:
                if 'id' not in vec or 'values' not in vec:
                    logger.warning(f"Skipping invalid vector: missing 'id' or 'values'")
                    continue
                
                upsert_vectors.append({
                    'id': str(vec['id']),
                    'values': vec['values'],
                    'metadata': vec.get('metadata', {})
                })
            
            if not upsert_vectors:
                return {"success": False, "error": "No valid vectors to upsert"}
            
            # Upsert to Pinecone
            index.upsert(vectors=upsert_vectors, namespace=namespace)
            
            logger.info(f"Upserted {len(upsert_vectors)} vectors to namespace '{namespace}'")
            
            return {
                "success": True,
                "upserted": len(upsert_vectors),
                "namespace": namespace
            }
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "upserted": 0
            }
    
    def upsert_chunk(
        self,
        chunk_id: int,
        embedding: List[float],
        property_id: Optional[int] = None,
        document_type: Optional[str] = None,
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        document_id: Optional[int] = None,
        chunk_index: Optional[int] = None,
        additional_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Upsert a single document chunk to Pinecone
        
        Args:
            chunk_id: Document chunk ID
            embedding: Embedding vector
            property_id: Property ID
            document_type: Document type
            period_year: Financial period year
            period_month: Financial period month
            document_id: Document upload ID
            chunk_index: Chunk index within document
            additional_metadata: Additional metadata
        
        Returns:
            Dict with success status
        """
        vector_id = self._build_vector_id(chunk_id)
        namespace = self._get_namespace(document_type)
        metadata = self._build_metadata(
            property_id=property_id,
            document_type=document_type,
            period_year=period_year,
            period_month=period_month,
            document_id=document_id,
            chunk_index=chunk_index,
            additional_metadata=additional_metadata
        )
        
        return self.upsert_vectors(
            vectors=[{
                'id': vector_id,
                'values': embedding,
                'metadata': metadata
            }],
            namespace=namespace
        )
    
    def upsert_chunks_batch(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]]
    ) -> Dict[str, Any]:
        """
        Upsert multiple document chunks in batch
        
        Args:
            chunks: List of DocumentChunk objects
            embeddings: List of embedding vectors (same order as chunks)
        
        Returns:
            Dict with success status and summary
        """
        if len(chunks) != len(embeddings):
            return {
                "success": False,
                "error": f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings"
            }
        
        # Group by namespace for efficient batch upsert
        namespace_vectors = {}
        
        for chunk, embedding in zip(chunks, embeddings):
            if not embedding:
                logger.warning(f"Skipping chunk {chunk.id}: no embedding")
                continue
            
            namespace = self._get_namespace(chunk.document_type)
            vector_id = self._build_vector_id(chunk.id)
            
            metadata = self._build_metadata(
                property_id=chunk.property_id,
                document_type=chunk.document_type,
                period_year=chunk.period.period_year if chunk.period else None,
                period_month=chunk.period.period_month if chunk.period else None,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index
            )
            
            if namespace not in namespace_vectors:
                namespace_vectors[namespace] = []
            
            namespace_vectors[namespace].append({
                'id': vector_id,
                'values': embedding,
                'metadata': metadata
            })
        
        # Upsert each namespace
        results = {
            "success": True,
            "total_chunks": len(chunks),
            "namespaces": {},
            "errors": []
        }
        
        for namespace, vectors in namespace_vectors.items():
            result = self.upsert_vectors(vectors, namespace=namespace)
            results["namespaces"][namespace] = result
            
            if not result.get("success"):
                results["success"] = False
                results["errors"].append({
                    "namespace": namespace,
                    "error": result.get("error")
                })
        
        return results
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
    def query_vectors(
        self,
        query_vector: List[float],
        top_k: int = 5,
        namespace: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_values: bool = False
    ) -> Dict[str, Any]:
        """
        Query vectors using semantic search
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            namespace: Namespace to search in (optional)
            filter: Metadata filter dictionary (e.g., {"property_id": 1, "document_type": "balance_sheet"})
            include_metadata: Include metadata in results
            include_values: Include vector values in results
        
        Returns:
            Dict with matches and metadata
        """
        try:
            index = pinecone_config.index
            namespace = namespace or ""
            
            # Build filter expression if provided
            filter_expr = None
            if filter:
                filter_expr = self._build_filter_expression(filter)
            
            # Query Pinecone
            results = index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter_expr,
                include_metadata=include_metadata,
                include_values=include_values
            )
            
            # Format results
            matches = []
            for match in results.get('matches', []):
                match_data = {
                    'id': match.get('id'),
                    'score': match.get('score', 0.0)
                }
                
                if include_metadata and match.get('metadata'):
                    match_data['metadata'] = match['metadata']
                
                if include_values and match.get('values'):
                    match_data['values'] = match['values']
                
                matches.append(match_data)
            
            logger.info(f"Query returned {len(matches)} matches from namespace '{namespace}'")
            
            return {
                "success": True,
                "matches": matches,
                "namespace": namespace,
                "top_k": top_k
            }
            
        except Exception as e:
            logger.error(f"Failed to query vectors: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "matches": []
            }
    
    def _build_filter_expression(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Pinecone filter expression from metadata filter
        
        Args:
            filter_dict: Metadata filter dictionary
        
        Returns:
            Pinecone filter expression
        """
        # Pinecone uses $eq, $in, $gt, $gte, $lt, $lte operators
        # For simple equality, we can use direct key-value pairs
        filter_expr = {}
        
        for key, value in filter_dict.items():
            if value is not None:
                if isinstance(value, (list, tuple)):
                    filter_expr[key] = {"$in": value}
                elif isinstance(value, dict):
                    # Already a filter expression
                    filter_expr[key] = value
                else:
                    filter_expr[key] = {"$eq": value}
        
        return filter_expr if filter_expr else None
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
    def delete_vectors(
        self,
        vector_ids: Optional[List[str]] = None,
        namespace: Optional[str] = None,
        filter: Optional[Dict[str, Any]] = None,
        delete_all: bool = False
    ) -> Dict[str, Any]:
        """
        Delete vectors from Pinecone
        
        Args:
            vector_ids: List of vector IDs to delete (optional)
            namespace: Namespace to delete from (optional)
            filter: Metadata filter for deletion (optional)
            delete_all: If True, delete all vectors in namespace (use with caution)
        
        Returns:
            Dict with success status
        """
        try:
            index = pinecone_config.index
            namespace = namespace or ""
            
            if delete_all:
                if not namespace:
                    return {
                        "success": False,
                        "error": "delete_all requires a namespace"
                    }
                # Delete all vectors in namespace
                index.delete(delete_all=True, namespace=namespace)
                logger.warning(f"Deleted all vectors in namespace '{namespace}'")
                return {
                    "success": True,
                    "deleted": "all",
                    "namespace": namespace
                }
            
            if filter:
                filter_expr = self._build_filter_expression(filter)
                index.delete(filter=filter_expr, namespace=namespace)
                logger.info(f"Deleted vectors matching filter in namespace '{namespace}'")
                return {
                    "success": True,
                    "deleted": "filtered",
                    "namespace": namespace,
                    "filter": filter
                }
            
            if vector_ids:
                index.delete(ids=vector_ids, namespace=namespace)
                logger.info(f"Deleted {len(vector_ids)} vectors from namespace '{namespace}'")
                return {
                    "success": True,
                    "deleted": len(vector_ids),
                    "namespace": namespace
                }
            
            return {
                "success": False,
                "error": "Must provide vector_ids, filter, or delete_all=True"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete vectors: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_chunk(self, chunk_id: int, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete a single document chunk from Pinecone
        
        Args:
            chunk_id: Document chunk ID
            document_type: Document type for namespace (optional)
        
        Returns:
            Dict with success status
        """
        vector_id = self._build_vector_id(chunk_id)
        namespace = self._get_namespace(document_type)
        
        return self.delete_vectors(vector_ids=[vector_id], namespace=namespace)
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0)
    def update_metadata(
        self,
        vector_id: str,
        metadata: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update metadata for a vector without re-embedding
        
        Note: Pinecone doesn't support direct metadata updates.
        This method fetches the vector, updates metadata, and re-upserts.
        
        Args:
            vector_id: Vector ID
            metadata: New metadata dictionary
            namespace: Namespace (optional)
        
        Returns:
            Dict with success status
        """
        try:
            index = pinecone_config.index
            namespace = namespace or ""
            
            # Fetch existing vector
            fetch_result = index.fetch(ids=[vector_id], namespace=namespace)
            
            if vector_id not in fetch_result.get('vectors', {}):
                return {
                    "success": False,
                    "error": f"Vector {vector_id} not found"
                }
            
            vector_data = fetch_result['vectors'][vector_id]
            
            # Merge metadata
            existing_metadata = vector_data.get('metadata', {})
            existing_metadata.update(metadata)
            
            # Re-upsert with updated metadata
            index.upsert(
                vectors=[{
                    'id': vector_id,
                    'values': vector_data['values'],
                    'metadata': existing_metadata
                }],
                namespace=namespace
            )
            
            logger.info(f"Updated metadata for vector {vector_id} in namespace '{namespace}'")
            
            return {
                "success": True,
                "vector_id": vector_id,
                "namespace": namespace
            }
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_index_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get index statistics
        
        Args:
            namespace: Namespace to get stats for (optional)
        
        Returns:
            Dict with index statistics
        """
        try:
            index = pinecone_config.index
            stats = index.describe_index_stats()
            
            if namespace:
                namespace_stats = stats.get('namespaces', {}).get(namespace, {})
                return {
                    "success": True,
                    "namespace": namespace,
                    "vector_count": namespace_stats.get('vector_count', 0)
                }
            else:
                return {
                    "success": True,
                    "total_vector_count": stats.get('total_vector_count', 0),
                    "namespaces": {
                        ns: ns_stats.get('vector_count', 0)
                        for ns, ns_stats in stats.get('namespaces', {}).items()
                    }
                }
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

