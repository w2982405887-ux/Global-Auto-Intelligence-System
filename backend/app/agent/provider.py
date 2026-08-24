"""LLM Provider — unified interface for OpenAI / Claude / custom models.

Configure via environment variables:
  AUTOPOLICY_LLM_PROVIDER=openai     # openai | claude | custom
  AUTOPOLICY_LLM_MODEL=gpt-4o
  AUTOPOLICY_LLM_API_KEY=sk-...
  AUTOPOLICY_LLM_BASE_URL=           # optional, for proxies/custom endpoints
"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI


class LLMProvider:
    """Factory for LLM instances. Supports OpenAI, Anthropic, and custom endpoints."""

    @staticmethod
    def create_model() -> BaseChatModel:
        provider_name = os.getenv("AUTOPOLICY_LLM_PROVIDER", "openai")
        model_name = os.getenv("AUTOPOLICY_LLM_MODEL", "gpt-4o")
        api_key = os.getenv("AUTOPOLICY_LLM_API_KEY", "")
        base_url = os.getenv("AUTOPOLICY_LLM_BASE_URL", None)

        if provider_name == "openai":
            kwargs: dict[str, Any] = {
                "model": model_name,
                "temperature": 0,
            }
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["base_url"] = base_url
            return ChatOpenAI(**kwargs)

        if provider_name == "claude":
            # Falls back to ChatOpenAI with Anthropic-compatible endpoint,
            # or we could use ChatAnthropic. For MVP, treat as openai-compatible.
            kwargs = {
                "model": model_name,
                "temperature": 0,
            }
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["base_url"] = base_url
            return ChatOpenAI(**kwargs)

        # Default: OpenAI-compatible
        kwargs = {
            "model": model_name,
            "temperature": 0,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)
