"""
Embedding Service for RAG

Generates vector embeddings for document chunks using OpenAI or sentence-transformers
"""
import logging
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.models.document_chunk import DocumentChunk
from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Try to import sentence-transformers as fallback
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class EmbeddingService:
    """Service for generating embeddings"""
    
    # OpenAI embedding model
    OPENAI_MODEL = "text-embedding-3-small"  # 1536 dimensions, cheaper
    OPENAI_DIMENSION = 1536
    
    # Sentence-transformers model (fallback)
    SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"  # 384 dimensions, local
    
    def __init__(self, db: Session):
        self.db = db
        self.openai_client = None
        self.sentence_transformer = None
        self.embedding_method = None
        
        # Initialize OpenAI if available
        if OPENAI_AVAILABLE and hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.embedding_method = 'openai'
                logger.info("EmbeddingService initialized with OpenAI")
            except Exception as e:
                logger.warning(f"OpenAI initialization failed: {e}")
        
        # Fallback to sentence-transformers if OpenAI not available
        if not self.openai_client and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.sentence_transformer = SentenceTransformer(self.SENTENCE_TRANSFORMER_MODEL)
                self.embedding_method = 'sentence_transformers'
                logger.info("EmbeddingService initialized with sentence-transformers")
            except Exception as e:
                logger.warning(f"Sentence-transformers initialization failed: {e}")
        
        if not self.embedding_method:
            logger.warning("No embedding method available. Embeddings will not be generated.")
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
        
        Returns:
            List of floats (embedding vector) or None if unavailable
        """
        if not text or len(text.strip()) == 0:
            return None
        
        if self.embedding_method == 'openai' and self.openai_client:
            try:
                response = self.openai_client.embeddings.create(
                    model=self.OPENAI_MODEL,
                    input=text.strip()
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"OpenAI embedding generation failed: {e}")
                return None
        
        elif self.embedding_method == 'sentence_transformers' and self.sentence_transformer:
            try:
                embedding = self.sentence_transformer.encode(text.strip(), convert_to_numpy=False)
                return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
            except Exception as e:
                logger.error(f"Sentence-transformers embedding generation failed: {e}")
                return None
        
        return None
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts (batch processing)
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
        
        Returns:
            List of embeddings (same order as input texts)
        """
        if not texts:
            return []
        
        embeddings = []
        
        if self.embedding_method == 'openai' and self.openai_client:
            # OpenAI supports batch processing
            try:
                # Process in batches
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    # Filter out empty texts
                    batch_with_indices = [(idx, text) for idx, text in enumerate(batch) if text and text.strip()]
                    
                    if not batch_with_indices:
                        embeddings.extend([None] * len(batch))
                        continue
                    
                    batch_texts = [text for _, text in batch_with_indices]
                    batch_indices = [idx for idx, _ in batch_with_indices]
                    
                    response = self.openai_client.embeddings.create(
                        model=self.OPENAI_MODEL,
                        input=batch_texts
                    )
                    
                    # Map embeddings back to original positions
                    batch_embeddings = [None] * len(batch)
                    for idx, embedding_data in zip(batch_indices, response.data):
                        batch_embeddings[idx] = embedding_data.embedding
                    
                    embeddings.extend(batch_embeddings)
                
                return embeddings
            except Exception as e:
                logger.error(f"OpenAI batch embedding generation failed: {e}")
                return [None] * len(texts)
        
        elif self.embedding_method == 'sentence_transformers' and self.sentence_transformer:
            # Process in batches
            try:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    batch_embeddings = self.sentence_transformer.encode(
                        batch,
                        convert_to_numpy=False,
                        show_progress_bar=False
                    )
                    # Convert to list of lists
                    if hasattr(batch_embeddings, 'tolist'):
                        batch_embeddings = batch_embeddings.tolist()
                    embeddings.extend([list(emb) for emb in batch_embeddings])
                
                return embeddings
            except Exception as e:
                logger.error(f"Sentence-transformers batch embedding generation failed: {e}")
                return [None] * len(texts)
        
        return [None] * len(texts)
    
    def embed_chunk(self, chunk_id: int, force_reembed: bool = False) -> Dict:
        """
        Generate and store embedding for a document chunk
        
        Args:
            chunk_id: DocumentChunk ID
            force_reembed: If True, regenerate embedding even if exists
        
        Returns:
            dict: Result with success status
        """
        try:
            chunk = self.db.query(DocumentChunk).filter(
                DocumentChunk.id == chunk_id
            ).first()
            
            if not chunk:
                return {
                    "success": False,
                    "error": f"Chunk {chunk_id} not found"
                }
            
            # Check if already embedded
            if chunk.embedding and not force_reembed:
                return {
                    "success": True,
                    "message": "Chunk already embedded",
                    "skipped": True
                }
            
            # Generate embedding
            embedding = self.generate_embedding(chunk.chunk_text)
            
            if not embedding:
                return {
                    "success": False,
                    "error": "Failed to generate embedding (no embedding service available)"
                }
            
            # Store embedding
            chunk.embedding = embedding
            chunk.embedding_model = self.OPENAI_MODEL if self.embedding_method == 'openai' else self.SENTENCE_TRANSFORMER_MODEL
            chunk.embedding_dimension = len(embedding)
            
            self.db.commit()
            
            logger.info(f"Embedded chunk {chunk_id} using {self.embedding_method}")
            
            return {
                "success": True,
                "chunk_id": chunk_id,
                "embedding_dimension": len(embedding),
                "embedding_model": chunk.embedding_model
            }
            
        except Exception as e:
            logger.error(f"Error embedding chunk {chunk_id}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def embed_document_chunks(self, document_id: int, force_reembed: bool = False) -> Dict:
        """
        Generate embeddings for all chunks of a document
        
        Args:
            document_id: DocumentUpload ID
            force_reembed: If True, regenerate embeddings even if they exist
        
        Returns:
            dict: Summary of embedding results
        """
        chunks = self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).all()
        
        if not chunks:
            return {
                "success": False,
                "error": f"No chunks found for document {document_id}"
            }
        
        results = {
            "document_id": document_id,
            "total_chunks": len(chunks),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        # Filter chunks that need embedding
        chunks_to_embed = [
            chunk for chunk in chunks
            if not chunk.embedding or force_reembed
        ]
        
        if not chunks_to_embed:
            results["skipped"] = len(chunks)
            return results
        
        # Generate embeddings in batch
        texts = [chunk.chunk_text for chunk in chunks_to_embed]
        embeddings = self.generate_embeddings_batch(texts)
        
        # Store embeddings
        for chunk, embedding in zip(chunks_to_embed, embeddings):
            if embedding:
                chunk.embedding = embedding
                chunk.embedding_model = self.OPENAI_MODEL if self.embedding_method == 'openai' else self.SENTENCE_TRANSFORMER_MODEL
                chunk.embedding_dimension = len(embedding)
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "chunk_id": chunk.id,
                    "error": "Failed to generate embedding"
                })
        
        # Mark skipped chunks
        results["skipped"] = len(chunks) - len(chunks_to_embed)
        
        self.db.commit()
        
        logger.info(f"Embedded {results['successful']} chunks for document {document_id}")
        
        return results
    
    def embed_all_chunks(self, force_reembed: bool = False) -> Dict:
        """
        Generate embeddings for all chunks without embeddings
        
        Args:
            force_reembed: If True, regenerate all embeddings
        
        Returns:
            dict: Summary of embedding results
        """
        if force_reembed:
            chunks = self.db.query(DocumentChunk).all()
        else:
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.embedding.is_(None)
            ).all()
        
        if not chunks:
            return {
                "success": True,
                "message": "No chunks need embedding",
                "total_chunks": 0
            }
        
        # Process in batches
        batch_size = 100
        results = {
            "total_chunks": len(chunks),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [chunk.chunk_text for chunk in batch]
            embeddings = self.generate_embeddings_batch(texts)
            
            for chunk, embedding in zip(batch, embeddings):
                if embedding:
                    chunk.embedding = embedding
                    chunk.embedding_model = self.OPENAI_MODEL if self.embedding_method == 'openai' else self.SENTENCE_TRANSFORMER_MODEL
                    chunk.embedding_dimension = len(embedding)
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "chunk_id": chunk.id,
                        "error": "Failed to generate embedding"
                    })
            
            # Commit after each batch
            self.db.commit()
        
        logger.info(f"Embedded {results['successful']} chunks (failed: {results['failed']})")
        
        return results

