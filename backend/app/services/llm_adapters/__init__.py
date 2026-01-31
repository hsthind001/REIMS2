"""
LLM adapters for multi-provider structured JSON extraction (AbeAI-style).
Each adapter returns: provider, model, raw_response, parsed_json, tokens_estimate, latency_ms, error.
"""
from typing import Any, Dict, List, Optional
import logging

from .base import LLMCandidateResult, BaseLLMAdapter
from .anthropic_adapter import AnthropicAdapter
from .openai_adapter import OpenAIAdapter
from .perplexity_adapter import PerplexityAdapter
from .mistral_adapter import MistralAdapter
from .gemini_adapter import GeminiAdapter

logger = logging.getLogger(__name__)

REGISTRY: Dict[str, BaseLLMAdapter] = {
    "anthropic": AnthropicAdapter(),
    "openai": OpenAIAdapter(),
    "perplexity": PerplexityAdapter(),
    "mistral": MistralAdapter(),
    "gemini": GeminiAdapter(),
}


def get_adapter(provider: str) -> Optional[BaseLLMAdapter]:
    return REGISTRY.get(provider)


def get_available_providers(api_keys: Dict[str, Optional[str]]) -> List[str]:
    """Return list of provider names that have API keys set."""
    key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "perplexity": "PERPLEXITY_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }
    return [p for p, key in key_map.items() if api_keys.get(key)]


__all__ = [
    "LLMCandidateResult",
    "BaseLLMAdapter",
    "AnthropicAdapter",
    "OpenAIAdapter",
    "PerplexityAdapter",
    "MistralAdapter",
    "GeminiAdapter",
    "REGISTRY",
    "get_adapter",
    "get_available_providers",
]
