from typing import Any

import cachebox

from backend.core.conf import settings


class LocalCacheManager:
    """Local cache manager"""

    def __init__(self) -> None:
        self.hot_cache: cachebox.TTLCache = cachebox.TTLCache(
            settings.CACHE_LOCAL_MAXSIZE, ttl=settings.CACHE_LOCAL_TTL
        )

    def get(self, key: str) -> Any:
        """Get a cache entry"""
        try:
            return self.hot_cache[key]
        except KeyError:
            return None

    def set(self, key: str, value: Any) -> None:
        """Set a cache entry"""
        self.hot_cache[key] = value

    def delete(self, key: str) -> bool:
        """Delete a cache entry"""
        try:
            del self.hot_cache[key]
        except KeyError:
            return False
        return True

    def clear(self) -> None:
        """Clear the cache"""
        self.hot_cache.clear()

    def delete_prefix(self, prefix: str, exclude: str | list[str] | None = None) -> None:
        """
        Delete cache entries with the given prefix

        :param prefix: key prefix to delete
        :param exclude: key or list of keys to exclude
        :return:
        """
        exclude_set = set(exclude) if isinstance(exclude, list) else {exclude} if isinstance(exclude, str) else set()
        for key in list(self.hot_cache.keys()):
            if key.startswith(prefix) and key not in exclude_set:
                try:
                    del self.hot_cache[key]
                except KeyError:
                    pass


local_cache_manager = LocalCacheManager()
