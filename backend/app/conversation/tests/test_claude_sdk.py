import asyncio

from collections.abc import AsyncIterator
from typing import Any

import pytest

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKError,
    RateLimitEvent,
    RateLimitInfo,
    RateLimitStatus,
    ResultMessage,
    TextBlock,
)

from backend.app.conversation.engine import claude_sdk
from backend.app.conversation.engine.claude_sdk import build_claude_prompt
from backend.app.conversation.engine.graph import _extract_usage

MESSAGES = [
    {'role': 'system', 'content': 'Be brief'},
    {'role': 'user', 'content': 'Pick an order'},
]
USAGE = {
    'input_tokens': 10,
    'cache_creation_input_tokens': 5,
    'cache_read_input_tokens': 100,
    'output_tokens': 7,
}


HANG = object()  # marks a query that never yields a message


class FakeQuery:
    """Stands in for claude_agent_sdk.query and records the prompt and options of each call."""

    def __init__(self, items: list[Any]) -> None:
        self.items = items
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *, prompt: str, options: Any) -> AsyncIterator[Any]:
        self.calls.append({'prompt': prompt, 'options': options})
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[Any]:
        for item in self.items:
            if item is HANG:
                await asyncio.sleep(60)
            if isinstance(item, BaseException):
                raise item
            yield item


def _install_fake_query(monkeypatch: pytest.MonkeyPatch, items: list[Any]) -> FakeQuery:
    fake_query = FakeQuery(items)
    monkeypatch.setattr(claude_sdk, 'query', fake_query)
    return fake_query


def _assistant_message(text: str = 'ok') -> AssistantMessage:
    return AssistantMessage(content=[TextBlock(text=text)], model='claude-haiku-5-5')


def _result_message(**overrides: Any) -> ResultMessage:
    fields: dict[str, Any] = {
        'subtype': 'success',
        'duration_ms': 1,
        'duration_api_ms': 1,
        'is_error': False,
        'num_turns': 1,
        'session_id': 'session',
        'usage': USAGE,
    }
    fields.update(overrides)
    return ResultMessage(**fields)


def _rate_limit_event(status: RateLimitStatus) -> RateLimitEvent:
    rate_limit_info = RateLimitInfo(status=status, resets_at=1_800_000_000)
    return RateLimitEvent(rate_limit_info=rate_limit_info, uuid='uuid', session_id='session')


def _complete(**kwargs: Any) -> Any:
    return asyncio.run(claude_sdk.claude_sdk_completion(model_name='claude-haiku-5-5', messages=MESSAGES, **kwargs))


@pytest.fixture(autouse=True)
def _reset_ignored_parameter_warnings() -> None:
    claude_sdk._warned_parameter_sets.clear()


def test_build_claude_prompt_joins_system_messages_into_system_prompt() -> None:
    messages = [
        {'role': 'system', 'content': 'Rules A'},
        {'role': 'system', 'content': 'Rules B'},
        {'role': 'user', 'content': 'Hello'},
    ]

    assert build_claude_prompt(messages) == ('Rules A\n\nRules B', 'Hello')


def test_build_claude_prompt_sends_single_message_raw() -> None:
    assert build_claude_prompt([{'role': 'user', 'content': '  raw text  '}]) == ('', '  raw text  ')


def test_build_claude_prompt_renders_labeled_transcript_in_order() -> None:
    messages = [
        {'role': 'user', 'content': 'First question'},
        {'role': 'assistant', 'content': 'First answer'},
        {'role': 'user', 'content': 'Second question'},
    ]

    assert build_claude_prompt(messages) == (
        '',
        '[user]\nFirst question\n\n[assistant]\nFirst answer\n\n[user]\nSecond question',
    )


