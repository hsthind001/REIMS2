# Structured Logging Guide

## Overview

Structured logging with JSON format, correlation IDs, and ELK Stack integration for comprehensive log aggregation and analysis.

## Architecture

```
Application
    ↓
[Structured Logging (structlog)]
    ├─ JSON Format
    ├─ Correlation IDs
    ├─ Context Variables
    └─ Sensitive Data Filtering
    ↓
[Log Files]
    ├─ /var/log/reims2/reims2.log
    └─ /var/log/reims2/reims2_error.log
    ↓
[Logstash]
    ├─ Parse JSON
    ├─ Add Metadata
    └─ Index to Elasticsearch
    ↓
[Elasticsearch]
    └─ Store Logs
    ↓
[Kibana]
    └─ Visualize & Search
```

## Log Structure

### Standard Log Format

```json
{
    "timestamp": "2024-11-26T10:00:00.123456Z",
    "level": "INFO",
    "logger": "app.services.nlq_service",
    "message": "nlq_query_complete",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": 123,
    "query_id": 456,
    "conversation_id": "conv-789",
    "property_id": 1,
    "question": "What was NOI for Eastern Shore in Q3?",
    "intent": "metric_query",
    "method": "hybrid_rag_sql",
    "from_cache": false,
    "execution_time_ms": 1234,
    "confidence": 0.95,
    "success": true,
    "retrieval_results": 5,
    "llm_tokens": 250,
    "event": "nlq_query_complete"
}
```

### Required Fields

- `timestamp`: ISO 8601 timestamp
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `message`: Log message/event name
- `correlation_id`: Request correlation ID (UUID)

### Optional Context Fields

- `user_id`: User ID
- `query_id`: NLQ query ID
- `conversation_id`: Conversation ID
- `property_id`: Property ID
- `intent`: Query intent
- `method`: Query method
- `execution_time_ms`: Execution time in milliseconds
- `success`: Success/failure flag
- `error_type`: Error type (for errors)
- `error_message`: Error message (for errors)

## Usage

### Basic Logging

```python
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)

# Info log
logger.info(
    "user_action",
    action="login",
    user_id=123,
    ip_address="192.168.1.1"
)

# Error log
logger.error(
    "operation_failed",
    operation="data_processing",
    error_type="ValueError",
    error_message="Invalid input",
    exc_info=True  # Include stack trace
)
```

### NLQ Query Logging

```python
from app.monitoring.logging_config import get_logger
from app.middleware.correlation_id import (
    set_user_id, set_query_id, set_conversation_id
)

logger = get_logger(__name__)

# Set context
set_user_id(123)
set_query_id(456)
set_conversation_id("conv-789")

# Log query start
logger.info(
    "nlq_query_start",
    question="What was NOI?",
    intent="metric_query",
    method="rag"
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
    llm_tokens=250
)
```

### Error Logging

```python
try:
    result = process_data()
except Exception as e:
    logger.error(
        "operation_error",
        operation="data_processing",
        error_type=type(e).__name__,
        error_message=str(e),
        exc_info=True  # Include full stack trace
    )
```

### Performance Logging

```python
import time

start_time = time.time()
result = expensive_operation()
duration_ms = (time.time() - start_time) * 1000

logger.info(
    "performance_metric",
    operation="expensive_operation",
    duration_ms=duration_ms,
    result_count=len(result)
)
```

## Correlation IDs

### Automatic Correlation IDs

Correlation IDs are automatically added by `CorrelationIDMiddleware`:
- Generated UUID if not present in `X-Correlation-ID` header
- Added to response headers
- Available in all logs via context variables

### Manual Correlation ID

```python
from app.middleware.correlation_id import get_correlation_id

correlation_id = get_correlation_id()
logger.info("operation", correlation_id=correlation_id)
```

### Request Tracing

```python
# Client sends request with correlation ID
headers = {"X-Correlation-ID": "550e8400-e29b-41d4-a716-446655440000"}

# All logs for this request will include the same correlation_id
# Can trace request across services using correlation_id
```

## Context Variables

### Setting Context

```python
from app.middleware.correlation_id import (
    set_user_id, set_query_id, set_conversation_id, set_property_id
)

# Set context (automatically added to all logs)
set_user_id(123)
set_query_id(456)
set_conversation_id("conv-789")
set_property_id(1)

# All subsequent logs will include these fields
logger.info("operation")  # Includes user_id, query_id, etc.
```

