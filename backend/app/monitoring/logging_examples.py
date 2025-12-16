"""
Structured Logging Examples

Examples of how to use structured logging in services.
"""
from app.monitoring.logging_config import get_logger
from app.middleware.correlation_id import (
    set_user_id, set_query_id, set_conversation_id, set_property_id,
    get_correlation_id
)

logger = get_logger(__name__)


# Example 1: Basic structured logging
def example_basic_logging():
    """Basic structured logging example"""
    logger.info(
        "user_login",
        user_id=123,
        ip_address="192.168.1.1",
        success=True
    )


# Example 2: NLQ Query Logging
def example_nlq_query_logging():
    """Example of logging NLQ query with full context"""
    # Set context variables
    set_user_id(123)
    set_query_id(456)
    set_conversation_id("conv-789")
    set_property_id(1)
    
    # Log query start
    logger.info(
        "nlq_query_start",
        question="What was NOI for Eastern Shore in Q3?",
        intent="metric_query",
        method="hybrid_rag_sql"
    )
    
    # Log query completion
    logger.info(
        "nlq_query_complete",
        query_id=456,
        execution_time_ms=1234,
        confidence=0.95,
        success=True,
        from_cache=False,
        retrieval_results=5,
        llm_tokens=250,
        answer_length=150
    )


# Example 3: Error Logging
def example_error_logging():
    """Example of logging errors with context"""
    try:
        # Some operation that might fail
        result = 1 / 0
    except Exception as e:
        logger.error(
            "operation_failed",
            operation="division",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True  # Include stack trace
        )


# Example 4: Retrieval Logging
def example_retrieval_logging():
    """Example of logging retrieval operations"""
    logger.info(
        "retrieval_start",
        query="NOI for property",
        method="pinecone",
        top_k=10
    )
    
    # Log retrieval results
    logger.info(
        "retrieval_complete",
        method="pinecone",
        results_count=8,
        latency_ms=45.2,
        avg_similarity=0.85,
        min_similarity=0.72,
        max_similarity=0.95
    )


# Example 5: LLM Call Logging
def example_llm_logging():
    """Example of logging LLM API calls"""
    logger.info(
        "llm_call_start",
        model="gpt-4o",
        operation="answer_generation",
        prompt_length=500
    )
    
    logger.info(
        "llm_call_complete",
        model="gpt-4o",
        operation="answer_generation",
        input_tokens=500,
        output_tokens=100,
        latency_ms=1234,
        cost_usd=0.012
    )


# Example 6: Cache Logging
def example_cache_logging():
    """Example of logging cache operations"""
    logger.info(
        "cache_hit",
        cache_type="semantic",
        query_hash="abc123",
        latency_ms=2.5
    )
    
    logger.info(
        "cache_miss",
        cache_type="semantic",
        query_hash="def456",
        latency_ms=1.2
    )


# Example 7: Hallucination Detection Logging
def example_hallucination_logging():
    """Example of logging hallucination detection"""
    logger.info(
        "hallucination_detection",
        claim_count=3,
        verified_claims=2,
        unverified_claims=1,
        detection_time_ms=45.2,
        flagged_claims=[
            {
                "claim_type": "currency",
                "value": 1500000.0,
                "verified": False
            }
        ]
    )


# Example 8: Citation Extraction Logging
def example_citation_logging():
    """Example of logging citation extraction"""
    logger.info(
        "citation_extraction",
        claim_count=2,
        citations_extracted=2,
        extraction_time_ms=23.5,
        sources=[
            {
                "type": "document",
                "document_type": "income_statement",
                "page": 2,
                "line": 15
            }
        ]
    )


# Example 9: Performance Logging
def example_performance_logging():
    """Example of logging performance metrics"""
    logger.info(
        "performance_metric",
        metric="query_latency",
        value=1234.5,
        unit="ms",
        percentile=95,
        method="rag"
    )


# Example 10: Context-Aware Logging
def example_context_aware_logging():
    """Example of using context variables for logging"""
    # Context is automatically added by logging_config
    correlation_id = get_correlation_id()
    
    logger.info(
        "context_aware_log",
        message="This log includes correlation_id, user_id, etc. from context",
        additional_data="some value"
    )


# Example 11: Structured Error with Context
def example_structured_error():
    """Example of structured error logging with full context"""
    try:
        # Operation that might fail
        raise ValueError("Invalid input")
    except Exception as e:
        logger.error(
            "operation_error",
            operation="data_processing",
            error_type=type(e).__name__,
            error_message=str(e),
            user_id=get_user_id(),
            query_id=get_query_id(),
            correlation_id=get_correlation_id(),
            exc_info=True
        )


# Example 12: Batch Operation Logging
def example_batch_logging():
    """Example of logging batch operations"""
    logger.info(
        "batch_operation_start",
        operation="index_rebuild",
        total_items=10000,
        batch_size=100
    )
    
    # Log progress
    for i in range(0, 10000, 100):
        logger.info(
            "batch_operation_progress",
            operation="index_rebuild",
            processed=i,
            total=10000,
            progress_percent=(i / 10000) * 100
        )
    
    logger.info(
        "batch_operation_complete",
        operation="index_rebuild",
        total_items=10000,
        success_count=10000,
        failed_count=0,
        duration_ms=5000
    )

