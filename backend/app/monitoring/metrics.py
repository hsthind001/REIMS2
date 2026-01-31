"""
Prometheus Metrics for NLQ System

Defines all metrics for monitoring query performance, retrieval quality,
cache hit rates, LLM token usage, and error tracking.
"""
from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
import time

# Create a custom registry for NLQ metrics
registry = CollectorRegistry()

# ============================================================================
# COUNTERS
# ============================================================================

nlq_queries_total = Counter(
    'nlq_queries_total',
    'Total number of NLQ queries processed',
    ['intent', 'method', 'from_cache', 'complexity'],
    registry=registry
)

nlq_llm_tokens_total = Counter(
    'nlq_llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'operation', 'type'],  # type is 'input' or 'output'
    registry=registry
)

nlq_errors_total = Counter(
    'nlq_errors_total',
    'Total number of errors',
    ['error_type', 'service', 'severity'],  # severity: 'critical', 'warning', 'info'
    registry=registry
)

nlq_hallucination_detections_total = Counter(
    'nlq_hallucination_detections_total',
    'Total number of hallucinations detected',
    ['claim_type', 'verified'],
    registry=registry
)

nlq_citations_extracted_total = Counter(
    'nlq_citations_extracted_total',
    'Total number of citations extracted',
    ['source_type', 'document_type'],
    registry=registry
)

nlq_cache_operations_total = Counter(
    'nlq_cache_operations_total',
    'Total cache operations',
    ['operation', 'result'],  # operation: 'get', 'set', 'delete', result: 'hit', 'miss', 'error'
    registry=registry
)

# ============================================================================
# HISTOGRAMS
# ============================================================================

