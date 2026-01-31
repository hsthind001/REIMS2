"""
Perplexity API adapter for multi-LLM structured JSON extraction.
Uses Perplexity chat completions API (OpenAI-compatible).
"""
import json
import logging
import re
import time
from typing import Any, Dict, Optional

import httpx

from .base import BaseLLMAdapter, LLMCandidateResult

logger = logging.getLogger(__name__)


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


class PerplexityAdapter(BaseLLMAdapter):
    provider_name = "perplexity"

    async def generate_structured_json(
        self,
        prompt: str,
        system_prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        max_retries: int = 2,
    ) -> LLMCandidateResult:
        if not api_key:
            return LLMCandidateResult(provider=self.provider_name, error="PERPLEXITY_API_KEY not set")
        url = "https://api.perplexity.ai/chat/completions"
        model = "llama-3.1-sonar-small-128k-online"
        start = time.perf_counter()
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    r = await client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "max_tokens": 4000,
                            "messages": [
                                {"role": "system", "content": system_prompt + "\n\nReturn ONLY valid JSON. No markdown or explanation."},
                                {"role": "user", "content": prompt},
                            ],
                        },
                    )
                r.raise_for_status()
                data = r.json()
                raw = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
                parsed = _extract_json_from_text(raw)
                latency_ms = (time.perf_counter() - start) * 1000
                usage = data.get("usage", {})
                tokens_estimate = (usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0)
                if parsed is None:
                    last_error = "Failed to parse JSON from response"
                    continue
                return LLMCandidateResult(
                    provider=self.provider_name,
                    model=model,
                    raw_response=raw[:500],
                    parsed_json=parsed,
                    tokens_estimate=tokens_estimate or None,
                    latency_ms=latency_ms,
                )
            except Exception as e:
                last_error = str(e)
                logger.warning("Perplexity attempt %s failed: %s", attempt + 1, e)
        latency_ms = (time.perf_counter() - start) * 1000
        return LLMCandidateResult(
            provider=self.provider_name,
            model=model,
            error=last_error or "Unknown error",
            latency_ms=latency_ms,
        )
