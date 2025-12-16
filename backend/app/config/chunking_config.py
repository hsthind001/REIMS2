"""
Chunking Configuration

Configurable parameters for document chunking strategy including
chunk size, overlap, table extraction settings, and performance targets.
"""
from typing import Dict, Any
from app.core.config import settings


class ChunkingConfig:
    """
    Configuration for document chunking and processing
    
    All parameters are configurable and can be overridden via environment variables
    or config file.
    """
    
    # Text Chunking Parameters
    CHUNK_SIZE: int = 1000  # Target chunk size in tokens
    CHUNK_OVERLAP: int = 100  # Overlap size in tokens (for context preservation)
    
    # Token Estimation (approximate: 1 token ≈ 4 characters for English)
    TOKENS_PER_CHAR: float = 0.25  # Conservative estimate
    
    # Table Extraction Parameters
    TABLE_EXTRACTION_MODES: list = ['lattice', 'stream']  # Camelot modes to try
    TABLE_MIN_ROWS: int = 2  # Minimum rows to consider as a table
    TABLE_MIN_COLS: int = 2  # Minimum columns to consider as a table
    TABLE_MARKDOWN_FORMAT: bool = True  # Convert tables to markdown
    
    # Header Detection Parameters
    HEADER_DETECTION_ENABLED: bool = True
    HEADER_FONT_SIZE_THRESHOLD: float = 1.2  # Relative to body text
    HEADER_POSITION_TOP_THRESHOLD: float = 0.15  # Top 15% of page
    HEADER_BOLD_WEIGHT: float = 0.7  # Bold text weight for header detection
    HEADER_LEVELS: int = 3  # Maximum header hierarchy levels
    
    # Parent-Child Relationship Parameters
    PARENT_CHILD_ENABLED: bool = True
    MAX_DISTANCE_FOR_PARENT: int = 500  # Maximum characters between header and content
    PARENT_SEARCH_RANGE: int = 3  # Number of chunks to search backward for parent
    
    # Metadata Enrichment Parameters
    INCLUDE_COORDINATES: bool = True  # Include PDF coordinates (x0, y0, x1, y1)
    INCLUDE_PAGE_NUMBERS: bool = True  # Include page numbers
    INCLUDE_TOKEN_COUNT: bool = True  # Include token count in metadata
    
    # Performance Targets (in seconds)
    TARGET_PROCESSING_TIME_PER_PAGE: float = 2.0
    TARGET_TABLE_EXTRACTION_TIME: float = 1.0
    TARGET_CHUNKING_TIME_PER_PAGE: float = 0.5
    WARNING_THRESHOLD_MULTIPLIER: float = 1.5  # Warn if exceeds target * multiplier
    
    # Multi-page Table Support
    MULTI_PAGE_TABLE_DETECTION: bool = True
    TABLE_CONTINUATION_THRESHOLD: float = 0.8  # Similarity threshold for continuation
    MAX_PAGES_FOR_TABLE: int = 10  # Maximum pages a table can span
    
    # Chunk Type Definitions
    CHUNK_TYPE_TEXT: str = 'text'
    CHUNK_TYPE_TABLE: str = 'table'
    CHUNK_TYPE_HEADER: str = 'header'
    
    # Separators for RecursiveCharacterTextSplitter (in order of preference)
    TEXT_SPLITTER_SEPARATORS: list = [
        "\n\n",  # Paragraph breaks
        "\n",    # Line breaks
        ". ",    # Sentence endings
        " ",     # Word boundaries
        ""       # Character boundaries (last resort)
    ]
    
    # Batch Processing Parameters
    BATCH_SIZE_FOR_EMBEDDINGS: int = 100  # Process embeddings in batches
    BATCH_SIZE_FOR_PINECONE: int = 100  # Sync to Pinecone in batches
    
    @classmethod
    def get_chunk_size_chars(cls) -> int:
        """Get chunk size in characters (approximate)"""
        return int(cls.CHUNK_SIZE / cls.TOKENS_PER_CHAR)
    
    @classmethod
    def get_overlap_size_chars(cls) -> int:
        """Get overlap size in characters (approximate)"""
        return int(cls.CHUNK_OVERLAP / cls.TOKENS_PER_CHAR)
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'chunk_size_tokens': cls.CHUNK_SIZE,
            'chunk_size_chars': cls.get_chunk_size_chars(),
            'chunk_overlap_tokens': cls.CHUNK_OVERLAP,
            'chunk_overlap_chars': cls.get_overlap_size_chars(),
            'table_extraction_modes': cls.TABLE_EXTRACTION_MODES,
            'header_detection_enabled': cls.HEADER_DETECTION_ENABLED,
            'parent_child_enabled': cls.PARENT_CHILD_ENABLED,
            'performance_targets': {
                'processing_time_per_page': cls.TARGET_PROCESSING_TIME_PER_PAGE,
                'table_extraction_time': cls.TARGET_TABLE_EXTRACTION_TIME,
                'chunking_time_per_page': cls.TARGET_CHUNKING_TIME_PER_PAGE
            }
        }
    
    @classmethod
    def validate_performance(cls, actual_time: float, target_time: float, operation: str) -> Dict[str, Any]:
        """
        Validate performance against targets
        
        Args:
            actual_time: Actual processing time in seconds
            target_time: Target processing time in seconds
            operation: Operation name for logging
        
        Returns:
            Dict with validation results
        """
        warning_threshold = target_time * cls.WARNING_THRESHOLD_MULTIPLIER
        
        result = {
            'operation': operation,
            'actual_time': actual_time,
            'target_time': target_time,
            'within_target': actual_time <= target_time,
            'within_warning': actual_time <= warning_threshold,
            'exceeds_warning': actual_time > warning_threshold
        }
        
        if result['exceeds_warning']:
            result['warning'] = f"{operation} took {actual_time:.2f}s, exceeds warning threshold of {warning_threshold:.2f}s"
        elif not result['within_target']:
            result['warning'] = f"{operation} took {actual_time:.2f}s, exceeds target of {target_time:.2f}s"
        else:
            result['warning'] = None
        
        return result


# Global configuration instance
chunking_config = ChunkingConfig()

