"""
Anthropic (Claude) adapter for multi-LLM structured JSON extraction.
"""
import json
import logging
import re
import time
from typing import Any, Dict, Optional

from .base import BaseLLMAdapter, LLMCandidateResult

logger = logging.getLogger(__name__)


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Try to parse JSON from response (handle markdown code blocks)."""
    text = text.strip()
    # Try raw parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try first { ... }
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


class AnthropicAdapter(BaseLLMAdapter):
    provider_name = "anthropic"

    async def generate_structured_json(
        self,
        prompt: str,
        system_prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        max_retries: int = 2,
    ) -> LLMCandidateResult:
        if not api_key:
            return LLMCandidateResult(provider=self.provider_name, error="ANTHROPIC_API_KEY not set")
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            return LLMCandidateResult(provider=self.provider_name, error="anthropic package not installed")
        client = AsyncAnthropic(api_key=api_key)
        model = "claude-3-5-sonnet-20241022"
        start = time.perf_counter()
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                msg = await client.messages.create(
                    model=model,
                    max_tokens=4000,
                    system=system_prompt + "\n\nReturn ONLY valid JSON. No markdown or explanation.",
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = msg.content[0].text if msg.content else ""
                parsed = _extract_json_from_text(raw)
                latency_ms = (time.perf_counter() - start) * 1000
                tokens_estimate = getattr(msg, "usage", None)
                if tokens_estimate:
                    tokens_estimate = getattr(tokens_estimate, "input_tokens", 0) + getattr(tokens_estimate, "output_tokens", 0)
                if parsed is None:
                    last_error = "Failed to parse JSON from response"
                    continue
                return LLMCandidateResult(
                    provider=self.provider_name,
                    model=model,
                    raw_response=raw[:500] if raw else None,
                    parsed_json=parsed,
                    tokens_estimate=tokens_estimate,
                    latency_ms=latency_ms,
                )
            except Exception as e:
                last_error = str(e)
                logger.warning("Anthropic attempt %s failed: %s", attempt + 1, e)
        latency_ms = (time.perf_counter() - start) * 1000
        return LLMCandidateResult(
            provider=self.provider_name,
            model=model,
            error=last_error or "Unknown error",
            latency_ms=latency_ms,
        )
