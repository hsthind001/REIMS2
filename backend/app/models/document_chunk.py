"""
Document Chunk Model for RAG (Retrieval Augmented Generation)

Stores document chunks with embeddings for semantic search
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class DocumentChunk(Base):
    """Stores document chunks with embeddings for RAG"""
    
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('document_uploads.id', ondelete='CASCADE'), nullable=False, index=True)
    extraction_log_id = Column(Integer, ForeignKey('extraction_logs.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Chunk information
    chunk_index = Column(Integer, nullable=False)  # Order of chunk in document
    chunk_text = Column(Text, nullable=False)  # The actual text content
    chunk_size = Column(Integer)  # Character count
    
    # Embedding (stored as JSON array for compatibility, can be converted to vector later)
    embedding = Column(JSON, nullable=True)  # Vector embedding as JSON array
    embedding_model = Column(String(100), nullable=True)  # e.g., 'text-embedding-3-small'
    embedding_dimension = Column(Integer, nullable=True)  # Dimension of embedding vector
    
    # Metadata
    chunk_metadata = Column(JSON, nullable=True)  # Additional metadata (page numbers, section, etc.)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=True, index=True)
    period_id = Column(Integer, ForeignKey('financial_periods.id', ondelete='CASCADE'), nullable=True, index=True)
    document_type = Column(String(50), nullable=True, index=True)  # For faster filtering
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    document = relationship("DocumentUpload", back_populates="chunks")
    extraction_log = relationship("ExtractionLog", foreign_keys=[extraction_log_id])
    property = relationship("Property")
    period = relationship("FinancialPeriod")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_chunk_document_index', 'document_id', 'chunk_index'),
        Index('idx_chunk_property_period', 'property_id', 'period_id'),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'chunk_text': self.chunk_text[:500] + '...' if len(self.chunk_text) > 500 else self.chunk_text,
            'chunk_size': self.chunk_size,
            'embedding_model': self.embedding_model,
            'embedding_dimension': self.embedding_dimension,
            'has_embedding': self.embedding is not None,
            'metadata': self.chunk_metadata,
            'property_id': self.property_id,
            'period_id': self.period_id,
            'document_type': self.document_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

