from functools import lru_cache
from redis import ConnectionPool


@lru_cache(maxsize=1)
def get_redis_connection_pool(redis_connection_str: str) -> ConnectionPool:
    return ConnectionPool.from_url(redis_connection_str, decode_components=True)
