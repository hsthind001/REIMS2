# Query Router Guide

## Overview

Query router classifies queries by complexity and routes them to appropriate processing pipelines for optimal performance:

- **Simple**: Direct SQL execution (<500ms)
- **Medium**: Hybrid RAG + SQL
- **Complex**: Multi-step reasoning

## Architecture

```
User Query
    ↓
[Query Router]
    ├─ Rule-Based Classification (fast)
    └─ LLM Classification (fallback)
    ↓
[Route Decision]
    ├─ Simple → Direct SQL
    ├─ Medium → Hybrid RAG + SQL
    └─ Complex → Multi-Step Reasoning
    ↓
[Execute Query]
```

## Query Complexity Levels

### Simple Queries

**Characteristics**:
- Single metric, single property, single period
- Direct questions
- Keywords: "what is", "show me", "get", "tell me"

**Examples**:
- "What is NOI for Property X?"
- "Show me revenue in Q3"
- "Get DSCR for Property 1"
- "Tell me the occupancy rate"

**Route**: `direct_sql`
**Target Latency**: <500ms

### Medium Queries

**Characteristics**:
- Multiple metrics, comparisons, trends
- Cross-property or cross-period queries
- Keywords: "compare", "trend", "across", "all properties"

**Examples**:
- "Compare revenue across properties"
- "Show trends for all properties"
- "Compare DSCR between Q2 and Q3"
- "Show NOI for all properties"

**Route**: `hybrid_rag_sql`
**Target Latency**: <2s

### Complex Queries

**Characteristics**:
- Multi-hop reasoning
- "Why" or "how" questions
- Predictions and analysis
- Keywords: "why", "how", "explain", "analyze", "predict"

**Examples**:
- "Why did NOI decrease for Property X?"
- "How did vacancy affect revenue?"
- "Explain why DSCR dropped"
- "Analyze the impact of rent increases on NOI"
- "Predict NOI for next quarter"

**Route**: `multi_step_reasoning`
**Target Latency**: <10s

## Configuration

Configuration is managed in `app/config/query_router_config.py`:

```python
from app.config.query_router_config import query_router_config

# Classification Settings
query_router_config.USE_LLM_CLASSIFICATION = True  # Use LLM for classification
query_router_config.LLM_MODEL = "gpt-4o"  # Fast, accurate
query_router_config.LLM_TEMPERATURE = 0.3  # Low for classification

# Performance Targets
query_router_config.TARGET_DECISION_TIME_MS = 100  # <100ms
query_router_config.TARGET_ROUTING_ACCURACY = 0.90  # >90%

# Routing Thresholds
query_router_config.SIMPLE_CONFIDENCE_THRESHOLD = 0.85
query_router_config.MEDIUM_CONFIDENCE_THRESHOLD = 0.80
query_router_config.COMPLEX_CONFIDENCE_THRESHOLD = 0.75

# Routes
query_router_config.SIMPLE_ROUTE = "direct_sql"
query_router_config.MEDIUM_ROUTE = "hybrid_rag_sql"
query_router_config.COMPLEX_ROUTE = "multi_step_reasoning"
```

### Environment Variables

```bash
# LLM Classification
export QUERY_ROUTER_USE_LLM="true"
export QUERY_ROUTER_LLM_MODEL="gpt-4o"
export QUERY_ROUTER_LLM_TEMPERATURE=0.3

# Performance
export QUERY_ROUTER_DECISION_TIME_MS=100
export QUERY_ROUTER_TARGET_ACCURACY=0.90

# Thresholds
export QUERY_ROUTER_SIMPLE_THRESHOLD=0.85
export QUERY_ROUTER_MEDIUM_THRESHOLD=0.80
export QUERY_ROUTER_COMPLEX_THRESHOLD=0.75

# Caching
export QUERY_ROUTER_CACHE_ENABLED="true"
export QUERY_ROUTER_CACHE_TTL_MINUTES=60
```

## Usage

### Basic Query Routing

```python
from app.services.query_router_service import QueryRouterService

# Initialize router
router = QueryRouterService()

# Route query
result = router.route_query("What is NOI for Property X?")

print(f"Query: {result['query']}")
print(f"Complexity: {result['complexity']}")
print(f"Route: {result['route']}")
print(f"Confidence: {result['confidence']:.2%}")
print(f"Method: {result['method']}")
print(f"Decision time: {result['decision_time_ms']:.2f}ms")
```

### Example Output

```python
{
    'query': 'What is NOI for Property X?',
    'complexity': 'simple',
    'route': 'direct_sql',
    'confidence': 0.92,
    'method': 'rules_simple',
    'decision_time_ms': 15.3,
    'cached': False
}
```

### Integration with NLQ Pipeline

