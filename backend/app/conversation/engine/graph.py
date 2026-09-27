"""LangGraph conversation graph engine: supports single Agent / multi-Agent
collaboration / MCP tool calls / streaming output."""

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, StateGraph

from backend.app.conversation.engine.llm import acompletion, acompletion_stream

log = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 10


def _extract_usage(usage_obj) -> dict:
    """Extract usage dict from an LLM response usage object, including cache/reasoning details."""
    if not usage_obj:
        return {}
    result = {
        'prompt_tokens': usage_obj.prompt_tokens or 0,
        'completion_tokens': usage_obj.completion_tokens or 0,
        'total_tokens': usage_obj.total_tokens or 0,
    }
    ptd = getattr(usage_obj, 'prompt_tokens_details', None)
    if ptd:
        cached = getattr(ptd, 'cached_tokens', None)
        if cached:
            result['cached_tokens'] = cached
    ctd = getattr(usage_obj, 'completion_tokens_details', None)
    if ctd:
        reasoning = getattr(ctd, 'reasoning_tokens', None)
        if reasoning:
            result['reasoning_tokens'] = reasoning
    return result

_SENTINEL = object()


@dataclass
class AgentConfig:
    """Complete config for a single Agent, including LLM and tool information."""

    agent_id: int = 0
    agent_name: str = ''
    system_prompt: str = ''
    rules: list[str] = field(default_factory=list)
    provider_type: str = 'openai'
    api_base: str | None = None
    api_key_encrypted: str | None = None
    model_name: str = 'gpt-4'
    temperature: float = 0.7
    top_p: float | None = None
    max_tokens: int | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    tools: list[dict] = field(default_factory=list)
    tool_configs: dict = field(default_factory=dict)
    llm_provider_id: int | None = None
    rpm_limit: int | None = None
    tpm_limit: int | None = None
    builtin_tool_handlers: dict = field(default_factory=dict)
    enable_sub_agents: bool = False


@dataclass
class ConversationState:
    """Graph state: shared data flowing through the entire conversation graph."""

    system_prompt: str = ''
    rules: list[str] = field(default_factory=list)
    rag_context: str = ''
    provider_type: str = 'openai'
    api_base: str | None = None
    api_key_encrypted: str | None = None
    model_name: str = 'gpt-4'
    temperature: float = 0.7
    top_p: float | None = None
    max_tokens: int | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    llm_provider_id: int | None = None
    rpm_limit: int | None = None
    tpm_limit: int | None = None

    history: list[dict] = field(default_factory=list)
    user_input: str = ''

    tools: list[dict] = field(default_factory=list)
    tool_configs: dict = field(default_factory=dict)
    builtin_tool_handlers: dict = field(default_factory=dict)
    enable_sub_agents: bool = False

    response: str = ''
    usage: dict = field(default_factory=dict)
    _tool_rounds: int = 0

    # Multi-Agent collaboration fields
    agent_configs: list[dict] = field(default_factory=list)
    current_agent_id: int | None = None
    agent_outputs: dict = field(default_factory=dict)
    collaboration_mode: str = 'single'
    coordinator_prompt: str = ''
    max_coordination_rounds: int = 1
    _coordination_round: int = 0

    # DAG topology fields
    topology: dict | None = None
    node_outputs: dict = field(default_factory=dict)
    _condition_target: str = ''
    _dynamic_sub_agents: list = field(default_factory=list)
    _dynamic_results: dict = field(default_factory=dict)

    # Streaming callback (injected by run_graph_streaming)
    _stream_queue: Any = field(default=None, repr=False)

    # Tool call log (persisted to response_json)
    _tool_call_log: list[dict] = field(default_factory=list)


def _build_system_message_from_parts(
    system_prompt: str, rules: list[str], rag_context: str
) -> dict:
    parts = []
    if system_prompt:
        parts.append(system_prompt)
    if rules:
        parts.append('\n## Rules\n' + '\n'.join(f'- {r}' for r in rules))
    if rag_context:
        parts.append(rag_context)
    content = '\n\n'.join(parts) if parts else 'You are a helpful assistant.'
    return {'role': 'system', 'content': content}


def _optional_llm_params(obj: AgentConfig | ConversationState) -> dict:
    """Extract optional LLM parameters (top_p, presence_penalty, frequency_penalty) as kwargs."""
    params: dict = {}
    if obj.top_p is not None:
        params['top_p'] = obj.top_p
    if obj.presence_penalty is not None:
        params['presence_penalty'] = obj.presence_penalty
    if obj.frequency_penalty is not None:
        params['frequency_penalty'] = obj.frequency_penalty
    return params


