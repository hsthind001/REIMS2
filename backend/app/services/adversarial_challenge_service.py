"""
Adversarial challenge: for low-confidence fields (ESCALATE_LLM), call a challenger LLM to suggest corrections and evidence.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.schemas.master_json import ChallengeSuggestion

logger = logging.getLogger(__name__)


def _extract_json_list(text: str) -> List[Dict[str, Any]]:
    """Try to parse a list of objects from challenger response."""
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "suggestions" in data:
            return data["suggestions"]
        return [data] if isinstance(data, dict) else []
    except json.JSONDecodeError:
        pass
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return []


async def run_challenge_async(
    low_confidence_fields: List[Dict[str, Any]],
    candidates_summary: str,
    evidence_summary: str,
    api_key: Optional[str] = None,
) -> List[ChallengeSuggestion]:
    """
    Call challenger LLM (Claude) with low-confidence fields, candidates, and evidence.
    Returns list of ChallengeSuggestion (suspected error type, correction, evidence pointer).
    """
    api_key = api_key or getattr(settings, "ANTHROPIC_API_KEY", None)
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set; skipping adversarial challenge")
        return []
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.warning("anthropic package not installed; skipping adversarial challenge")
        return []
    client = AsyncAnthropic(api_key=api_key)
    prompt = f"""You are an adversarial reviewer for financial document extraction.
Given the following low-confidence fields and the candidate extractions and evidence, suggest potential errors and corrections.

Low-confidence fields:
{json.dumps(low_confidence_fields, indent=2)}

Candidate extractions summary:
{candidates_summary[:2000]}

Evidence summary:
{evidence_summary[:1500]}

For each field that may have an error (e.g. sign swap, wrong total, misread number), return a JSON array of objects with:
- "field_name": string
- "suspected_error_type": string (e.g. "sign_swap", "wrong_total", "misread_digit")
- "suggested_correction": number or string
- "evidence_pointer": string (e.g. "page 2, snippet ...")

Return ONLY a JSON array. No markdown or explanation."""

    try:
        msg = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text if msg.content else ""
        items = _extract_json_list(raw)
        out: List[ChallengeSuggestion] = []
        for it in items:
            if isinstance(it, dict) and it.get("field_name"):
                out.append(
                    ChallengeSuggestion(
                        field_name=it["field_name"],
                        suspected_error_type=it.get("suspected_error_type"),
                        suggested_correction=it.get("suggested_correction"),
                        evidence_pointer=it.get("evidence_pointer"),
                    )
                )
        return out
    except Exception as e:
        logger.warning("Adversarial challenge LLM call failed: %s", e)
        return []


def run_challenge(
    low_confidence_fields: List[Dict[str, Any]],
    candidates_summary: str,
    evidence_summary: str,
    api_key: Optional[str] = None,
) -> List[ChallengeSuggestion]:
    """Synchronous wrapper for run_challenge_async."""
    import asyncio
    return asyncio.run(run_challenge_async(low_confidence_fields, candidates_summary, evidence_summary, api_key))
