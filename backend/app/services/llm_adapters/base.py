"""
Base types for multi-LLM adapters.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class LLMCandidateResult:
    """Result of one LLM call for candidate extraction."""
    provider: str
    model: Optional[str] = None
    raw_response: Optional[str] = None
    parsed_json: Dict[str, Any] = field(default_factory=dict)
    tokens_estimate: Optional[int] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.parsed_json)


class BaseLLMAdapter(ABC):
    """Base interface for LLM adapters (structured JSON extraction)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def generate_structured_json(
        self,
        prompt: str,
        system_prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        max_retries: int = 2,
    ) -> LLMCandidateResult:
        """
        Call the provider and return structured JSON.
        Retries on malformed JSON up to max_retries.
        """
        pass
