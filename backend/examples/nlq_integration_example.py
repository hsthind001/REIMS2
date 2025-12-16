"""
Example: Using Integrated NLQ Service

Demonstrates how to use the integrated service with SemanticCacheService
and NaturalLanguageQueryService.
"""
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.nlq_service_integrated import IntegratedNLQService


def example_basic_usage():
    """Basic usage example"""
    db = SessionLocal()
    
    try:
        # Initialize integrated service
        service = IntegratedNLQService(db)
        
        # Query 1: First time (cache miss)
        print("=" * 60)
        print("Query 1: First time (cache miss)")
        print("=" * 60)
        result1 = service.query(
            question="What was NOI for Eastern Shore in Q3 2024?",
            user_id=1,
            context={
                'property_id': 1,
                'property_code': 'ESP001',
                'property_name': 'Eastern Shore Plaza'
            }
        )
        print(f"From Cache: {result1.get('from_cache')}")
        print(f"Answer: {result1.get('answer')}")
        print(f"Execution Time: {result1.get('execution_time_ms')}ms")
        
        # Query 2: Same question (cache hit)
        print("\n" + "=" * 60)
        print("Query 2: Same question (cache hit)")
        print("=" * 60)
        result2 = service.query(
            question="What was NOI for Eastern Shore in Q3 2024?",
            user_id=1
        )
        print(f"From Cache: {result2.get('from_cache')}")
        print(f"Answer: {result2.get('answer')}")
        print(f"Cache Similarity: {result2.get('cache_similarity')}")
        print(f"Execution Time: {result2.get('execution_time_ms')}ms")
        
        # Query 3: Paraphrased question (semantic cache hit)
        print("\n" + "=" * 60)
        print("Query 3: Paraphrased question (semantic cache hit)")
        print("=" * 60)
        result3 = service.query(
            question="Show me the net operating income for Eastern Shore Plaza in the third quarter of 2024",
            user_id=1
        )
        print(f"From Cache: {result3.get('from_cache')}")
        print(f"Answer: {result3.get('answer')}")
        print(f"Cache Similarity: {result3.get('cache_similarity')}")
        print(f"Execution Time: {result3.get('execution_time_ms')}ms")
        
        # Get statistics
        print("\n" + "=" * 60)
        print("Cache Statistics")
        print("=" * 60)
        stats = service.get_cache_statistics(hours=24)
        print(f"Total Queries: {stats['integration_stats']['total_queries']}")
        print(f"Cache Hits: {stats['integration_stats']['cache_hits']}")
        print(f"Cache Misses: {stats['integration_stats']['cache_misses']}")
        print(f"Cache Errors: {stats['integration_stats']['cache_errors']}")
        print(f"Hit Rate: {stats['integration_stats']['hit_rate']:.2%}")
        
        # Get health status
        print("\n" + "=" * 60)
        print("Health Status")
        print("=" * 60)
        health = service.get_health_status()
        print(f"Component A (Cache): {health['component_a']['available']}")
        print(f"Component B (NLQ): {health['component_b']['available']}")
        print(f"Integration Status: {health['integration']['status']}")
        print(f"Graceful Degradation: {health['integration']['graceful_degradation']}")
        
    finally:
        db.close()


def example_error_handling():
    """Example showing graceful degradation"""
    db = SessionLocal()
    
    try:
        service = IntegratedNLQService(db)
        
        # Even if cache fails, query still works
        print("=" * 60)
        print("Error Handling Example")
        print("=" * 60)
        
        # Query with potential cache error (simulated)
        result = service.query(
            question="What was NOI for Eastern Shore?",
            user_id=1
        )
        
        # Query succeeds even if cache had errors
        assert result.get('success') is True
        print(f"Query succeeded: {result.get('success')}")
        print(f"Answer: {result.get('answer')[:100]}...")
        
    finally:
        db.close()


def example_metrics_monitoring():
    """Example showing metrics monitoring"""
    db = SessionLocal()
    
    try:
        service = IntegratedNLQService(db)
        
        # Process multiple queries
        questions = [
            "What was NOI for Eastern Shore?",
            "Show me properties with losses",
            "What is the DSCR for all properties?",
            "Compare revenue across properties"
        ]
        
        for question in questions:
            result = service.query(
                question=question,
                user_id=1
            )
            print(f"Query: {question[:40]}...")
            print(f"  Cache: {'HIT' if result.get('from_cache') else 'MISS'}")
            print(f"  Latency: {result.get('execution_time_ms')}ms")
        
        # Get final statistics
        stats = service.get_cache_statistics()
        print("\n" + "=" * 60)
        print("Final Statistics")
        print("=" * 60)
        print(f"Total: {stats['integration_stats']['total_queries']}")
        print(f"Hits: {stats['integration_stats']['cache_hits']}")
        print(f"Misses: {stats['integration_stats']['cache_misses']}")
        print(f"Hit Rate: {stats['integration_stats']['hit_rate']:.2%}")
        
    finally:
        db.close()


if __name__ == "__main__":
    print("Running Integrated NLQ Service Examples\n")
    
    # Example 1: Basic usage
    example_basic_usage()
    
    # Example 2: Error handling
    # example_error_handling()
    
    # Example 3: Metrics monitoring
    # example_metrics_monitoring()