def _sanitize_tool_messages(history: list[dict]) -> list[dict]:
    """Sanitize tool-related messages in history.

    1. Drop orphan 'tool' messages not linked to a preceding assistant with tool_calls.
    2. Strip tool_calls from assistant messages whose tool results are entirely missing.
    """
    pending_tool_ids: set[str] = set()
    cleaned: list[dict] = []
    for msg in history:
        if msg.get('role') == 'assistant' and msg.get('tool_calls'):
            pending_tool_ids = {tc['id'] for tc in msg['tool_calls'] if tc.get('id')}
            cleaned.append(msg)
        elif msg.get('role') == 'tool':
            tc_id = msg.get('tool_call_id')
            if tc_id and tc_id in pending_tool_ids:
                cleaned.append(msg)
                pending_tool_ids.discard(tc_id)
        else:
            pending_tool_ids = set()
            cleaned.append(msg)

    result: list[dict] = []
    for i, msg in enumerate(cleaned):
        if msg.get('role') == 'assistant' and msg.get('tool_calls'):
            expected_ids = {tc['id'] for tc in msg['tool_calls'] if tc.get('id')}
            found_ids = set()
            for later in cleaned[i + 1:]:
                if later.get('role') == 'tool' and later.get('tool_call_id') in expected_ids:
                    found_ids.add(later['tool_call_id'])
                elif later.get('role') != 'tool':
                    break
            if not found_ids:
                sanitized = {k: v for k, v in msg.items() if k != 'tool_calls'}
                result.append(sanitized)
                continue
        result.append(msg)
    return result


def _build_messages(state: ConversationState) -> list[dict]:
    messages = [
        _build_system_message_from_parts(
            state.system_prompt, state.rules, state.rag_context
        )
    ]
    messages.extend(_sanitize_tool_messages(state.history))
    if state.user_input:
        messages.append({'role': 'user', 'content': state.user_input})
    return messages


def _build_messages_for_agent(
    config: AgentConfig, history: list[dict], user_input: str, rag_context: str
) -> list[dict]:
    messages = [
        _build_system_message_from_parts(
            config.system_prompt, config.rules, rag_context
        )
    ]
    messages.extend(history)
    if user_input:
        messages.append({'role': 'user', 'content': user_input})
    return messages


def _build_openai_tools(tools: list[dict]) -> list[dict]:
    openai_tools = []
    for tool in tools:
        openai_tools.append({
            'type': 'function',
            'function': {
                'name': tool['name'],
                'description': tool.get('description', ''),
                'parameters': tool.get('input_schema', {}),
            },
        })
    return openai_tools


def _build_tool_call_history(message) -> list[dict]:
    assistant_msg: dict[str, Any] = {'role': 'assistant', 'content': message.content or ''}
    tool_calls_data = []
    for tc in message.tool_calls:
        tool_calls_data.append({
            'id': tc.id,
            'type': 'function',
            'function': {
                'name': tc.function.name,
                'arguments': tc.function.arguments,
            },
        })
    assistant_msg['tool_calls'] = tool_calls_data
    return [assistant_msg]


async def _push_event(state: ConversationState, event: dict) -> None:
    """Push an SSE event to the streaming queue."""
    if state._stream_queue is not None:
        await state._stream_queue.put(event)


# ---------------------------------------------------------------------------
# Single-Agent node (supports streaming output + tool call loop)
# ---------------------------------------------------------------------------

async def agent_node(state: ConversationState) -> dict[str, Any]:
    """Agent execution node: streams the LLM call, supports a tool call loop."""
    messages = _build_messages(state)

    if state._tool_rounds > 0:
        roles = [f"{m.get('role')}({'tc:' + str(len(m.get('tool_calls', []))) if m.get('tool_calls') else m.get('tool_call_id', '')[:8] if m.get('role') == 'tool' else ''})" for m in messages]
        log.debug(f'agent_node round={state._tool_rounds} messages=[{", ".join(roles)}]')

    kwargs: dict[str, Any] = _optional_llm_params(state)
    tool_defs = list(_build_openai_tools(state.tools)) if state.tools else []
    if state.enable_sub_agents:
        tool_defs.append(build_spawn_agent_tool_schema())
    if tool_defs:
        kwargs['tools'] = tool_defs

    full_content: list[str] = []
    tool_calls_raw: list = []
    usage: dict = {}
    call_status = 'success'
    error_msg: str | None = None
    t0 = time.monotonic()

    try:
        response = await acompletion(
            provider_type=state.provider_type,
            api_base=state.api_base,
            api_key_encrypted=state.api_key_encrypted,
            model_name=state.model_name,
            messages=messages,
            temperature=state.temperature,
            max_tokens=state.max_tokens,
            stream=True,
            stream_options={'include_usage': True},
            provider_id=state.llm_provider_id,
            rpm_limit=state.rpm_limit,
            **kwargs,
        )

        async for chunk in response:
            choices = chunk.choices
            if not choices:
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = _extract_usage(chunk.usage)
                continue
            delta = choices[0].delta

            if delta and delta.content:
                full_content.append(delta.content)
                await _push_event(state, {'type': 'token', 'content': delta.content})

            if delta and delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    while len(tool_calls_raw) <= idx:
                        tool_calls_raw.append({'id': '', 'function': {'name': '', 'arguments': ''}})
                    if tc_delta.id:
                        tool_calls_raw[idx]['id'] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_calls_raw[idx]['function']['name'] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_calls_raw[idx]['function']['arguments'] += tc_delta.function.arguments

            if hasattr(chunk, 'usage') and chunk.usage:
                usage = _extract_usage(chunk.usage)

        if not full_content and not tool_calls_raw:
            fallback = await acompletion(
                provider_type=state.provider_type,
                api_base=state.api_base,
                api_key_encrypted=state.api_key_encrypted,
                model_name=state.model_name,
                messages=messages,
                temperature=state.temperature,
                max_tokens=state.max_tokens,
                stream=False,
                provider_id=state.llm_provider_id,
                rpm_limit=state.rpm_limit,
                **kwargs,
            )
            choice = fallback.choices[0]
            msg = choice.message
            content = msg.content or ''
            if content:
                full_content.append(content)
                await _push_event(state, {'type': 'token', 'content': content})
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_raw.append({
                        'id': tc.id,
                        'function': {
                            'name': tc.function.name,
                            'arguments': tc.function.arguments,
                        },
                    })
            if fallback.usage:
                usage = _extract_usage(fallback.usage)
    except Exception as e:
        call_status = 'failed'
        error_msg = str(e)[:500]
        log.exception('agent_node LLM call failed')
        raise

    duration_ms = int((time.monotonic() - t0) * 1000)

    if tool_calls_raw and state._tool_rounds < MAX_TOOL_ROUNDS:
        assistant_msg: dict[str, Any] = {
            'role': 'assistant',
            'content': ''.join(full_content),
            'tool_calls': [
                {'id': tc['id'], 'type': 'function', 'function': tc['function']}
                for tc in tool_calls_raw
            ],
        }
        new_history = list(state.history)
        if state.user_input:
            new_history.append({'role': 'user', 'content': state.user_input})
        new_history.append(assistant_msg)
        return {
            'response': '',
            'usage': usage,
            'history': new_history,
            'user_input': '',
            '_tool_rounds': state._tool_rounds + 1,
        }

    await _push_event(state, {
        'type': 'usage',
        'model_name': state.model_name,
        'provider_type': state.provider_type,
        'status': call_status,
        'error_message': error_msg,
        'duration_ms': duration_ms,
        **usage,
    })

    return {'response': ''.join(full_content), 'usage': usage}


