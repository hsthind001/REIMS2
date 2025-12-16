"""
Query Rewriter Service

Generates query variations using LLM to improve retrieval recall.
Uses GPT-4o for fast, high-quality generation with domain-specific synonyms.
"""
import logging
import json
import time
import hashlib
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from app.config.query_rewriter_config import query_rewriter_config

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available. Install with: pip install openai")


class QueryRewriterService:
    """
    Query rewriter service for generating query variations using LLM
    
    Improves retrieval recall by generating synonym-based variations
    of user queries.
    """
    
    def __init__(self):
        """
        Initialize query rewriter service
        
        Loads synonym dictionary and initializes OpenAI client if available.
        """
        self.openai_client = None
        self.use_openai = False
        self.synonym_dict = {}
        self.cache: Dict[str, Dict[str, Any]] = {}  # query_hash -> {variations, cached_at}
        
        # Load synonym dictionary
        self._load_synonym_dict()
        
        # Try to initialize OpenAI
        if OPENAI_AVAILABLE and query_rewriter_config.is_openai_available():
            try:
                self.openai_client = OpenAI(api_key=query_rewriter_config.OPENAI_API_KEY)
                self.use_openai = True
                logger.info(f"QueryRewriterService initialized with OpenAI ({query_rewriter_config.OPENAI_MODEL})")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Will use synonym dictionary fallback.")
                self.openai_client = None
        
        if not self.use_openai:
            logger.info("QueryRewriterService initialized with synonym dictionary fallback only")
    
    def _load_synonym_dict(self):
        """Load synonym dictionary from file"""
        try:
            dict_path = Path(query_rewriter_config.SYNONYM_DICT_PATH)
            if not dict_path.is_absolute():
                # Relative to backend directory
                dict_path = Path(__file__).parent.parent.parent / dict_path
            
            if dict_path.exists():
                with open(dict_path, 'r') as f:
                    self.synonym_dict = json.load(f)
                logger.info(f"Loaded {len(self.synonym_dict)} synonym entries from {dict_path}")
            else:
                logger.warning(f"Synonym dictionary not found at {dict_path}. Using empty dictionary.")
                self.synonym_dict = {}
        except Exception as e:
            logger.error(f"Failed to load synonym dictionary: {e}", exc_info=True)
            self.synonym_dict = {}
    
    def rewrite_query(
        self,
        query: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate query variations for improved recall
        
        Args:
            query: Original user query
            use_cache: Whether to use cached variations (default: True)
        
        Returns:
            Dict with original query, variations, and metadata
        """
        if not query or not query.strip():
            return {
                'original_query': query,
                'variations': [query],
                'method': 'none',
                'cached': False
            }
        
        query = query.strip()
        
        # Check cache
        if use_cache and query_rewriter_config.CACHE_ENABLED:
            cached_result = self._get_from_cache(query)
            if cached_result:
                logger.debug(f"Using cached variations for query: {query[:50]}...")
                return cached_result
        
        start_time = time.time()
        
        try:
            # Try LLM rewriting first
            if self.use_openai and self.openai_client:
                try:
                    variations = self._rewrite_with_llm(query)
                    method = 'llm'
                except Exception as e:
                    logger.warning(f"LLM rewriting failed: {e}. Falling back to synonym dictionary.")
                    if query_rewriter_config.USE_SYNONYM_DICT_ON_FAILURE:
                        variations = self._rewrite_with_synonyms(query)
                        method = 'synonym_dict'
                    else:
                        variations = [query]
                        method = 'fallback'
            else:
                # Use synonym dictionary
                if query_rewriter_config.USE_SYNONYM_DICT_ON_FAILURE:
                    variations = self._rewrite_with_synonyms(query)
                    method = 'synonym_dict'
                else:
                    variations = [query]
                    method = 'fallback'
            
            generation_time_ms = (time.time() - start_time) * 1000
            
            result = {
                'original_query': query,
                'variations': variations,
                'method': method,
                'cached': False,
                'generation_time_ms': generation_time_ms,
                'num_variations': len(variations)
            }
            
            # Cache result
            if use_cache and query_rewriter_config.CACHE_ENABLED:
                self._save_to_cache(query, result)
                result['cached'] = False  # This was just generated, not from cache
            
            if query_rewriter_config.LOG_REWRITING_SUCCESS:
                logger.info(
                    f"Generated {len(variations)} variations for query '{query[:50]}...' "
                    f"using {method} in {generation_time_ms:.2f}ms"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Query rewriting failed: {e}", exc_info=True)
            if query_rewriter_config.FALLBACK_TO_ORIGINAL:
                return {
                    'original_query': query,
                    'variations': [query],
                    'method': 'fallback',
                    'cached': False,
                    'error': str(e)
                }
            raise
    
    def _rewrite_with_llm(self, query: str) -> List[str]:
        """
        Generate query variations using LLM
        
        Args:
            query: Original query
        
        Returns:
            List of query variations
        """
        prompt = f"""Given this user question about real estate financial data, generate {query_rewriter_config.NUM_VARIATIONS} alternative phrasings:

Original: {query}

Requirements:
- Maintain the same intent
- Use financial synonyms (revenue→income, property→asset, NOI→operating income, DSCR→debt service coverage ratio)
- One should be more specific (add context)
- One should be more general (remove restrictive terms)
- All variations should be natural, complete questions

Return JSON only with this exact format:
{{"variations": ["variation1", "variation2", "variation3"]}}"""

        try:
            response = self.openai_client.chat.completions.create(
                model=query_rewriter_config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a financial data query expert. Generate query variations that maintain intent while using synonyms and different phrasings."},
                    {"role": "user", "content": prompt}
                ],
                temperature=query_rewriter_config.OPENAI_TEMPERATURE,
                max_tokens=query_rewriter_config.OPENAI_MAX_TOKENS,
                timeout=query_rewriter_config.OPENAI_TIMEOUT
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if content.startswith('```'):
                # Remove markdown code blocks
                lines = content.split('\n')
                content = '\n'.join([line for line in lines if not line.startswith('```')])
            
            # Parse JSON
            try:
                result = json.loads(content)
                variations = result.get('variations', [])
                
                # Validate variations
                if not variations or len(variations) == 0:
                    raise ValueError("No variations returned from LLM")
                
                # Ensure we have the requested number
                while len(variations) < query_rewriter_config.NUM_VARIATIONS:
                    variations.append(query)  # Pad with original if needed
                
                # Limit to requested number
                variations = variations[:query_rewriter_config.NUM_VARIATIONS]
                
                # Ensure original is included if not already
                if query not in variations:
                    variations = [query] + variations[:query_rewriter_config.NUM_VARIATIONS - 1]
                
                return variations
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {content[:200]}... Error: {e}")
                raise ValueError(f"Invalid JSON response from LLM: {e}")
                
        except Exception as e:
            logger.error(f"LLM rewriting failed: {e}", exc_info=True)
            raise
    
    def _rewrite_with_synonyms(self, query: str) -> List[str]:
        """
        Generate query variations using synonym dictionary
        
        Args:
            query: Original query
        
        Returns:
            List of query variations
        """
        variations = [query]  # Always include original
        
        query_lower = query.lower()
        
        # Find synonyms in query
        found_synonyms = []
        for term, synonyms in self.synonym_dict.items():
            if term.lower() in query_lower:
                found_synonyms.extend(synonyms)
        
        # Generate variations by replacing terms with synonyms
        if found_synonyms:
            # Variation 1: Replace first occurrence with synonym
            for synonym in found_synonyms[:1]:
                variation = query_lower.replace(
                    next(term for term in self.synonym_dict.keys() if term.lower() in query_lower).lower(),
                    synonym.lower(),
                    1
                )
                if variation not in variations:
                    variations.append(variation.capitalize())
        
        # Variation 2: More specific (add context if possible)
        if "DSCR" in query_lower or "debt service" in query_lower:
            specific_variation = query + " for property financial analysis"
        elif "revenue" in query_lower or "income" in query_lower:
            specific_variation = query + " from property operations"
        else:
            specific_variation = query + " in financial statements"
        
        if specific_variation not in variations:
            variations.append(specific_variation)
        
        # Variation 3: More general (remove restrictive terms)
        general_variation = query
        for term in ["below", "above", "exceeds", "threshold", "limit"]:
            if term in query_lower:
                general_variation = general_variation.replace(term, "").strip()
                break
        
        if general_variation != query and general_variation not in variations:
            variations.append(general_variation)
        
        # Ensure we have the requested number
        while len(variations) < query_rewriter_config.NUM_VARIATIONS:
            variations.append(query)
        
        return variations[:query_rewriter_config.NUM_VARIATIONS]
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def _get_from_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """Get variations from cache"""
        cache_key = self._get_cache_key(query)
        
        if cache_key in self.cache:
            cached_entry = self.cache[cache_key]
            cached_at = cached_entry.get('cached_at')
            
            # Check TTL
            if cached_at:
                age = datetime.utcnow() - cached_at
                if age < timedelta(hours=query_rewriter_config.CACHE_TTL_HOURS):
                    result = cached_entry.copy()
                    result['cached'] = True
                    return result
                else:
                    # Expired, remove from cache
                    del self.cache[cache_key]
        
        return None
    
    def _save_to_cache(self, query: str, result: Dict[str, Any]):
        """Save variations to cache"""
        # Enforce max cache size
        if len(self.cache) >= query_rewriter_config.CACHE_MAX_SIZE:
            # Remove oldest entry (simple FIFO)
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].get('cached_at', datetime.min)
            )
            del self.cache[oldest_key]
        
        cache_key = self._get_cache_key(query)
        self.cache[cache_key] = {
            'original_query': result['original_query'],
            'variations': result['variations'],
            'method': result['method'],
            'cached_at': datetime.utcnow()
        }
    
    def clear_cache(self):
        """Clear all cached variations"""
        self.cache.clear()
        logger.info("Query rewriter cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self.cache),
            'cache_max_size': query_rewriter_config.CACHE_MAX_SIZE,
            'cache_ttl_hours': query_rewriter_config.CACHE_TTL_HOURS,
            'cache_enabled': query_rewriter_config.CACHE_ENABLED
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            'openai_available': self.use_openai and self.openai_client is not None,
            'synonym_dict_loaded': len(self.synonym_dict) > 0,
            'synonym_dict_size': len(self.synonym_dict),
            'cache_stats': self.get_cache_stats(),
            'config': query_rewriter_config.get_config_dict()
        }