### Getting Context

```python
from app.middleware.correlation_id import (
    get_user_id, get_query_id, get_conversation_id, get_correlation_id
)

user_id = get_user_id()
query_id = get_query_id()
correlation_id = get_correlation_id()
```

## Sensitive Data Filtering

### Automatic Filtering

Sensitive data is automatically filtered from logs:
- Passwords, tokens, API keys
- Email addresses, phone numbers
- Credit card numbers, SSNs
- Authorization headers

### Filtered Fields

```python
# These fields are automatically redacted
logger.info("login", password="secret123")  # password: "[REDACTED]"
logger.info("api_call", api_key="abc123")  # api_key: "[REDACTED]"
```

### Disable Filtering (Not Recommended)

```bash
export FILTER_SENSITIVE_DATA="false"
```

## Log Sampling

### High-Volume Log Sampling

High-volume logs are sampled to reduce storage:
- Default: 10% sampling rate
- Errors and critical logs are never sampled
- Configurable via `LOG_SAMPLING_RATE`

### Configuration

```bash
# Sample 10% of logs (default)
export LOG_SAMPLING_RATE=0.1

# Sample 50% of logs
export LOG_SAMPLING_RATE=0.5

# No sampling (100% of logs)
export LOG_SAMPLING_RATE=1.0
```

### Always Logged

These logs are never sampled:
- Errors (`level=ERROR`)
- Critical messages (`level=CRITICAL`)
- Exceptions (`exc_info=True`)

## Log Rotation

### Automatic Rotation

Logs are automatically rotated:
- Max file size: 1GB (configurable)
- Keep: 30 days (configurable)
- Compression: Enabled for old logs

### Configuration

```bash
# Max file size (bytes)
export LOG_MAX_BYTES=1073741824  # 1GB

# Number of backup files to keep
export LOG_BACKUP_COUNT=30  # 30 days
```

### Manual Rotation

```bash
# Using logrotate (if installed)
sudo logrotate -f /etc/logrotate.d/reims2
```

## ELK Stack Setup

### Start ELK Stack

```bash
# Start ELK Stack
docker-compose -f docker-compose.elk.yml up -d

# Check status
docker-compose -f docker-compose.elk.yml ps

# View logs
docker-compose -f docker-compose.elk.yml logs -f
```

### Access Services

- **Elasticsearch**: http://localhost:9200
- **Kibana**: http://localhost:5601
- **Logstash**: http://localhost:9600

### Verify Logs

```bash
# Check Elasticsearch indices
curl http://localhost:9200/_cat/indices?v

# Search logs
curl http://localhost:9200/reims2-logs-*/_search?q=message:nlq_query
```

## Kibana Dashboard

### Import Dashboard

1. Open Kibana: http://localhost:5601
2. Go to **Management** → **Saved Objects**
3. Click **Import**
4. Select `backend/monitoring/kibana_dashboard.json`
5. Click **Import**

### Dashboard Panels

1. **Query Rate by Method**: Shows query volume over time
2. **Query Latency (P50, P95, P99)**: Performance percentiles
3. **Error Rate by Type**: Error breakdown
4. **Cache Hit Rate**: Cache effectiveness

### Custom Queries

```kibana
# Find all queries for a user
user_id:123

# Find queries by correlation ID
correlation_id:"550e8400-e29b-41d4-a716-446655440000"

# Find errors
level:ERROR

# Find slow queries
execution_time_ms:>5000

# Find queries by intent
intent:"metric_query"
```

## Best Practices

### 1. Use Structured Logging

```python
# ✅ Good: Structured logging
logger.info(
    "user_action",
    action="login",
    user_id=123,
    success=True
)

# ❌ Bad: String formatting
logger.info(f"User {user_id} logged in successfully")
```

### 2. Include Context

```python
# ✅ Good: Include all relevant context
logger.info(
    "nlq_query_complete",
    query_id=456,
    execution_time_ms=1234,
    confidence=0.95,
    success=True
)

# ❌ Bad: Missing context
logger.info("Query completed")
```

### 3. Use Appropriate Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General information about operations
- **WARNING**: Warning messages (non-critical issues)
- **ERROR**: Error messages (operations failed)
- **CRITICAL**: Critical errors (system failures)

### 4. Include Correlation IDs