def _resolve_display_name(tool_name: str) -> str:
    """Resolve human-readable display name from builtin registry."""
    try:
        from backend.app.conversation.engine.builtin_tools import builtin_registry
        tool_def = builtin_registry.get(tool_name)
        if tool_def and tool_def.display_name:
            return tool_def.display_name
    except Exception:
        pass
    return ''


def _log_tool_call(
    state: ConversationState,
    tool_name: str,
    tool_type: str,
    arguments: dict,
    result_text: str,
    duration_ms: int,
    status: str = 'success',
    error: str | None = None,
) -> None:
    """Append a tool call record to the persistent log in state."""
    entry: dict[str, Any] = {
        'tool_name': tool_name,
        'tool_type': tool_type,
        'arguments': arguments,
        'result': result_text[:1000],
        'duration_ms': duration_ms,
        'status': status,
        'round': state._tool_rounds,
    }
    display_name = _resolve_display_name(tool_name)
    if display_name:
        entry['display_name'] = display_name
    if error:
        entry['error'] = error[:500]
    state._tool_call_log.append(entry)
    log.info(f'Tool call: {tool_name}({tool_type}) round={state._tool_rounds} {status} {duration_ms}ms result_len={len(result_text)}')


async def _execute_tool_call(
    state: ConversationState,
    tool_name: str,
    arguments: dict,
) -> str:
    """Unified tool execution router: builtin tools call Python directly, MCP tools go
    through the MCP protocol, spawn_agent dynamically generates a sub-agent."""
    t0 = time.monotonic()

    if tool_name == 'spawn_agent':
        parent_cfg = AgentConfig(
            provider_type=state.provider_type,
            api_base=state.api_base,
            api_key_encrypted=state.api_key_encrypted,
            model_name=state.model_name,
            temperature=state.temperature,
            max_tokens=state.max_tokens,
            top_p=state.top_p,
            presence_penalty=state.presence_penalty,
            frequency_penalty=state.frequency_penalty,
        )
        result = await execute_dynamic_sub_agent(parent_cfg, arguments, state)
        _log_tool_call(state, tool_name, 'spawn_agent', arguments, result, int((time.monotonic() - t0) * 1000))
        return result

    display_name = _resolve_display_name(tool_name)

    builtin_handler = state.builtin_tool_handlers.get(tool_name)
    if builtin_handler:
        try:
            await _push_event(state, {
                'type': 'tool_call',
                'tool_name': tool_name,
                'tool_type': 'builtin',
                'display_name': display_name,
                'arguments': arguments,
            })
            result = await builtin_handler(**arguments)
            result_text = str(result)
            ms = int((time.monotonic() - t0) * 1000)
            await _push_event(state, {
                'type': 'tool_result',
                'tool_name': tool_name,
                'tool_type': 'builtin',
                'display_name': display_name,
                'result': result_text[:500],
            })
            _log_tool_call(state, tool_name, 'builtin', arguments, result_text, ms)
            return result_text
        except Exception as e:
            ms = int((time.monotonic() - t0) * 1000)
            log.exception(f'Builtin tool call failed: {tool_name}')
            _log_tool_call(state, tool_name, 'builtin', arguments, '', ms, 'error', str(e))
            return f'Error calling builtin tool {tool_name}'

    mcp_config = state.tool_configs.get(tool_name, {})
    if mcp_config:
        try:
            from backend.app.mcp.service.mcp_client import call_tool

            await _push_event(state, {
                'type': 'tool_call',
                'tool_name': tool_name,
                'tool_type': 'mcp',
                'display_name': display_name,
                'arguments': arguments,
            })
            result = await call_tool(
                mcp_config['transport_type'],
                mcp_config['connection_config'],
                tool_name,
                arguments,
            )
            result_text = str(result)
            ms = int((time.monotonic() - t0) * 1000)
            await _push_event(state, {
                'type': 'tool_result',
                'tool_name': tool_name,
                'tool_type': 'mcp',
                'display_name': display_name,
                'result': result_text[:500],
            })
            _log_tool_call(state, tool_name, 'mcp', arguments, result_text, ms)
            return result_text
        except Exception as e:
            ms = int((time.monotonic() - t0) * 1000)
            log.exception(f'MCP tool call failed: {tool_name}')
            _log_tool_call(state, tool_name, 'mcp', arguments, '', ms, 'error', str(e))
            return f'Error calling tool {tool_name}'

    _log_tool_call(state, tool_name, 'unknown', arguments, '', 0, 'not_configured')
    return f'Tool {tool_name} not configured'


