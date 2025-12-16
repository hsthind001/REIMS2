# Conversation Memory Guide

## Overview

Conversation memory enables natural follow-up questions by maintaining context across multiple queries. The system remembers properties, metrics, and time periods from previous questions, allowing users to ask follow-ups like "And for Q4?" or "What about that property in Q1?" without repeating context.

## Architecture

```
User Query
    ↓
[Conversation Manager]
    ├─ Get/Create Conversation ID
    ├─ Load Conversation History (last 5 turns)
    ├─ Extract Context (properties, metrics, periods)
    └─ Save Query & Answer
    ↓
[NLQ Service]
    ├─ Use Context for Query Enhancement
    └─ Extract Entities from Answer
    ↓
[Save to History]
    └─ Store with Conversation ID & Turn Number
```

## Conversation Structure

### Conversation ID

- **Format**: UUID string
- **Purpose**: Groups related queries together
- **Expiration**: 30 minutes of inactivity
- **Generation**: Auto-generated if not provided

### Turn Number

- **Format**: Integer (1-indexed)
- **Purpose**: Orders queries within a conversation
- **Increment**: Auto-increments for each query in conversation

### Context Structure

```python
{
    'conversation_id': 'uuid-string',
    'history': [
        {
            'question': 'What was NOI for Eastern Shore in Q3?',
            'answer': 'The NOI was $1.2M',
            'entities': {
                'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
                'metrics': ['noi'],
                'periods': [{'year': 2024, 'quarter': 3}]
            },
            'timestamp': '2024-11-26T10:00:00Z',
            'turn_number': 1
        }
    ],
    'context': {
        'properties': [
            {'property_id': 1, 'property_name': 'Eastern Shore Plaza', 'property_code': 'ESP001'}
        ],
        'metrics': ['noi'],
        'time_periods': [{'year': 2024, 'quarter': 3}]
    },
    'last_query_time': '2024-11-26T10:00:00Z',
    'turn_count': 1
}
```

## Usage

### Basic Conversation Flow

```python
from app.services.conversation_manager import ConversationManager
from app.db.database import SessionLocal

db = SessionLocal()
manager = ConversationManager(db, user_id=1)

# First query
conv_id = manager.get_or_create_conversation_id()
turn_number = manager.get_next_turn_number(conv_id)

manager.save_query(
    query="What was NOI for Eastern Shore in Q3?",
    answer="The NOI was $1.2M",
    conversation_id=conv_id,
    turn_number=turn_number,
    entities={
        'properties': [{'property_id': 1, 'property_name': 'Eastern Shore Plaza'}],
        'metrics': ['noi'],
        'periods': [{'year': 2024, 'quarter': 3}]
    }
)

# Follow-up query (uses same conversation_id)
history = manager.get_conversation_history(conv_id)
context = history['context']  # Contains properties, metrics, periods

# Use context for follow-up query
# "And for Q4?" can use property from context
```

### API Usage

#### Process Query with Conversation

```bash
# First query
curl -X POST "http://localhost:8000/api/v1/nlq/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What was NOI for Eastern Shore in Q3?",
    "property_id": 1
  }'

# Response includes conversation_id
# {
#   "conversation_id": "abc-123-def",
#   "turn_number": 1,
#   "context_used": {...}
# }

# Follow-up query (use conversation_id)
curl -X POST "http://localhost:8000/api/v1/nlq/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "And for Q4?",
    "conversation_id": "abc-123-def"
  }'
```

#### Get Conversation History

```bash
# Get conversation history
curl -X GET "http://localhost:8000/api/v1/nlq/conversations/abc-123-def"

# Response:
# {
#   "conversation_id": "abc-123-def",
#   "history": [
#     {
#       "question": "What was NOI for Eastern Shore in Q3?",
#       "answer": "The NOI was $1.2M",
#       "entities": {...},
#       "turn_number": 1
#     }
#   ],
#   "context": {
#     "properties": [...],
#     "metrics": ["noi"],
#     "time_periods": [...]
#   }
# }
```

#### Get User Conversations

```bash
# Get recent conversations for user
curl -X GET "http://localhost:8000/api/v1/nlq/conversations?user_id=1&limit=10"

# Response:
# {
#   "conversations": [
#     {
#       "conversation_id": "abc-123-def",
#       "last_query": "What was NOI for Eastern Shore?",
#       "last_query_time": "2024-11-26T10:00:00Z",
#       "turn_count": 3
#     }
#   ]
# }
```

## Context Extraction

### Properties

Extracted from entity mentions in queries/answers:
- Property names: "Eastern Shore", "Hammond Aire"
- Property IDs: Resolved from names
- Property codes: Retrieved from database

