# Direct LLM Integration for AI Assistant

## What Changed

The AI Assistant now uses **LLM (ChatGPT/Claude) directly** to understand and answer questions, making it much more flexible and capable of handling any question variation.

## How It Works Now

### Before (Rule-Based):
1. Rule-based intent detection → Often missed variations
2. SQL query generation → Could fail for complex queries
3. Template-based answers → Limited flexibility

### After (LLM-Powered):
1. **LLM understands query** → Handles any wording, typos, variations
2. **LLM determines data needs** → Knows what to query
3. **Retrieve structured data + documents** → Gets all relevant info
4. **LLM generates answer** → Natural, comprehensive responses

## Setup Required

### Step 1: Add API Key to `.env` file

Create or edit `.env` file in project root:

```bash
# For OpenAI (ChatGPT)
OPENAI_API_KEY=your_openai_api_key_here

# OR for Anthropic (Claude)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Specify which provider to use
LLM_PROVIDER=openai  # or 'anthropic'
LLM_MODEL=gpt-4-turbo-preview  # or 'claude-3-5-sonnet-20241022'
```

### Step 2: Restart Backend

```bash
docker compose restart backend
```

### Step 3: Verify LLM is Active

The system will automatically:
- ✅ Detect API key
- ✅ Initialize LLM client
- ✅ Use LLM for all queries
- ✅ Fallback to rule-based if LLM unavailable

## Benefits

### ✅ Handles Any Question Variation
- "which property is making loses for me?" ✅
- "show me properties losing money" ✅
- "what properties have negative income?" ✅
- "which ones are unprofitable?" ✅

### ✅ Better Understanding
- Understands context and intent
- Handles typos and variations
- Knows what data to retrieve

### ✅ Comprehensive Answers
- Uses both structured data AND document content
- Provides actionable insights
- Formats answers naturally

### ✅ Fallback Support
- If LLM unavailable → Uses rule-based system
- If API key missing → Still works (limited)
- Always provides an answer

## Example Flow

**User asks:** "which property is making loses for me?"

1. **LLM Understanding:**
   ```json
   {
     "query_type": "loss_query",
     "needs_structured_data": true,
     "key_entities": {
       "filters": {"loss": true}
     }
   }
   ```

2. **Data Retrieval:**
   - Queries `financial_metrics` for properties with `net_income < 0`
   - Gets property details, NOI, revenue, period

3. **LLM Answer Generation:**
   - Uses retrieved data
   - Formats answer naturally
   - Adds recommendations

4. **Response:**
   ```
   Found 4 properties with losses:
   
   1. 🔴 Wendover Commons (WEND001)
      Net Income: -$571.9K
      NOI: $1860.0K | Revenue: $6358.9K
      Period: 2024-12
   
   💡 Total Loss: $1013.4K across 4 properties
   Recommendation: Review these properties for operational improvements...
   ```

## Testing

Test that LLM is working:

```bash
docker exec reims-backend python -c "
from app.db.database import SessionLocal
from app.services.nlq_service import NaturalLanguageQueryService

db = SessionLocal()
service = NaturalLanguageQueryService(db)

print(f'LLM Type: {service.llm_type}')
print(f'LLM Available: {service.llm_client is not None}')

result = service.query('which property is making loses for me?', 1)
print(f'Success: {result.get(\"success\")}')
print(f'Answer: {result.get(\"answer\", \"\")[:200]}')

db.close()
"
```

## Troubleshooting

### LLM Not Working?

1. **Check API Key:**
   ```bash
   # Check if .env exists
   cat .env | grep OPENAI_API_KEY
   # or
   cat .env | grep ANTHROPIC_API_KEY
   ```

2. **Check Backend Logs:**
   ```bash
   docker logs reims-backend | grep -i "llm\|openai\|anthropic"
   ```

3. **Verify Environment Variables:**
   ```bash
   docker exec reims-backend env | grep -i "openai\|anthropic\|llm"
   ```

### Still Using Rule-Based?

- Check API key is set correctly
- Restart backend after adding API key
- Check logs for initialization errors
- System will fallback gracefully if LLM unavailable

## Cost Considerations

- **OpenAI GPT-4 Turbo:** ~$0.01-0.03 per query
- **Anthropic Claude:** ~$0.015-0.03 per query
- **Caching:** Results cached for 24 hours (reduces cost)

## Next Steps

1. ✅ Add API key to `.env`
2. ✅ Restart backend
3. ✅ Test queries
4. ✅ Enjoy flexible AI answers!

The AI Assistant is now powered by real AI models and can handle any question variation! 🚀

