"""LLM wrapper with a zero-dependency mock fallback.

`AnthropicLLM` calls Claude (lazy import of the `anthropic` SDK) when an API key is set.
`MockLLM` returns short deterministic rationale so the full pipeline runs offline (dry runs
and CI). The trading *decision* is grounded in deterministic signals (see firm.py); the LLM
supplies reasoning/narrative and risk commentary, not raw alpha.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLM(ABC):
    @abstractmethod
    def complete(self, system: str, prompt: str, model: str | None = None) -> str:
        ...


class MockLLM(LLM):
    name = "mock"

    def complete(self, system: str, prompt: str, model: str | None = None) -> str:
        # Deterministic, content-aware stub: echo the key context so traces are useful.
        head = prompt.strip().splitlines()[0] if prompt.strip() else ""
        return f"[mock-llm] {head[:160]}"


class AnthropicLLM(LLM):  # pragma: no cover - requires network + key
    name = "anthropic"

    def __init__(self, config):
        from anthropic import Anthropic

        self.client = Anthropic(api_key=config.anthropic_api_key)
        self.default_model = config.model_smart

    def complete(self, system: str, prompt: str, model: str | None = None) -> str:
        msg = self.client.messages.create(
            model=model or self.default_model,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")


def get_llm(config=None) -> LLM:
    if config is not None and config.anthropic_api_key:
        try:  # pragma: no cover
            return AnthropicLLM(config)
        except Exception:
            pass
    return MockLLM()
