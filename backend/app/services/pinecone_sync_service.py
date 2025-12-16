"""
Pinecone Sync Service

Handles synchronization between PostgreSQL document_chunks and Pinecone vector database.
Maintains dual storage for redundancy and enables migration from PostgreSQL-only to hybrid.
"""
import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.document_chunk import DocumentChunk
from app.models.document_upload import DocumentUpload
from app.services.pinecone_service import PineconeService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class PineconeSyncService:
    """
    Service for syncing document chunks between PostgreSQL and Pinecone
    
    Maintains dual storage:
    - PostgreSQL: Full chunk data, metadata, relationships
    - Pinecone: Vectors for semantic search
    """
    
    def __init__(self, db: Session):
        """
        Initialize sync service
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.pinecone_service = PineconeService(db=db)
        self.embedding_service = EmbeddingService(db)
    
    def sync_chunk_to_pinecone(
        self,
        chunk_id: int,
        force_reembed: bool = False
    ) -> Dict[str, Any]:
        """
        Sync a single chunk from PostgreSQL to Pinecone
        
        Args:
            chunk_id: Document chunk ID
            force_reembed: If True, regenerate embedding even if exists
        
        Returns:
            Dict with sync status
        """
        try:
            # Get chunk from PostgreSQL
            chunk = self.db.query(DocumentChunk).filter(
                DocumentChunk.id == chunk_id
            ).first()
            
            if not chunk:
                return {
                    "success": False,
                    "error": f"Chunk {chunk_id} not found in PostgreSQL"
                }
            
            # Check if embedding exists
            if not chunk.embedding:
                if force_reembed:
                    # Generate embedding
                    embedding_result = self.embedding_service.embed_chunk(
                        chunk_id=chunk_id,
                        force_reembed=True
                    )
                    if not embedding_result.get("success"):
                        return {
                            "success": False,
                            "error": f"Failed to generate embedding: {embedding_result.get('error')}"
                        }
                    # Refresh chunk to get new embedding
                    self.db.refresh(chunk)
                else:
                    return {
                        "success": False,
                        "error": f"Chunk {chunk_id} has no embedding. Set force_reembed=True to generate."
                    }
            
            # Get period info if available
            period_year = None
            period_month = None
            if chunk.period:
                period_year = chunk.period.period_year
                period_month = chunk.period.period_month
            
            # Upsert to Pinecone
            result = self.pinecone_service.upsert_chunk(
                chunk_id=chunk.id,
                embedding=chunk.embedding,
                property_id=chunk.property_id,
                document_type=chunk.document_type,
                period_year=period_year,
                period_month=period_month,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index
            )
            
            if result.get("success"):
                logger.info(f"Synced chunk {chunk_id} to Pinecone")
                return {
                    "success": True,
                    "chunk_id": chunk_id,
                    "synced_to_pinecone": True
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to upsert to Pinecone: {result.get('error')}"
                }
            
        except Exception as e:
            logger.error(f"Error syncing chunk {chunk_id}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_document_to_pinecone(
        self,
        document_id: int,
        force_reembed: bool = False
    ) -> Dict[str, Any]:
        """
        Sync all chunks of a document to Pinecone
        
        Args:
            document_id: Document upload ID
            force_reembed: If True, regenerate embeddings even if they exist
        
        Returns:
            Dict with sync summary
        """
        try:
            # Get all chunks for document
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            if not chunks:
                return {
                    "success": False,
                    "error": f"No chunks found for document {document_id}"
                }
            
            # Filter chunks that need embedding
            chunks_to_sync = []
            for chunk in chunks:
                if not chunk.embedding:
                    if force_reembed:
                        # Generate embedding
                        self.embedding_service.embed_chunk(
                            chunk_id=chunk.id,
                            force_reembed=True
                        )
                        self.db.refresh(chunk)
                    else:
                        continue  # Skip chunks without embeddings
                chunks_to_sync.append(chunk)
            
            if not chunks_to_sync:
                return {
                    "success": False,
                    "error": f"No chunks with embeddings found for document {document_id}"
                }
            
            # Prepare embeddings
            embeddings = [chunk.embedding for chunk in chunks_to_sync]
            
            # Batch upsert to Pinecone
            result = self.pinecone_service.upsert_chunks_batch(
                chunks=chunks_to_sync,
                embeddings=embeddings
            )
            
            if result.get("success"):
                logger.info(f"Synced {len(chunks_to_sync)} chunks for document {document_id} to Pinecone")
                return {
                    "success": True,
                    "document_id": document_id,
                    "total_chunks": len(chunks),
                    "synced_chunks": len(chunks_to_sync),
                    "namespaces": result.get("namespaces", {})
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to sync to Pinecone: {result.get('error')}",
                    "errors": result.get("errors", [])
                }
            
        except Exception as e:
            logger.error(f"Error syncing document {document_id}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_all_chunks_to_pinecone(
        self,
        batch_size: int = 100,
        force_reembed: bool = False,
        property_id: Optional[int] = None,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync all chunks from PostgreSQL to Pinecone (migration utility)
        
        Args:
            batch_size: Number of chunks to process per batch
            force_reembed: If True, regenerate embeddings even if they exist
            property_id: Filter by property ID (optional)
            document_type: Filter by document type (optional)
        
        Returns:
            Dict with migration summary
        """
        try:
            # Build query
            query = self.db.query(DocumentChunk).filter(
                DocumentChunk.embedding.isnot(None)
            )
            
            if property_id:
                query = query.filter(DocumentChunk.property_id == property_id)
            
            if document_type:
                query = query.filter(DocumentChunk.document_type == document_type)
            
            # Get total count
            total_chunks = query.count()
            
            if total_chunks == 0:
                return {
                    "success": True,
                    "message": "No chunks with embeddings found to sync",
                    "total_chunks": 0,
                    "synced": 0
                }
            
            logger.info(f"Starting sync of {total_chunks} chunks to Pinecone...")
            
            # Process in batches
            synced_count = 0
            failed_count = 0
            errors = []
            
            offset = 0
            while offset < total_chunks:
                batch = query.offset(offset).limit(batch_size).all()
                
                if not batch:
                    break
                
                # Prepare embeddings
                embeddings = [chunk.embedding for chunk in batch]
                
                # Batch upsert
                result = self.pinecone_service.upsert_chunks_batch(
                    chunks=batch,
                    embeddings=embeddings
                )
                
                if result.get("success"):
                    synced_count += len(batch)
                    logger.info(f"Synced batch: {offset + 1}-{offset + len(batch)} of {total_chunks}")
                else:
                    failed_count += len(batch)
                    errors.extend(result.get("errors", []))
                    logger.error(f"Failed to sync batch: {offset + 1}-{offset + len(batch)}")
                
                offset += batch_size
            
            return {
                "success": failed_count == 0,
                "total_chunks": total_chunks,
                "synced": synced_count,
                "failed": failed_count,
                "errors": errors[:10] if errors else []  # Limit error list
            }
            
        except Exception as e:
            logger.error(f"Error syncing all chunks: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_new_chunk(
        self,
        chunk_id: int
    ) -> Dict[str, Any]:
        """
        Sync a newly created chunk to Pinecone
        
        This is called automatically when a new chunk is created with an embedding.
        
        Args:
            chunk_id: Document chunk ID
        
        Returns:
            Dict with sync status
        """
        return self.sync_chunk_to_pinecone(chunk_id=chunk_id, force_reembed=False)
    
    def remove_chunk_from_pinecone(
        self,
        chunk_id: int,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Remove a chunk from Pinecone (when deleted from PostgreSQL)
        
        Args:
            chunk_id: Document chunk ID
            document_type: Document type for namespace (optional)
        
        Returns:
            Dict with deletion status
        """
        try:
            result = self.pinecone_service.delete_chunk(
                chunk_id=chunk_id,
                document_type=document_type
            )
            
            if result.get("success"):
                logger.info(f"Removed chunk {chunk_id} from Pinecone")
            
            return result
            
        except Exception as e:
            logger.error(f"Error removing chunk {chunk_id} from Pinecone: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_sync_status(
        self,
        chunk_id: int
    ) -> Dict[str, Any]:
        """
        Verify if a chunk is synced to Pinecone
        
        Args:
            chunk_id: Document chunk ID
        
        Returns:
            Dict with sync status
        """
        try:
            # Get chunk from PostgreSQL
            chunk = self.db.query(DocumentChunk).filter(
                DocumentChunk.id == chunk_id
            ).first()
            
            if not chunk:
                return {
                    "success": False,
                    "error": f"Chunk {chunk_id} not found in PostgreSQL"
                }
            
            if not chunk.embedding:
                return {
                    "success": False,
                    "in_postgresql": True,
                    "has_embedding": False,
                    "in_pinecone": False,
                    "error": "Chunk has no embedding"
                }
            
            # Check if exists in Pinecone
            vector_id = self.pinecone_service._build_vector_id(chunk_id)
            namespace = self.pinecone_service._get_namespace(chunk.document_type)
            
            try:
                from app.config.pinecone_config import pinecone_config
                index = pinecone_config.index
                fetch_result = index.fetch(ids=[vector_id], namespace=namespace)
                
                in_pinecone = vector_id in fetch_result.get('vectors', {})
                
                return {
                    "success": True,
                    "chunk_id": chunk_id,
                    "in_postgresql": True,
                    "has_embedding": True,
                    "in_pinecone": in_pinecone,
                    "namespace": namespace
                }
            except Exception as e:
                logger.warning(f"Could not verify Pinecone status: {str(e)}")
                return {
                    "success": False,
                    "error": f"Could not verify Pinecone status: {str(e)}"
                }
            
        except Exception as e:
            logger.error(f"Error verifying sync status: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def reconcile_sync(
        self,
        document_id: Optional[int] = None,
        property_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Reconcile sync status between PostgreSQL and Pinecone
        
        Identifies chunks that are in PostgreSQL but not in Pinecone,
        and optionally syncs them.
        
        Args:
            document_id: Filter by document ID (optional)
            property_id: Filter by property ID (optional)
        
        Returns:
            Dict with reconciliation report
        """
        try:
            # Get chunks with embeddings from PostgreSQL
            query = self.db.query(DocumentChunk).filter(
                DocumentChunk.embedding.isnot(None)
            )
            
            if document_id:
                query = query.filter(DocumentChunk.document_id == document_id)
            
            if property_id:
                query = query.filter(DocumentChunk.property_id == property_id)
            
            chunks = query.all()
            
            if not chunks:
                return {
                    "success": True,
                    "total_chunks": 0,
                    "in_pinecone": 0,
                    "missing_in_pinecone": 0,
                    "missing_chunk_ids": []
                }
            
            # Check each chunk
            missing_chunk_ids = []
            in_pinecone_count = 0
            
            for chunk in chunks:
                vector_id = self.pinecone_service._build_vector_id(chunk.id)
                namespace = self.pinecone_service._get_namespace(chunk.document_type)
                
                try:
                    from app.config.pinecone_config import pinecone_config
                    index = pinecone_config.index
                    fetch_result = index.fetch(ids=[vector_id], namespace=namespace)
                    
                    if vector_id not in fetch_result.get('vectors', {}):
                        missing_chunk_ids.append(chunk.id)
                    else:
                        in_pinecone_count += 1
                except Exception:
                    # If we can't check, assume missing
                    missing_chunk_ids.append(chunk.id)
            
            return {
                "success": True,
                "total_chunks": len(chunks),
                "in_pinecone": in_pinecone_count,
                "missing_in_pinecone": len(missing_chunk_ids),
                "missing_chunk_ids": missing_chunk_ids[:100]  # Limit to first 100
            }
            
        except Exception as e:
            logger.error(f"Error reconciling sync: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

