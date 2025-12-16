# Entity Resolver Guide

## Overview

Entity resolver provides fuzzy matching for property names and codes to handle typos and variations in user input. It uses the `fuzzywuzzy` library to match user queries against the property database with confidence scores.

## Architecture

```
User Input (with typos)
    ↓
[Entity Resolver Service]
    ├─ Load Properties (from DB)
    ├─ Fuzzy Match (fuzzywuzzy)
    └─ Cache Results
    ↓
[Return Top Matches with Confidence]
```

## When to Use Entity Resolution

### Use Entity Resolution When:
- **User input has typos** (e.g., "Easten" vs "Eastern")
- **Property names are long** (e.g., "Hammond Aire Shopping Center")
- **Users type partial names** (e.g., "Hammond" instead of full name)
- **Property codes are used** (e.g., "ESP01" vs "ESP001")
- **Need confidence scores** for match quality

### Example Use Cases:
- **NLQ Queries**: "Show me revenue for Easten Shore" → matches "Eastern Shore Plaza"
- **Property Search**: "Hamond Air" → matches "Hammond Aire Shopping Center"
- **Code Lookup**: "ESP01" → matches "ESP001"

## Configuration

Configuration is managed in `app/config/entity_resolver_config.py`:

```python
from app.config.entity_resolver_config import entity_resolver_config

# Fuzzy Matching Settings
entity_resolver_config.SIMILARITY_THRESHOLD = 0.75  # 75% similarity
entity_resolver_config.MIN_CONFIDENCE = 0.75  # Minimum confidence
entity_resolver_config.MAX_MATCHES = 3  # Top 3 matches

# Performance
entity_resolver_config.TARGET_MATCHING_TIME_MS = 50  # <50ms target

# Property List Refresh
entity_resolver_config.REFRESH_INTERVAL_MINUTES = 5  # Refresh every 5 minutes
entity_resolver_config.AUTO_REFRESH_ENABLED = True

# Caching
entity_resolver_config.CACHE_ENABLED = True
entity_resolver_config.CACHE_TTL_MINUTES = 30
entity_resolver_config.CACHE_MAX_SIZE = 1000
```

### Environment Variables

```bash
# Fuzzy Matching
export ENTITY_RESOLVER_THRESHOLD=0.75
export ENTITY_RESOLVER_MIN_CONFIDENCE=0.75
export ENTITY_RESOLVER_MAX_MATCHES=3

# Performance
export ENTITY_RESOLVER_TARGET_TIME_MS=50

# Refresh
export ENTITY_RESOLVER_REFRESH_INTERVAL=5
export ENTITY_RESOLVER_AUTO_REFRESH="true"

# Caching
export ENTITY_RESOLVER_CACHE_ENABLED="true"
export ENTITY_RESOLVER_CACHE_TTL_MINUTES=30
export ENTITY_RESOLVER_CACHE_MAX_SIZE=1000
```

## Usage

### Basic Property Resolution

```python
from app.services.entity_resolver_service import EntityResolverService
from app.db.database import SessionLocal

db = SessionLocal()
resolver = EntityResolverService(db)

# Resolve property with typo
result = resolver.resolve_property("Easten Shore")

print(f"Query: {result['query']}")
print(f"Matches: {result['num_matches']}")
for match in result['matches']:
    print(f"  - {match['property_name']} (Code: {match['property_code']})")
    print(f"    Confidence: {match['confidence']:.2%}")
    print(f"    Matched Field: {match['matched_field']}")
```

### Example Output

```python
{
    'query': 'Easten Shore',
    'matches': [
        {
            'property_id': 1,
            'property_name': 'Eastern Shore Plaza',
            'property_code': 'ESP001',
            'confidence': 0.92,
            'similarity_score': 92,
            'match_type': 'name_partial',
            'matched_field': 'name'
        }
    ],
    'num_matches': 1,
    'matching_time_ms': 12.5,
    'cached': False
}
```

### Multiple Matches

```python
# Query that matches multiple properties
result = resolver.resolve_property("mall")

# Returns top 3 matches (if above threshold)
for match in result['matches']:
    print(f"{match['property_name']}: {match['confidence']:.2%}")
```

## Fuzzy Matching Strategies

### Partial Ratio (Default)

**Best for**: Partial matches, typos, missing words

```python
# "Easten Shore" matches "Eastern Shore Plaza"
fuzz.partial_ratio("easten shore", "eastern shore plaza")  # High score
```

### Ratio

**Best for**: Exact or near-exact matches

```python
# "ESP001" matches "ESP001"
fuzz.ratio("esp001", "ESP001")  # High score
```

### Token Sort Ratio

**Best for**: Word order variations

```python
# "Shore Eastern" matches "Eastern Shore"
fuzz.token_sort_ratio("shore eastern", "eastern shore")  # High score
```

## Common Typo Scenarios

### Missing Letter

```python
# "Easten" → "Eastern"
result = resolver.resolve_property("Easten Shore")
# Matches: "Eastern Shore Plaza" (confidence: 0.92)
```

### Extra Letter