```python
# ✅ Good: Correlation ID automatically included
logger.info("operation", additional_data="value")

# ❌ Bad: Manual correlation ID (not needed)
logger.info("operation", correlation_id=get_correlation_id())
```

### 5. Filter Sensitive Data

```python
# ✅ Good: Sensitive data automatically filtered
logger.info("api_call", api_key="secret123")  # api_key: "[REDACTED]"

# ❌ Bad: Logging sensitive data directly
logger.info(f"API key: {api_key}")  # Exposed in logs!
```

### 6. Log Errors with Context

```python
# ✅ Good: Error with full context
try:
    result = process_data()
except Exception as e:
    logger.error(
        "operation_error",
        operation="data_processing",
        error_type=type(e).__name__,
        error_message=str(e),
        user_id=get_user_id(),
        exc_info=True
    )

# ❌ Bad: Error without context
except Exception as e:
    logger.error(str(e))
```

### 7. Use Event Names

```python
# ✅ Good: Descriptive event names
logger.info("nlq_query_complete", ...)
logger.info("cache_hit", ...)
logger.info("retrieval_start", ...)

# ❌ Bad: Generic messages
logger.info("done", ...)
logger.info("success", ...)
```

## Configuration

### Environment Variables

```bash
# Log directory
export LOG_DIR="/var/log/reims2"

# Log level
export LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Log rotation
export LOG_MAX_BYTES=1073741824  # 1GB
export LOG_BACKUP_COUNT=30  # 30 days

# Log sampling
export LOG_SAMPLING_RATE=0.1  # 10%

# Sensitive data filtering
export FILTER_SENSITIVE_DATA="true"
```

### Application Configuration

```python
from app.monitoring.logging_config import configure_logging

# Configure logging
configure_logging(
    log_level="INFO",
    log_to_file=True,
    log_to_console=True,
    sampling_rate=0.1
)
```

## Troubleshooting

### Logs Not Appearing

1. Check log directory permissions
2. Verify log level configuration
3. Check for log rotation issues
4. Verify file handlers are configured

### Correlation IDs Missing

1. Ensure `CorrelationIDMiddleware` is added to FastAPI app
2. Check context variables are set correctly
3. Verify middleware order (should be first)

### Sensitive Data in Logs

1. Verify `FILTER_SENSITIVE_DATA=true`
2. Check sensitive data filter is working
3. Review log output for redacted fields

### High Log Volume

1. Enable log sampling (`LOG_SAMPLING_RATE=0.1`)
2. Increase log rotation frequency
3. Filter out debug logs in production
4. Use log aggregation (ELK Stack)

### ELK Stack Issues

1. Check Elasticsearch health: `curl http://localhost:9200/_cluster/health`
2. Verify Logstash is processing logs
3. Check Kibana index patterns
4. Review Logstash logs: `docker-compose -f docker-compose.elk.yml logs logstash`

## Success Criteria

- ✅ All logs in JSON format
- ✅ Include: timestamp, level, user_id, query_id, conversation_id, execution_time
- ✅ Correlation ID for tracing across services
- ✅ Log sampling for high-volume operations (10%)
- ✅ Log rotation (max 1GB files, keep 30 days)
- ✅ No sensitive data in logs (PII, API keys)
- ✅ ELK Stack integration
- ✅ Kibana dashboards
- ✅ Documentation

## Example Log Entries

### Query Start

```json
{
    "timestamp": "2024-11-26T10:00:00.123456Z",
    "level": "INFO",
    "message": "nlq_query_start",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": 123,
    "question": "What was NOI for Eastern Shore in Q3?",
    "intent": "metric_query",
    "method": "hybrid_rag_sql"
}
```

### Query Complete

```json
{
    "timestamp": "2024-11-26T10:00:01.357890Z",
    "level": "INFO",
    "message": "nlq_query_complete",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": 123,
    "query_id": 456,
    "conversation_id": "conv-789",
    "execution_time_ms": 1234,
    "confidence": 0.95,
    "success": true,
    "from_cache": false,
    "retrieval_results": 5,
    "llm_tokens": 250
}
```

### Error

```json
{
    "timestamp": "2024-11-26T10:00:02.123456Z",
    "level": "ERROR",
    "message": "operation_error",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": 123,
    "query_id": 456,
    "operation": "data_processing",
    "error_type": "ValueError",
    "error_message": "Invalid input",
    "exception": "Traceback (most recent call last):\n..."
}
```

