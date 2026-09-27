import re

from pathlib import Path

import pytest

from backend.core.path_conf import BASE_PATH

HAN_RE = re.compile(f'[{chr(0x4E00)}-{chr(0x9FFF)}{chr(0x3400)}-{chr(0x4DBF)}]')

REPO_ROOT = BASE_PATH.parent

TRANSLATED_PACKAGES = [
    'backend/app/admin',
    'backend/plugin',
    'backend/common',
    'backend/core',
    'backend/middleware',
    'backend/database',
    'backend/alembic',
    'backend/cli.py',
    'backend/run.py',
    'backend/main.py',
    'backend/utils',
    'backend/app/task',
    'backend/app/conversation',
    'backend/app/map',
    'backend/app/knowledge',
    'backend/app/mcp',
    'backend/app/llm',
    'backend/app/open',
    'backend/app/agent',
    'backend/app/builtin_tool',
    'backend/app/project',
    'backend/app/billing',
    'backend/app/topology',
    'backend/app/showcase',
]


def _iter_py_files(package: str) -> list[Path]:
    package_dir = REPO_ROOT / package
    if package_dir.is_file():
        return [package_dir]
    return sorted(package_dir.rglob('*.py'))


def _find_han_lines(file_path: Path) -> list[str]:
    findings = []
    text = file_path.read_text(encoding='utf-8')
    for lineno, line in enumerate(text.splitlines(), start=1):
        if HAN_RE.search(line):
            rel_path = file_path.relative_to(REPO_ROOT)
            findings.append(f'{rel_path}:{lineno}: {line.strip()}')
    return findings


@pytest.mark.parametrize('package', TRANSLATED_PACKAGES)
def test_no_chinese_characters(package: str) -> None:
    all_findings = []
    for py_file in _iter_py_files(package):
        all_findings.extend(_find_han_lines(py_file))

    assert not all_findings, 'Found untranslated Chinese text:\n' + '\n'.join(all_findings)


NON_PY_TRANSLATED_PATHS = [
    'backend/plugin/code_generator/README.md',
    'backend/plugin/config/README.md',
    'backend/plugin/dict/README.md',
    'backend/plugin/email/README.md',
    'backend/plugin/notice/README.md',
    'backend/plugin/oauth2/README.md',
    'backend/plugin/code_generator/plugin.toml',
    'backend/plugin/config/plugin.toml',
    'backend/plugin/dict/plugin.toml',
    'backend/plugin/email/plugin.toml',
    'backend/plugin/notice/plugin.toml',
    'backend/plugin/oauth2/plugin.toml',
    'backend/plugin/code_generator/templates/python/api.jinja',
    'backend/plugin/code_generator/templates/python/crud.jinja',
    'backend/plugin/code_generator/templates/python/model.jinja',
    'backend/plugin/code_generator/templates/python/router.jinja',
    'backend/plugin/code_generator/templates/python/schema.jinja',
    'backend/plugin/code_generator/templates/python/service.jinja',
    'backend/plugin/code_generator/templates/sql/mysql/init.jinja',
    'backend/plugin/code_generator/templates/sql/mysql/init_snowflake.jinja',
    'backend/plugin/code_generator/templates/sql/postgresql/init.jinja',
    'backend/plugin/code_generator/templates/sql/postgresql/init_snowflake.jinja',
    'backend/plugin/email/templates/captcha.html',
    'docker-compose.yml',
    'pyproject.toml',
    'deploy/backend/nginx.conf',
    'deploy/backend/grafana/fba_config.alloy',
    'deploy/backend/grafana/fba_dashboards.yml',
    'deploy/backend/grafana/fba_datasource.yml',
    'deploy/backend/grafana/fba_grafana.ini',
    'deploy/backend/grafana/fba_prometheus.yml',
    'deploy/backend/grafana/fba_tempo.yml',
    'deploy/backend/grafana/dashboards/fba_celery.json',
    'deploy/backend/grafana/dashboards/fba_server.json',
]


@pytest.mark.parametrize('rel_path', NON_PY_TRANSLATED_PATHS)
def test_no_chinese_characters_non_python(rel_path: str) -> None:
    findings = _find_han_lines(REPO_ROOT / rel_path)
    assert not findings, 'Found untranslated Chinese text:\n' + '\n'.join(findings)
