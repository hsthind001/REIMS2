"""
Coreference Resolution Service

Resolves pronouns and implicit references in follow-up queries using conversation context.
Enables natural follow-up questions like "What about that property in Q4?" without repeating context.
"""
import logging
import re
import time
import hashlib
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, timedelta

from app.config.coreference_config import coreference_config

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available. Will use rule-based resolution only.")


class CoreferenceResolver:
    """
    Resolves coreferences (pronouns, implicit references) in queries using conversation context
    
    Uses LLM for accurate resolution with rule-based fallback.
    """
    
    def __init__(self):
        """
        Initialize coreference resolver
        
        Sets up rule-based detection and optional LLM resolver.
        """
        self.openai_client = None
        self.use_llm = False
        self.resolution_cache: Dict[str, Dict[str, Any]] = {}  # query_hash -> {resolved_query, cached_at}
        
        # Try to initialize OpenAI for LLM resolution
        if OPENAI_AVAILABLE and coreference_config.USE_LLM_RESOLUTION:
            try:
                from app.core.config import settings
                if settings.OPENAI_API_KEY:
                    self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                    self.use_llm = True
                    logger.info(f"CoreferenceResolver initialized with LLM resolution ({coreference_config.LLM_MODEL})")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Will use rule-based resolution only.")
                self.openai_client = None
        
        if not self.use_llm:
            logger.info("CoreferenceResolver initialized with rule-based resolution only")
    
    def has_coreference(self, query: str) -> bool:
        """
        Detect if query contains coreference indicators
        
        Args:
            query: User query text
        
        Returns:
            True if query likely contains coreferences
        """
        if not query:
            return False
        
        query_lower = query.lower()
        
        # Check for pronouns
        for pronoun in coreference_config.PRONOUNS:
            if pronoun in query_lower:
                return True
        
        # Check for implicit phrases
        for phrase in coreference_config.IMPLICIT_PHRASES:
            if phrase in query_lower:
                # Check if it's at the start (more likely to be implicit reference)
                if query_lower.startswith(phrase):
                    return True
        
        # Check for temporal indicators without explicit context
        for temporal in coreference_config.TEMPORAL_INDICATORS:
            if temporal in query_lower:
                # Check if it's used without explicit date/period
                if not self._has_explicit_period(query_lower):
                    return True
        
        return False
    
    def _has_explicit_period(self, query_lower: str) -> bool:
        """Check if query has explicit period reference"""
        # Check for explicit periods: Q1-Q4, months, years
        period_patterns = [
            r'\bq[1-4]\b',  # Q1, Q2, Q3, Q4
            r'\b\d{4}\b',   # 2024, 2023
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'  # Dates
        ]
        
        for pattern in period_patterns:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    def resolve_coreference(
        self,
        query: str,
        conversation_history: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Resolve coreferences in query using conversation history
        
        Args:
            query: Current user query (may contain coreferences)
            conversation_history: List of previous Q&A pairs
            context: Extracted context (properties, metrics, periods)
        
        Returns:
            Dict with resolved_query, confidence, method, resolution_time_ms
        """
        if not query or not query.strip():
            return {
                'original_query': query,
                'resolved_query': query,
                'has_coreference': False,
                'confidence': 1.0,
                'method': 'no_resolution_needed',
                'resolution_time_ms': 0.0
            }
        
        query = query.strip()
        
        # Check if resolution is needed
        if not self.has_coreference(query):
            return {
                'original_query': query,
                'resolved_query': query,
                'has_coreference': False,
                'confidence': 1.0,
                'method': 'no_coreference_detected',
                'resolution_time_ms': 0.0
            }
        
        # Check cache
        if coreference_config.CACHE_ENABLED:
            cache_key = self._get_cache_key(query, conversation_history)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.debug(f"Using cached coreference resolution for query: {query[:50]}...")
                return cached_result
        
        start_time = time.time()
        
        try:
            # Resolve using LLM or rules
            if self.use_llm and self.openai_client:
                try:
                    resolved_query, confidence, method = self._resolve_with_llm(query, conversation_history, context)
                except Exception as e:
                    logger.warning(f"LLM resolution failed: {e}. Falling back to rules.")
                    if coreference_config.FALLBACK_TO_RULES:
                        resolved_query, confidence, method = self._resolve_with_rules(query, conversation_history, context)
                    else:
                        resolved_query = query
                        confidence = 0.5
                        method = 'llm_fallback'
            else:
                resolved_query, confidence, method = self._resolve_with_rules(query, conversation_history, context)
            
            resolution_time_ms = (time.time() - start_time) * 1000
            
            result = {
                'original_query': query,
                'resolved_query': resolved_query,
                'has_coreference': True,
                'confidence': confidence,
                'method': method,
                'resolution_time_ms': resolution_time_ms
            }
            
            # Cache result
            if coreference_config.CACHE_ENABLED:
                self._save_to_cache(cache_key, result)
            
            logger.info(
                f"Resolved coreference: '{query[:50]}...' -> '{resolved_query[:50]}...' "
                f"(confidence: {confidence:.2f}, method: {method}, time: {resolution_time_ms:.2f}ms)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Coreference resolution failed: {e}", exc_info=True)
            return {
                'original_query': query,
                'resolved_query': query,  # Return original on error
                'has_coreference': True,
                'confidence': 0.0,
                'method': 'error',
                'resolution_time_ms': (time.time() - start_time) * 1000,
                'error': str(e)
            }
    
    def _resolve_with_llm(
        self,
        query: str,
        conversation_history: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float, str]:
        """
        Resolve coreferences using LLM
        
        Args:
            query: Current query
            conversation_history: Previous Q&A pairs
            context: Extracted context
        
        Returns:
            Tuple of (resolved_query, confidence, method)
        """
        # Build conversation history string
        history_text = ""
        for i, entry in enumerate(conversation_history[-coreference_config.MAX_HISTORY_TURNS:], 1):
            history_text += f"Q{i}: {entry.get('question', '')}\n"
            history_text += f"A{i}: {entry.get('answer', '')}\n\n"
        
        # Build context string
        context_text = ""
        if context:
            if context.get('properties'):
                props = [p.get('property_name', '') for p in context.get('properties', [])]
                context_text += f"Properties mentioned: {', '.join(props)}\n"
            if context.get('metrics'):
                context_text += f"Metrics mentioned: {', '.join(context.get('metrics', []))}\n"
            if context.get('time_periods'):
                periods = context.get('time_periods', [])
                period_strs = []
                for p in periods:
                    if isinstance(p, dict):
                        if 'quarter' in p:
                            period_strs.append(f"Q{p['quarter']} {p.get('year', '')}")
                        elif 'month' in p:
                            period_strs.append(f"{p.get('month', '')} {p.get('year', '')}")
                        elif 'year' in p:
                            period_strs.append(str(p['year']))
                if period_strs:
                    context_text += f"Time periods mentioned: {', '.join(period_strs)}\n"
        
        prompt = f"""Given this conversation history and current query, resolve any coreferences (pronouns, implicit references) to create a standalone query that doesn't need conversation history.

Conversation history:
{history_text.strip() if history_text else "No previous conversation."}

Context:
{context_text.strip() if context_text else "No additional context."}

Current query: {query}

Instructions:
1. Identify any pronouns (that, this, it, they, etc.) or implicit references (e.g., "and for Q4", "what about December")
2. Replace them with explicit references from the conversation history
3. Generate a complete, standalone query that makes sense without the conversation history
4. Preserve the original intent and question structure
5. If the query is already complete, return it unchanged

Return JSON only with this exact format:
{{"resolved_query": "complete standalone query", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

        try:
            response = self.openai_client.chat.completions.create(
                model=coreference_config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "You are a coreference resolution expert. Resolve pronouns and implicit references in queries using conversation context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=coreference_config.LLM_TEMPERATURE,
                max_tokens=coreference_config.LLM_MAX_TOKENS,
                timeout=coreference_config.LLM_TIMEOUT
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response (handle markdown code blocks)
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join([line for line in lines if not line.startswith('```')])
            
            import json
            result = json.loads(content)
            
            resolved_query = result.get('resolved_query', query)
            confidence = float(result.get('confidence', 0.8))
            
            # Validate confidence threshold
            if confidence < coreference_config.MIN_CONFIDENCE_THRESHOLD:
                logger.warning(f"LLM resolution confidence ({confidence}) below threshold. Using original query.")
                return query, confidence, 'llm_low_confidence'
            
            return resolved_query, confidence, 'llm'
            
        except Exception as e:
            logger.error(f"LLM resolution failed: {e}", exc_info=True)
            raise
    
    def _resolve_with_rules(
        self,
        query: str,
        conversation_history: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float, str]:
        """
        Resolve coreferences using rule-based approach
        
        Args:
            query: Current query
            conversation_history: Previous Q&A pairs
            context: Extracted context
        
        Returns:
            Tuple of (resolved_query, confidence, method)
        """
        resolved_query = query
        confidence = 0.6  # Lower confidence for rule-based
        changes_made = False
        
        # Get most recent question for context
        if conversation_history:
            last_question = conversation_history[-1].get('question', '')
            last_answer = conversation_history[-1].get('answer', '')
        else:
            last_question = ""
            last_answer = ""
        
        # Rule 1: Resolve "that property", "this property" using context
        if context and context.get('properties'):
            property_name = context['properties'][0].get('property_name', '')
            if property_name:
                # Replace "that property", "this property", "it" with property name
                resolved_query = re.sub(
                    r'\b(that|this|it)\s+property\b',
                    property_name,
                    resolved_query,
                    flags=re.IGNORECASE
                )
                if resolved_query != query:
                    changes_made = True
                    confidence = 0.7
        
        # Rule 2: Resolve implicit temporal references
        if context and context.get('time_periods'):
            # Extract last period
            last_period = context['time_periods'][-1] if context['time_periods'] else None
            if last_period and isinstance(last_period, dict):
                year = last_period.get('year')
                quarter = last_period.get('quarter')
                month = last_period.get('month')
                
                # Resolve "and for Q4", "what about Q4" with year
                if quarter and year:
                    period_ref = f"Q{quarter} {year}"
                    # Simple pattern matching for "and for Q4" -> "and for Q4 2024"
                    if re.search(r'\bq[1-4]\b', resolved_query.lower()) and not str(year) in resolved_query:
                        resolved_query = re.sub(
                            r'\bq([1-4])\b',
                            f'Q\\1 {year}',
                            resolved_query,
                            flags=re.IGNORECASE
                        )
                        if resolved_query != query:
                            changes_made = True
                            confidence = 0.75
        
        # Rule 3: Resolve "and for", "what about" with metric from context
        if context and context.get('metrics'):
            metric = context['metrics'][0] if context['metrics'] else None
            if metric:
                # If query starts with "and for" or "what about", add metric
                if re.match(r'^(and|what|how)\s+(for|about)', resolved_query.lower()):
                    # Try to infer metric from last question
                    if last_question:
                        # Extract metric from last question if possible
                        metric_patterns = {
                            'noi': r'\bnoi\b',
                            'dscr': r'\bdscr\b',
                            'revenue': r'\brevenue\b',
                            'occupancy': r'\boccupancy\b'
                        }
                        for m, pattern in metric_patterns.items():
                            if re.search(pattern, last_question.lower()):
                                # Prepend metric to query
                                resolved_query = f"What was {m} {resolved_query}"
                                changes_made = True
                                confidence = 0.7
                                break
        
        if not changes_made:
            # No changes made, return original
            return query, 0.5, 'rules_no_changes'
        
        return resolved_query, confidence, 'rules'
    
    def _get_cache_key(self, query: str, conversation_history: List[Dict[str, Any]]) -> str:
        """Generate cache key for query and history"""
        # Use query + last question hash for cache key
        normalized_query = query.lower().strip()
        last_question = conversation_history[-1].get('question', '').lower() if conversation_history else ''
        cache_string = f"{normalized_query}|||{last_question}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get resolution from cache"""
        if cache_key in self.resolution_cache:
            cached_entry = self.resolution_cache[cache_key]
            cached_at = cached_entry.get('cached_at')
            
            # Check TTL
            if cached_at:
                age = datetime.utcnow() - cached_at
                if age < timedelta(minutes=coreference_config.CACHE_TTL_MINUTES):
                    result = cached_entry.copy()
                    result['cached'] = True
                    return result
                else:
                    # Expired, remove from cache
                    del self.resolution_cache[cache_key]
        
        return None
    
    def _save_to_cache(self, cache_key: str, result: Dict[str, Any]):
        """Save resolution to cache"""
        self.resolution_cache[cache_key] = {
            'original_query': result['original_query'],
            'resolved_query': result['resolved_query'],
            'has_coreference': result['has_coreference'],
            'confidence': result['confidence'],
            'method': result['method'],
            'cached_at': datetime.utcnow()
        }
    
    def clear_cache(self):
        """Clear all cached resolutions"""
        self.resolution_cache.clear()
        logger.info("Coreference resolver cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self.resolution_cache),
            'cache_ttl_minutes': coreference_config.CACHE_TTL_MINUTES,
            'cache_enabled': coreference_config.CACHE_ENABLED
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            'llm_available': self.use_llm and self.openai_client is not None,
            'llm_model': coreference_config.LLM_MODEL if self.use_llm else None,
            'cache_stats': self.get_cache_stats(),
            'config': coreference_config.get_config_dict()
        }

