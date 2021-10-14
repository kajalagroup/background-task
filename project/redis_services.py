import json
import logging
from functools import lru_cache
from typing import Any, Optional
from django.conf import settings
from redis import Redis
from project.redis_connection import get_redis_connection_pool_instance

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_redis_instance() -> Redis:
    connection_pool = get_redis_connection_pool_instance(settings.REDIS_URL)  # type: ignore  # noqa
    return Redis(connection_pool=connection_pool)


def redis_set(name: str, value: Any, ex: Optional[int] = None):
    prefix = str(settings.DATABASES["default"]["NAME"]) + "."
    get_redis_instance().set(prefix + name, value, ex=ex)


def redis_get(name: str) -> Any:
    prefix = str(settings.DATABASES["default"]["NAME"]) + "."
    return get_redis_instance().get(prefix + name)


def redis_set_json(name: str, value: Any, ex: Optional[int] = None, exceptions: bool = False):
    try:
        redis_set(name, json.dumps(value).encode() if value is not None else b"", ex)
    except Exception as err:
        logger.warning("redis_set_json(%s, %s, %s): %s", name, value, ex, err)
        if exceptions:
            raise


def redis_get_json(name: str) -> Any:
    res = redis_get(name)
    if not res:
        return None
    return json.loads(res.decode())


def redis_get_json_or_none(name: str) -> Any:
    try:
        return redis_get_json(name)
    except Exception as err:
        logger.warning("redis_get_json_or_none(%s): %s", name, err)
        return None


def redis_delete(name: str):
    prefix = str(settings.DATABASES["default"]["NAME"]) + "."
    get_redis_instance().delete(prefix + name)


def redis_throttle(name: str, ex: int) -> bool:
    """
    Sets key value if it's not in DB.
    :param name: Key name
    :param ex: Expires in seconds
    :return: True if value was set, False if previous value existed
    """
    name = str(settings.DATABASES["default"]["NAME"]) + "." + name
    redis = get_redis_instance()
    old = redis.get(name)
    if old is not None:
        return False
    redis.set(name, 1, ex=ex)
    return True