async def tool_node(state: ConversationState) -> dict[str, Any]:
    """Tool execution node: routes to a builtin tool or an MCP tool."""
    last_assistant = None
    for msg in reversed(state.history):
        if msg.get('role') == 'assistant' and msg.get('tool_calls'):
            last_assistant = msg
            break

    if not last_assistant or not last_assistant.get('tool_calls'):
        return {}

    tool_results = []
    for tc in last_assistant['tool_calls']:
        tool_name = tc['function']['name']
        try:
            arguments = json.loads(tc['function']['arguments'])
        except (json.JSONDecodeError, TypeError):
            arguments = {}

        result_text = await _execute_tool_call(state, tool_name, arguments)

        tool_results.append({
            'role': 'tool',
            'tool_call_id': tc['id'],
            'content': result_text,
        })

    return {'history': state.history + tool_results}


def _should_call_tools(state: ConversationState) -> str:
    if not state.tools and not state.builtin_tool_handlers:
        return END
    last_assistant_idx = -1
    for i in range(len(state.history) - 1, -1, -1):
        if state.history[i].get('role') == 'assistant' and state.history[i].get('tool_calls'):
            last_assistant_idx = i
            break
    if last_assistant_idx < 0:
        return END
    expected_ids = {tc['id'] for tc in state.history[last_assistant_idx]['tool_calls']}
    found_ids = set()
    for msg in state.history[last_assistant_idx + 1:]:
        if msg.get('role') == 'tool' and msg.get('tool_call_id') in expected_ids:
            found_ids.add(msg['tool_call_id'])
    if found_ids >= expected_ids:
        return END
    return 'tool'


# ---------------------------------------------------------------------------
# Multi-Agent node
# ---------------------------------------------------------------------------

async def _execute_agent_tool_calls(
    cfg: AgentConfig,
    tool_calls_raw: list[dict],
    state: ConversationState,
) -> list[str]:
    """Execute tool calls for an agent, returning result text lines."""
    results: list[str] = []
    for tc in tool_calls_raw:
        tool_name = tc['function']['name']
        try:
            arguments = json.loads(tc['function']['arguments'])
        except (json.JSONDecodeError, TypeError):
            arguments = {}

        if tool_name == 'spawn_agent':
            result = await execute_dynamic_sub_agent(cfg, arguments, state)
            results.append(f'[SubAgent: {arguments.get("name", "?")}] {result}')
            continue

        builtin_h = cfg.builtin_tool_handlers.get(tool_name)
        tc_config = cfg.tool_configs.get(tool_name, {})
        if builtin_h:
            try:
                await _push_event(state, {
                    'type': 'tool_call', 'tool_name': tool_name,
                    'tool_type': 'builtin', 'agent_id': cfg.agent_id,
                })
                result = await builtin_h(**arguments)
                results.append(f'[Tool: {tool_name}] {result}')
            except Exception:
                log.exception(f'Agent builtin tool failed: {tool_name}')
                results.append(f'[Tool: {tool_name}] Error')
        elif tc_config:
            try:
                from backend.app.mcp.service.mcp_client import call_tool
                await _push_event(state, {
                    'type': 'tool_call', 'tool_name': tool_name,
                    'tool_type': 'mcp', 'agent_id': cfg.agent_id,
                })
                result = await call_tool(
                    tc_config['transport_type'],
                    tc_config['connection_config'],
                    tool_name,
                    arguments,
                )
                results.append(f'[Tool: {tool_name}] {result}')
            except Exception:
                log.exception(f'Agent MCP tool call failed: {tool_name}')
                results.append(f'[Tool: {tool_name}] Error')
    return results


