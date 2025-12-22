# Quick Setup: Enable Direct LLM Integration

## The Problem
The AI Assistant wasn't handling wording variations well because it relied on rule-based pattern matching.

## The Solution
Now the AI uses **LLM (ChatGPT/Claude) directly** to understand ANY question variation!

## Setup (2 Steps)

### Step 1: Add API Key to `.env`

Edit `/home/singh/REIMS2/.env` and add:

```bash
# For OpenAI (ChatGPT) - Recommended
OPENAI_API_KEY=sk-your-key-here

# OR for Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: Specify provider
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
```

### Step 2: Restart Backend

```bash
docker compose restart backend
```

## That's It! 🎉

The AI will now:
- ✅ Understand ANY question wording
- ✅ Handle typos and variations
- ✅ Use real AI models (ChatGPT/Claude)
- ✅ Fallback to rule-based if API key missing

## Test It

Try these queries - they'll all work now:
- "which property is making loses for me?"
- "show me properties losing money"
- "what properties have negative income?"
- "which ones are unprofitable?"

## Get API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys

## Cost

- ~$0.01-0.03 per query
- Results cached for 24 hours (reduces cost)
- Very affordable for typical usage

The AI is now powered by real AI models! 🚀

