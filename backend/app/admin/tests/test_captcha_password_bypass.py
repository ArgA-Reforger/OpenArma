import asyncio

from unittest.mock import AsyncMock

import pytest

from backend.app.admin.api.v1.auth import captcha as captcha_module
from backend.app.admin.schema.captcha import GetCaptchaDetail


def _get_captcha(monkeypatch: pytest.MonkeyPatch, *, bypass: bool) -> GetCaptchaDetail:
    monkeypatch.setattr(captcha_module, 'load_login_config', AsyncMock())
    monkeypatch.setattr(captcha_module, 'img_captcha', lambda img_byte: ('image', 'code'))
    monkeypatch.setattr(captcha_module.redis_client, 'set', AsyncMock())
    monkeypatch.setattr(captcha_module.settings, 'LOGIN_CAPTCHA_ENABLED', True)
    monkeypatch.setattr(captcha_module.settings, 'LOGIN_PASSWORD_BYPASS', bypass, raising=False)
    monkeypatch.setattr(captcha_module.settings, 'LOGIN_PASSWORD_BYPASS_USERNAME', 'admin', raising=False)
    return asyncio.run(captcha_module.get_captcha(AsyncMock())).data


def test_captcha_reports_no_bypass_user_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _get_captcha(monkeypatch, bypass=False)

    assert data.bypass_username is None
    assert data.is_enabled is True


def test_captcha_reports_bypass_user_and_disables_captcha_when_bypass_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _get_captcha(monkeypatch, bypass=True)

    assert data.bypass_username == 'admin'
    assert data.is_enabled is False
