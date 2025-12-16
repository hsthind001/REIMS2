"""
Fixed Chunking Configuration

Improvements:
- Increased overlap to preserve context
- Sentence-aware chunking
- Better boundary detection
"""
from app.core.config import settings
import os


class FixedChunkingConfig:
    """
    Fixed chunking configuration with accuracy improvements.
    """
    
    # Increased overlap to preserve context across chunks
    CHUNK_SIZE_CHARS = int(os.getenv("CHUNK_SIZE_CHARS", 3200))  # ~800 tokens
    CHUNK_OVERLAP_CHARS = int(os.getenv("CHUNK_OVERLAP_CHARS", 800))  # ~200 tokens (increased from 100)
    
    # Sentence-aware chunking
    USE_SENTENCE_AWARE = os.getenv("USE_SENTENCE_AWARE", "true").lower() == "true"
    
    # Preserve table structure
    PRESERVE_TABLES = os.getenv("PRESERVE_TABLES", "true").lower() == "true"
    
    @classmethod
    def get_chunk_size_chars(cls) -> int:
        """Get chunk size in characters."""
        return cls.CHUNK_SIZE_CHARS
    
    @classmethod
    def get_overlap_size_chars(cls) -> int:
        """Get overlap size in characters."""
        return cls.CHUNK_OVERLAP_CHARS

