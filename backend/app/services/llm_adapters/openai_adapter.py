"""
OpenAI (GPT) adapter for multi-LLM structured JSON extraction.
"""
import json
import logging
import re
import time
from typing import Any, Dict, Optional

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


class OpenAIAdapter(BaseLLMAdapter):
    provider_name = "openai"

    async def generate_structured_json(
        self,
        prompt: str,
        system_prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        max_retries: int = 2,
    ) -> LLMCandidateResult:
        if not api_key:
            return LLMCandidateResult(provider=self.provider_name, error="OPENAI_API_KEY not set")
        try:
            from openai import AsyncOpenAI
        except ImportError:
            return LLMCandidateResult(provider=self.provider_name, error="openai package not installed")
        client = AsyncOpenAI(api_key=api_key)
        model = "gpt-4o-mini"
        start = time.perf_counter()
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                resp = await client.chat.completions.create(
                    model=model,
                    max_tokens=4000,
                    messages=[
                        {"role": "system", "content": system_prompt + "\n\nReturn ONLY valid JSON. No markdown or explanation."},
                        {"role": "user", "content": prompt},
                    ],
                )
                raw = resp.choices[0].message.content if resp.choices else ""
                parsed = _extract_json_from_text(raw or "")
                latency_ms = (time.perf_counter() - start) * 1000
                tokens_estimate = None
                if resp.usage:
                    tokens_estimate = (resp.usage.prompt_tokens or 0) + (resp.usage.completion_tokens or 0)
                if parsed is None:
                    last_error = "Failed to parse JSON from response"
                    continue
                return LLMCandidateResult(
                    provider=self.provider_name,
                    model=model,
                    raw_response=(raw or "")[:500],
                    parsed_json=parsed,
                    tokens_estimate=tokens_estimate,
                    latency_ms=latency_ms,
                )
            except Exception as e:
                last_error = str(e)
                logger.warning("OpenAI attempt %s failed: %s", attempt + 1, e)
        latency_ms = (time.perf_counter() - start) * 1000
        return LLMCandidateResult(
            provider=self.provider_name,
            model=model,
            error=last_error or "Unknown error",
            latency_ms=latency_ms,
        )
