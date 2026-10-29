"""Claude Agent SDK provider: runs single-turn Claude queries behind a LiteLLM-shaped interface."""

import asyncio
import sys

from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import aclosing
from types import SimpleNamespace
from typing import Any, TypeVar, cast

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ClaudeSDKError,
    EffortLevel,
    Message,
    RateLimitEvent,
    ResultMessage,
    TextBlock,
    query,
)

from backend.common.log import log
from backend.core.conf import settings

_T = TypeVar('_T')

RATE_LIMIT_ASSISTANT_ERROR = 'rate_limit'
RATE_LIMIT_HTTP_STATUS = 429
RATE_LIMIT_REJECTED_STATUS = 'rejected'
_RESTRICTED_SDK_ENV = {'ANTHROPIC_API_KEY': '', 'ENABLE_CLAUDEAI_MCP_SERVERS': 'false'}

_warned_parameter_sets: set[tuple[str, ...]] = set()


class ClaudeSdkError(Exception):
    """Raised when a Claude Agent SDK query fails or returns no usable text."""


class ClaudeSdkRateLimitError(ClaudeSdkError):
    """Raised when the Claude subscription rate limit rejects a query."""


def build_claude_prompt(messages: list[dict]) -> tuple[str, str]:
    """
    Split OpenAI-style chat messages into the SDK system prompt and user prompt

    System messages are joined into the system prompt. A single remaining message is sent raw,
    otherwise the turns are rendered as a labeled transcript in order. Messages without text
    (e.g. assistant tool calls with content=None) are skipped, since tools are not supported yet.

    :param messages: chat messages with role and content
    :return: (system_prompt, prompt)
    """
    system_parts: list[str] = []
    turns: list[tuple[str, str]] = []
    for message in messages:
        role = message.get('role') or 'user'
        content = message.get('content')
        text = content if isinstance(content, str) else ''
        if role == 'system':
            if text:
                system_parts.append(text)
        elif text:
            turns.append((role, text))

    system_prompt = '\n\n'.join(system_parts)
    if len(turns) == 1:
        return system_prompt, turns[0][1]
    prompt = '\n\n'.join(f'[{role}]\n{text}' for role, text in turns)
    return system_prompt, prompt


