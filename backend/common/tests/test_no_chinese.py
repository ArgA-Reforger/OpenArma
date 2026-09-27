import re

from pathlib import Path

import pytest

from backend.core.path_conf import BASE_PATH

HAN_RE = re.compile(f'[{chr(0x4E00)}-{chr(0x9FFF)}{chr(0x3400)}-{chr(0x4DBF)}]')

REPO_ROOT = BASE_PATH.parent

TRANSLATED_PACKAGES = ['backend/app/admin']


def _iter_py_files(package: str) -> list[Path]:
    package_dir = REPO_ROOT / package
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
