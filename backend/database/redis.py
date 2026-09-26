import sys

from redis.asyncio import Redis
from redis.exceptions import AuthenticationError, TimeoutError

from backend.common.log import log
from backend.core.conf import settings


class RedisCli(Redis):
    """Redis client"""

    def __init__(
        self,
        host: str = settings.REDIS_HOST,
        port: int = settings.REDIS_PORT,
        password: str = settings.REDIS_PASSWORD,
        db: int = settings.REDIS_DATABASE,
        socket_timeout: int = settings.REDIS_TIMEOUT,
        socket_connect_timeout: int = settings.REDIS_TIMEOUT,
        *,
        socket_keepalive: bool = True,
        health_check_interval: int = 30,
        decode_responses: bool = True,
    ) -> None:
        """
        Initialize the Redis client

        :param host: Redis server host address
        :param port: Redis server port number
        :param password: Redis authentication password
        :param db: Redis logical database index to use
        :param socket_timeout: timeout for socket read/write operations
        :param socket_connect_timeout: timeout when establishing the TCP connection
        :param socket_keepalive: whether to enable TCP keepalive probing
        :param health_check_interval: health check interval (seconds)
        :param decode_responses: whether to automatically decode bytes returned by Redis into strings (utf-8)
        """
        super().__init__(
            host=host,
            port=port,
            password=password,
            db=db,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            socket_keepalive=socket_keepalive,
            health_check_interval=health_check_interval,
            decode_responses=decode_responses,
        )

    async def init(self) -> None:
        """Initialize the Redis server"""
        try:
            await self.ping()
        except TimeoutError:
            log.error('Redis server connection timed out')
            sys.exit()
        except AuthenticationError:
            log.error('Redis server connection authentication failed')
            sys.exit()
        except Exception as e:
            log.error('Redis server connection exception %s', e)
            sys.exit()

    async def delete_prefix(self, prefix: str, exclude: str | list[str] | None = None, batch_size: int = 1000) -> None:
        """
        Delete all keys with the given prefix

        :param prefix: key prefix to delete
        :param exclude: key or list of keys to exclude
        :param batch_size: batch size for deletion, to avoid blocking Redis by deleting too many keys at once
        :return:
        """
        exclude_set = set(exclude) if isinstance(exclude, list) else {exclude} if isinstance(exclude, str) else set()
        batch_keys = []

        async for key in self.scan_iter(match=f'{prefix}*'):
            if key not in exclude_set:
                batch_keys.append(key)

                if len(batch_keys) >= batch_size:
                    await self.delete(*batch_keys)
                    batch_keys.clear()

        if batch_keys:
            await self.delete(*batch_keys)

    async def get_prefix(self, prefix: str, count: int = 100) -> list[str]:
        """
        Get all keys with the given prefix

        :param prefix: key prefix to search for
        :param count: number of keys scanned per batch; a larger value scans faster but uses more server resources
        :return:
        """
        return [key async for key in self.scan_iter(match=f'{prefix}*', count=count)]


# Create the redis client singleton
redis_client: RedisCli = RedisCli()
