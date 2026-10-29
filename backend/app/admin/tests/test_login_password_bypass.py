import asyncio

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.admin.service import auth_service as auth_module
from backend.common.exception import errors


def _patch_dependencies(monkeypatch: pytest.MonkeyPatch, *, bypass: bool, password_ok: bool) -> AsyncMock:
    user = SimpleNamespace(id=1, status=1, password='hashed', last_password_changed_time=None)
    failure = AsyncMock()
    monkeypatch.setattr(auth_module.user_dao, 'get_by_username', AsyncMock(return_value=user))
    monkeypatch.setattr(auth_module.password_security_service, 'check_status', AsyncMock())
    monkeypatch.setattr(auth_module.password_security_service, 'handle_login_failure', failure)
    monkeypatch.setattr(auth_module.password_security_service, 'handle_login_success', AsyncMock())
    monkeypatch.setattr(
        auth_module.password_security_service, 'check_password_expiry_status', AsyncMock(return_value=None)
    )
    monkeypatch.setattr(auth_module, 'password_verify', lambda plain, hashed: password_ok)
    monkeypatch.setattr(auth_module.settings, 'LOGIN_PASSWORD_BYPASS', bypass, raising=False)
    return failure


def test_user_verify_rejects_wrong_password_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    failure = _patch_dependencies(monkeypatch, bypass=False, password_ok=False)

    with pytest.raises(errors.AuthorizationError):
        asyncio.run(auth_module.AuthService.user_verify(AsyncMock(), 'admin', 'wrong'))

    failure.assert_awaited_once()


def test_user_verify_skips_password_when_bypass_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    failure = _patch_dependencies(monkeypatch, bypass=True, password_ok=False)

    user, _ = asyncio.run(auth_module.AuthService.user_verify(AsyncMock(), 'admin', ''))

    assert user.id == 1
    failure.assert_not_awaited()
