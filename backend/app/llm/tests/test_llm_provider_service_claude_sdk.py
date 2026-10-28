import asyncio

from collections.abc import Awaitable
from types import SimpleNamespace
from typing import Any

import litellm
import pytest

from typing_extensions import Self

from backend.app.conversation.engine import claude_sdk
from backend.app.llm.service import llm_provider_service as service_module
from backend.app.llm.service.llm_provider_service import LLMProviderService

CLAUDE_MODEL = 'claude-haiku-5-5'


class FakeDao:
    """Stands in for llm_provider_dao and records the models updates written by verify_connection."""

    def __init__(self, provider: Any) -> None:
        self.provider = provider
        self.updates: list[tuple[int, dict[str, Any]]] = []

    async def get(self, db: Any, pk: int) -> Any:
        return self.provider

    async def update(self, db: Any, pk: int, data: dict[str, Any]) -> int:
        self.updates.append((pk, data))
        return 1


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def _provider(**overrides: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        'id': 1,
        'user_id': 7,
        'provider_type': 'claude_sdk',
        'api_base': None,
        'api_key_encrypted': None,
        'models': [{'name': CLAUDE_MODEL, 'verified_at': None, 'verified_ok': None}],
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _install_dao(monkeypatch: pytest.MonkeyPatch, provider: SimpleNamespace) -> FakeDao:
    dao = FakeDao(provider)
    monkeypatch.setattr(service_module, 'llm_provider_dao', dao)
    return dao


def _response(text: str) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def _verify(db: Any, model_name: str = CLAUDE_MODEL) -> dict[str, Any]:
    return asyncio.run(LLMProviderService.verify_connection(db=db, pk=1, user_id=7, model_name=model_name))


def test_verify_claude_sdk_success_records_verification_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    dao = _install_dao(monkeypatch, _provider())
    db = FakeDb()
    calls: list[dict[str, Any]] = []

    def fake_completion(**kwargs: Any) -> Awaitable[SimpleNamespace]:
        calls.append(kwargs)
        return asyncio.sleep(0, result=_response('Hi there, how can I help?'))

    monkeypatch.setattr(claude_sdk, 'claude_sdk_completion', fake_completion)

    result = _verify(db)

    assert result == {
        'success': True,
        'message': f'Connection successful (model={CLAUDE_MODEL}, reply=Hi there, how can I help?)',
    }
    assert calls == [{'model_name': CLAUDE_MODEL, 'messages': [{'role': 'user', 'content': 'Hi'}], 'stream': False}]
    _, data = dao.updates[0]
    assert data['models'][0]['name'] == CLAUDE_MODEL
    assert data['models'][0]['verified_ok'] is True
    assert data['models'][0]['verified_at'] is not None
    assert db.commits == 1


def test_verify_claude_sdk_truncates_reply_to_fifty_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_dao(monkeypatch, _provider())

    def fake_completion(**kwargs: Any) -> Awaitable[SimpleNamespace]:
        return asyncio.sleep(0, result=_response('x' * 80))

    monkeypatch.setattr(claude_sdk, 'claude_sdk_completion', fake_completion)

    result = _verify(FakeDb())

    assert result['message'] == f'Connection successful (model={CLAUDE_MODEL}, reply={"x" * 50})'


def test_verify_claude_sdk_failure_returns_error_and_records_failed_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dao = _install_dao(monkeypatch, _provider())
    db = FakeDb()
    error_text = 'Claude query exceeded the timeout of 300s ' + 'x' * 300

    def fake_completion(**kwargs: Any) -> Awaitable[SimpleNamespace]:
        raise claude_sdk.ClaudeSdkError(error_text)

    monkeypatch.setattr(claude_sdk, 'claude_sdk_completion', fake_completion)

    result = _verify(db)

    assert result == {'success': False, 'message': error_text[:200]}
    _, data = dao.updates[0]
    assert data['models'][0]['verified_ok'] is False
    assert db.commits == 1


def test_verify_claude_sdk_never_decrypts_key_or_calls_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_dao(monkeypatch, _provider(api_key_encrypted='cipher'))
    decrypt_calls: list[str] = []
    litellm_calls: list[str] = []

    def record_decrypt(encrypted: str) -> str:
        decrypt_calls.append(encrypted)
        return 'plain'

    def record_acompletion(**params: Any) -> Awaitable[None]:
        litellm_calls.append('acompletion')
        return asyncio.sleep(0)

    def record_aembedding(**params: Any) -> Awaitable[None]:
        litellm_calls.append('aembedding')
        return asyncio.sleep(0)

    def fake_completion(**kwargs: Any) -> Awaitable[SimpleNamespace]:
        return asyncio.sleep(0, result=_response('ok'))

    monkeypatch.setattr(service_module, '_decrypt_api_key', record_decrypt)
    monkeypatch.setattr(litellm, 'acompletion', record_acompletion)
    monkeypatch.setattr(litellm, 'aembedding', record_aembedding)
    monkeypatch.setattr(claude_sdk, 'claude_sdk_completion', fake_completion)

    result = _verify(FakeDb())

    assert result['success'] is True
    assert decrypt_calls == []
    assert litellm_calls == []


def test_verify_other_providers_still_decrypt_key_and_use_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    dao = _install_dao(
        monkeypatch,
        _provider(provider_type='openai', api_key_encrypted='cipher', models=[{'name': 'gpt-4o'}]),
    )
    db = FakeDb()
    captured: dict[str, Any] = {}

    def fake_acompletion(**params: Any) -> Awaitable[SimpleNamespace]:
        captured.update(params)
        return asyncio.sleep(0, result=_response('ok'))

    monkeypatch.setattr(service_module, '_decrypt_api_key', lambda encrypted: f'plain-{encrypted}')
    monkeypatch.setattr(litellm, 'acompletion', fake_acompletion)

    result = _verify(db, model_name='gpt-4o')

    assert result == {'success': True, 'message': 'Connection successful (model=gpt-4o, reply=ok)'}
    assert captured['api_key'] == 'plain-cipher'
    assert dao.updates[0][1]['models'][0]['verified_ok'] is True
    assert db.commits == 1


class ForbiddenHttpClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise AssertionError('claude_sdk must not use httpx')


def _fetch(db: Any) -> dict[str, Any]:
    return asyncio.run(LLMProviderService.fetch_remote_models(db=db, pk=1, user_id=7))


def test_fetch_remote_models_claude_sdk_returns_sdk_model_names_without_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_dao(monkeypatch, _provider())
    monkeypatch.setattr(service_module.httpx, 'AsyncClient', ForbiddenHttpClient)

    def fake_list_models() -> Awaitable[list[str]]:
        return asyncio.sleep(0, result=['claude-haiku-5-5', 'claude-sonnet-5-5'])

    monkeypatch.setattr(claude_sdk, 'list_claude_models', fake_list_models)

    result = _fetch(FakeDb())

    assert result == {
        'success': True,
        'models': ['claude-haiku-5-5', 'claude-sonnet-5-5'],
        'message': 'Fetched 2 models',
    }


def test_fetch_remote_models_claude_sdk_reports_sdk_error_without_decrypting_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_dao(monkeypatch, _provider(api_key_encrypted='cipher'))
    decrypt_calls: list[str] = []
    error_text = 'Claude Code server did not start ' + 'x' * 300

    def record_decrypt(encrypted: str) -> str:
        decrypt_calls.append(encrypted)
        return 'plain'

    def fake_list_models() -> Awaitable[list[str]]:
        raise claude_sdk.ClaudeSdkError(error_text)

    monkeypatch.setattr(service_module, '_decrypt_api_key', record_decrypt)
    monkeypatch.setattr(claude_sdk, 'list_claude_models', fake_list_models)

    result = _fetch(FakeDb())

    assert result == {'success': False, 'models': [], 'message': error_text[:200]}
    assert decrypt_calls == []


class FakeHttpResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {'data': [{'id': 'gpt-4o-mini'}, {'id': 'gpt-4o'}, {'object': 'model'}]}


class FakeHttpClient:
    urls: list[str] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    def get(self, url: str, headers: Any = None) -> Awaitable[FakeHttpResponse]:
        FakeHttpClient.urls.append(url)
        return asyncio.sleep(0, result=FakeHttpResponse())


def test_fetch_remote_models_other_providers_still_list_openai_style_models_over_httpx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_dao(monkeypatch, _provider(provider_type='openai', api_base='https://api.example.com/v1/', models=None))
    monkeypatch.setattr(service_module.httpx, 'AsyncClient', FakeHttpClient)
    FakeHttpClient.urls.clear()

    result = _fetch(FakeDb())

    assert result == {'success': True, 'models': ['gpt-4o', 'gpt-4o-mini'], 'message': 'Fetched 2 models'}
    assert FakeHttpClient.urls == ['https://api.example.com/v1/models']
