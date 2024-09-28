import abc
import hashlib
import time
import uuid


class RedisLuaScriptBase(abc.ABC):
    """Helper to store and run Redis Lua scripts"""

    def __init__(self, script: str):
        self._script = script
        self._script_sha1 = hashlib.sha1(script.encode("utf-8")).hexdigest()

    @abc.abstractmethod
    async def run(self, _redis, keys: tuple, args: list):
        """Abstract method for async run()"""

    @abc.abstractmethod
    def run(self, _redis, keys: tuple, args: list):
        """Abstract method for sync run()"""


# UNLOCK_SCRIPT: Redis Lua script to unlock a resource (KEY[1]) only if the
#                caller provided the correct secret token (ARGV[1])
UNLOCK_SCRIPT = """
    local lock_name = KEYS[1]
    local lock_secret_token = ARGV[1] 
    if redis.call("get", lock_name) == lock_secret_token
    then
        return redis.call("del", lock_name)
    else
        return 0
    end
"""

_DEFAULT_REDIS_PORT = 6379
_DEFAULT_REDIS_HOST = "localhost"
_DEFAULT_REDIS_DB = 0


class DistributedLockBase:
    """Distributed Lock - interface for async/sync implementations"""

    def __init__(
        self,
        redis_host: str = _DEFAULT_REDIS_HOST,
        redis_port: int = _DEFAULT_REDIS_PORT,
        redis_db: int = _DEFAULT_REDIS_DB,
    ):
        self._redis = None
        self._redis_host: str = redis_host
        self._redis_port: int = redis_port
        self._redis_db: int = redis_db

    @classmethod
    def _prepare_lock(
        cls,
        lock_name: str,
        ttl: float,
        block: bool | float | int,
        interval: float | int,
    ):
        assert isinstance(ttl, (int, float)) and ttl > 0, "ttl must be >0"
        assert (
            isinstance(interval, (int, float)) and interval > 0
        ), "interval must be >0"
        if isinstance(block, bool):
            end_wait = None
        else:
            assert isinstance(block, (int, float)) and block > 0, "block must be >0"
            end_wait = time.time() + block

        return f"_LOCK_{lock_name}_{uuid.uuid4().hex}", end_wait

    @abc.abstractmethod
    async def lock(
        self,
        lock_name: str,
        ttl: float,
        block: float | bool = True,
        interval: float = 0.25,
    ):
        """Lock a resource (by lock name).  Wait until lock is owned.

        :param str lock_name: the name of the lock  (e.g. resource to lock)
        :param float|int ttl: Time To Leave (or Time To Lock) in seconds
        :param bool|float|int block: Max time to wait for lock (in seconds)
                                 block=True means block until lock is acquired
        :param float|int interval: interval to query lock (if locked by others)

        :returns:
          On success:  string - token to unlock
          On failure:  boolean False - Lock couldn't be acquired
        """

    @abc.abstractmethod
    def lock(
        self,
        lock_name: str,
        ttl: float,
        block: float | bool = True,
        interval: float = 0.25,
    ):
        """Refer to docstring for async lock()"""

    @abc.abstractmethod
    async def unlock(self, lock_name: str, unlock_secret_token: str) -> bool:
        """Unlock a resource

        :param str lock_name: the name of the lock
        :param str unlock_secret_token: the secret token for the unlock

        :returns: boolean  (True for success, False otherwise)
        """

    @abc.abstractmethod
    def unlock(self, lock_name: str, unlock_secret_token: str) -> bool:
        """Refer to docstring for async unlock()"""