```python
from app.services.query_router_service import QueryRouterService
from app.services.nlq_service import NLQService

router = QueryRouterService()
nlq_service = NLQService(db)

# Route query first
routing_result = router.route_query(user_query)

# Execute based on route
if routing_result['route'] == 'direct_sql':
    # Execute direct SQL
    result = nlq_service.execute_direct_sql(user_query)
elif routing_result['route'] == 'hybrid_rag_sql':
    # Execute hybrid RAG + SQL
    result = nlq_service.execute_hybrid_query(user_query)
elif routing_result['route'] == 'multi_step_reasoning':
    # Execute multi-step reasoning
    result = nlq_service.execute_multi_step_reasoning(user_query)
```

## Classification Methods

### Rule-Based Classification (Primary)

**Advantages**:
- Fast (<10ms)
- No API costs
- Predictable
- Works offline

**How It Works**:
1. Check for complex keywords/patterns first
2. Check for medium keywords/patterns
3. Check for simple keywords/patterns
4. Default to medium if no match

**Example**:
```python
# Query: "Why did NOI decrease?"
# Matches: "why" keyword → Complex pattern
# Result: complexity=complex, confidence=0.88
```

### LLM Classification (Fallback)

**Advantages**:
- High accuracy
- Context-aware
- Handles edge cases

**When Used**:
- When `USE_LLM_CLASSIFICATION=true`
- Falls back to rules if LLM fails

**Example**:
```python
# Query: "What's the revenue situation?"
# LLM analyzes context → Simple query
# Result: complexity=simple, confidence=0.91
```

## Routing Accuracy

### Target: >90% Accuracy

**Measurement**:
- Compare routing decisions to ground truth
- Track accuracy over time
- Monitor route distribution

**Improving Accuracy**:
- Tune confidence thresholds
- Add more keywords/patterns
- Use LLM for ambiguous queries
- Learn from user feedback

## Performance

### Decision Time Target: <100ms

**Breakdown**:
- Rule-based: <10ms
- LLM-based: ~50-100ms
- Cached: <1ms

**Optimization**:
- Use caching for common queries
- Prefer rule-based when possible
- Batch LLM calls if needed

## Caching

### Cache Behavior

- **Cache Key**: MD5 hash of normalized query
- **TTL**: 60 minutes (configurable)
- **Purpose**: Avoid re-classifying identical queries

### Cache Management

```python
# Get cache statistics
stats = router.get_cache_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"Cache TTL: {stats['cache_ttl_minutes']} minutes")

# Clear cache
router.clear_cache()
```

## Monitoring

### Routing Statistics

```python
stats = router.get_routing_stats()
print(f"Total queries: {stats['total_cached_queries']}")
print(f"Complexity distribution: {stats['complexity_distribution']}")
print(f"Route distribution: {stats['route_distribution']}")
```

### Example Output

```python
{
    'total_cached_queries': 150,
    'complexity_distribution': {
        'simple': 80,
        'medium': 50,
        'complex': 20
    },
    'route_distribution': {
        'direct_sql': 80,
        'hybrid_rag_sql': 50,
        'multi_step_reasoning': 20
    }
}
```

## Best Practices

1. **Use Caching**: Enable caching for common queries
2. **Monitor Accuracy**: Track routing accuracy over time
3. **Tune Thresholds**: Adjust confidence thresholds based on data
4. **Fallback Strategy**: Always have rule-based fallback
5. **Log Decisions**: Enable logging for debugging
6. **Review Edge Cases**: Monitor queries that default to medium

## Troubleshooting

### Low Accuracy (<90%)

**Possible Causes**:
- Thresholds too strict/loose
- Missing keywords/patterns
- Ambiguous queries

**Solutions**:
- Adjust confidence thresholds
- Add more keywords/patterns
- Use LLM for ambiguous cases
- Review misclassified queries

### High Decision Time (>100ms)

**Possible Causes**:
- LLM calls too slow
- Cache not working
- Too many pattern checks

**Solutions**:
- Enable caching
- Use rule-based for common patterns
- Optimize LLM timeout
- Reduce pattern complexity

### Incorrect Routing

**Possible Causes**:
- Query doesn't match patterns
- LLM misclassification
- Threshold too low

**Solutions**:
- Review query examples
- Adjust thresholds
- Add custom patterns
- Use LLM for edge cases

## Success Criteria

- ✅ Classifies queries into: simple, medium, complex
- ✅ Simple queries routed to direct SQL execution
- ✅ Medium queries use hybrid search + SQL
- ✅ Complex queries use multi-step reasoning
- ✅ Routing accuracy >90%
- ✅ Decision time <100ms
- ✅ Caching for common queries
- ✅ Monitoring for route distribution

## Future Enhancements

- **Machine Learning**: Train classifier on query logs
- **Adaptive Thresholds**: Adjust thresholds based on accuracy
- **User Feedback**: Learn from user corrections
- **Query History**: Use query history to improve classification
- **Context-Aware**: Consider user context in classification

