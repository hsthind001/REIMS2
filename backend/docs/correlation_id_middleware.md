# Correlation ID Middleware

## Overview

The Correlation ID Middleware automatically generates and tracks unique correlation IDs for all HTTP requests, enabling distributed tracing across services. Correlation IDs are added to request/response headers and stored in context variables for logging.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP Request                             │
│  GET /api/v1/nlq/query                                      │
│  Headers: {X-Correlation-ID: "550e8400-..."} (optional)    │
└────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              CorrelationIDMiddleware                        │
│  1. Check for X-Correlation-ID header                      │
│  2. Generate UUID if not present                            │
│  3. Set in context variable                                 │
│  4. Add to response header                                  │
└────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Request Processing                             │
│  All logs include correlation_id automatically             │
└────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    HTTP Response                            │
│  Headers: {X-Correlation-ID: "550e8400-..."}                │
└─────────────────────────────────────────────────────────────┘
```

## Installation

No additional installation required. Middleware is automatically added to FastAPI app in `main.py`.

## Usage

### Automatic Usage

The middleware is automatically active for all requests:

```python
# In main.py
from app.middleware.correlation_id import CorrelationIDMiddleware

app.add_middleware(CorrelationIDMiddleware)
```

### Manual Correlation ID

```python
from app.middleware.correlation_id import get_correlation_id, set_user_id

# Get current correlation ID
correlation_id = get_correlation_id()
print(f"Correlation ID: {correlation_id}")

# Set context variables (automatically included in logs)
set_user_id(123)
```

### Client-Side Usage

```python
import requests

# Send request with correlation ID
headers = {"X-Correlation-ID": "550e8400-e29b-41d4-a716-446655440000"}
response = requests.get("http://api/v1/nlq/query", headers=headers)

# Response includes same correlation ID
correlation_id = response.headers.get("X-Correlation-ID")
```

## API Reference

### CorrelationIDMiddleware

#### `__init__(app: ASGIApp, header_name: str = "X-Correlation-ID")`

Initialize correlation ID middleware.

**Args**:
- `app`: ASGI application
- `header_name`: Header name for correlation ID (default: "X-Correlation-ID")

**Example**:
```python
app.add_middleware(CorrelationIDMiddleware, header_name="X-Request-ID")
```

---

### Context Functions

#### `get_correlation_id() -> Optional[str]`

Get current correlation ID from context.

**Returns**:
Correlation ID string or None

**Example**:
```python
correlation_id = get_correlation_id()
```

#### `set_user_id(user_id: int)`

Set user ID in context (automatically added to logs).

**Args**:
- `user_id`: User ID

**Example**:
```python
set_user_id(123)
```

#### `get_user_id() -> Optional[int]`

Get user ID from context.

**Returns**:
User ID or None

#### `set_query_id(query_id: int)`

Set query ID in context.

**Args**:
- `query_id`: Query ID

#### `get_query_id() -> Optional[int]`

Get query ID from context.

#### `set_conversation_id(conversation_id: str)`

Set conversation ID in context.

**Args**:
- `conversation_id`: Conversation ID

#### `get_conversation_id() -> Optional[str]`

Get conversation ID from context.

#### `set_property_id(property_id: int)`

Set property ID in context.

**Args**:
- `property_id`: Property ID

#### `get_property_id() -> Optional[int]`

Get property ID from context.

## Configuration

No configuration required. Middleware uses default header name `X-Correlation-ID`.

To customize:

```python
app.add_middleware(
    CorrelationIDMiddleware,
    header_name="X-Request-ID"  # Custom header name
)
```

## Integration with Logging

Correlation IDs are automatically included in structured logs:

```python
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)

# Correlation ID automatically included
logger.info("operation_complete", result="success")
# Log output: {"correlation_id": "550e8400-...", "message": "operation_complete", ...}
```

## Distributed Tracing

### Cross-Service Tracing

When calling other services, include correlation ID:

```python
import requests
from app.middleware.correlation_id import get_correlation_id

correlation_id = get_correlation_id()
headers = {"X-Correlation-ID": correlation_id}

response = requests.get(
    "http://other-service/api/endpoint",
    headers=headers
)
```

### Tracing in Logs

Search logs by correlation ID:

```bash
# In Kibana/ELK
correlation_id:"550e8400-e29b-41d4-a716-446655440000"

# In grep
grep "550e8400-e29b-41d4-a716-446655440000" /var/log/reims2/reims2.log
```

## Error Handling

The middleware handles errors gracefully:

- **Missing Header**: Generates new UUID
- **Invalid UUID**: Generates new UUID
- **Context Errors**: Returns None (doesn't break request)

## Performance

- **Overhead**: <1ms per request
- **Memory**: Minimal (single UUID string)
- **Thread Safety**: Uses contextvars (thread-safe)

## Testing

### Unit Tests

```python
from app.middleware.correlation_id import get_correlation_id, set_user_id

def test_correlation_id():
    # Set context
    set_user_id(123)
    
    # Get correlation ID (from middleware)
    correlation_id = get_correlation_id()
    assert correlation_id is not None
```

### Integration Tests

```python
from fastapi.testclient import TestClient

def test_correlation_id_header(client: TestClient):
    response = client.get("/api/v1/nlq/query")
    
    # Check response includes correlation ID
    assert "X-Correlation-ID" in response.headers
    correlation_id = response.headers["X-Correlation-ID"]
    assert len(correlation_id) == 36  # UUID length
```

## Troubleshooting

### Missing Correlation ID

**Issue**: Correlation ID not in logs.

**Solutions**:
- Verify middleware is added to FastAPI app
- Check middleware order (should be first)
- Verify structured logging is configured

### Correlation ID Not Propagated

**Issue**: Correlation ID not passed to other services.

**Solutions**:
- Include `X-Correlation-ID` header in external requests
- Use `get_correlation_id()` to get current ID
- Verify header name matches middleware configuration

## Examples

### Example 1: Automatic Correlation ID

```python
# Request without correlation ID
GET /api/v1/nlq/query

# Middleware generates UUID
# Response includes: X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
```

### Example 2: Client-Provided Correlation ID

```python
# Request with correlation ID
GET /api/v1/nlq/query
Headers: {X-Correlation-ID: "client-provided-id"}

# Middleware uses provided ID
# Response includes: X-Correlation-ID: client-provided-id
```

### Example 3: Context Variables

```python
from app.middleware.correlation_id import set_user_id, set_query_id

# Set context (automatically included in logs)
set_user_id(123)
set_query_id(456)

# All subsequent logs include user_id and query_id
logger.info("operation")  # Includes user_id=123, query_id=456
```

## Related Documentation

- [Structured Logging](./structured_logging_guide.md)
- [NLQ/RAG System Overview](./nlq_rag_system_overview.md)