### Metrics

Extracted from query/answer text:
- Financial metrics: "NOI", "DSCR", "revenue", "expenses"
- Normalized to standard names

### Time Periods

Extracted from temporal references:
- Quarters: "Q3", "Q4"
- Years: "2024", "2023"
- Months: "January", "March"
- Relative: "last quarter", "this year"

## Follow-Up Query Examples

### Example 1: Period Follow-Up

**Initial Query**:
```
"What was NOI for Eastern Shore in Q3?"
```

**Context Extracted**:
- Property: Eastern Shore Plaza (ID: 1)
- Metric: NOI
- Period: Q3 2024

**Follow-Up Query**:
```
"And for Q4?"
```

**Context Used**:
- Property: Eastern Shore Plaza (from context)
- Metric: NOI (from context)
- Period: Q4 2024 (new)

### Example 2: Property Reference

**Initial Query**:
```
"What was NOI for Eastern Shore in Q3?"
```

**Follow-Up Query**:
```
"What about that property in Q1?"
```

**Context Used**:
- Property: Eastern Shore Plaza (resolved from "that property")
- Metric: NOI (from context)
- Period: Q1 2024 (new)

### Example 3: Metric Change

**Initial Query**:
```
"What was NOI for Eastern Shore in Q3?"
```

**Follow-Up Query**:
```
"What about DSCR?"
```

**Context Used**:
- Property: Eastern Shore Plaza (from context)
- Metric: DSCR (new, replaces NOI)
- Period: Q3 2024 (from context)

## Configuration

### Conversation Settings

```python
from app.services.conversation_manager import ConversationManager

manager = ConversationManager(
    db=db,
    user_id=1
)

# Settings (can be made configurable)
manager.max_history_length = 5  # Last 5 Q&A pairs
manager.context_expiry_minutes = 30  # 30 minutes of inactivity
```

### Database Schema

```sql
-- Add conversation fields to nlq_queries table
ALTER TABLE nlq_queries ADD COLUMN conversation_id VARCHAR(64);
ALTER TABLE nlq_queries ADD COLUMN turn_number INTEGER;

-- Create indexes
CREATE INDEX idx_nlq_queries_conversation_id ON nlq_queries(conversation_id);
CREATE INDEX idx_nlq_queries_conv_turn ON nlq_queries(conversation_id, turn_number);
```

## Context Expiration

### Expiration Rules

- **Time-based**: 30 minutes of inactivity
- **Check**: On each query, validates conversation is not expired
- **Action**: Creates new conversation if expired

### Expiration Check

```python
# Conversation is valid if last query was < 30 minutes ago
is_valid = manager._is_conversation_valid(conversation_id)

# If expired, create new conversation
if not is_valid:
    conversation_id = manager.get_or_create_conversation_id()  # Creates new
```

## Best Practices

1. **Always Pass Conversation ID**: Include conversation_id in follow-up queries
2. **Extract Entities**: Extract entities from both queries and answers
3. **Use Context**: Use context to resolve references like "that property"
4. **Monitor Expiration**: Track conversation expiration for user experience
5. **Limit History**: Keep only last 5 turns to avoid context bloat
6. **Clear Expired**: Run cleanup job to clear expired conversations

## Troubleshooting

### Context Not Preserved

**Possible Causes**:
- Conversation ID not passed in follow-up
- Conversation expired (>30 minutes)
- Entities not extracted correctly

**Solutions**:
- Always return conversation_id in API response
- Check conversation expiration time
- Verify entity extraction logic

### Follow-Up Queries Fail

**Possible Causes**:
- Context not used in query processing
- Entities not in expected format
- Property resolution fails

**Solutions**:
- Verify context is passed to NLQ service
- Check entity extraction format
- Ensure property lookup works

### High Memory Usage

**Possible Causes**:
- Too many conversations stored
- History not limited
- Expired conversations not cleared

**Solutions**:
- Limit history to 5 turns
- Run cleanup job for expired conversations
- Consider archiving old conversations

## Success Criteria

- ✅ Remembers last 5 Q&A pairs per user
- ✅ Context expires after 30 minutes of inactivity
- ✅ Stores conversation history in database
- ✅ Extracts accumulated context (properties, metrics, periods)
- ✅ Conversation ID for grouping related queries
- ✅ API endpoints for conversation history
- ✅ Follow-up queries work without repeating context

## Future Enhancements

- **Context Summarization**: Summarize long conversations
- **Multi-User Conversations**: Support shared conversations
- **Context Learning**: Learn from user corrections
- **Smart Expiration**: Adaptive expiration based on conversation type
- **Context Visualization**: Show conversation flow in UI