async def _agent_llm_with_tool_loop(
    cfg: AgentConfig,
    messages: list[dict],
    state: ConversationState,
    *,
    event_extra: dict | None = None,
) -> tuple[str, dict]:
    """Run an agent's LLM call with multi-round tool calling loop.

    Returns (output_text, cumulative_usage).
    """
    extra = event_extra or {}
    kwargs: dict[str, Any] = _optional_llm_params(cfg)
    has_tools = cfg.tools or cfg.tool_configs or cfg.builtin_tool_handlers or cfg.enable_sub_agents
    tool_defs = list(_build_openai_tools(cfg.tools)) if cfg.tools else []
    if cfg.enable_sub_agents:
        tool_defs.append(build_spawn_agent_tool_schema())
    if tool_defs:
        kwargs['tools'] = tool_defs

    cumulative_usage: dict = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0, 'cached_tokens': 0, 'reasoning_tokens': 0}

    for _round in range(MAX_TOOL_ROUNDS):
        full_content: list[str] = []
        tool_calls_raw: list = []
        usage: dict = {}

        response = await acompletion(
            provider_type=cfg.provider_type,
            api_base=cfg.api_base,
            api_key_encrypted=cfg.api_key_encrypted,
            model_name=cfg.model_name,
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            stream=True,
            stream_options={'include_usage': True},
            provider_id=cfg.llm_provider_id,
            rpm_limit=cfg.rpm_limit,
            **kwargs,
        )

        async for chunk in response:
            choices = chunk.choices
            if not choices:
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = _extract_usage(chunk.usage)
                continue
            delta = choices[0].delta
            if delta and delta.content:
                full_content.append(delta.content)
                await _push_event(state, {'type': 'token', 'content': delta.content, **extra})
            if delta and delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    while len(tool_calls_raw) <= idx:
                        tool_calls_raw.append({'id': '', 'function': {'name': '', 'arguments': ''}})
                    if tc_delta.id:
                        tool_calls_raw[idx]['id'] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_calls_raw[idx]['function']['name'] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_calls_raw[idx]['function']['arguments'] += tc_delta.function.arguments
            if hasattr(chunk, 'usage') and chunk.usage:
                usage = _extract_usage(chunk.usage)

        if not full_content and not tool_calls_raw:
            fallback = await acompletion(
                provider_type=cfg.provider_type,
                api_base=cfg.api_base,
                api_key_encrypted=cfg.api_key_encrypted,
                model_name=cfg.model_name,
                messages=messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                stream=False,
                provider_id=cfg.llm_provider_id,
                rpm_limit=cfg.rpm_limit,
                **kwargs,
            )
            msg = fallback.choices[0].message
            if msg.content:
                full_content.append(msg.content)
                await _push_event(state, {'type': 'token', 'content': msg.content, **extra})
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_raw.append({
                        'id': tc.id,
                        'function': {'name': tc.function.name, 'arguments': tc.function.arguments},
                    })
            if fallback.usage:
                usage = _extract_usage(fallback.usage)

        for k in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'cached_tokens', 'reasoning_tokens'):
            cumulative_usage[k] = cumulative_usage.get(k, 0) + usage.get(k, 0)

        if not tool_calls_raw or not has_tools:
            return ''.join(full_content), cumulative_usage

        tool_results = await _execute_agent_tool_calls(cfg, tool_calls_raw, state)
        if not tool_results:
            return ''.join(full_content), cumulative_usage

        assistant_content = ''.join(full_content)
        messages.append({
            'role': 'assistant',
            'content': assistant_content,
            'tool_calls': [
                {'id': tc['id'], 'type': 'function', 'function': tc['function']}
                for tc in tool_calls_raw
            ],
        })
        for i, tc in enumerate(tool_calls_raw):
            messages.append({
                'role': 'tool',
                'tool_call_id': tc['id'],
                'content': tool_results[i] if i < len(tool_results) else '',
            })

    return ''.join(full_content) if full_content else '', cumulative_usage


def _make_agent_executor(config_index: int) -> Callable:
    """Create an execution closure for the given agent_config, used as a graph node."""

    async def _agent_exec(state: ConversationState) -> dict[str, Any]:
        if config_index >= len(state.agent_configs):
            return {}

        cfg = AgentConfig(**state.agent_configs[config_index])
        messages = _build_messages_for_agent(
            cfg, state.history, state.user_input, state.rag_context
        )

        await _push_event(state, {
            'type': 'agent_start',
            'agent_id': cfg.agent_id,
            'agent_name': cfg.agent_name,
        })

        call_status = 'success'
        error_msg: str | None = None
        t0 = time.monotonic()

        try:
            output_text, usage = await _agent_llm_with_tool_loop(
                cfg, messages, state,
                event_extra={'agent_id': cfg.agent_id},
            )
        except Exception as e:
            call_status = 'failed'
            error_msg = str(e)[:500]
            output_text = ''
            usage = {}
            log.exception(f'Multi-agent executor failed: {cfg.agent_name}')

        duration_ms = int((time.monotonic() - t0) * 1000)

        await _push_event(state, {
            'type': 'usage',
            'agent_id': cfg.agent_id,
            'agent_name': cfg.agent_name,
            'model_name': cfg.model_name,
            'provider_type': cfg.provider_type,
            'status': call_status,
            'error_message': error_msg,
            'duration_ms': duration_ms,
            **usage,
        })

        agent_outputs = dict(state.agent_outputs)
        agent_outputs[cfg.agent_id] = output_text

        await _push_event(state, {
            'type': 'agent_end',
            'agent_id': cfg.agent_id,
            'agent_name': cfg.agent_name,
        })

        return {'agent_outputs': agent_outputs}

    return _agent_exec


async def router_node(state: ConversationState) -> dict[str, Any]:
    """Router node: decides the execution path based on the number of agents and the collaboration mode."""
    return {}


def _route_decision(state: ConversationState) -> str:
    configs = state.agent_configs
    mode = state.collaboration_mode

    if not configs or len(configs) <= 1 or mode == 'single':
        return 'single_agent'

    return 'parallel_start'


