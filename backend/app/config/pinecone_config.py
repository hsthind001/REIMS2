"""
Pinecone Vector Database Configuration

Production-grade Pinecone client initialization with connection pooling,
retry logic, and index management utilities.
"""
import logging
import time
from typing import Optional, Dict, List, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Try to import Pinecone
try:
    from pinecone import Pinecone, ServerlessSpec, PodSpec
    from pinecone.exceptions import PineconeException
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("Pinecone client not available. Install with: pip install pinecone-client>=3.0.0")

from app.core.config import settings


class PineconeConfig:
    """
    Pinecone Configuration and Client Manager
    
    Singleton pattern for client reuse with connection pooling,
    retry logic, and comprehensive error handling.
    """
    
    _instance = None
    _client = None
    _index = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PineconeConfig, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = False
            self._api_key = None
            self._environment = None
            self._index_name = None
            self._dimension = None
            self._metric = None
            self._timeout = None
    
    def initialize(
        self,
        api_key: Optional[str] = None,
        environment: Optional[str] = None,
        index_name: Optional[str] = None,
        dimension: Optional[int] = None,
        metric: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Initialize Pinecone client
        
        Args:
            api_key: Pinecone API key (defaults to settings.PINECONE_API_KEY)
            environment: Pinecone environment/region (defaults to settings.PINECONE_ENVIRONMENT)
            index_name: Index name (defaults to settings.PINECONE_INDEX_NAME)
            dimension: Vector dimension (defaults to settings.PINECONE_DIMENSION)
            metric: Similarity metric (defaults to settings.PINECONE_METRIC)
            timeout: Request timeout in seconds (defaults to settings.PINECONE_TIMEOUT)
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not PINECONE_AVAILABLE:
            logger.error("Pinecone client not available. Cannot initialize.")
            return False
        
        try:
            self._api_key = api_key or settings.PINECONE_API_KEY
            self._environment = environment or getattr(settings, 'PINECONE_ENVIRONMENT', 'us-east-1-aws')
            self._index_name = index_name or getattr(settings, 'PINECONE_INDEX_NAME', 'reims2-documents')
            self._dimension = dimension or getattr(settings, 'PINECONE_DIMENSION', 1536)
            self._metric = metric or getattr(settings, 'PINECONE_METRIC', 'cosine')
            self._timeout = timeout or getattr(settings, 'PINECONE_TIMEOUT', 30)
            
            if not self._api_key:
                logger.error("PINECONE_API_KEY not configured. Cannot initialize Pinecone.")
                return False
            
            # Initialize Pinecone client
            self._client = Pinecone(api_key=self._api_key)
            
            # Get or create index
            if not self.index_exists(self._index_name):
                logger.info(f"Index '{self._index_name}' does not exist. Creating...")
                self.create_index_if_not_exists(
                    index_name=self._index_name,
                    dimension=self._dimension,
                    metric=self._metric
                )
            
            # Connect to index
            self._index = self._client.Index(self._index_name)
            
            self._initialized = True
            logger.info(f"Pinecone initialized successfully. Index: {self._index_name}, Dimension: {self._dimension}, Metric: {self._metric}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {str(e)}", exc_info=True)
            self._initialized = False
            return False
    
    @property
    def client(self):
        """Get Pinecone client instance"""
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("Pinecone not initialized. Call initialize() first.")
        return self._client
    
    @property
    def index(self):
        """Get Pinecone index instance"""
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("Pinecone not initialized. Call initialize() first.")
        return self._index
    
    def is_initialized(self) -> bool:
        """Check if Pinecone is initialized"""
        return self._initialized and self._client is not None
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Pinecone connection health
        
        Returns:
            Dict with health status and details
        """
        if not self.is_initialized():
            return {
                "healthy": False,
                "error": "Pinecone not initialized",
                "initialized": False
            }
        
        try:
            # Try to describe index as health check
            stats = self._index.describe_index_stats()
            return {
                "healthy": True,
                "initialized": True,
                "index_name": self._index_name,
                "dimension": self._dimension,
                "metric": self._metric,
                "stats": {
                    "total_vector_count": stats.get("total_vector_count", 0),
                    "namespaces": list(stats.get("namespaces", {}).keys())
                }
            }
        except Exception as e:
            logger.error(f"Pinecone health check failed: {str(e)}")
            return {
                "healthy": False,
                "error": str(e),
                "initialized": True
            }
    
    def create_index_if_not_exists(
        self,
        index_name: Optional[str] = None,
        dimension: Optional[int] = None,
        metric: Optional[str] = None,
        spec: Optional[Dict] = None
    ) -> bool:
        """
        Create Pinecone index if it doesn't exist
        
        Args:
            index_name: Name of index (defaults to configured index name)
            dimension: Vector dimension (defaults to configured dimension)
            metric: Similarity metric - 'cosine', 'euclidean', or 'dotproduct' (defaults to configured metric)
            spec: Index specification (serverless or pod-based)
        
        Returns:
            True if index created or already exists, False on error
        """
        if not PINECONE_AVAILABLE:
            logger.error("Pinecone client not available")
            return False
        
        try:
            index_name = index_name or self._index_name
            dimension = dimension or self._dimension
            metric = metric or self._metric
            
            if not index_name or not dimension:
                logger.error("Index name and dimension required")
                return False
            
            # Check if index already exists
            if self.index_exists(index_name):
                logger.info(f"Index '{index_name}' already exists")
                return True
            
            # Default to serverless spec if not provided
            if spec is None:
                spec = ServerlessSpec(
                    cloud="aws",
                    region=self._environment or "us-east-1-aws"
                )
            
            # Create index
            self._client.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=spec
            )
            
            logger.info(f"Index '{index_name}' created successfully (dimension={dimension}, metric={metric})")
            
            # Wait for index to be ready
            self._wait_for_index_ready(index_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index '{index_name}': {str(e)}", exc_info=True)
            return False
    
    def delete_index(self, index_name: Optional[str] = None, confirm: bool = False) -> bool:
        """
        Delete Pinecone index
        
        Args:
            index_name: Name of index to delete (defaults to configured index name)
            confirm: Must be True to actually delete (safety check)
        
        Returns:
            True if deleted successfully, False otherwise
        """
        if not confirm:
            logger.warning("Delete operation requires confirm=True")
            return False
        
        if not PINECONE_AVAILABLE:
            logger.error("Pinecone client not available")
            return False
        
        try:
            index_name = index_name or self._index_name
            
            if not self.index_exists(index_name):
                logger.warning(f"Index '{index_name}' does not exist")
                return True  # Already deleted
            
            self._client.delete_index(index_name)
            logger.info(f"Index '{index_name}' deleted successfully")
            
            # Reset index connection if it was the active index
            if index_name == self._index_name:
                self._index = None
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete index '{index_name}': {str(e)}", exc_info=True)
            return False
    
    def describe_index(self, index_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get index description and statistics
        
        Args:
            index_name: Name of index (defaults to configured index name)
        
        Returns:
            Dict with index information or None on error
        """
        if not PINECONE_AVAILABLE:
            logger.error("Pinecone client not available")
            return None
        
        try:
            index_name = index_name or self._index_name
            
            if not self.index_exists(index_name):
                logger.warning(f"Index '{index_name}' does not exist")
                return None
            
            index = self._client.Index(index_name)
            stats = index.describe_index_stats()
            
            return {
                "name": index_name,
                "dimension": stats.get("dimension"),
                "metric": stats.get("metric"),
                "total_vector_count": stats.get("total_vector_count", 0),
                "namespaces": list(stats.get("namespaces", {}).keys()),
                "index_fullness": stats.get("index_fullness", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to describe index '{index_name}': {str(e)}", exc_info=True)
            return None
    
    def list_indexes(self) -> List[str]:
        """
        List all indexes in the Pinecone environment
        
        Returns:
            List of index names
        """
        if not PINECONE_AVAILABLE:
            logger.error("Pinecone client not available")
            return []
        
        try:
            if not self.is_initialized():
                if not self.initialize():
                    return []
            
            indexes = self._client.list_indexes()
            index_names = [idx.name for idx in indexes]
            logger.info(f"Found {len(index_names)} indexes: {index_names}")
            return index_names
            
        except Exception as e:
            logger.error(f"Failed to list indexes: {str(e)}", exc_info=True)
            return []
    
    def index_exists(self, index_name: Optional[str] = None) -> bool:
        """
        Check if index exists
        
        Args:
            index_name: Name of index to check (defaults to configured index name)
        
        Returns:
            True if index exists, False otherwise
        """
        if not PINECONE_AVAILABLE:
            return False
        
        try:
            index_name = index_name or self._index_name
            if not index_name:
                return False
            
            indexes = self._client.list_indexes()
            return any(idx.name == index_name for idx in indexes)
            
        except Exception as e:
            logger.error(f"Failed to check if index exists: {str(e)}")
            return False
    
    def _wait_for_index_ready(self, index_name: str, max_wait: int = 60) -> bool:
        """
        Wait for index to be ready after creation
        
        Args:
            index_name: Name of index
            max_wait: Maximum seconds to wait
        
        Returns:
            True if index is ready, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                index = self._client.Index(index_name)
                stats = index.describe_index_stats()
                # If we can get stats, index is ready
                return True
            except Exception:
                time.sleep(2)
        
        logger.warning(f"Index '{index_name}' not ready after {max_wait} seconds")
        return False


def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
    """
    Decorator for retrying operations with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay between retries
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except PineconeException as e:
                    last_exception = e
                    
                    # Check if it's a rate limit error (429)
                    if hasattr(e, 'status_code') and e.status_code == 429:
                        logger.warning(f"Rate limit hit. Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries + 1})")
                    elif attempt < max_retries:
                        logger.warning(f"Pinecone operation failed: {str(e)}. Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries + 1})")
                    else:
                        logger.error(f"Pinecone operation failed after {max_retries + 1} attempts: {str(e)}")
                        raise
                    
                    if attempt < max_retries:
                        time.sleep(delay)
                        delay *= backoff_factor
                except Exception as e:
                    # For non-Pinecone exceptions, don't retry
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise
            
            # If we exhausted retries, raise the last exception
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


# Global instance
pinecone_config = PineconeConfig()

