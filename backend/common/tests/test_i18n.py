import glob
import json
import re

from pathlib import Path
from typing import Any

import pytest
import yaml

from starlette.requests import Request

from backend.core.path_conf import LOCALE_DIR

PLACEHOLDER_RE = re.compile(r'\{(\w+)\}')
HAN_RE = re.compile(f'[{chr(0x4E00)}-{chr(0x9FFF)}]')


def make_request(accept_language: str) -> Request:
    headers = []
    if accept_language:
        headers.append((b'accept-language', accept_language.encode()))
    scope = {
        'type': 'http',
        'headers': headers,
        'method': 'GET',
        'path': '/',
    }
    return Request(scope)


@pytest.mark.parametrize(
    ('accept_language', 'expected'),
    [
        ('es', 'es-ES'),
        ('es-ES', 'es-ES'),
        ('es-AR,es;q=0.9', 'es-ES'),
        ('es-419', 'es-ES'),
        ('en', 'en-US'),
        ('en-GB', 'en-US'),
    ],
)
def test_get_current_language_maps_known_tags(accept_language: str, expected: str) -> None:
    from backend.middleware.i18n_middleware import get_current_language

    request = make_request(accept_language)
    assert get_current_language(request) == expected


def test_get_current_language_defaults_when_missing() -> None:
    from backend.core.conf import settings
    from backend.middleware.i18n_middleware import get_current_language

    request = make_request('')
    assert get_current_language(request) == settings.I18N_DEFAULT_LANGUAGE


def test_get_current_language_defaults_for_unknown_tag() -> None:
    from backend.core.conf import settings
    from backend.middleware.i18n_middleware import get_current_language

    request = make_request('fr-FR')
    assert get_current_language(request) == settings.I18N_DEFAULT_LANGUAGE


def flatten_keys(data: dict[str, Any], prefix: str = '') -> dict[str, Any]:
    keys: dict[str, Any] = {}
    for k, v in data.items():
        full_key = f'{prefix}.{k}' if prefix else k
        if isinstance(v, dict):
            keys.update(flatten_keys(v, full_key))
        else:
            keys[full_key] = v
    return keys


def load_catalog(stem: str) -> dict[str, Any]:
    for ext in ('yml', 'yaml', 'json'):
        path = LOCALE_DIR / f'{stem}.{ext}'
        if path.exists():
            with open(path, encoding='utf-8') as f:
                if ext == 'json':
                    return json.loads(f.read())
                return yaml.full_load(f.read())
    raise FileNotFoundError(stem)


def test_es_and_en_catalogs_have_identical_key_and_placeholder_sets() -> None:
    es = flatten_keys(load_catalog('es-ES'))
    en = flatten_keys(load_catalog('en-US'))

    assert set(es.keys()) == set(en.keys())

    for key in es:
        es_placeholders = set(PLACEHOLDER_RE.findall(es[key])) if isinstance(es[key], str) else set()
        en_placeholders = set(PLACEHOLDER_RE.findall(en[key])) if isinstance(en[key], str) else set()
        assert es_placeholders == en_placeholders, key


def test_all_locale_files_parse() -> None:
    for path in glob.glob(str(LOCALE_DIR / '*')):
        suffix = Path(path).suffix.lower()
        with open(path, encoding='utf-8') as f:
            content = f.read()
        if suffix == '.json':
            json.loads(content)
        elif suffix in ('.yml', '.yaml'):
            yaml.full_load(content)


def test_no_han_characters_in_locale_files() -> None:
    for path in glob.glob(str(LOCALE_DIR / '*')):
        text = Path(path).read_text(encoding='utf-8')
        assert not HAN_RE.search(text), path


def test_zh_cn_not_loaded() -> None:
    from backend.common.i18n import i18n

    assert 'zh-CN' not in i18n.locales


def test_default_language_is_es_es_and_loaded() -> None:
    from backend.common.i18n import i18n
    from backend.core.conf import settings

    assert settings.I18N_DEFAULT_LANGUAGE == 'es-ES'
    assert 'es-ES' in i18n.locales
