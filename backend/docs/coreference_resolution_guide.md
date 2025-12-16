# Coreference Resolution Guide

## Overview

Coreference resolution enables natural follow-up questions by resolving pronouns and implicit references using conversation context. Users can ask "What about that property in Q4?" without repeating "Eastern Shore Plaza" from the previous question.

## Architecture

```
User Query (with coreference)
    ↓
[Coreference Resolver]
    ├─ Detect Coreference Indicators
    ├─ Load Conversation History
    ├─ Extract Context
    └─ Resolve (LLM or Rules)
    ↓
[Resolved Query]
    └─ Standalone query ready for NLQ
```

## Coreference Types

### 1. Pronouns

**Examples**:
- "that property" → "Eastern Shore Plaza"
- "this property" → "Eastern Shore Plaza"
- "it" → Property/metric from context
- "they" → Multiple properties from context

**Detection**: Checks for pronouns in query text

### 2. Implicit References

**Examples**:
- "And for Q4?" → "What was NOI for Eastern Shore Plaza in Q4 2024?"
- "What about December?" → "What was NOI for Eastern Shore Plaza in December 2024?"
- "How about Q1?" → "What was NOI for Eastern Shore Plaza in Q1 2024?"

**Detection**: Checks for implicit phrases at query start

### 3. Temporal References

**Examples**:
- "last quarter" → "Q3 2024" (from context)
- "next month" → "December 2024" (from context)
- "previous year" → "2023" (from context)

**Detection**: Checks for temporal indicators without explicit dates

## Usage

### Basic Resolution

```python
from app.services.coreference_resolver import CoreferenceResolver
from app.services.conversation_manager import ConversationManager

# Initialize resolver
resolver = CoreferenceResolver()

# Conversation history
history = [
    {
        'question': 'What was NOI for Eastern Shore Plaza in Q3 2024?',
        'answer': 'The NOI was $1.2M'
    }
]

# Context from conversation
context = {
    'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
    'metrics': ['noi'],
    'time_periods': [{'year': 2024, 'quarter': 3}]
}

# Resolve coreference
result = resolver.resolve_coreference(
    query="What about Q4?",
    conversation_history=history,
    context=context
)

print(f"Original: {result['original_query']}")
print(f"Resolved: {result['resolved_query']}")
print(f"Confidence: {result['confidence']:.2%}")
print(f"Method: {result['method']}")
```

### Integration with Conversation Manager

```python
from app.services.conversation_manager import ConversationManager

manager = ConversationManager(db, user_id=1)

# Get conversation history
conv_id = "abc-123-def"
history = manager.get_conversation_history(conv_id)

# Resolve query with context
result = manager.resolve_query_with_context(
    query="What about that property in Q4?",
    conversation_id=conv_id
)

# Use resolved query for NLQ
resolved_query = result['resolved_query']
```

### API Integration

```python
# In NLQ API endpoint
from app.services.conversation_manager import ConversationManager

manager = ConversationManager(db, user_id=current_user.id)

# Get or create conversation
conv_id = manager.get_or_create_conversation_id(request.conversation_id)

# Resolve coreferences if needed
if manager.coreference_resolver:
    resolution = manager.resolve_query_with_context(
        query=request.question,
        conversation_id=conv_id
    )
    query_to_process = resolution['resolved_query']
else:
    query_to_process = request.question

# Process resolved query
result = nlq_service.process_query(query_to_process, ...)
```

## Resolution Methods

### LLM-Based Resolution (Primary)

**Advantages**:
- High accuracy (>90%)
- Context-aware
- Handles complex coreferences

**When Used**:
- When `USE_LLM_RESOLUTION=true`
- Falls back to rules if LLM fails

**Example**:
```python
# Query: "What about Q4?"
# LLM resolves using context:
# - Property: Eastern Shore Plaza (from history)
# - Metric: NOI (from history)
# - Period: Q4 2024 (new, year from context)
# Result: "What was NOI for Eastern Shore Plaza in Q4 2024?"
```

### Rule-Based Resolution (Fallback)

**Advantages**:
- Fast (<10ms)
- No API costs
- Works offline

**When Used**:
- When LLM unavailable
- As fallback if LLM fails
- For simple coreferences

**Example**:
```python
# Query: "What about that property in Q4?"
# Rules resolve:
# - "that property" → Property name from context
# - "Q4" → Add year from context
# Result: "What about Eastern Shore Plaza in Q4 2024?"
```

## Configuration

### Coreference Settings

```python
from app.config.coreference_config import coreference_config

# LLM Settings
coreference_config.USE_LLM_RESOLUTION = True
coreference_config.LLM_MODEL = "gpt-4o"
coreference_config.LLM_TEMPERATURE = 0.2  # Low for consistency
coreference_config.LLM_TIMEOUT = 3  # 3 seconds max

# Performance Targets
coreference_config.TARGET_RESOLUTION_TIME_MS = 500  # <500ms
coreference_config.TARGET_RESOLUTION_ACCURACY = 0.90  # >90%

# Confidence Threshold
coreference_config.MIN_CONFIDENCE_THRESHOLD = 0.7

# Caching
coreference_config.CACHE_ENABLED = True
coreference_config.CACHE_TTL_MINUTES = 30
```

### Environment Variables