nlq_query_latency_seconds = Histogram(
    'nlq_query_latency_seconds',
    'Latency of NLQ queries in seconds',
    ['method', 'complexity'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=registry
)

nlq_retrieval_latency_seconds = Histogram(
    'nlq_retrieval_latency_seconds',
    'Latency of retrieval stages in seconds',
    ['stage', 'method'],  # stage: 'embedding', 'semantic', 'bm25', 'fusion', 'reranking'
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
    registry=registry
)

nlq_embedding_latency_seconds = Histogram(
    'nlq_embedding_latency_seconds',
    'Latency of embedding generation in seconds',
    ['model', 'batch_size'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0],
    registry=registry
)

nlq_reranking_latency_seconds = Histogram(
    'nlq_reranking_latency_seconds',
    'Latency of reranking in seconds',
    ['method', 'candidate_count'],
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
    registry=registry
)

nlq_llm_latency_seconds = Histogram(
    'nlq_llm_latency_seconds',
    'Latency of LLM API calls in seconds',
    ['model', 'operation'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=registry
)

nlq_hallucination_detection_latency_seconds = Histogram(
    'nlq_hallucination_detection_latency_seconds',
    'Latency of hallucination detection in seconds',
    ['claim_count'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0],
    registry=registry
)

nlq_citation_extraction_latency_seconds = Histogram(
    'nlq_citation_extraction_latency_seconds',
    'Latency of citation extraction in seconds',
    ['claim_count'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0],
    registry=registry
)

# ============================================================================
# GAUGES
# ============================================================================

nlq_retrieval_precision = Gauge(
    'nlq_retrieval_precision',
    'Precision@k for retrieval',
    ['k'],
    registry=registry
)

nlq_retrieval_recall = Gauge(
    'nlq_retrieval_recall',
    'Recall@k for retrieval',
    ['k'],
    registry=registry
)

nlq_cache_hit_rate = Gauge(
    'nlq_cache_hit_rate',
    'Cache hit rate (0-1)',
    registry=registry
)

nlq_active_conversations = Gauge(
    'nlq_active_conversations',
    'Number of active conversations',
    registry=registry
)

nlq_index_size = Gauge(
    'nlq_index_size',
    'Size of search indexes',
    ['index_type'],  # 'pinecone', 'bm25', 'postgresql'
    registry=registry
)

nlq_embedding_cache_size = Gauge(
    'nlq_embedding_cache_size',
    'Number of cached embeddings',
    registry=registry
)

nlq_pending_reviews = Gauge(
    'nlq_pending_reviews',
    'Number of pending hallucination reviews',
    registry=registry
)

# ============================================================================
# SUMMARIES (for detailed statistics)
# ============================================================================

nlq_query_duration = Summary(
    'nlq_query_duration_seconds',
    'Query duration summary',
    ['method'],
    registry=registry
)

nlq_retrieval_duration = Summary(
    'nlq_retrieval_duration_seconds',
    'Retrieval duration summary',
    ['stage'],
    registry=registry
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def track_query(
    intent: str,
    method: str,
    from_cache: bool,
    complexity: str,
    duration: float
):
    """
    Track a completed NLQ query
    
    Args:
        intent: Query intent (e.g., 'metric_query', 'comparison', 'trend')
        method: Query method (e.g., 'direct_sql', 'rag', 'hybrid')
        from_cache: Whether result came from cache
        complexity: Query complexity ('simple', 'medium', 'complex')
        duration: Query duration in seconds
    """
    nlq_queries_total.labels(
        intent=intent,
        method=method,
        from_cache=str(from_cache).lower(),
        complexity=complexity
    ).inc()
    
    nlq_query_latency_seconds.labels(
        method=method,
        complexity=complexity
    ).observe(duration)
    
    nlq_query_duration.labels(method=method).observe(duration)


def track_llm_tokens(
    model: str,
    operation: str,
    input_tokens: int,
    output_tokens: int
):
    """
    Track LLM token usage
    
    Args:
        model: LLM model name (e.g., 'gpt-4o', 'claude-3-opus')
        operation: Operation type (e.g., 'query_rewriting', 'answer_generation', 'coreference')
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
    """
    nlq_llm_tokens_total.labels(
        model=model,
        operation=operation,
        type='input'
    ).inc(input_tokens)
    
    nlq_llm_tokens_total.labels(
        model=model,
        operation=operation,
        type='output'
    ).inc(output_tokens)


def track_error(
    error_type: str,
    service: str,
    severity: str = 'warning'
):
    """
    Track an error
    
    Args:
        error_type: Error type (e.g., 'llm_api_error', 'retrieval_error', 'timeout')
        service: Service name (e.g., 'nlq_service', 'rag_service', 'embedding_service')
        severity: Error severity ('critical', 'warning', 'info')
    """
    nlq_errors_total.labels(
        error_type=error_type,
        service=service,
        severity=severity
    ).inc()


def track_retrieval(
    stage: str,
    method: str,
    duration: float
):
    """
    Track retrieval stage latency
    
    Args:
        stage: Retrieval stage (e.g., 'embedding', 'semantic', 'bm25', 'fusion', 'reranking')
        method: Method used (e.g., 'pinecone', 'postgresql', 'bm25', 'rrf', 'cohere')
        duration: Duration in seconds
    """
    nlq_retrieval_latency_seconds.labels(
        stage=stage,
        method=method
    ).observe(duration)
    
    nlq_retrieval_duration.labels(stage=stage).observe(duration)


def update_cache_hit_rate(hit_rate: float):
    """
    Update cache hit rate
    
    Args:
        hit_rate: Cache hit rate (0-1)
    """
    nlq_cache_hit_rate.set(hit_rate)


def update_retrieval_quality(precision_at_k: dict, recall_at_k: dict):
    """
    Update retrieval quality metrics
    
    Args:
        precision_at_k: Dict mapping k values to precision scores
        recall_at_k: Dict mapping k values to recall scores
    """
    for k, precision in precision_at_k.items():
        nlq_retrieval_precision.labels(k=str(k)).set(precision)
    
    for k, recall in recall_at_k.items():
        nlq_retrieval_recall.labels(k=str(k)).set(recall)


def update_active_conversations(count: int):
    """
    Update active conversations count
    
    Args:
        count: Number of active conversations
    """
    nlq_active_conversations.set(count)


def track_hallucination_detection(
    claim_type: str,
    verified: bool,
    duration: float,
    claim_count: int
):
    """
    Track hallucination detection
    
    Args:
        claim_type: Type of claim ('currency', 'percentage', 'date', 'ratio')
        verified: Whether claim was verified
        duration: Detection duration in seconds
        claim_count: Number of claims checked
    """
    nlq_hallucination_detections_total.labels(
        claim_type=claim_type,
        verified=str(verified).lower()
    ).inc()
    
    nlq_hallucination_detection_latency_seconds.labels(
        claim_count=str(claim_count)
    ).observe(duration)


def track_citation_extraction(
    source_type: str,
    document_type: str,
    duration: float,
    claim_count: int
):
    """
    Track citation extraction
    
    Args:
        source_type: Source type ('document', 'sql')
        document_type: Document type (e.g., 'income_statement', 'balance_sheet')
        duration: Extraction duration in seconds
        claim_count: Number of claims processed
    """
    nlq_citations_extracted_total.labels(
        source_type=source_type,
        document_type=document_type or 'unknown'
    ).inc()
    
    nlq_citation_extraction_latency_seconds.labels(
        claim_count=str(claim_count)
    ).observe(duration)


def get_metrics():
    """
    Get Prometheus metrics in text format
    
    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(registry)


def get_metrics_content_type():
    """
    Get content type for metrics endpoint
    
    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST

