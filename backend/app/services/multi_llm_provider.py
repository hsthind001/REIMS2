"""
Multi-LLM provider: call 2–3 LLM providers in parallel for candidate extraction (AbeAI-style).
Returns list of LLMCandidateResult for storage in Master JSON candidates section.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.llm_adapters import get_adapter, get_available_providers
from app.services.llm_adapters.base import LLMCandidateResult

logger = logging.getLogger(__name__)

# Default providers to use for candidate extraction (first 2–3 that have keys)
DEFAULT_PROVIDER_ORDER = ["anthropic", "openai", "perplexity", "mistral", "gemini"]


def _get_api_keys() -> Dict[str, Optional[str]]:
    return {
        "ANTHROPIC_API_KEY": getattr(settings, "ANTHROPIC_API_KEY", None),
        "OPENAI_API_KEY": getattr(settings, "OPENAI_API_KEY", None),
        "PERPLEXITY_API_KEY": getattr(settings, "PERPLEXITY_API_KEY", None),
        "MISTRAL_API_KEY": getattr(settings, "MISTRAL_API_KEY", None),
        "GOOGLE_API_KEY": getattr(settings, "GOOGLE_API_KEY", None),
    }


def _provider_to_key(provider: str) -> Optional[str]:
    key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "perplexity": "PERPLEXITY_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }
    return key_map.get(provider)


async def _call_one(
    provider: str,
    prompt: str,
    system_prompt: str,
    schema: Optional[Dict[str, Any]],
    api_keys: Dict[str, Optional[str]],
    max_retries: int = 2,
) -> LLMCandidateResult:
    adapter = get_adapter(provider)
    if not adapter:
        return LLMCandidateResult(provider=provider, error=f"Unknown provider: {provider}")
    key_name = _provider_to_key(provider)
    api_key = api_keys.get(key_name) if key_name else None
    return await adapter.generate_structured_json(
        prompt=prompt,
        system_prompt=system_prompt,
        schema=schema,
        api_key=api_key,
        max_retries=max_retries,
    )


async def generate_candidates_async(
    prompt: str,
    system_prompt: str,
    document_type: str,
    schema: Optional[Dict[str, Any]] = None,
    providers: Optional[List[str]] = None,
    max_providers: int = 3,
) -> List[LLMCandidateResult]:
    """
    Call up to max_providers LLMs in parallel for candidate extraction.
    If providers is None, use first max_providers from available (with API keys).
    """
    api_keys = _get_api_keys()
    available = get_available_providers(api_keys)
    if not available:
        logger.warning("No LLM API keys set; skipping multi-LLM candidate extraction")
        return []
    to_use = providers if providers else [p for p in DEFAULT_PROVIDER_ORDER if p in available][:max_providers]
    if not to_use:
        return []
    schema = schema or _default_schema_for_document_type(document_type)
    tasks = [
        _call_one(provider, prompt, system_prompt, schema, api_keys)
        for provider in to_use
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out: List[LLMCandidateResult] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            out.append(LLMCandidateResult(provider=to_use[i], error=str(r)))
        else:
            out.append(r)
    return out


def generate_candidates(
    prompt: str,
    system_prompt: str,
    document_type: str,
    schema: Optional[Dict[str, Any]] = None,
    providers: Optional[List[str]] = None,
    max_providers: int = 3,
) -> List[LLMCandidateResult]:
    """Synchronous wrapper for generate_candidates_async."""
    return asyncio.run(
        generate_candidates_async(
            prompt=prompt,
            system_prompt=system_prompt,
            document_type=document_type,
            schema=schema,
            providers=providers,
            max_providers=max_providers,
        )
    )


def _default_schema_for_document_type(document_type: str) -> Dict[str, Any]:
    """Default JSON schema for statement type (strict line_items)."""
    if document_type == "balance_sheet":
        return {
            "type": "object",
            "properties": {
                "statement_date": {"type": "string"},
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "account_name": {"type": "string"},
                            "amount": {"type": "number"},
                            "category": {"type": "string"},
                        },
                        "required": ["account_name", "amount"],
                    },
                },
                "total_assets": {"type": "number"},
                "total_liabilities": {"type": "number"},
                "total_equity": {"type": "number"},
            },
            "required": ["line_items"],
        }
    if document_type in ("income_statement", "profit_loss"):
        return {
            "type": "object",
            "properties": {
                "period_start": {"type": "string"},
                "period_end": {"type": "string"},
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "account_name": {"type": "string"},
                            "amount": {"type": "number"},
                            "section": {"type": "string"},
                        },
                        "required": ["account_name", "amount"],
                    },
                },
                "total_revenue": {"type": "number"},
                "total_expenses": {"type": "number"},
                "net_operating_income": {"type": "number"},
            },
            "required": ["line_items"],
        }
    if document_type == "rent_roll":
        return {
            "type": "object",
            "properties": {
                "units": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "unit_id": {"type": "string"},
                            "tenant_name": {"type": "string"},
                            "monthly_rent": {"type": "number"},
                        },
                        "required": ["unit_id", "monthly_rent"],
                    },
                },
            },
            "required": ["units"],
        }
    if document_type == "cash_flow":
        return {
            "type": "object",
            "properties": {
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "account_name": {"type": "string"},
                            "amount": {"type": "number"},
                        },
                        "required": ["account_name", "amount"],
                    },
                },
            },
            "required": ["line_items"],
        }
    return {"type": "object", "properties": {"line_items": {"type": "array"}}, "required": ["line_items"]}


def default_system_prompt_for_document_type(document_type: str) -> str:
    """Default system prompt for extraction (strict JSON)."""
    return (
        "You are an expert financial analyst. Extract structured data from the provided document text. "
        "Return ONLY a valid JSON object with the required fields. No markdown, no explanation. "
        "Normalize amounts to numbers (remove currency symbols; use negative for parentheses)."
    )
