# NLQ Metrics Guide

## Overview

Comprehensive Prometheus metrics for monitoring NLQ system health, performance, and quality. All metrics are exposed at `/metrics` endpoint and can be scraped by Prometheus.

## Metrics Endpoint

**URL**: `http://localhost:8000/metrics`

**Format**: Prometheus text format

**Content-Type**: `text/plain; version=0.0.4; charset=utf-8`

## Metrics Categories

### 1. Counters

#### `nlq_queries_total`

Total number of NLQ queries processed.

**Labels**:
- `intent`: Query intent (e.g., 'metric_query', 'comparison', 'trend')
- `method`: Query method (e.g., 'direct_sql', 'rag', 'hybrid')
- `from_cache`: Whether result came from cache ('true' or 'false')
- `complexity`: Query complexity ('simple', 'medium', 'complex')

**Example**:
```
nlq_queries_total{intent="metric_query",method="rag",from_cache="false",complexity="medium"} 1234
```

#### `nlq_llm_tokens_total`

Total LLM tokens used.

**Labels**:
- `model`: LLM model name (e.g., 'gpt-4o', 'claude-3-opus')
- `operation`: Operation type (e.g., 'query_rewriting', 'answer_generation', 'coreference')
- `type`: Token type ('input' or 'output')

**Example**:
```
nlq_llm_tokens_total{model="gpt-4o",operation="answer_generation",type="input"} 50000
nlq_llm_tokens_total{model="gpt-4o",operation="answer_generation",type="output"} 10000
```

#### `nlq_errors_total`

Total number of errors.

**Labels**:
- `error_type`: Error type (e.g., 'llm_api_error', 'retrieval_error', 'timeout')
- `service`: Service name (e.g., 'nlq_service', 'rag_service', 'embedding_service')
- `severity`: Error severity ('critical', 'warning', 'info')

**Example**:
```
nlq_errors_total{error_type="llm_api_error",service="nlq_service",severity="critical"} 5
```

#### `nlq_hallucination_detections_total`

Total number of hallucinations detected.

**Labels**:
- `claim_type`: Type of claim ('currency', 'percentage', 'date', 'ratio')
- `verified`: Whether claim was verified ('true' or 'false')

**Example**:
```
nlq_hallucination_detections_total{claim_type="currency",verified="false"} 12
```

#### `nlq_citations_extracted_total`

Total number of citations extracted.

**Labels**:
- `source_type`: Source type ('document' or 'sql')
- `document_type`: Document type (e.g., 'income_statement', 'balance_sheet')

**Example**:
```
nlq_citations_extracted_total{source_type="document",document_type="income_statement"} 456
```

### 2. Histograms

#### `nlq_query_latency_seconds`

Latency of NLQ queries in seconds.

**Labels**:
- `method`: Query method
- `complexity`: Query complexity

**Buckets**: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0

**Example**:
```
nlq_query_latency_seconds_bucket{method="rag",complexity="medium",le="0.5"} 100
nlq_query_latency_seconds_bucket{method="rag",complexity="medium",le="1.0"} 200
nlq_query_latency_seconds_bucket{method="rag",complexity="medium",le="+Inf"} 250
```

#### `nlq_retrieval_latency_seconds`

Latency of retrieval stages in seconds.

**Labels**:
- `stage`: Retrieval stage ('embedding', 'semantic', 'bm25', 'fusion', 'reranking')
- `method`: Method used (e.g., 'pinecone', 'postgresql', 'bm25', 'rrf', 'cohere')

**Buckets**: 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0

**Example**:
```
nlq_retrieval_latency_seconds_bucket{stage="semantic",method="pinecone",le="0.1"} 500
```

#### `nlq_embedding_latency_seconds`

Latency of embedding generation in seconds.

**Labels**:
- `model`: Embedding model (e.g., 'text-embedding-3-large')
- `batch_size`: Batch size used

**Buckets**: 0.01, 0.05, 0.1, 0.5, 1.0, 2.0

#### `nlq_reranking_latency_seconds`

Latency of reranking in seconds.

**Labels**:
- `method`: Reranking method (e.g., 'cohere', 'cross-encoder')
- `candidate_count`: Number of candidates reranked

**Buckets**: 0.05, 0.1, 0.2, 0.5, 1.0, 2.0

#### `nlq_llm_latency_seconds`

Latency of LLM API calls in seconds.

**Labels**:
- `model`: LLM model name
- `operation`: Operation type

**Buckets**: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0

### 3. Gauges

#### `nlq_retrieval_precision`

Precision@k for retrieval.

**Labels**:
- `k`: K value (e.g., '5', '10', '20')

**Example**:
```
nlq_retrieval_precision{k="5"} 0.85
nlq_retrieval_precision{k="10"} 0.78
```

#### `nlq_retrieval_recall`

Recall@k for retrieval.

**Labels**:
- `k`: K value

**Example**:
```
nlq_retrieval_recall{k="5"} 0.72
nlq_retrieval_recall{k="10"} 0.88
```

#### `nlq_cache_hit_rate`

Cache hit rate (0-1).

**Example**:
```
nlq_cache_hit_rate 0.65
```

#### `nlq_active_conversations`

Number of active conversations.

**Example**:
```
nlq_active_conversations 42
```

#### `nlq_index_size`

Size of search indexes.

**Labels**:
- `index_type`: Index type ('pinecone', 'bm25', 'postgresql')

**Example**:
```
nlq_index_size{index_type="pinecone"} 10000
nlq_index_size{index_type="bm25"} 10000
```

## Usage

### Instrumenting Code

#### Track Query

```python
from app.monitoring.metrics import track_query

track_query(
    intent='metric_query',
    method='rag',
    from_cache=False,
    complexity='medium',
    duration=1.2
)
```

