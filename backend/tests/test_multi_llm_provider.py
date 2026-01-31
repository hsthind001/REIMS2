"""Unit tests for multi-LLM provider (candidate extraction)."""
import pytest
from unittest.mock import patch
from app.services.multi_llm_provider import (
    generate_candidates,
    get_available_providers,
    _get_api_keys,
    default_system_prompt_for_document_type,
    _default_schema_for_document_type,
)


class TestMultiLLMProvider:
    def test_get_available_providers_empty_when_no_keys(self):
        api_keys = {"ANTHROPIC_API_KEY": None, "OPENAI_API_KEY": None, "PERPLEXITY_API_KEY": None}
        available = get_available_providers(api_keys)
        assert available == []

    def test_get_available_providers_returns_providers_with_keys(self):
        api_keys = {"ANTHROPIC_API_KEY": "sk-x", "OPENAI_API_KEY": None, "PERPLEXITY_API_KEY": "pplx-y"}
        available = get_available_providers(api_keys)
        assert "anthropic" in available
        assert "perplexity" in available
        assert "openai" not in available

    def test_default_system_prompt_balance_sheet(self):
        prompt = default_system_prompt_for_document_type("balance_sheet")
        assert "financial" in prompt.lower()
        assert "JSON" in prompt

    def test_default_schema_balance_sheet_has_line_items(self):
        schema = _default_schema_for_document_type("balance_sheet")
        assert "line_items" in schema.get("required", [])
        assert "properties" in schema

    def test_generate_candidates_returns_empty_when_no_api_keys(self):
        with patch("app.services.multi_llm_provider._get_api_keys", return_value={k: None for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "PERPLEXITY_API_KEY", "MISTRAL_API_KEY", "GOOGLE_API_KEY")}):
            results = generate_candidates(
                prompt="test",
                system_prompt="test",
                document_type="balance_sheet",
                max_providers=3,
            )
        assert results == []