async def coordinator_node(state: ConversationState) -> dict[str, Any]:
    """Coordinator node (ForumEngine "idea clash"): analyzes each Agent's output, identifies biases and
    blind spots, and produces a synthesis.
    Supports multi-round iterative coordination: when max_coordination_rounds > 1, the coordinator can
    judge whether the analysis is sufficient; if not, it emits a [NEEDS_MORE] prefix plus follow-up
    instructions, triggering the agents to run again.
    """
    if not state.agent_outputs:
        return {'response': ''}

    current_round = state._coordination_round + 1
    max_rounds = state.max_coordination_rounds

    agent_sections = []
    for cfg_dict in state.agent_configs:
        aid = cfg_dict.get('agent_id', 0)
        aname = cfg_dict.get('agent_name', f'Agent {aid}')
        output = state.agent_outputs.get(aid, '')
        if output:
            agent_sections.append(f'## {aname}\n{output}')

    combined = '\n\n---\n\n'.join(agent_sections)

    base_system = state.coordinator_prompt or (
        'You are a coordinator synthesizing multiple expert analyses. '
        'Review each expert\'s output below. Identify key agreements, contradictions, '
        'potential blind spots, and biases. Produce a comprehensive, balanced synthesis '
        'that integrates the strongest insights from all experts.'
    )

    if max_rounds > 1 and current_round < max_rounds:
        coordinator_system = (
            f'{base_system}\n\n'
            f'This is coordination round {current_round}/{max_rounds}. '
            'After reviewing the analyses, decide:\n'
            '1. If the analyses are comprehensive enough, produce your final synthesis directly.\n'
            '2. If important gaps remain, start your response with "[NEEDS_MORE]" on its own line, '
            'then provide specific follow-up questions or instructions for the experts. '
            'The experts will then provide additional analysis.'
        )
    else:
        coordinator_system = base_system

    messages = [
        {'role': 'system', 'content': coordinator_system},
        {'role': 'user', 'content': f'Here are the expert analyses:\n\n{combined}\n\nPlease synthesize these into a comprehensive response.'},
    ]

    cfg = AgentConfig(**state.agent_configs[0]) if state.agent_configs else AgentConfig()

    await _push_event(state, {
        'type': 'coordinator_start',
        'round': current_round,
        'max_rounds': max_rounds,
    })

    full_content: list[str] = []
    usage: dict = {}
    call_status = 'success'
    error_msg: str | None = None
    t0 = time.monotonic()

    try:
        response = await acompletion(
            provider_type=cfg.provider_type,
            api_base=cfg.api_base,
            api_key_encrypted=cfg.api_key_encrypted,
            model_name=cfg.model_name,
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            stream=True,
            stream_options={'include_usage': True},
            provider_id=cfg.llm_provider_id,
            rpm_limit=cfg.rpm_limit,
        )

        async for chunk in response:
            choices = chunk.choices
            if not choices:
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = _extract_usage(chunk.usage)
                continue
            delta = choices[0].delta
            if delta and delta.content:
                full_content.append(delta.content)
                await _push_event(state, {'type': 'token', 'content': delta.content})
            if hasattr(chunk, 'usage') and chunk.usage:
                usage = _extract_usage(chunk.usage)

        if not full_content:
            fallback = await acompletion(
                provider_type=cfg.provider_type,
                api_base=cfg.api_base,
                api_key_encrypted=cfg.api_key_encrypted,
                model_name=cfg.model_name,
                messages=messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                stream=False,
                provider_id=cfg.llm_provider_id,
                rpm_limit=cfg.rpm_limit,
            )
            content = fallback.choices[0].message.content or ''
            if content:
                full_content.append(content)
                await _push_event(state, {'type': 'token', 'content': content})
            if fallback.usage:
                usage = _extract_usage(fallback.usage)
    except Exception as e:
        call_status = 'failed'
        error_msg = str(e)[:500]
        log.exception('coordinator_node LLM call failed')

    duration_ms = int((time.monotonic() - t0) * 1000)

    await _push_event(state, {
        'type': 'usage',
        'role': 'coordinator',
        'model_name': cfg.model_name,
        'provider_type': cfg.provider_type,
        'status': call_status,
        'error_message': error_msg,
        'duration_ms': duration_ms,
        **usage,
    })

    result_text = ''.join(full_content)
    updates: dict[str, Any] = {'_coordination_round': current_round}

    if result_text.startswith('[NEEDS_MORE]') and current_round < max_rounds:
        follow_up = result_text[len('[NEEDS_MORE]'):].strip()
        await _push_event(state, {
            'type': 'coordinator_followup',
            'round': current_round,
            'content': follow_up,
        })
        updates['user_input'] = follow_up
        updates['agent_outputs'] = {}
        updates['response'] = result_text
    else:
        if result_text.startswith('[NEEDS_MORE]'):
            result_text = result_text[len('[NEEDS_MORE]'):].strip()
        updates['response'] = result_text

    await _push_event(state, {'type': 'coordinator_end', 'round': current_round})

    return updates