def test_build_claude_prompt_renders_tool_text_and_skips_none_content() -> None:
    messages = [
        {'role': 'user', 'content': 'Question'},
        {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'call_1'}]},
        {'role': 'tool', 'content': 'Tool output', 'tool_call_id': 'call_1'},
        {'role': 'tool', 'content': None, 'tool_call_id': 'call_2'},
        {'role': 'user', 'content': 'Follow up'},
    ]

    assert build_claude_prompt(messages) == (
        '',
        '[user]\nQuestion\n\n[tool]\nTool output\n\n[user]\nFollow up',
    )


def test_claude_sdk_completion_builds_restricted_query_options(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_query = _install_fake_query(monkeypatch, [_assistant_message('{}'), _result_message()])

    _complete()

    call = fake_query.calls[0]
    options = call['options']
    assert call['prompt'] == 'Pick an order'
    assert options.model == 'claude-haiku-5-5'
    assert options.system_prompt == 'Be brief'
    assert options.tools == []
    assert options.max_turns == 1
    assert options.setting_sources == []
    assert options.thinking == {'type': 'disabled'}
    assert options.env == {'ANTHROPIC_API_KEY': '', 'ENABLE_CLAUDEAI_MCP_SERVERS': 'false'}


def test_claude_sdk_completion_returns_litellm_shaped_response(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_query(monkeypatch, [_assistant_message(' {"orders": []} \n'), _result_message()])

    response = _complete()

    choice = response.choices[0]
    assert choice.message.content == '{"orders": []}'
    assert choice.message.tool_calls is None
    assert choice.finish_reason == 'stop'


def test_claude_sdk_completion_sums_input_and_cache_tokens_as_prompt_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_query(monkeypatch, [_assistant_message(), _result_message()])

    usage = _complete().usage

    assert usage.prompt_tokens == 115
    assert usage.completion_tokens == 7
    assert usage.total_tokens == 122
    assert _extract_usage(usage) == {
        'prompt_tokens': 115,
        'completion_tokens': 7,
        'total_tokens': 122,
        'cached_tokens': 100,
    }


def test_claude_sdk_stream_emits_whole_text_then_empty_choices_usage_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_query(monkeypatch, [_assistant_message('hello'), _result_message()])

    async def collect_chunks() -> list[Any]:
        stream = await claude_sdk.claude_sdk_completion(model_name='claude-haiku-5-5', messages=MESSAGES, stream=True)
        return [chunk async for chunk in stream]

    chunks = asyncio.run(collect_chunks())

    assert len(chunks) == 2
    assert chunks[0].choices[0].delta.content == 'hello'
    assert chunks[0].choices[0].delta.tool_calls is None
    assert chunks[1].choices == []
    assert _extract_usage(chunks[1].usage)['prompt_tokens'] == 115


def test_claude_sdk_completion_maps_timeout_to_sdk_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claude_sdk, 'CLAUDE_SDK_TIMEOUT_SECONDS', 0.01)
    _install_fake_query(monkeypatch, [HANG])

    with pytest.raises(claude_sdk.ClaudeSdkError, match='exceeded the timeout'):
        _complete()


def test_claude_sdk_completion_maps_sdk_exception_to_sdk_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_query(monkeypatch, [ClaudeSDKError('process crashed')])

    with pytest.raises(claude_sdk.ClaudeSdkError, match='Claude SDK error: process crashed') as exception:
        _complete()

    assert not isinstance(exception.value, claude_sdk.ClaudeSdkRateLimitError)


def test_claude_sdk_completion_maps_non_rate_limit_assistant_error_to_sdk_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assistant_error = AssistantMessage(content=[], model='claude-haiku-5-5', error='billing_error')
    _install_fake_query(monkeypatch, [assistant_error])

    with pytest.raises(claude_sdk.ClaudeSdkError, match='assistant error: billing_error') as exception:
        _complete()

    assert not isinstance(exception.value, claude_sdk.ClaudeSdkRateLimitError)


def test_claude_sdk_completion_maps_rate_limit_assistant_error_to_rate_limit_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assistant_error = AssistantMessage(content=[], model='claude-haiku-5-5', error='rate_limit')
    _install_fake_query(monkeypatch, [assistant_error])

    with pytest.raises(claude_sdk.ClaudeSdkRateLimitError, match='assistant error: rate_limit'):
        _complete()


def test_claude_sdk_completion_maps_assistant_error_during_rejected_limit_to_rate_limit_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assistant_error = AssistantMessage(content=[], model='claude-haiku-5-5', error='server_error')
    _install_fake_query(monkeypatch, [_rate_limit_event('rejected'), assistant_error])

    with pytest.raises(claude_sdk.ClaudeSdkRateLimitError, match='rate limit rejected'):
        _complete()


def test_claude_sdk_completion_maps_result_429_to_rate_limit_error(monkeypatch: pytest.MonkeyPatch) -> None:
    result_error = _result_message(is_error=True, subtype='error_during_execution', api_error_status=429)
    _install_fake_query(monkeypatch, [result_error])

    with pytest.raises(claude_sdk.ClaudeSdkRateLimitError, match='result error'):
        _complete()


def test_claude_sdk_completion_maps_other_result_error_to_sdk_error(monkeypatch: pytest.MonkeyPatch) -> None:
    result_error = _result_message(
        is_error=True,
        subtype='error_during_execution',
        api_error_status=500,
        errors=['upstream failed'],
    )
    _install_fake_query(monkeypatch, [result_error])

    with pytest.raises(claude_sdk.ClaudeSdkError, match='upstream failed') as exception:
        _complete()

    assert not isinstance(exception.value, claude_sdk.ClaudeSdkRateLimitError)


def test_claude_sdk_completion_rejects_blank_response(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_query(monkeypatch, [AssistantMessage(content=[TextBlock(text='   ')], model='claude-haiku-5-5')])

    with pytest.raises(claude_sdk.ClaudeSdkError, match='Claude returned an empty response'):
        _complete()


class RecordingLog:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def test_claude_sdk_completion_warns_once_listing_ignored_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    recording_log = RecordingLog()
    monkeypatch.setattr(claude_sdk, 'log', recording_log)
    _install_fake_query(monkeypatch, [_assistant_message(), _result_message()])

    _complete(temperature=0.2, top_p=0.9, max_tokens=None, stream_options={'include_usage': True})

    assert recording_log.warnings == ['claude_sdk ignores unsupported parameters: stream_options, temperature, top_p']


def test_claude_sdk_completion_warns_only_once_for_the_same_ignored_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    recording_log = RecordingLog()
    monkeypatch.setattr(claude_sdk, 'log', recording_log)
    _install_fake_query(monkeypatch, [_assistant_message(), _result_message()])

    _complete(temperature=0.2, top_p=0.9)
    _complete(temperature=0.5, top_p=0.1)

    assert recording_log.warnings == ['claude_sdk ignores unsupported parameters: temperature, top_p']


def test_claude_sdk_completion_warns_again_when_the_ignored_parameters_change(monkeypatch: pytest.MonkeyPatch) -> None:
    recording_log = RecordingLog()
    monkeypatch.setattr(claude_sdk, 'log', recording_log)
    _install_fake_query(monkeypatch, [_assistant_message(), _result_message()])

    _complete(temperature=0.2)
    _complete(temperature=0.2, top_p=0.9)

    assert recording_log.warnings == [
        'claude_sdk ignores unsupported parameters: temperature',
        'claude_sdk ignores unsupported parameters: temperature, top_p',
    ]


def test_claude_sdk_completion_stays_silent_without_ignored_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    recording_log = RecordingLog()
    monkeypatch.setattr(claude_sdk, 'log', recording_log)
    _install_fake_query(monkeypatch, [_assistant_message(), _result_message()])

    _complete(max_tokens=None)

    assert recording_log.warnings == []
