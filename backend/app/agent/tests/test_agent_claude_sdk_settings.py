import asyncio

from collections.abc import Awaitable
from types import SimpleNamespace
from typing import Any

import pytest

from pydantic import ValidationError

from backend.app.agent.crud.crud_agent import agent_dao
from backend.app.agent.model import Agent
from backend.app.agent.schema.agent import CreateAgentParam, UpdateAgentParam
from backend.app.agent.service.agent_service import agent_service
from backend.app.llm.crud.crud_llm_provider import llm_provider_dao
from backend.common.exception import errors

CLAUDE_SDK_PROVIDER_ID = 1
OPENAI_PROVIDER_ID = 2
PROVIDER_TYPES = {CLAUDE_SDK_PROVIDER_ID: 'claude_sdk', OPENAI_PROVIDER_ID: 'openai'}


def _install_daos(monkeypatch: pytest.MonkeyPatch, agent: Any = None) -> dict[str, list]:
    """Replaces the DAO calls with fakes; records the objects passed to create and update."""
    calls: dict[str, list] = {'create': [], 'update': []}

    def get_provider(db: Any, pk: int) -> Awaitable[Any]:
        provider_type = PROVIDER_TYPES.get(pk)
        provider = None if provider_type is None else SimpleNamespace(id=pk, provider_type=provider_type)
        return asyncio.sleep(0, result=provider)

    def get_agent(db: Any, pk: int) -> Awaitable[Any]:
        return asyncio.sleep(0, result=agent)

    def create_agent(db: Any, obj: Any, user_id: int) -> Awaitable[Any]:
        calls['create'].append(obj)
        return asyncio.sleep(0, result=obj)

    def update_agent(db: Any, pk: int, obj: Any) -> Awaitable[int]:
        calls['update'].append(obj)
        return asyncio.sleep(0, result=1)

    monkeypatch.setattr(llm_provider_dao, 'get', get_provider)
    monkeypatch.setattr(agent_dao, 'get', get_agent)
    monkeypatch.setattr(agent_dao, 'create', create_agent)
    monkeypatch.setattr(agent_dao, 'update', update_agent)
    return calls


def _existing_agent(**overrides: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        'id': 10,
        'user_id': 1,
        'visibility': 'private',
        'name': 'Agent',
        'description': None,
        'system_prompt': 'Be brief',
        'rules': None,
        'skills': None,
        'llm_provider_id': CLAUDE_SDK_PROVIDER_ID,
        'model_name': 'claude-haiku-5-5',
        'temperature': 0.7,
        'top_p': None,
        'max_tokens': None,
        'presence_penalty': None,
        'frequency_penalty': None,
        'sort_order': 0,
        'is_default': False,
        'builtin_tools': None,
        'enable_sub_agents': False,
        'think': True,
        'effort': 'high',
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_agent_model_declares_nullable_think_and_effort_columns() -> None:
    assert Agent.__table__.c.think.nullable is True
    assert Agent.__table__.c.effort.nullable is True


def test_create_schema_defaults_think_and_effort_to_none() -> None:
    obj = CreateAgentParam(name='Agent')

    assert obj.think is None
    assert obj.effort is None


def test_update_schema_rejects_effort_outside_the_supported_levels() -> None:
    with pytest.raises(ValidationError):
        UpdateAgentParam(effort='ultra')


@pytest.mark.parametrize(
    'fields',
    [
        {'think': None, 'effort': 'high'},
        {'think': True, 'effort': None},
        {'think': None, 'effort': None},
    ],
)
def test_create_rejects_claude_sdk_agent_missing_think_or_effort(
    monkeypatch: pytest.MonkeyPatch, fields: dict[str, Any]
) -> None:
    calls = _install_daos(monkeypatch)
    obj = CreateAgentParam(name='Agent', llm_provider_id=CLAUDE_SDK_PROVIDER_ID, **fields)

    with pytest.raises(errors.RequestError, match='think and effort are required'):
        asyncio.run(agent_service.create(db=None, obj=obj, user_id=1))

    assert calls['create'] == []


def test_create_accepts_claude_sdk_agent_with_think_and_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_daos(monkeypatch)
    obj = CreateAgentParam(name='Agent', llm_provider_id=CLAUDE_SDK_PROVIDER_ID, think=False, effort='low')

    asyncio.run(agent_service.create(db=None, obj=obj, user_id=1))

    assert len(calls['create']) == 1


def test_create_ignores_think_and_effort_for_other_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_daos(monkeypatch)
    obj = CreateAgentParam(name='Agent', llm_provider_id=OPENAI_PROVIDER_ID)

    asyncio.run(agent_service.create(db=None, obj=obj, user_id=1))

    assert len(calls['create']) == 1


def test_update_rejects_clearing_think_on_claude_sdk_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_daos(monkeypatch, agent=_existing_agent())
    obj = UpdateAgentParam(think=None)

    with pytest.raises(errors.RequestError, match='think and effort are required'):
        asyncio.run(agent_service.update(db=None, pk=10, obj=obj, user_id=1))

    assert calls['update'] == []


def test_update_validates_merged_state_when_switching_to_claude_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _existing_agent(llm_provider_id=OPENAI_PROVIDER_ID, think=None, effort=None)
    calls = _install_daos(monkeypatch, agent=agent)

    with pytest.raises(errors.RequestError, match='think and effort are required'):
        asyncio.run(
            agent_service.update(
                db=None, pk=10, obj=UpdateAgentParam(llm_provider_id=CLAUDE_SDK_PROVIDER_ID), user_id=1
            )
        )

    assert calls['update'] == []


def test_update_accepts_switching_to_claude_sdk_when_request_sets_both(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _existing_agent(llm_provider_id=OPENAI_PROVIDER_ID, think=None, effort=None)
    calls = _install_daos(monkeypatch, agent=agent)
    obj = UpdateAgentParam(llm_provider_id=CLAUDE_SDK_PROVIDER_ID, think=True, effort='max')

    asyncio.run(agent_service.update(db=None, pk=10, obj=obj, user_id=1))

    assert calls['update'] == [obj]


def test_update_allows_leaving_claude_sdk_for_another_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _existing_agent(think=None, effort=None)
    calls = _install_daos(monkeypatch, agent=agent)
    obj = UpdateAgentParam(llm_provider_id=OPENAI_PROVIDER_ID)

    asyncio.run(agent_service.update(db=None, pk=10, obj=obj, user_id=1))

    assert calls['update'] == [obj]


def test_clone_copies_think_and_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_daos(monkeypatch, agent=_existing_agent(think=False, effort='xhigh'))

    asyncio.run(agent_service.clone(db=None, pk=10, user_id=1))

    cloned = calls['create'][0]
    assert cloned.think is False
    assert cloned.effort == 'xhigh'