```bash
# LLM Resolution
export COREFERENCE_USE_LLM="true"
export COREFERENCE_LLM_MODEL="gpt-4o"
export COREFERENCE_LLM_TEMPERATURE=0.2

# Performance
export COREFERENCE_TARGET_TIME_MS=500
export COREFERENCE_TARGET_ACCURACY=0.90

# Confidence
export COREFERENCE_MIN_CONFIDENCE=0.7

# Caching
export COREFERENCE_CACHE_ENABLED="true"
export COREFERENCE_CACHE_TTL_MINUTES=30
```

## Examples

### Example 1: Property Reference

**Initial Query**:
```
"What was NOI for Eastern Shore Plaza in Q3 2024?"
```

**Context Extracted**:
- Property: Eastern Shore Plaza
- Metric: NOI
- Period: Q3 2024

**Follow-Up Query**:
```
"What about that property in Q4?"
```

**Resolved Query**:
```
"What was NOI for Eastern Shore Plaza in Q4 2024?"
```

### Example 2: Implicit Period

**Initial Query**:
```
"What was NOI for Eastern Shore Plaza in Q3 2024?"
```

**Follow-Up Query**:
```
"And for December?"
```

**Resolved Query**:
```
"What was NOI for Eastern Shore Plaza in December 2024?"
```

### Example 3: Pronoun Resolution

**Initial Query**:
```
"What was NOI for Eastern Shore Plaza in Q3 2024?"
```

**Follow-Up Query**:
```
"What about it in Q1?"
```

**Resolved Query**:
```
"What was NOI for Eastern Shore Plaza in Q1 2024?"
```

## LLM Prompt Template

The LLM uses this prompt template for resolution:

```
Given this conversation history and current query, resolve any coreferences 
(pronouns, implicit references) to create a standalone query that doesn't 
need conversation history.

Conversation history:
Q1: What was the NOI for Eastern Shore Plaza in Q3 2024?
A1: The NOI was $1,234,567.89

Context:
Properties mentioned: Eastern Shore Plaza
Metrics mentioned: NOI
Time periods mentioned: Q3 2024

Current query: What about Q4?

Instructions:
1. Identify any pronouns (that, this, it, they, etc.) or implicit references
2. Replace them with explicit references from the conversation history
3. Generate a complete, standalone query
4. Preserve the original intent and question structure
5. If the query is already complete, return it unchanged

Return JSON:
{"resolved_query": "complete standalone query", "confidence": 0.0-1.0, "reasoning": "brief explanation"}
```

## Performance

### Resolution Time Target: <500ms

**Breakdown**:
- Rule-based: <10ms
- LLM-based: ~200-500ms
- Cached: <1ms

**Optimization**:
- Use caching for common queries
- Prefer rule-based for simple cases
- Batch LLM calls if needed

## Accuracy

### Target: >90% Accuracy

**Measurement**:
- Compare resolved queries to ground truth
- Track accuracy over time
- Monitor resolution method distribution

**Improving Accuracy**:
- Tune LLM temperature
- Add more detection patterns
- Improve context extraction
- Learn from user feedback

## Caching

### Cache Behavior

- **Cache Key**: MD5 hash of query + last question
- **TTL**: 30 minutes (configurable)
- **Purpose**: Avoid re-resolving identical queries

### Cache Management

```python
# Get cache statistics
stats = resolver.get_cache_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"Cache TTL: {stats['cache_ttl_minutes']} minutes")

# Clear cache
resolver.clear_cache()
```

## Best Practices

1. **Always Check for Coreferences**: Use `has_coreference()` before processing
2. **Use Conversation Context**: Pass full conversation history for best results
3. **Monitor Accuracy**: Track resolution accuracy over time
4. **Fallback Strategy**: Always have rule-based fallback
5. **Cache Resolutions**: Enable caching for common queries
6. **Log Resolutions**: Enable logging for debugging

## Troubleshooting

### Low Accuracy (<90%)

**Possible Causes**:
- Insufficient conversation history
- Context not extracted correctly
- LLM misresolution

**Solutions**:
- Ensure conversation history is passed
- Verify context extraction
- Adjust LLM temperature
- Review misresolved queries

### High Resolution Time (>500ms)

**Possible Causes**:
- LLM calls too slow
- Cache not working
- Too many pattern checks

**Solutions**:
- Enable caching
- Use rule-based for simple cases
- Optimize LLM timeout
- Reduce pattern complexity

### Incorrect Resolution

**Possible Causes**:
- Ambiguous context
- Multiple possible resolutions
- LLM misclassification

**Solutions**:
- Provide more context
- Use explicit references when possible
- Review resolution examples
- Adjust confidence threshold

## Success Criteria

- ✅ Resolves pronouns: "that", "this", "it", "they"
- ✅ Resolves implicit references: "And for Q4?", "What about December?"
- ✅ Generates standalone query that doesn't need conversation history
- ✅ Resolution accuracy >90%
- ✅ Resolution time <500ms (LLM call)
- ✅ Caching for common queries
- ✅ Fallback to rules if LLM fails

## Future Enhancements

- **Multi-Entity Resolution**: Handle multiple properties/metrics
- **Temporal Reasoning**: Better handling of relative dates
- **Context Learning**: Learn from user corrections
- **Confidence Calibration**: Improve confidence scoring
- **Batch Resolution**: Resolve multiple queries at once

