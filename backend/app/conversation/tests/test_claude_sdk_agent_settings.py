import asyncio

from collections.abc import Awaitable
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.conversation.engine import graph
from backend.app.conversation.engine.graph import OLLAMA_NUM_CTX, AgentConfig, ConversationState, _optional_llm_params
from backend.app.conversation.service.chat_service import ChatService
from backend.app.llm.crud.crud_llm_provider import llm_provider_dao


def test_claude_sdk_agent_config_passes_think_and_effort_to_the_llm_call() -> None:
    cfg = AgentConfig(provider_type='claude_sdk', think=True, effort='high')

    assert _optional_llm_params(cfg) == {'think': True, 'effort': 'high'}


def test_claude_sdk_state_forwards_unset_think_and_effort_for_the_runtime_guard() -> None:
    # None must reach claude_sdk_completion, which names the missing field in its error
    state = ConversationState(provider_type='claude_sdk')

    assert _optional_llm_params(state) == {'think': None, 'effort': None}


@pytest.mark.parametrize('provider_type', ['openai', 'anthropic', 'deepseek'])
def test_other_providers_never_receive_think_or_effort(provider_type: str) -> None:
    cfg = AgentConfig(provider_type=provider_type, think=True, effort='max')

    assert _optional_llm_params(cfg) == {}


def test_ollama_keeps_num_ctx_and_think_false_without_effort() -> None:
    cfg = AgentConfig(provider_type='ollama', think=True, effort='max')

    assert _optional_llm_params(cfg) == {'num_ctx': OLLAMA_NUM_CTX, 'think': False}


def test_spawned_sub_agent_inherits_think_and_effort_from_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_execute_dynamic_sub_agent(parent_cfg: AgentConfig, arguments: dict, state: Any) -> Awaitable[str]:
        captured['parent_cfg'] = parent_cfg
        return asyncio.sleep(0, result='done')

    monkeypatch.setattr(graph, 'execute_dynamic_sub_agent', fake_execute_dynamic_sub_agent)
    monkeypatch.setattr(graph, '_log_tool_call', lambda *args, **kwargs: None)
    state = ConversationState(provider_type='claude_sdk', think=False, effort='low')

    asyncio.run(graph._execute_tool_call(state, 'spawn_agent', {}))

    assert captured['parent_cfg'].think is False
    assert captured['parent_cfg'].effort == 'low'


def _agent(**overrides: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        'id': 10,
        'name': 'Agent',
        'system_prompt': 'Be brief',
        'rules': [],
        'llm_provider_id': 1,
        'model_name': 'claude-haiku-5-5',
        'temperature': 0.7,
        'top_p': None,
        'max_tokens': None,
        'presence_penalty': None,
        'frequency_penalty': None,
        'builtin_tools': None,
        'enable_sub_agents': False,
        'think': True,
        'effort': 'max',
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _no_tools(db: Any, agent_id: int) -> Awaitable[tuple[list, dict]]:
    return asyncio.sleep(0, result=([], {}))


def test_chat_service_agent_config_carries_think_and_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = SimpleNamespace(
        id=1,
        provider_type='claude_sdk',
        api_base=None,
        api_key_encrypted=None,
        rpm_limit=None,
        tpm_limit=None,
    )

    def get_provider(db: Any, pk: int) -> Awaitable[Any]:
        return asyncio.sleep(0, result=provider)

    monkeypatch.setattr(llm_provider_dao, 'get', get_provider)
    monkeypatch.setattr(ChatService, '_get_agent_tools', _no_tools)
    monkeypatch.setattr(ChatService, '_get_builtin_tools_for_agent', lambda *args, **kwargs: ([], {}))

    config = asyncio.run(ChatService._build_agent_config(db=None, agent=_agent(), project_id=1))

    assert config is not None
    assert config['think'] is True
    assert config['effort'] == 'max'
