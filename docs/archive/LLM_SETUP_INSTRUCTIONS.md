# LLM Integration Setup Instructions

The AI Assistant now supports integration with ChatGPT (OpenAI) and Claude (Anthropic) for enhanced natural language responses.

## Quick Setup

### Step 1: Get API Keys

**For OpenAI (ChatGPT):**
1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

**For Anthropic (Claude):**
1. Go to https://console.anthropic.com/settings/keys
2. Sign in or create an account
3. Click "Create Key"
4. Copy the key (starts with `sk-ant-`)

### Step 2: Create `.env` File

Create a `.env` file in the project root (`/home/singh/REIMS2/.env`) with your API keys:

```bash
# Choose one or both LLM providers
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Optional: Configure which LLM to use (default: openai)
LLM_PROVIDER=openai  # or "anthropic"
LLM_MODEL=gpt-4-turbo-preview  # or "claude-3-5-sonnet-20241022"
```

### Step 3: Restart Backend

```bash
docker compose restart backend
```

### Step 4: Verify Setup

The AI Assistant will automatically use the LLM if API keys are configured. Without API keys, it will use template-based answers (which still work but are less flexible).

## How It Works

1. **With LLM (ChatGPT/Claude):**
   - Queries are processed with AI for natural, contextual answers
   - Better handling of complex questions
   - More conversational responses

2. **Without LLM (Template-based):**
   - Uses predefined templates for common queries
   - Works for DSCR queries, trend queries, etc.
   - Still provides accurate data but less flexible

## Current Features

✅ **DSCR Queries**: "Which properties have DSCR below 1.25?"
   - Uses specialized DSCR answer generator (works with or without LLM)

✅ **NOI Trend Queries**: "Show me NOI trends for last 12 months"
   - Queries actual NOI data from `financial_metrics` table
   - Shows trend analysis with percentage changes

✅ **General Queries**: Other financial questions
   - Uses LLM if available, otherwise template-based

## Troubleshooting

**LLM not working?**
- Check that `.env` file exists in project root
- Verify API keys are correct (no extra spaces)
- Check backend logs: `docker logs reims-backend`
- Verify environment variables: `docker exec reims-backend env | grep OPENAI`

**Getting errors?**
- Make sure you have credits/quota in your OpenAI/Anthropic account
- Check API key permissions
- Verify network connectivity from Docker container

## Cost Considerations

- **OpenAI GPT-4**: ~$0.01-0.03 per query (varies by model)
- **Anthropic Claude**: ~$0.003-0.015 per query (varies by model)
- Template-based answers are free (no API calls)

The system will automatically fall back to template-based answers if:
- API keys are not set
- API calls fail
- Rate limits are exceeded