#### Track LLM Tokens

```python
from app.monitoring.metrics import track_llm_tokens

track_llm_tokens(
    model='gpt-4o',
    operation='answer_generation',
    input_tokens=500,
    output_tokens=100
)
```

#### Track Error

```python
from app.monitoring.metrics import track_error

track_error(
    error_type='llm_api_error',
    service='nlq_service',
    severity='critical'
)
```

#### Track Retrieval

```python
from app.monitoring.metrics import track_retrieval

track_retrieval(
    stage='semantic',
    method='pinecone',
    duration=0.15
)
```

#### Using Decorators

```python
from app.monitoring.instrumentation import track_query_metric, track_llm_call

@track_query_metric(intent='metric_query', method='rag', complexity='medium')
def process_query(query: str):
    # Query processing logic
    pass

@track_llm_call(model='gpt-4o', operation='answer_generation')
def generate_answer(query: str):
    # LLM call logic
    pass
```

#### Using Context Managers

```python
from app.monitoring.instrumentation import (
    track_retrieval_stage,
    track_embedding_generation,
    track_reranking
)

# Track retrieval stage
with track_retrieval_stage('semantic', 'pinecone'):
    results = pinecone_service.query_vectors(...)

# Track embedding generation
with track_embedding_generation('text-embedding-3-large', batch_size=10):
    embeddings = embedding_service.generate_embeddings(...)

# Track reranking
with track_reranking('cohere', candidate_count=50):
    reranked = reranker_service.rerank(...)
```

## Prometheus Configuration

### prometheus.yml

```yaml
scrape_configs:
  - job_name: 'nlq-backend'
    scrape_interval: 30s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8000']
        labels:
          service: 'nlq-backend'
          environment: 'production'
```

## Grafana Dashboard

Import the dashboard JSON from `backend/monitoring/grafana_dashboard.json`.

**Dashboard Panels**:
1. Query Rate
2. Cache Hit Rate
3. Query Latency (P50, P95, P99)
4. Retrieval Stage Latency
5. LLM Token Usage
6. Error Rate by Type
7. Retrieval Precision@K
8. Retrieval Recall@K
9. Active Conversations
10. Hallucination Detections
11. Citations Extracted
12. LLM Latency by Model

## Prometheus Alerts

Alerts are defined in `backend/monitoring/prometheus_alerts.yml`.

**Key Alerts**:
- **NLQHighErrorRate**: Error rate > 0.1/sec for 5 minutes
- **NLQCriticalErrorRate**: Critical error rate > 0.05/sec for 2 minutes
- **NLQHighQueryLatency**: P95 latency > 5s for 5 minutes
- **NLQVeryHighQueryLatency**: P95 latency > 10s for 2 minutes
- **NLQLowCacheHitRate**: Cache hit rate < 30% for 10 minutes
- **NLQVeryLowCacheHitRate**: Cache hit rate < 10% for 5 minutes
- **NLQHighRetrievalLatency**: P95 retrieval latency > 2s for 5 minutes
- **NLQLowRetrievalPrecision**: Precision@5 < 70% for 15 minutes
- **NLQHighLLMLatency**: P95 LLM latency > 10s for 5 minutes
- **NLQHighLLMTokenUsage**: Token usage > 10k/sec for 10 minutes
- **NLQHighHallucinationRate**: Unverified hallucination rate > 10% for 15 minutes
- **NLQNoQueries**: No queries received for 15 minutes
- **NLQHighActiveConversations**: Active conversations > 1000 for 5 minutes

## Query Examples

### Query Rate by Method

```promql
rate(nlq_queries_total[5m])
```

### Cache Hit Rate

```promql
nlq_cache_hit_rate
```

### P95 Query Latency

```promql
histogram_quantile(0.95, sum(rate(nlq_query_latency_seconds_bucket[5m])) by (le, method))
```

### Error Rate by Type

```promql
rate(nlq_errors_total[5m])
```

### LLM Token Usage Rate

```promql
rate(nlq_llm_tokens_total[5m])
```

### Retrieval Precision@5

```promql
nlq_retrieval_precision{k="5"}
```

### Active Conversations

```promql
nlq_active_conversations
```

## Best Practices

1. **Label Cardinality**: Keep label cardinality low to avoid metric explosion
2. **Histogram Buckets**: Choose buckets appropriate for your latency ranges
3. **Error Tracking**: Track errors with sufficient context (type, service, severity)
4. **Cache Metrics**: Monitor cache hit rate to optimize caching strategy
5. **Quality Metrics**: Track precision/recall to monitor retrieval quality
6. **Cost Tracking**: Monitor LLM token usage to track costs
7. **Alert Thresholds**: Set thresholds based on SLOs and business requirements

## Troubleshooting

### Metrics Not Appearing

1. Check `/metrics` endpoint is accessible
2. Verify Prometheus is scraping the endpoint
3. Check metric names match Prometheus naming conventions
4. Verify labels are valid (no special characters)

### High Cardinality

1. Review label combinations
2. Remove unnecessary labels
3. Use recording rules to aggregate metrics

### Missing Metrics

1. Verify instrumentation code is executed
2. Check for exceptions in metric tracking
3. Verify metric registration

## Success Criteria

- ✅ All queries tracked with labels (intent, method, from_cache)
- ✅ Latency histograms with buckets (0.1s, 0.5s, 1s, 2s, 5s)
- ✅ Retrieval quality metrics (precision@k, recall@k)
- ✅ Cache hit rate gauge
- ✅ LLM token usage counter (by model and operation)
- ✅ Error counters by type
- ✅ Metrics endpoint at /metrics
- ✅ Grafana dashboard configured
- ✅ Prometheus alerts configured

