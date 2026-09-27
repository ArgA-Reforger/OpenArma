"""LiteLLM wrapper providing a unified LLM call interface."""

import asyncio
import time

from collections import deque
from collections.abc import AsyncGenerator, Generator

import litellm

from backend.app.llm.service.llm_provider_service import _decrypt_api_key

_rpm_windows: dict[int, deque[float]] = {}
_rpm_lock = asyncio.Lock()


async def _wait_for_rpm(provider_id: int | None, rpm_limit: int | None) -> None:
    """Sliding-window RPM limiter.  Blocks until a request slot is available."""
    if not provider_id or not rpm_limit or rpm_limit <= 0:
        return
    async with _rpm_lock:
        window = _rpm_windows.setdefault(provider_id, deque())
        now = time.monotonic()
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= rpm_limit:
            wait = 60.0 - (now - window[0])
            if wait > 0:
                await asyncio.sleep(wait)
                now = time.monotonic()
                while window and now - window[0] >= 60:
                    window.popleft()
        window.append(time.monotonic())


def _build_model_string(provider_type: str, model_name: str) -> str:
    """
    Build the LiteLLM model string

    :param provider_type: provider type
    :param model_name: model name
    :return: LiteLLM model string
    """
    provider_prefix_map = {
        'openai': '',
        'anthropic': 'anthropic/',
        'deepseek': 'deepseek/',
        'ollama': 'ollama/',
        'openai_compatible': 'openai/',
    }
    prefix = provider_prefix_map.get(provider_type, 'openai/')
    return f'{prefix}{model_name}' if prefix else model_name


def completion(
    *,
    provider_type: str,
    api_base: str | None,
    api_key_encrypted: str | None,
    model_name: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int | None = None,
    stream: bool = False,
    provider_id: int | None = None,
    rpm_limit: int | None = None,
    **kwargs,
):
    """Synchronous LLM call interface (RPM rate limiting requires manually awaiting _wait_for_rpm before the call)"""
    api_key = _decrypt_api_key(api_key_encrypted) if api_key_encrypted else None
    model = _build_model_string(provider_type, model_name)

    params: dict = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'stream': stream,
        'drop_params': True,
        **kwargs,
    }
    if api_key:
        params['api_key'] = api_key
    if api_base:
        params['api_base'] = api_base
    if max_tokens:
        params['max_tokens'] = max_tokens

    return litellm.completion(**params)


async def acompletion(
    *,
    provider_type: str,
    api_base: str | None,
    api_key_encrypted: str | None,
    model_name: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int | None = None,
    stream: bool = False,
    provider_id: int | None = None,
    rpm_limit: int | None = None,
    **kwargs,
):
    """Asynchronous LLM call interface, automatically respects RPM rate limiting."""
    await _wait_for_rpm(provider_id, rpm_limit)

    api_key = _decrypt_api_key(api_key_encrypted) if api_key_encrypted else None
    model = _build_model_string(provider_type, model_name)

    params: dict = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'stream': stream,
        'drop_params': True,
        **kwargs,
    }
    if api_key:
        params['api_key'] = api_key
    if api_base:
        params['api_base'] = api_base
    if max_tokens:
        params['max_tokens'] = max_tokens

    return await litellm.acompletion(**params)


def completion_stream(
    *,
    provider_type: str,
    api_base: str | None,
    api_key_encrypted: str | None,
    model_name: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int | None = None,
    **kwargs,
) -> Generator[str, None, None]:
    """
    Synchronous streaming LLM call, returns content token by token

    :param provider_type: provider type
    :param api_base: API base URL
    :param api_key_encrypted: encrypted API key
    :param model_name: model name
    :param messages: message list
    :param temperature: temperature
    :param max_tokens: maximum number of tokens
    :return: content generator
    """
    response = completion(
        provider_type=provider_type,
        api_base=api_base,
        api_key_encrypted=api_key_encrypted,
        model_name=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        **kwargs,
    )
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


async def acompletion_stream(
    *,
    provider_type: str,
    api_base: str | None,
    api_key_encrypted: str | None,
    model_name: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int | None = None,
    **kwargs,
) -> AsyncGenerator[str, None]:
    """
    Asynchronous streaming LLM call, returns content token by token.
    If the streamed response is empty, automatically falls back to a non-streaming call.
    """
    response = await acompletion(
        provider_type=provider_type,
        api_base=api_base,
        api_key_encrypted=api_key_encrypted,
        model_name=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        **kwargs,
    )
    has_content = False
    async for chunk in response:
        choices = chunk.choices
        if not choices:
            continue
        delta = choices[0].delta
        if delta and delta.content:
            has_content = True
            yield delta.content

    if not has_content:
        fallback = await acompletion(
            provider_type=provider_type,
            api_base=api_base,
            api_key_encrypted=api_key_encrypted,
            model_name=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **kwargs,
        )
        content = fallback.choices[0].message.content
        if content:
            yield content