async def claude_sdk_completion(
    *,
    model_name: str,
    messages: list[dict],
    think: bool | None,
    effort: EffortLevel | None,
    stream: bool = False,
    **ignored: Any,
) -> Any:
    """
    Run one single-turn Claude query and return a LiteLLM-shaped response

    :param model_name: Claude model name, e.g. claude-haiku-5-5
    :param messages: OpenAI-style chat messages
    :param think: per-agent thinking switch, required
    :param effort: per-agent effort level, required
    :param stream: return an async iterator of chunks instead of a full response
    :param ignored: unsupported LiteLLM parameters, reported and dropped
    :return: response object with choices and usage
    """
    if think is None:
        raise ClaudeSdkError("'think' is required for claude_sdk agents")
    if effort is None:
        raise ClaudeSdkError("'effort' is required for claude_sdk agents")
    _warn_ignored_parameters(ignored)
    system_prompt, prompt = build_claude_prompt(messages)
    timeout_seconds = settings.CLAUDE_SDK_TIMEOUT_SECONDS

    async def run_query() -> tuple[str, dict[str, Any]]:
        try:
            return await asyncio.wait_for(
                _query_text(
                    model_name=model_name, system_prompt=system_prompt, prompt=prompt, think=think, effort=effort
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError as exception:
            raise ClaudeSdkError(f'Claude query exceeded the timeout of {timeout_seconds}s') from exception

    text, result_usage = await _run_with_subprocess_support(run_query)

    usage = _build_usage(result_usage)
    if stream:
        return _stream_chunks(text=text, usage=usage)
    return _non_stream_response(text=text, usage=usage)


async def _run_with_subprocess_support(run: Callable[[], Awaitable[_T]]) -> _T:
    """
    Run a coroutine on a loop that can spawn the Claude CLI subprocess

    On Windows the Celery CLI loads the flower plugin, which switches the process to the selector event loop
    policy, and selector loops cannot start subprocesses. In that case the coroutine runs on a Proactor loop
    in a worker thread. Everywhere else it runs on the current loop.
    """
    if sys.platform != 'win32' or isinstance(asyncio.get_running_loop(), asyncio.ProactorEventLoop):
        return await run()

    def run_on_proactor_loop() -> _T:
        loop = asyncio.ProactorEventLoop()
        try:
            return loop.run_until_complete(run())
        finally:
            loop.close()

    return await asyncio.get_running_loop().run_in_executor(None, run_on_proactor_loop)


async def list_claude_models() -> list[str]:
    """
    List the Claude model names reported by the Claude Code server, without sending a prompt

    Each model reports an alias (value) and, when known, the resolved model id (resolvedModel).

    :return: sorted unique model names
    """
    options = ClaudeAgentOptions(
        tools=[],
        max_turns=1,
        setting_sources=[],
        env=_RESTRICTED_SDK_ENV,
    )
    server_info: dict[str, Any] | None = None
    async with ClaudeSDKClient(options=options) as client:
        server_info = await client.get_server_info()
    models = (server_info or {}).get('models') or []
    names = {item.get('resolvedModel') or item.get('value') for item in models if isinstance(item, dict)}
    return sorted(name for name in names if name)


async def _query_text(
    *, model_name: str, system_prompt: str, prompt: str, think: bool, effort: EffortLevel
) -> tuple[str, dict[str, Any]]:
    text_fragments: list[str] = []
    result_usage: dict[str, Any] = {}
    latest_rate_limit_event: RateLimitEvent | None = None
    options = _build_options(model_name=model_name, system_prompt=system_prompt, think=think, effort=effort)

    try:
        message_source = cast('AsyncGenerator[Message, None]', query(prompt=prompt, options=options))
        async with aclosing(message_source) as message_stream:
            async for message in message_stream:
                if isinstance(message, RateLimitEvent):
                    latest_rate_limit_event = message
                elif isinstance(message, AssistantMessage):
                    if message.error is not None:
                        raise _build_assistant_error(message=message, rate_limit_event=latest_rate_limit_event)
                    text_fragments.extend(block.text for block in message.content if isinstance(block, TextBlock))
                elif isinstance(message, ResultMessage):
                    if message.is_error:
                        raise _build_result_error(message=message, rate_limit_event=latest_rate_limit_event)
                    result_usage = message.usage or {}
    except ClaudeSDKError as exception:
        raise ClaudeSdkError(f'Claude SDK error: {exception}') from exception

    text = ''.join(text_fragments).strip()
    if not text:
        raise ClaudeSdkError('Claude returned an empty response')
    return text, result_usage


def _warn_ignored_parameters(ignored: dict[str, Any]) -> None:
    names = tuple(sorted(name for name, value in ignored.items() if value is not None))
    if names and names not in _warned_parameter_sets:
        _warned_parameter_sets.add(names)
        log.warning(f'claude_sdk ignores unsupported parameters: {", ".join(names)}')


def _build_options(*, model_name: str, system_prompt: str, think: bool, effort: EffortLevel) -> ClaudeAgentOptions:
    # Thinking is disabled unless the agent enables think; effort comes from the agent
    return ClaudeAgentOptions(
        model=model_name,
        system_prompt=system_prompt,
        tools=[],
        max_turns=1,
        setting_sources=[],
        env=_RESTRICTED_SDK_ENV,
        thinking=None if think else {'type': 'disabled'},
        effort=effort,
    )


def _build_assistant_error(*, message: AssistantMessage, rate_limit_event: RateLimitEvent | None) -> ClaudeSdkError:
    description = f'assistant error: {message.error}{_build_rate_limit_suffix(rate_limit_event)}'
    if message.error == RATE_LIMIT_ASSISTANT_ERROR or _is_rate_limit_rejected(rate_limit_event):
        return ClaudeSdkRateLimitError(description)
    return ClaudeSdkError(description)


def _build_result_error(*, message: ResultMessage, rate_limit_event: RateLimitEvent | None) -> ClaudeSdkError:
    description = (
        f'result error: subtype={message.subtype}, api_error_status={message.api_error_status}, '
        f'errors={message.errors}{_build_rate_limit_suffix(rate_limit_event)}'
    )
    if message.api_error_status == RATE_LIMIT_HTTP_STATUS or _is_rate_limit_rejected(rate_limit_event):
        return ClaudeSdkRateLimitError(description)
    return ClaudeSdkError(description)


def _is_rate_limit_rejected(rate_limit_event: RateLimitEvent | None) -> bool:
    return rate_limit_event is not None and rate_limit_event.rate_limit_info.status == RATE_LIMIT_REJECTED_STATUS


def _build_rate_limit_suffix(rate_limit_event: RateLimitEvent | None) -> str:
    if rate_limit_event is None or not _is_rate_limit_rejected(rate_limit_event):
        return ''
    rate_limit_info = rate_limit_event.rate_limit_info
    return f'; rate limit rejected (type={rate_limit_info.rate_limit_type}, resets_at={rate_limit_info.resets_at})'


def _build_usage(result_usage: dict[str, Any]) -> SimpleNamespace:
    """Map SDK usage to LiteLLM usage; cache reads and writes both count as prompt tokens."""
    cache_read_tokens = result_usage.get('cache_read_input_tokens') or 0
    cache_creation_tokens = result_usage.get('cache_creation_input_tokens') or 0
    prompt_tokens = (result_usage.get('input_tokens') or 0) + cache_creation_tokens + cache_read_tokens
    completion_tokens = result_usage.get('output_tokens') or 0
    return SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        prompt_tokens_details=SimpleNamespace(cached_tokens=cache_read_tokens),
        completion_tokens_details=SimpleNamespace(reasoning_tokens=None),
    )


def _non_stream_response(*, text: str, usage: SimpleNamespace) -> SimpleNamespace:
    message = SimpleNamespace(content=text, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason='stop')], usage=usage)


async def _stream_chunks(*, text: str, usage: SimpleNamespace) -> AsyncIterator[SimpleNamespace]:  # ruff: ignore[unused-async]
    """Emulate streaming: the SDK yields whole messages, so the text arrives as one delta before the usage chunk."""
    delta = SimpleNamespace(content=text, tool_calls=None)
    yield SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=None)], usage=None)
    yield SimpleNamespace(choices=[], usage=usage)