async def aggregator_node(state: ConversationState) -> dict[str, Any]:
    """Aggregator node ("late integration"): merges each Agent's output and produces a brief summary."""
    if not state.agent_outputs:
        return {'response': ''}

    agent_sections = []
    for cfg_dict in state.agent_configs:
        aid = cfg_dict.get('agent_id', 0)
        aname = cfg_dict.get('agent_name', f'Agent {aid}')
        output = state.agent_outputs.get(aid, '')
        if output:
            agent_sections.append(f'### {aname}\n{output}')

    combined = '\n\n'.join(agent_sections)

    cfg = AgentConfig(**state.agent_configs[0]) if state.agent_configs else AgentConfig()

    summary_messages = [
        {'role': 'system', 'content': 'Summarize the following expert analyses into a concise, actionable conclusion. Preserve key details from each expert.'},
        {'role': 'user', 'content': combined},
    ]

    await _push_event(state, {'type': 'aggregator_start'})

    full_content: list[str] = []
    usage: dict = {}
    call_status = 'success'
    error_msg: str | None = None
    t0 = time.monotonic()

    try:
        response = await acompletion(
            provider_type=cfg.provider_type,
            api_base=cfg.api_base,
            api_key_encrypted=cfg.api_key_encrypted,
            model_name=cfg.model_name,
            messages=summary_messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            stream=True,
            stream_options={'include_usage': True},
            provider_id=cfg.llm_provider_id,
            rpm_limit=cfg.rpm_limit,
        )

        async for chunk in response:
            choices = chunk.choices
            if not choices:
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = _extract_usage(chunk.usage)
                continue
            delta = choices[0].delta
            if delta and delta.content:
                full_content.append(delta.content)
                await _push_event(state, {'type': 'token', 'content': delta.content})
            if hasattr(chunk, 'usage') and chunk.usage:
                usage = _extract_usage(chunk.usage)

        if not full_content:
            fallback = await acompletion(
                provider_type=cfg.provider_type,
                api_base=cfg.api_base,
                api_key_encrypted=cfg.api_key_encrypted,
                model_name=cfg.model_name,
                messages=summary_messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                stream=False,
                provider_id=cfg.llm_provider_id,
                rpm_limit=cfg.rpm_limit,
            )
            content = fallback.choices[0].message.content or ''
            if content:
                full_content.append(content)
                await _push_event(state, {'type': 'token', 'content': content})
            if fallback.usage:
                usage = _extract_usage(fallback.usage)
    except Exception as e:
        call_status = 'failed'
        error_msg = str(e)[:500]
        log.exception('aggregator_node LLM call failed')

    duration_ms = int((time.monotonic() - t0) * 1000)

    await _push_event(state, {
        'type': 'usage',
        'role': 'aggregator',
        'model_name': cfg.model_name,
        'provider_type': cfg.provider_type,
        'status': call_status,
        'error_message': error_msg,
        'duration_ms': duration_ms,
        **usage,
    })

    await _push_event(state, {'type': 'aggregator_end'})

    return {'response': ''.join(full_content)}


def build_spawn_agent_tool_schema() -> dict:
    """Build the OpenAI function-calling schema for the spawn_agent tool."""
    return {
        'type': 'function',
        'function': {
            'name': 'spawn_agent',
            'description': (
                'Dynamically create and execute a sub-agent to handle a specific subtask. '
                'The sub-agent will use the same LLM provider as the caller. '
                'Use this when the current task can be decomposed into independent subtasks '
                'that benefit from specialized handling.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'description': 'A descriptive name for the sub-agent (e.g. "Code Reviewer", "Data Analyst")',
                    },
                    'system_prompt': {
                        'type': 'string',
                        'description': 'The system prompt defining the sub-agent\'s role and expertise',
                    },
                    'task': {
                        'type': 'string',
                        'description': 'The specific task or question for the sub-agent to handle',
                    },
                },
                'required': ['name', 'system_prompt', 'task'],
            },
        },
    }


async def execute_dynamic_sub_agent(
    parent_cfg: AgentConfig,
    sub_agent_def: dict,
    state: ConversationState,
) -> str:
    """Execute a dynamically spawned sub-agent using the parent's LLM config."""
    name = sub_agent_def.get('name', 'SubAgent')
    system_prompt = sub_agent_def.get('system_prompt', '')
    task = sub_agent_def.get('task', '')

    sub_cfg = AgentConfig(
        agent_id=0,
        agent_name=name,
        system_prompt=system_prompt,
        provider_type=parent_cfg.provider_type,
        api_base=parent_cfg.api_base,
        api_key_encrypted=parent_cfg.api_key_encrypted,
        model_name=parent_cfg.model_name,
        temperature=parent_cfg.temperature,
        max_tokens=parent_cfg.max_tokens,
        top_p=parent_cfg.top_p,
        presence_penalty=parent_cfg.presence_penalty,
        frequency_penalty=parent_cfg.frequency_penalty,
        llm_provider_id=parent_cfg.llm_provider_id,
        rpm_limit=parent_cfg.rpm_limit,
        tpm_limit=parent_cfg.tpm_limit,
    )

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': task},
    ]

    await _push_event(state, {
        'type': 'sub_agent_start',
        'agent_name': name,
        'task': task[:200],
    })

    call_status = 'success'
    error_msg: str | None = None
    t0 = time.monotonic()

    try:
        output_text, usage = await _agent_llm_with_tool_loop(
            sub_cfg, messages, state,
            event_extra={'agent_name': name, 'is_sub_agent': True},
        )
    except Exception as e:
        call_status = 'failed'
        error_msg = str(e)[:500]
        output_text = f'[SubAgent {name} failed: {error_msg}]'
        usage = {}
        log.exception(f'Dynamic sub-agent failed: {name}')

    duration_ms = int((time.monotonic() - t0) * 1000)

    await _push_event(state, {
        'type': 'usage',
        'agent_name': name,
        'model_name': sub_cfg.model_name,
        'provider_type': sub_cfg.provider_type,
        'status': call_status,
        'error_message': error_msg,
        'duration_ms': duration_ms,
        'is_sub_agent': True,
        **usage,
    })

    await _push_event(state, {
        'type': 'sub_agent_end',
        'agent_name': name,
    })

    return output_text


