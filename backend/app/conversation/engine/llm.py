"""LiteLLM 封装，提供统一 LLM 调用接口。"""

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
    构建 LiteLLM 模型字符串

    :param provider_type: 服务商类型
    :param model_name: 模型名称
    :return: LiteLLM 模型字符串
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
    """同步 LLM 调用接口（RPM 限速需在调用前手动 await _wait_for_rpm）"""
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
    """异步 LLM 调用接口，自动遵守 RPM 限速。"""
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
    同步流式 LLM 调用，逐 token 返回内容

    :param provider_type: 服务商类型
    :param api_base: API 基础地址
    :param api_key_encrypted: 加密后的 API Key
    :param model_name: 模型名称
    :param messages: 消息列表
    :param temperature: 温度
    :param max_tokens: 最大 token 数
    :return: 内容生成器
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
    异步流式 LLM 调用，逐 token 返回内容。
    如果流式返回空内容，自动 fallback 到非流式调用。
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
