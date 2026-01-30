"""
Query Router Service

Routes queries based on complexity to optimize processing:
- Simple: Direct SQL (fast)
- Medium: Hybrid RAG + SQL
- Complex: Multi-step reasoning
"""
import logging
import time
import re
import hashlib
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum

from app.config.query_router_config import query_router_config

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available. Will use rule-based classification only.")


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class QueryRouterService:
    """
    Query router service for complexity-based routing
    
    Classifies queries and routes them to appropriate processing pipelines.
    """
    
    def __init__(self):
        """
        Initialize query router service
        
        Sets up rule-based classification and optional LLM classifier.
        """
        self.openai_client = None
        self.use_llm = False
        self.routing_cache: Dict[str, Dict[str, Any]] = {}  # query_hash -> {route, complexity, cached_at}
        
        # Try to initialize OpenAI for LLM classification
        if OPENAI_AVAILABLE and query_router_config.USE_LLM_CLASSIFICATION:
            try:
                from app.core.config import settings
                if settings.OPENAI_API_KEY:
                    self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                    self.use_llm = True
                    logger.info(f"QueryRouterService initialized with LLM classification ({query_router_config.LLM_MODEL})")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Will use rule-based classification only.")
                self.openai_client = None
        
        if not self.use_llm:
            logger.info("QueryRouterService initialized with rule-based classification only")
    
    def route_query(
        self,
        query: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Route query based on complexity
        
        Args:
            query: User query text
            use_cache: Whether to use cached routing decisions (default: True)
        
        Returns:
            Dict with route, complexity, confidence, and metadata
        """
        if not query or not query.strip():
            return {
                'query': query,
                'complexity': QueryComplexity.MEDIUM.value,
                'route': query_router_config.DEFAULT_ROUTE,
                'confidence': 0.5,
                'method': 'default',
                'error': 'Empty query'
            }
        
        query = query.strip()
        
        # Check cache
        if use_cache and query_router_config.CACHE_ENABLED:
            cached_result = self._get_from_cache(query)
            if cached_result:
                logger.debug(f"Using cached routing for query: {query[:50]}...")
                cached_result.setdefault('decision_time_ms', 0)
                return cached_result
        
        start_time = time.time()
        
        try:
            # Classify query complexity
            if self.use_llm and self.openai_client:
                try:
                    complexity, confidence, method = self._classify_with_llm(query)
                except Exception as e:
                    logger.warning(f"LLM classification failed: {e}. Falling back to rules.")
                    if query_router_config.FALLBACK_TO_RULES:
                        complexity, confidence, method = self._classify_with_rules(query)
                    else:
                        complexity = QueryComplexity.MEDIUM
                        confidence = 0.5
                        method = 'fallback'
            else:
                complexity, confidence, method = self._classify_with_rules(query)
            
            # Determine route based on complexity
            route = self._get_route_for_complexity(complexity)
            
            decision_time_ms = (time.time() - start_time) * 1000
            
            result = {
                'query': query,
                'complexity': complexity.value,
                'route': route,
                'confidence': confidence,
                'method': method,
                'decision_time_ms': decision_time_ms,
                'cached': False
            }
            
            # Cache result
            if use_cache and query_router_config.CACHE_ENABLED:
                self._save_to_cache(query, result)
                result['cached'] = False  # This was just generated
            
            if query_router_config.LOG_ROUTING_DECISIONS:
                logger.info(
                    f"Routed query '{query[:50]}...' to {route} "
                    f"(complexity: {complexity.value}, confidence: {confidence:.2f}, "
                    f"method: {method}, time: {decision_time_ms:.2f}ms)"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Query routing failed: {e}", exc_info=True)
            return {
                'query': query,
                'complexity': QueryComplexity.MEDIUM.value,
                'route': query_router_config.DEFAULT_ROUTE,
                'confidence': 0.5,
                'method': 'error_fallback',
                'error': str(e)
            }
    
    def _classify_with_rules(self, query: str) -> Tuple[QueryComplexity, float, str]:
        """
        Classify query complexity using rule-based approach
        
        Args:
            query: User query
        
        Returns:
            Tuple of (complexity, confidence, method)
        """
        query_lower = query.lower()
        
        # Check for complex patterns first (most specific)
        complex_score = self._score_complexity(query_lower, query_router_config.COMPLEX_KEYWORDS, query_router_config.COMPLEX_PATTERNS)
        if complex_score >= query_router_config.COMPLEX_CONFIDENCE_THRESHOLD:
            return QueryComplexity.COMPLEX, complex_score, 'rules_complex'
        
        # Check for medium patterns
        medium_score = self._score_complexity(query_lower, query_router_config.MEDIUM_KEYWORDS, query_router_config.MEDIUM_PATTERNS)
        if medium_score >= query_router_config.MEDIUM_CONFIDENCE_THRESHOLD:
            return QueryComplexity.MEDIUM, medium_score, 'rules_medium'
        
        # Check for simple patterns
        simple_score = self._score_complexity(query_lower, query_router_config.SIMPLE_KEYWORDS, query_router_config.SIMPLE_PATTERNS)
        if simple_score >= query_router_config.SIMPLE_CONFIDENCE_THRESHOLD:
            return QueryComplexity.SIMPLE, simple_score, 'rules_simple'
        
        # Default to medium if no clear match
        return QueryComplexity.MEDIUM, 0.6, 'rules_default'
    
    def _score_complexity(
        self,
        query_lower: str,
        keywords: list,
        patterns: list
    ) -> float:
        """
        Score query complexity based on keywords and patterns
        
        Args:
            query_lower: Lowercase query
            keywords: List of keywords to match
            patterns: List of regex patterns to match
        
        Returns:
            Confidence score (0-1)
        """
        score = 0.0
        
        # Check keywords
        keyword_matches = sum(1 for keyword in keywords if keyword in query_lower)
        if keyword_matches > 0:
            score += min(0.6, keyword_matches * 0.2)  # Max 0.6 from keywords
        
        # Check patterns
        pattern_matches = sum(1 for pattern in patterns if re.search(pattern, query_lower))
        if pattern_matches > 0:
            score += min(0.4, pattern_matches * 0.2)  # Max 0.4 from patterns
        
        # Normalize to 0-1 range
        return min(1.0, score)
    
    def _classify_with_llm(self, query: str) -> Tuple[QueryComplexity, float, str]:
        """
        Classify query complexity using LLM
        
        Args:
            query: User query
        
        Returns:
            Tuple of (complexity, confidence, method)
        """
        prompt = f"""Classify this real estate financial data query into one of three complexity levels:

Query: "{query}"

Complexity Levels:
1. SIMPLE: Single metric, single property, single period. Direct questions like "What is NOI for Property X?" or "Show me revenue in Q3"
2. MEDIUM: Multiple metrics, comparisons, trends. Questions like "Compare revenue across properties" or "Show trends for all properties"
3. COMPLEX: Multi-hop reasoning, "why" questions, predictions, analysis. Questions like "Why did NOI decrease?" or "Analyze the impact of vacancy on revenue"

Return JSON only with this exact format:
{{"complexity": "simple|medium|complex", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

        try:
            response = self.openai_client.chat.completions.create(
                model=query_router_config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a query classification expert. Classify queries into simple, medium, or complex based on their processing requirements."},
                    {"role": "user", "content": prompt}
                ],
                temperature=query_router_config.LLM_TEMPERATURE,
                max_tokens=150,
                timeout=query_router_config.LLM_TIMEOUT
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join([line for line in lines if not line.startswith('```')])
            
            import json
            result = json.loads(content)
            
            complexity_str = result.get('complexity', 'medium').lower()
            confidence = float(result.get('confidence', 0.7))
            
            # Map to enum
            if complexity_str == 'simple':
                complexity = QueryComplexity.SIMPLE
            elif complexity_str == 'complex':
                complexity = QueryComplexity.COMPLEX
            else:
                complexity = QueryComplexity.MEDIUM
            
            return complexity, confidence, 'llm'
            
        except Exception as e:
            logger.error(f"LLM classification failed: {e}", exc_info=True)
            raise
    
    def _get_route_for_complexity(self, complexity: QueryComplexity) -> str:
        """
        Get routing destination for complexity level
        
        Args:
            complexity: Query complexity level
        
        Returns:
            Route identifier
        """
        route_map = {
            QueryComplexity.SIMPLE: query_router_config.SIMPLE_ROUTE,
            QueryComplexity.MEDIUM: query_router_config.MEDIUM_ROUTE,
            QueryComplexity.COMPLEX: query_router_config.COMPLEX_ROUTE
        }
        return route_map.get(complexity, query_router_config.DEFAULT_ROUTE)
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query"""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _get_from_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """Get routing decision from cache"""
        cache_key = self._get_cache_key(query)
        
        if cache_key in self.routing_cache:
            cached_entry = self.routing_cache[cache_key]
            cached_at = cached_entry.get('cached_at')
            
            # Check TTL
            if cached_at:
                age = datetime.now(timezone.utc) - cached_at
                if age < timedelta(minutes=query_router_config.CACHE_TTL_MINUTES):
                    result = cached_entry.copy()
                    result['cached'] = True
                    return result
                else:
                    # Expired, remove from cache
                    del self.routing_cache[cache_key]
        
        return None
    
    def _save_to_cache(self, query: str, result: Dict[str, Any]):
        """Save routing decision to cache"""
        cache_key = self._get_cache_key(query)
        self.routing_cache[cache_key] = {
            'query': result['query'],
            'complexity': result['complexity'],
            'route': result['route'],
            'confidence': result['confidence'],
            'method': result['method'],
            'cached_at': datetime.now(timezone.utc)
        }
    
    def clear_cache(self):
        """Clear all cached routing decisions"""
        self.routing_cache.clear()
        logger.info("Query router cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self.routing_cache),
            'cache_ttl_minutes': query_router_config.CACHE_TTL_MINUTES,
            'cache_enabled': query_router_config.CACHE_ENABLED
        }
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        complexity_counts = {}
        route_counts = {}
        
        for entry in self.routing_cache.values():
            complexity = entry.get('complexity', 'unknown')
            route = entry.get('route', 'unknown')
            
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
            route_counts[route] = route_counts.get(route, 0) + 1
        
        return {
            'total_cached_queries': len(self.routing_cache),
            'complexity_distribution': complexity_counts,
            'route_distribution': route_counts
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            'llm_available': self.use_llm and self.openai_client is not None,
            'llm_model': query_router_config.LLM_MODEL if self.use_llm else None,
            'cache_stats': self.get_cache_stats(),
            'routing_stats': self.get_routing_stats(),
            'config': query_router_config.get_config_dict()
        }