async def dynamic_sub_agent_node(state: ConversationState) -> dict[str, Any]:
    """Execute all dynamically spawned sub-agents in parallel, merge results."""
    if not state._dynamic_sub_agents:
        return {}

    parent_cfg = AgentConfig(**state.agent_configs[0]) if state.agent_configs else AgentConfig()

    tasks = [
        execute_dynamic_sub_agent(parent_cfg, sub_def, state)
        for sub_def in state._dynamic_sub_agents
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    dynamic_results = dict(state._dynamic_results)
    for i, (sub_def, result) in enumerate(zip(state._dynamic_sub_agents, results)):
        name = sub_def.get('name', f'SubAgent_{i}')
        if isinstance(result, Exception):
            dynamic_results[name] = f'[Error: {str(result)[:200]}]'
        else:
            dynamic_results[name] = result

    return {
        '_dynamic_results': dynamic_results,
        '_dynamic_sub_agents': [],
    }


async def _parallel_dispatch(state: ConversationState) -> dict[str, Any]:
    """Run all Agents in parallel and collect their outputs."""
    tasks = []
    for i in range(len(state.agent_configs)):
        executor = _make_agent_executor(i)
        tasks.append(executor(state))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    merged_outputs: dict = {}
    for result in results:
        if isinstance(result, Exception):
            log.exception('Agent execution failed', exc_info=result)
            continue
        if isinstance(result, dict) and 'agent_outputs' in result:
            merged_outputs.update(result['agent_outputs'])

    return {'agent_outputs': merged_outputs}


def _route_after_parallel(state: ConversationState) -> str:
    if state.collaboration_mode == 'parallel_coordinate':
        return 'coordinator'
    return 'aggregator'


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_single_agent_graph() -> Any:
    """Build a single-Agent conversation graph supporting tool calls + streaming output."""
    graph = StateGraph(ConversationState)
    graph.add_node('agent', agent_node)
    graph.add_node('tool', tool_node)
    graph.set_entry_point('agent')
    graph.add_conditional_edges('agent', _should_call_tools, {END: END, 'tool': 'tool'})
    graph.add_edge('tool', 'agent')
    return graph.compile()


def build_multi_agent_graph() -> Any:
    """Build a multi-Agent collaboration graph: router -> parallel -> coordinator/aggregator."""
    graph = StateGraph(ConversationState)

    graph.add_node('router', router_node)
    graph.add_node('single_agent', agent_node)
    graph.add_node('single_tool', tool_node)
    graph.add_node('parallel', _parallel_dispatch)
    graph.add_node('coordinator', coordinator_node)
    graph.add_node('aggregator', aggregator_node)

    graph.set_entry_point('router')

    graph.add_conditional_edges('router', _route_decision, {
        'single_agent': 'single_agent',
        'parallel_start': 'parallel',
    })

    graph.add_conditional_edges('single_agent', _should_call_tools, {
        END: END,
        'tool': 'single_tool',
    })
    graph.add_edge('single_tool', 'single_agent')

    graph.add_conditional_edges('parallel', _route_after_parallel, {
        'coordinator': 'coordinator',
        'aggregator': 'aggregator',
    })

    def _should_iterate_coordination(state: ConversationState) -> str:
        if (
            state.max_coordination_rounds > 1
            and state._coordination_round < state.max_coordination_rounds
            and state.response
            and state.response.startswith('[NEEDS_MORE]')
        ):
            return 'parallel'
        return END

    graph.add_conditional_edges('coordinator', _should_iterate_coordination, {
        'parallel': 'parallel',
        END: END,
    })
    graph.add_edge('aggregator', END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Streaming execution bridge
# ---------------------------------------------------------------------------

async def run_graph_streaming(
    initial_state: ConversationState,
    *,
    multi_agent: bool = False,
    dag_graph: Any = None,
) -> AsyncGenerator[dict, None]:
    """
    Execute the LangGraph graph and stream out SSE events.

    Uses asyncio.Queue as the bridge between graph execution and the SSE stream:
    - graph nodes push events through state._stream_queue
    - this function yields events from the queue
    """
    queue: asyncio.Queue = asyncio.Queue()
    initial_state._stream_queue = queue

    if dag_graph is not None:
        graph = dag_graph
    elif multi_agent:
        graph = build_multi_agent_graph()
    else:
        graph = build_single_agent_graph()

    async def _run():
        try:
            await graph.ainvoke(initial_state)
        except Exception:
            log.exception('Graph execution failed')
            await queue.put({'type': 'error', 'content': 'Graph execution failed'})
        finally:
            await queue.put(_SENTINEL)

    task = asyncio.create_task(_run())

    try:
        while True:
            event = await queue.get()
            if event is _SENTINEL:
                break
            yield event
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
