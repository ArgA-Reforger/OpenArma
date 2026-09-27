"""Operator-visible strings (builtin tool display names, plugin manifests,
geo-IP locale, Redis cache clearing on init) must be Spanish, not Chinese.

LLM-facing text (tool `description` / `input_schema` descriptions / prompts)
is explicitly out of scope for this slice and is not checked here.
"""

import re

from pathlib import Path

import pytest
import rtoml

from backend.app.builtin_tool.service.seed import SYSTEM_TOOLS
from backend.core.path_conf import BASE_PATH

REPO_ROOT = BASE_PATH.parent

# Build the CJK range without embedding literal CJK characters in this file.
CJK_RE_CHARS = f'{chr(0x4E00)}-{chr(0x9FFF)}{chr(0x3400)}-{chr(0x4DBF)}'
CJK_RE = re.compile(f'[{CJK_RE_CHARS}]')


def _has_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text))


# ---------------------------------------------------------------------------
# 1. Builtin tool display names (seed.py + registries)
# ---------------------------------------------------------------------------


def test_seed_display_names_are_non_empty_and_cjk_free() -> None:
    findings = []
    for tool in SYSTEM_TOOLS:
        display_name = tool.get('display_name', '')
        if not display_name:
            findings.append(f'{tool["name"]}: missing display_name')
        elif _has_cjk(display_name):
            findings.append(f'{tool["name"]}: display_name still has CJK: {display_name!r}')
    assert not findings, '\n'.join(findings)


def test_registry_display_names_are_cjk_free_and_consistent_with_seed() -> None:
    # Importing these modules registers their tools as a side effect.
    import backend.app.conversation.engine.builtin_tools.arma_tools  # noqa: F401
    import backend.app.conversation.engine.builtin_tools.rag_retrieval  # noqa: F401
    import backend.app.conversation.engine.builtin_tools.web_search  # noqa: F401
    import backend.app.open.service.map_tools  # noqa: F401
    from backend.app.conversation.engine.builtin_tools.registry import builtin_registry

    seed_by_name = {tool['name']: tool['display_name'] for tool in SYSTEM_TOOLS}

    findings = []
    for name, tool_def in builtin_registry.get_all().items():
        if _has_cjk(tool_def.display_name):
            findings.append(f'{name}: registry display_name still has CJK: {tool_def.display_name!r}')
        seed_label = seed_by_name.get(name)
        if seed_label is not None and tool_def.display_name != seed_label:
            findings.append(
                f'{name}: registry display_name {tool_def.display_name!r} != seed.py display_name {seed_label!r}'
            )
    assert not findings, '\n'.join(findings)


# ---------------------------------------------------------------------------
# 2. Plugin manifests (backend/plugin/*/plugin.toml)
# ---------------------------------------------------------------------------


def _plugin_toml_paths() -> list[Path]:
    return sorted((REPO_ROOT / 'backend' / 'plugin').glob('*/plugin.toml'))


@pytest.mark.parametrize('toml_path', _plugin_toml_paths(), ids=lambda p: p.parent.name)
def test_plugin_toml_summary_and_description_are_cjk_free(toml_path: Path) -> None:
    data = rtoml.loads(toml_path.read_text(encoding='utf-8'))
    plugin = data.get('plugin', {})
    summary = plugin.get('summary', '')
    description = plugin.get('description', '')
    findings = []
    if _has_cjk(summary):
        findings.append(f'{toml_path}: summary still has CJK: {summary!r}')
    if _has_cjk(description):
        findings.append(f'{toml_path}: description still has CJK: {description!r}')
    assert not findings, '\n'.join(findings)


# ---------------------------------------------------------------------------
# 3. request_parse.py geo-IP locale
# ---------------------------------------------------------------------------


def test_request_parse_online_geo_ip_uses_spanish_locale() -> None:
    source = (REPO_ROOT / 'backend' / 'utils' / 'request_parse.py').read_text(encoding='utf-8')
    start = source.index('async def get_location_online')
    end = source.index('\n\n\n', start)
    function_source = source[start:end]

    assert 'lang=es' in function_source
    assert 'lang=zh-CN' not in function_source


def test_geo_ip_defaults_to_online_lookup() -> None:
    # The offline ip2region database only returns Chinese place names.
    from backend.core.conf import Settings

    assert Settings.model_fields['IP_LOCATION_PARSE'].default == 'online'


# ---------------------------------------------------------------------------
# 4. cli.py init() Redis prefix clearing
# ---------------------------------------------------------------------------


def test_cli_init_clears_cache_and_plugin_redis_prefixes() -> None:
    from backend.cli import INIT_REDIS_CLEAR_PREFIXES
    from backend.core.conf import settings

    assert settings.CACHE_CONFIG_REDIS_PREFIX in INIT_REDIS_CLEAR_PREFIXES
    assert settings.CACHE_DICT_REDIS_PREFIX in INIT_REDIS_CLEAR_PREFIXES
    assert settings.PLUGIN_REDIS_PREFIX in INIT_REDIS_CLEAR_PREFIXES
    assert settings.IP_LOCATION_REDIS_PREFIX in INIT_REDIS_CLEAR_PREFIXES
    # Previously-cleared prefixes must still be cleared.
    assert settings.JWT_USER_REDIS_PREFIX in INIT_REDIS_CLEAR_PREFIXES
    assert settings.TOKEN_REDIS_PREFIX in INIT_REDIS_CLEAR_PREFIXES
    assert settings.TOKEN_EXTRA_INFO_REDIS_PREFIX in INIT_REDIS_CLEAR_PREFIXES
    assert settings.TOKEN_REFRESH_REDIS_PREFIX in INIT_REDIS_CLEAR_PREFIXES
