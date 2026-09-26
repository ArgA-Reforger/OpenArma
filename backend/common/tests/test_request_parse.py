"""Tests for IP geolocation caching in backend.utils.request_parse."""

import asyncio

from types import SimpleNamespace

import pytest

from backend.core.conf import settings
from backend.utils import request_parse


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value
        self.ttls[key] = ex


def _request(ip: str) -> SimpleNamespace:
    return SimpleNamespace(headers={'X-Real-IP': ip}, client=SimpleNamespace(host=ip))


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    redis = FakeRedis()
    monkeypatch.setattr(request_parse, 'redis_client', redis)
    monkeypatch.setattr(settings, 'IP_LOCATION_PARSE', 'online')
    return redis


def test_failed_online_lookup_is_cached_briefly(fake_redis: FakeRedis, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    async def failing_lookup(ip: str) -> None:
        calls.append(ip)

    monkeypatch.setattr(request_parse, 'get_location_online', failing_lookup)

    first = asyncio.run(request_parse.parse_ip_info(_request('203.0.113.7')))
    second = asyncio.run(request_parse.parse_ip_info(_request('203.0.113.7')))

    assert calls == ['203.0.113.7']
    assert (first.country, first.region, first.city) == (None, None, None)
    assert (second.country, second.region, second.city) == (None, None, None)
    key = f'{settings.IP_LOCATION_REDIS_PREFIX}:203.0.113.7'
    assert fake_redis.ttls[key] == settings.IP_LOCATION_FAILURE_EXPIRE_SECONDS
    assert settings.IP_LOCATION_FAILURE_EXPIRE_SECONDS < settings.IP_LOCATION_EXPIRE_SECONDS


def test_missing_fields_are_not_cached_as_none_text(fake_redis: FakeRedis, monkeypatch: pytest.MonkeyPatch) -> None:
    async def partial_lookup(ip: str) -> dict:
        return {'country': 'Argentina', 'regionName': None, 'city': None}

    monkeypatch.setattr(request_parse, 'get_location_online', partial_lookup)

    asyncio.run(request_parse.parse_ip_info(_request('190.210.1.1')))
    cached = asyncio.run(request_parse.parse_ip_info(_request('190.210.1.1')))

    assert (cached.country, cached.region, cached.city) == ('Argentina', None, None)
    key = f'{settings.IP_LOCATION_REDIS_PREFIX}:190.210.1.1'
    assert fake_redis.ttls[key] == settings.IP_LOCATION_EXPIRE_SECONDS