```python
# "Hammondd" → "Hammond"
result = resolver.resolve_property("Hammondd Aire")
# Matches: "Hammond Aire Shopping Center" (confidence: 0.93)
```

### Wrong Letter

```python
# "Hamond" → "Hammond"
result = resolver.resolve_property("Hamond Air")
# Matches: "Hammond Aire Shopping Center" (confidence: 0.91)
```

### Transposed Letters

```python
# "Wetsfield" → "Westfield"
result = resolver.resolve_property("Wetsfield")
# Matches: "Westfield Mall" (confidence: 0.90)
```

### Partial Match

```python
# "Hammond" → "Hammond Aire Shopping Center"
result = resolver.resolve_property("Hammond")
# Matches: "Hammond Aire Shopping Center" (confidence: 0.88)
```

## Property List Management

### Automatic Refresh

Properties are automatically refreshed every 5 minutes (configurable):

```python
# Properties are refreshed automatically
# No manual action needed
```

### Manual Refresh

```python
# Manually refresh property list
resolver.refresh_properties()
```

### Property Statistics

```python
stats = resolver.get_property_stats()
print(f"Properties loaded: {stats['num_properties']}")
print(f"Last refresh: {stats['last_refresh']}")
print(f"Refresh interval: {stats['refresh_interval_minutes']} minutes")
```

## Caching

### Cache Behavior

- **Cache Key**: MD5 hash of normalized query
- **TTL**: 30 minutes (configurable)
- **Max Size**: 1000 queries (configurable)
- **Eviction**: FIFO when max size reached

### Cache Management

```python
# Get cache statistics
stats = resolver.get_cache_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"Max size: {stats['cache_max_size']}")

# Clear cache
resolver.clear_cache()
```

## Performance

### Latency Targets

- **Fuzzy Matching**: <50ms for single query
- **Cached Lookup**: <1ms
- **Property Refresh**: <1s for typical property lists

### Accuracy Targets

- **Target Accuracy**: >85% correct matches
- **Confidence Threshold**: 75% minimum
- **False Positive Rate**: <5%

## Integration Examples

### With NLQ Service

```python
from app.services.entity_resolver_service import EntityResolverService
from app.services.nlq_service import NLQService

db = SessionLocal()
resolver = EntityResolverService(db)
nlq_service = NLQService(db)

# User query with typo
user_query = "Show me revenue for Easten Shore"

# Resolve property first
property_result = resolver.resolve_property("Easten Shore")
if property_result['matches']:
    property_id = property_result['matches'][0]['property_id']
    
    # Use resolved property in NLQ
    nlq_result = nlq_service.process_query(
        query=user_query,
        property_id=property_id
    )
```

### With Property Search API

```python
from app.services.entity_resolver_service import EntityResolverService

@app.get("/api/properties/search")
def search_properties(query: str, db: Session = Depends(get_db)):
    resolver = EntityResolverService(db)
    result = resolver.resolve_property(query)
    
    return {
        'query': query,
        'matches': result['matches'],
        'num_matches': result['num_matches']
    }
```

## Best Practices

1. **Use for User Input**: Always use entity resolution for user-entered property names
2. **Check Confidence**: Only use matches with confidence >= threshold
3. **Show Multiple Matches**: Display top 3 matches when confidence is close
4. **Cache Aggressively**: Enable caching for common queries
5. **Monitor Accuracy**: Track resolution accuracy over time
6. **Refresh Regularly**: Ensure property list is up-to-date

## Troubleshooting

### Low Accuracy (<85%)

**Possible Causes**:
- Threshold too low
- Property names too similar
- Typos too severe

**Solutions**:
- Increase `SIMILARITY_THRESHOLD` (e.g., 0.80)
- Increase `MIN_CONFIDENCE` (e.g., 0.80)
- Review property naming conventions
- Consider using token_sort_ratio for word order variations

### High Latency (>50ms)

**Possible Causes**:
- Too many properties
- Cache not working
- Fuzzy matching too slow

**Solutions**:
- Enable caching
- Reduce property list size (filter inactive)
- Use only partial_ratio (disable other ratios)
- Consider indexing property names

### No Matches Found

**Possible Causes**:
- Query too different from property names
- Threshold too high
- Properties not loaded

**Solutions**:
- Check property list is loaded: `resolver.get_property_stats()`
- Lower threshold temporarily for debugging
- Check query normalization (case sensitivity)
- Verify properties exist in database

## Success Criteria

- ✅ Fuzzy matches property names and codes with >85% accuracy
- ✅ Returns confidence scores (0-1)
- ✅ Threshold: 75+ similarity score for matches
- ✅ Handles multiple matches (shows top 3 with confidence)
- ✅ Works for both property names and property codes
- ✅ Matching time <50ms
- ✅ Auto-refreshes property list every 5 minutes
- ✅ Caches match results

## Future Enhancements

- **Machine Learning**: Train custom model on user corrections
- **Context-Aware**: Use query context to improve matching
- **Multi-Language**: Support property names in multiple languages
- **Phonetic Matching**: Use Soundex/Metaphone for phonetic typos
- **Learning from Corrections**: Improve matching based on user feedback

