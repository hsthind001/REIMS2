"""
Instrumentation Decorators and Context Managers

Provides decorators and context managers for easy metric tracking.
"""
import time
import functools
from typing import Callable, Any, Optional
from contextlib import contextmanager

from app.monitoring.metrics import (
    track_query,
    track_llm_tokens,
    track_error,
    track_retrieval,
    track_hallucination_detection,
    track_citation_extraction,
    nlq_llm_latency_seconds,
    nlq_embedding_latency_seconds,
    nlq_reranking_latency_seconds
)


def track_query_metric(
    intent: Optional[str] = None,
    method: Optional[str] = None,
    complexity: Optional[str] = None
):
    """
    Decorator to track NLQ query metrics
    
    Usage:
        @track_query_metric(intent='metric_query', method='rag', complexity='medium')
        def process_query(query: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            from_cache = False
            error = None
            
            try:
                result = func(*args, **kwargs)
                
                # Check if result came from cache
                if isinstance(result, dict):
                    from_cache = result.get('from_cache', False)
                    # Extract intent, method, complexity from result if not provided
                    actual_intent = intent or result.get('intent', 'unknown')
                    actual_method = method or result.get('method', 'unknown')
                    actual_complexity = complexity or result.get('complexity', 'unknown')
                else:
                    actual_intent = intent or 'unknown'
                    actual_method = method or 'unknown'
                    actual_complexity = complexity or 'unknown'
                
                duration = time.time() - start_time
                
                track_query(
                    intent=actual_intent,
                    method=actual_method,
                    from_cache=from_cache,
                    complexity=actual_complexity,
                    duration=duration
                )
                
                return result
                
            except Exception as e:
                error = e
                duration = time.time() - start_time
                
                # Track error
                track_error(
                    error_type=type(e).__name__,
                    service='nlq_service',
                    severity='critical' if isinstance(e, (SystemError, MemoryError)) else 'warning'
                )
                
                raise
                
        return wrapper
    return decorator


def track_llm_call(model: str, operation: str):
    """
    Decorator to track LLM API calls
    
    Usage:
        @track_llm_call(model='gpt-4o', operation='answer_generation')
        def generate_answer(query: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Track latency
                nlq_llm_latency_seconds.labels(
                    model=model,
                    operation=operation
                ).observe(duration)
                
                # Track tokens if available in result
                if isinstance(result, dict):
                    input_tokens = result.get('input_tokens', 0)
                    output_tokens = result.get('output_tokens', 0)
                    
                    if input_tokens > 0 or output_tokens > 0:
                        track_llm_tokens(
                            model=model,
                            operation=operation,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens
                        )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Track error
                track_error(
                    error_type=type(e).__name__,
                    service='llm_service',
                    severity='critical'
                )
                
                raise
                
        return wrapper
    return decorator


@contextmanager
def track_retrieval_stage(stage: str, method: str):
    """
    Context manager to track retrieval stage latency
    
    Usage:
        with track_retrieval_stage('semantic', 'pinecone'):
            results = pinecone_service.query_vectors(...)
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        track_retrieval(stage=stage, method=method, duration=duration)


@contextmanager
def track_embedding_generation(model: str, batch_size: int = 1):
    """
    Context manager to track embedding generation latency
    
    Usage:
        with track_embedding_generation('text-embedding-3-large', batch_size=10):
            embeddings = embedding_service.generate_embeddings(...)
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        nlq_embedding_latency_seconds.labels(
            model=model,
            batch_size=str(batch_size)
        ).observe(duration)


@contextmanager
def track_reranking(method: str, candidate_count: int):
    """
    Context manager to track reranking latency
    
    Usage:
        with track_reranking('cohere', candidate_count=50):
            reranked = reranker_service.rerank(...)
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        nlq_reranking_latency_seconds.labels(
            method=method,
            candidate_count=str(candidate_count)
        ).observe(duration)


@contextmanager
def track_hallucination_check(claim_count: int):
    """
    Context manager to track hallucination detection
    
    Usage:
        with track_hallucination_check(claim_count=3) as tracker:
            result = detector.detect_hallucinations(...)
            # Update tracker with results
            tracker.update(result)
    """
    start_time = time.time()
    
    class Tracker:
        def __init__(self):
            self.result = None
        
        def update(self, result: dict):
            self.result = result
    
    tracker = Tracker()
    
    try:
        yield tracker
    finally:
        duration = time.time() - start_time
        
        if tracker.result:
            flagged_claims = tracker.result.get('flagged_claims', [])
            for claim in flagged_claims:
                claim_type = claim.get('claim_type', 'unknown')
                verified = claim.get('verified', False)
                
                track_hallucination_detection(
                    claim_type=claim_type,
                    verified=verified,
                    duration=duration / len(flagged_claims) if flagged_claims else duration,
                    claim_count=claim_count
                )


@contextmanager
def track_citation_extraction_stage(claim_count: int):
    """
    Context manager to track citation extraction
    
    Usage:
        with track_citation_extraction_stage(claim_count=2) as tracker:
            result = extractor.extract_citations(...)
            tracker.update(result)
    """
    start_time = time.time()
    
    class Tracker:
        def __init__(self):
            self.result = None
        
        def update(self, result: dict):
            self.result = result
    
    tracker = Tracker()
    
    try:
        yield tracker
    finally:
        duration = time.time() - start_time
        
        if tracker.result:
            citations = tracker.result.get('citations', [])
            for citation in citations:
                sources = citation.get('sources', [])
                for source in sources:
                    source_type = source.get('type', 'unknown')
                    document_type = source.get('document_type', 'unknown')
                    
                    track_citation_extraction(
                        source_type=source_type,
                        document_type=document_type,
                        duration=duration / len(citations) if citations else duration,
                        claim_count=claim_count
                    )

