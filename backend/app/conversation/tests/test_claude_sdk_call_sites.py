import asyncio

from collections.abc import AsyncIterator, Awaitable
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.conversation.engine import graph_builder
from backend.app.conversation.engine.graph import ConversationState
from backend.app.conversation.engine.graph_builder import TopologyEdge, TopologyNode
from backend.app.conversation.service import context_manager


class _FakeAcompletion:
    """Records every acompletion call; streams one chunk per text, or answers with a single message."""

    def __init__(self, *, stream_texts: list[str] | None = None, message: str = 'target') -> None:
        self.calls: list[dict[str, Any]] = []
        self._stream_texts = stream_texts or []
        self._message = message

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if kwargs.get('stream'):
            return _stream_chunks(self._stream_texts)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._message))],
            usage=None,
        )


async def _stream_chunks(texts: list[str]) -> AsyncIterator[SimpleNamespace]:
    for text in texts:
        await asyncio.sleep(0)
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))], usage=None)


def _agent_config_map(provider_type: str) -> dict[int, dict]:
    return {
        1: {
            'agent_id': 1,
            'agent_name': 'Agent',
            'provider_type': provider_type,
            'model_name': 'model-x',
            'think': True,
            'effort': 'high',
        }
    }


def _run_coordinator(monkeypatch: pytest.MonkeyPatch, provider_type: str, stream_texts: list[str]) -> _FakeAcompletion:
    fake = _FakeAcompletion(stream_texts=stream_texts, message='fallback')
    monkeypatch.setattr(graph_builder, 'acompletion', fake)
    node = TopologyNode(id='coord', type='coordinator')
    state = ConversationState(
        topology={
            'nodes': [{'id': 'up', 'type': 'agent'}],
            'edges': [{'id': 'e1', 'source': 'up', 'target': 'coord'}],
        },
        node_outputs={'up': 'upstream analysis'},
    )

    asyncio.run(graph_builder._make_dag_coordinator_node(node, _agent_config_map(provider_type))(state))

    return fake


def _run_condition(monkeypatch: pytest.MonkeyPatch, provider_type: str) -> _FakeAcompletion:
    fake = _FakeAcompletion(message='a')
    monkeypatch.setattr(graph_builder, 'acompletion', fake)
    node = TopologyNode(id='cond', type='condition', config={'expression': 'enemy visible'})
    edges = [TopologyEdge(id='e1', source='cond', target='a')]
    state = ConversationState(user_input='situation')

    result = asyncio.run(graph_builder._make_dag_condition_node(node, edges, _agent_config_map(provider_type))(state))

    assert result['_condition_target'] == 'a'
    return fake


def test_coordinator_stream_passes_think_and_effort_to_claude_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _run_coordinator(monkeypatch, 'claude_sdk', stream_texts=['ok'])

    assert len(fake.calls) == 1
    assert fake.calls[0]['think'] is True
    assert fake.calls[0]['effort'] == 'high'


def test_coordinator_fallback_passes_think_and_effort_to_claude_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _run_coordinator(monkeypatch, 'claude_sdk', stream_texts=[])

    assert [call['stream'] for call in fake.calls] == [True, False]
    for call in fake.calls:
        assert call['think'] is True
        assert call['effort'] == 'high'


def test_condition_router_passes_think_and_effort_to_claude_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _run_condition(monkeypatch, 'claude_sdk')

    assert len(fake.calls) == 1
    assert fake.calls[0]['think'] is True
    assert fake.calls[0]['effort'] == 'high'


@pytest.mark.parametrize('provider_type', ['openai', 'anthropic', 'deepseek'])
def test_graph_builder_call_sites_never_send_think_or_effort_to_other_providers(
    monkeypatch: pytest.MonkeyPatch, provider_type: str
) -> None:
    coordinator = _run_coordinator(monkeypatch, provider_type, stream_texts=[])
    condition = _run_condition(monkeypatch, provider_type)

    for call in [*coordinator.calls, *condition.calls]:
        assert 'think' not in call
        assert 'effort' not in call


def _patch_history(monkeypatch: pytest.MonkeyPatch, total: int) -> None:
    messages = [SimpleNamespace(role='user', content=f'msg {i}', del_flag=False, metadata_={}) for i in range(total)]

    def count_messages(db: Any, conversation_id: int) -> Awaitable[int]:
        return asyncio.sleep(0, result=total)

    def get_recent(db: Any, conversation_id: int, limit: int) -> Awaitable[list]:
        return asyncio.sleep(0, result=messages)

    monkeypatch.setattr(context_manager.message_dao, 'count_messages', count_messages)
    monkeypatch.setattr(context_manager.message_dao, 'get_recent', get_recent)


def _run_summary(monkeypatch: pytest.MonkeyPatch, llm_config: dict) -> _FakeAcompletion:
    fake = _FakeAcompletion(message='summary')
    monkeypatch.setattr('backend.app.conversation.engine.llm.acompletion', fake)
    _patch_history(monkeypatch, total=5)

    summary = asyncio.run(
        context_manager._generate_summary(
            db=None,
            conversation_id=1,
            context_window=2,
            llm_config=llm_config,
            is_arma=False,
        )
    )

    assert summary == 'summary'
    return fake


def test_summary_passes_think_and_effort_to_claude_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    llm_config = {'provider_type': 'claude_sdk', 'model_name': 'model-x', 'think': True, 'effort': 'high'}

    fake = _run_summary(monkeypatch, llm_config)

    assert len(fake.calls) == 1
    assert fake.calls[0]['think'] is True
    assert fake.calls[0]['effort'] == 'high'


@pytest.mark.parametrize('provider_type', ['openai', 'anthropic', 'deepseek'])
def test_summary_never_sends_think_or_effort_to_other_providers(
    monkeypatch: pytest.MonkeyPatch, provider_type: str
) -> None:
    llm_config = {'provider_type': provider_type, 'model_name': 'model-x', 'think': True, 'effort': 'high'}

    fake = _run_summary(monkeypatch, llm_config)

    assert 'think' not in fake.calls[0]
    assert 'effort' not in fake.calls[0]
