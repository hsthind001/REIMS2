"""
Entity Resolver Service

Fuzzy matching for property names and codes to handle typos
and variations in user input.
"""
import logging
import time
import hashlib
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from threading import Lock

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config.entity_resolver_config import entity_resolver_config

logger = logging.getLogger(__name__)

# Try to import fuzzywuzzy
try:
    from fuzzywuzzy import fuzz
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False
    logger.warning("fuzzywuzzy library not available. Install with: pip install fuzzywuzzy python-Levenshtein")


class EntityResolverService:
    """
    Entity resolver service for fuzzy property name matching
    
    Handles typos and variations in property names and codes
    using fuzzy string matching.
    """
    
    def __init__(self, db: Session):
        """
        Initialize entity resolver service
        
        Args:
            db: Database session
        """
        self.db = db
        self.properties: List[Dict[str, Any]] = []
        self.last_refresh: Optional[datetime] = None
        self.refresh_lock = Lock()
        self.match_cache: Dict[str, Dict[str, Any]] = {}  # query_hash -> {matches, cached_at}
        
        if not FUZZYWUZZY_AVAILABLE:
            logger.warning("fuzzywuzzy not available. Entity resolution will be disabled.")
        
        # Load properties on initialization
        self._load_properties()
    
    def _load_properties(self):
        """Load property list from database"""
        try:
            query = text("""
                SELECT 
                    id as property_id,
                    property_name,
                    property_code
                FROM properties
                WHERE status = :status
                ORDER BY property_name
            """)
            
            result = self.db.execute(query, {"status": entity_resolver_config.PROPERTY_STATUS_FILTER})
            rows = result.fetchall()
            
            self.properties = [
                {
                    'property_id': row.property_id,
                    'property_name': row.property_name or '',
                    'property_code': row.property_code or ''
                }
                for row in rows
            ]
            
            self.last_refresh = datetime.utcnow()
            logger.info(f"Loaded {len(self.properties)} properties for fuzzy matching")
            
        except Exception as e:
            logger.error(f"Failed to load properties: {e}", exc_info=True)
            self.properties = []
    
    def _should_refresh(self) -> bool:
        """Check if property list should be refreshed"""
        if not entity_resolver_config.AUTO_REFRESH_ENABLED:
            return False
        
        if not self.last_refresh:
            return True
        
        age = datetime.utcnow() - self.last_refresh
        return age >= timedelta(minutes=entity_resolver_config.REFRESH_INTERVAL_MINUTES)
    
    def refresh_properties(self):
        """Manually refresh property list"""
        with self.refresh_lock:
            self._load_properties()
            logger.info("Property list refreshed")
    
    def resolve_property(
        self,
        query: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Resolve property name or code using fuzzy matching
        
        Args:
            query: User input (property name or code, possibly with typos)
            use_cache: Whether to use cached results (default: True)
        
        Returns:
            Dict with matches, confidence scores, and metadata
        """
        if not FUZZYWUZZY_AVAILABLE:
            return {
                'query': query,
                'matches': [],
                'error': 'fuzzywuzzy not available'
            }
        
        if not query or not query.strip():
            return {
                'query': query,
                'matches': [],
                'error': 'Empty query'
            }
        
        query = query.strip()
        
        # Check if refresh is needed
        if self._should_refresh():
            self.refresh_properties()
        
        # Check cache
        if use_cache and entity_resolver_config.CACHE_ENABLED:
            cached_result = self._get_from_cache(query)
            if cached_result:
                logger.debug(f"Using cached match for query: {query[:50]}...")
                return cached_result
        
        start_time = time.time()
        
        try:
            matches = self._fuzzy_match(query)
            
            matching_time_ms = (time.time() - start_time) * 1000
            
            result = {
                'query': query,
                'matches': matches,
                'num_matches': len(matches),
                'matching_time_ms': matching_time_ms,
                'cached': False
            }
            
            # Cache result
            if use_cache and entity_resolver_config.CACHE_ENABLED:
                self._save_to_cache(query, result)
                result['cached'] = False  # This was just generated
            
            if entity_resolver_config.LOG_MATCHES:
                logger.info(
                    f"Resolved query '{query}' to {len(matches)} matches "
                    f"in {matching_time_ms:.2f}ms"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Property resolution failed: {e}", exc_info=True)
            return {
                'query': query,
                'matches': [],
                'error': str(e)
            }
    
    def _fuzzy_match(self, query: str) -> List[Dict[str, Any]]:
        """
        Perform fuzzy matching against property list
        
        Args:
            query: User input
        
        Returns:
            List of matches with confidence scores, sorted by confidence (descending)
        """
        if not self.properties:
            logger.warning("No properties loaded. Cannot perform fuzzy matching.")
            return []
        
        matches = []
        query_lower = query.lower() if not entity_resolver_config.CASE_SENSITIVE else query
        
        for property_data in self.properties:
            property_name = property_data['property_name']
            property_code = property_data['property_code']
            
            # Normalize for comparison
            name_lower = property_name.lower() if not entity_resolver_config.CASE_SENSITIVE else property_name
            code_lower = property_code.lower() if not entity_resolver_config.CASE_SENSITIVE else property_code
            
            # Calculate similarity scores
            scores = []
            
            # Match against property name
            if property_name:
                if entity_resolver_config.USE_PARTIAL_RATIO:
                    name_partial_score = fuzz.partial_ratio(query_lower, name_lower)
                    scores.append(('name_partial', name_partial_score))
                
                if entity_resolver_config.USE_RATIO:
                    name_ratio_score = fuzz.ratio(query_lower, name_lower)
                    scores.append(('name_ratio', name_ratio_score))
                
                if entity_resolver_config.USE_TOKEN_SORT_RATIO:
                    name_token_score = fuzz.token_sort_ratio(query_lower, name_lower)
                    scores.append(('name_token', name_token_score))
            
            # Match against property code
            if property_code:
                if entity_resolver_config.USE_PARTIAL_RATIO:
                    code_partial_score = fuzz.partial_ratio(query_lower, code_lower)
                    scores.append(('code_partial', code_partial_score))
                
                if entity_resolver_config.USE_RATIO:
                    code_ratio_score = fuzz.ratio(query_lower, code_lower)
                    scores.append(('code_ratio', code_ratio_score))
            
            # Get best score
            if scores:
                best_score_type, best_score = max(scores, key=lambda x: x[1])
                
                # Convert to confidence (0-1)
                confidence = best_score / 100.0
                
                # Apply threshold
                if confidence >= entity_resolver_config.SIMILARITY_THRESHOLD:
                    matches.append({
                        'property_id': property_data['property_id'],
                        'property_name': property_name,
                        'property_code': property_code,
                        'confidence': confidence,
                        'similarity_score': best_score,
                        'match_type': best_score_type,
                        'matched_field': 'name' if 'name' in best_score_type else 'code'
                    })
        
        # Sort by confidence (descending)
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Return top matches
        top_matches = matches[:entity_resolver_config.MAX_MATCHES]
        
        # Filter by minimum confidence
        filtered_matches = [
            m for m in top_matches
            if m['confidence'] >= entity_resolver_config.MIN_CONFIDENCE
        ]
        
        return filtered_matches
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query"""
        normalized = query.lower().strip() if not entity_resolver_config.CASE_SENSITIVE else query.strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _get_from_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """Get match results from cache"""
        cache_key = self._get_cache_key(query)
        
        if cache_key in self.match_cache:
            cached_entry = self.match_cache[cache_key]
            cached_at = cached_entry.get('cached_at')
            
            # Check TTL
            if cached_at:
                age = datetime.utcnow() - cached_at
                if age < timedelta(minutes=entity_resolver_config.CACHE_TTL_MINUTES):
                    result = cached_entry.copy()
                    result['cached'] = True
                    return result
                else:
                    # Expired, remove from cache
                    del self.match_cache[cache_key]
        
        return None
    
    def _save_to_cache(self, query: str, result: Dict[str, Any]):
        """Save match results to cache"""
        # Enforce max cache size
        if len(self.match_cache) >= entity_resolver_config.CACHE_MAX_SIZE:
            # Remove oldest entry (simple FIFO)
            oldest_key = min(
                self.match_cache.keys(),
                key=lambda k: self.match_cache[k].get('cached_at', datetime.min)
            )
            del self.match_cache[oldest_key]
        
        cache_key = self._get_cache_key(query)
        self.match_cache[cache_key] = {
            'query': result['query'],
            'matches': result['matches'],
            'num_matches': result['num_matches'],
            'cached_at': datetime.utcnow()
        }
    
    def clear_cache(self):
        """Clear all cached match results"""
        self.match_cache.clear()
        logger.info("Entity resolver cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self.match_cache),
            'cache_max_size': entity_resolver_config.CACHE_MAX_SIZE,
            'cache_ttl_minutes': entity_resolver_config.CACHE_TTL_MINUTES,
            'cache_enabled': entity_resolver_config.CACHE_ENABLED
        }
    
    def get_property_stats(self) -> Dict[str, Any]:
        """Get property list statistics"""
        return {
            'num_properties': len(self.properties),
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
            'refresh_interval_minutes': entity_resolver_config.REFRESH_INTERVAL_MINUTES,
            'auto_refresh_enabled': entity_resolver_config.AUTO_REFRESH_ENABLED
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            'fuzzywuzzy_available': FUZZYWUZZY_AVAILABLE,
            'properties_loaded': len(self.properties) > 0,
            'property_stats': self.get_property_stats(),
            'cache_stats': self.get_cache_stats(),
            'config': entity_resolver_config.get_config_dict()
        }

