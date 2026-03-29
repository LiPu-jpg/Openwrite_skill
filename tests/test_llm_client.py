import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import openai

from tools.llm.client import LLMClient, LLMConfig


def test_llm_config_normalizes_full_chat_completions_endpoint():
    config = LLMConfig(
        provider="openai",
        api_key="test-key",
        base_url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
        model="glm-5",
    )

    assert config.base_url == "https://open.bigmodel.cn/api/paas/v4"


def test_llm_client_uses_normalized_base_url_for_openai_sdk(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)

    LLMClient(
        LLMConfig(
            provider="openai",
            api_key="test-key",
            base_url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
            model="glm-5",
        )
    )

    assert captured["base_url"] == "https://open.bigmodel.cn/api/paas/v4"


def test_llm_config_reads_timeout_and_retry_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_API_KEY", "env-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "glm-5")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "600")
    monkeypatch.setenv("LLM_MAX_RETRIES", "0")

    config = LLMConfig.from_env()

    assert config.base_url == "https://open.bigmodel.cn/api/paas/v4"
    assert config.timeout_seconds == 600.0
    assert config.max_retries == 0


def test_llm_client_passes_timeout_and_retry_to_openai_sdk(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)

    LLMClient(
        LLMConfig(
            provider="openai",
            api_key="test-key",
            base_url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
            model="glm-5",
            timeout_seconds=600.0,
            max_retries=0,
        )
    )

    assert captured["timeout"] == 600.0
    assert captured["max_retries"] == 0
