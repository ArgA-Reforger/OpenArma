import asyncio
import sys

import pytest

from backend.app.conversation.engine import claude_sdk

pytestmark = pytest.mark.skipif(sys.platform != 'win32', reason='Windows selector loops cannot spawn subprocesses')


def _query_loop_type(monkeypatch: pytest.MonkeyPatch, caller_loop: asyncio.AbstractEventLoop) -> type:
    loops: list[type] = []

    async def fake_query_text(**_: object) -> tuple[str, dict]:
        await asyncio.sleep(0)
        loops.append(type(asyncio.get_running_loop()))
        return 'ok', {}

    monkeypatch.setattr(claude_sdk, '_query_text', fake_query_text)
    monkeypatch.setattr(claude_sdk.settings, 'CLAUDE_SDK_TIMEOUT_SECONDS', 5)
    try:
        caller_loop.run_until_complete(
            claude_sdk.claude_sdk_completion(
                model_name='claude-haiku-5-5',
                messages=[{'role': 'user', 'content': 'hi'}],
                think=False,
                effort='low',
            )
        )
    finally:
        caller_loop.close()
    return loops[0]


def test_query_runs_on_a_subprocess_capable_loop_when_called_from_a_selector_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _query_loop_type(monkeypatch, asyncio.SelectorEventLoop()) is asyncio.ProactorEventLoop


def test_query_keeps_the_current_loop_when_it_can_spawn_subprocesses(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _query_loop_type(monkeypatch, asyncio.ProactorEventLoop()) is asyncio.ProactorEventLoop
