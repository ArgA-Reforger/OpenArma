import asyncio

from collections.abc import Awaitable
from typing import Any

import litellm
import pytest

from backend.app.conversation.engine import claude_sdk, llm

MESSAGES = [{'role': 'user', 'content': 'Hi'}]


def test_acompletion_keeps_litellm_path_for_other_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_litellm_acompletion(**params: Any) -> Awaitable[str]:
        captured.update(params)
        return asyncio.sleep(0, result='litellm response')

    monkeypatch.setattr(litellm, 'acompletion', fake_litellm_acompletion)
    monkeypatch.setattr(llm, '_decrypt_api_key', lambda encrypted: f'decrypted-{encrypted}')

    response = asyncio.run(
        llm.acompletion(
            provider_type='ollama',
            api_base='http://localhost:11434',
            api_key_encrypted='cipher',
            model_name='gemma4',
            messages=MESSAGES,
            stream=False,
        )
    )

    assert response == 'litellm response'
    assert captured['model'] == 'ollama/gemma4'
    assert captured['api_key'] == 'decrypted-cipher'
    assert captured['api_base'] == 'http://localhost:11434'


def test_acompletion_routes_claude_sdk_without_key_decryption_or_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_claude_sdk_completion(**kwargs: Any) -> Awaitable[str]:
        calls.append(kwargs)
        return asyncio.sleep(0, result='sdk response')

    def fail_decrypt(encrypted: str) -> str:
        raise AssertionError('claude_sdk must not decrypt API keys')

    def fail_litellm(**params: Any) -> None:
        raise AssertionError('claude_sdk must not reach LiteLLM')

    monkeypatch.setattr(claude_sdk, 'claude_sdk_completion', fake_claude_sdk_completion)
    monkeypatch.setattr(llm, '_decrypt_api_key', fail_decrypt)
    monkeypatch.setattr(litellm, 'acompletion', fail_litellm)

    response = asyncio.run(
        llm.acompletion(
            provider_type='claude_sdk',
            api_base=None,
            api_key_encrypted='cipher',
            model_name='claude-haiku-5-5',
            messages=MESSAGES,
            temperature=0.2,
            max_tokens=512,
            stream=True,
            top_p=0.9,
            think=True,
            effort='high',
        )
    )

    assert response == 'sdk response'
    assert calls == [
        {
            'model_name': 'claude-haiku-5-5',
            'messages': MESSAGES,
            'stream': True,
            'think': True,
            'effort': 'high',
            'temperature': 0.2,
            'max_tokens': 512,
            'top_p': 0.9,
        }
    ]
