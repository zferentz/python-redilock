"""base classes & utilities for redilock"""

import abc
import hashlib
import time
import uuid


class RedisLuaScriptBase(abc.ABC):
    """Helper base-class to store and run Redis Lua scripts

    redis allows us to load a lua-script to the server and run it.
    This base-class hides the details and makes it easy to use.

    This class is a base-class and should not be used directly.
    The derived class must implement `def run()` or `async def run()` and
    callers can simply load and run a script using this function.
    The `run` function takes care of loading and running the script efficiently.
    """

    def __init__(self, script: str):
        self._script = script
        self._script_sha1 = hashlib.sha1(script.encode("utf-8")).hexdigest()

    @abc.abstractmethod
    async def run(self, _redis, keys: tuple, args: list):
        """Abstract method for async run()

        :param Redis _redis: the redis client/connection to use
        :param tuple keys: tuple KEYS (key-names) for the lua script
        :param list args: list ARGV (args-names) for the lua script
        :returns: value return by the lua script
        """

    @abc.abstractmethod
    def run(self, _redis, keys: tuple, args: list):
        """Refer to docstring for async run() above"""


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

_DEFAULT_INTERVAL = 0.25


class DistributedLockBase:
    """Distributed Lock - interface for async/sync implementations"""

    def __init__(
        self,
        redis_host: str = _DEFAULT_REDIS_HOST,
        redis_port: int = _DEFAULT_REDIS_PORT,
        redis_db: int = _DEFAULT_REDIS_DB,
        ttl: int = None,
        interval: int = _DEFAULT_INTERVAL,
    ):
        """Initialize the distributed lock
        :param str redis_host: Redis host to use (default is "localhost")
        :param int redis_port: Redis port to use (default is 6379)
        :param int redis_db: Redis DB to use (default is 0)
        :param float|int ttl: the Time To Lock (in seconds)
        :param float|int interval: default interval to query lock-state
        """
        self._redis = None
        self._redis_host: str = redis_host
        self._redis_port: int = redis_port
        self._redis_db: int = redis_db
        self._ttl = ttl
        self._interval = interval

    def _prepare_lock(
        self,
        lock_name: str,
        ttl: float,
        block: bool | float | int,
        interval: float | int,
    ) -> tuple:
        ttl = ttl or self._ttl
        assert isinstance(ttl, (int, float)) and ttl > 0, "ttl must be >0"

        interval = interval or self._interval
        assert (
            isinstance(interval, (int, float)) and interval > 0
        ), "interval must be >0"
        if isinstance(block, bool):
            end_wait = None
        else:
            assert isinstance(block, (int, float)) and block > 0, "block must be >0"
            end_wait = time.time() + block

        unlock_secret_token = self._lockname2token(lock_name)

        return unlock_secret_token, ttl, end_wait, interval

    @classmethod
    def _lockname2token(cls, lock_name: str) -> str:
        return f"_LOCK:{lock_name}:{uuid.uuid4().hex}"

    @classmethod
    def _token2lockname(cls, unlock_secret_token: str) -> str:
        if not isinstance(unlock_secret_token, str):
            return ""
        delim = unlock_secret_token.split(":")
        if len(delim) != 3 or delim[0] != "_LOCK":
            return ""
        return delim[1]



    @abc.abstractmethod
    async def lock(
        self,
        lock_name: str,
        ttl: float = None,
        block: float | bool = True,
        interval: float = None,
    ):
        """Lock a resource (by lock name).  Wait until lock is owned.

        :param str lock_name: the name of the lock  (e.g. resource to lock)
        :param float|int ttl: Time To Leave (or Time To Lock) in seconds
        :param bool|float|int block: Max time to wait for lock (in seconds)
                                 block=True means block until lock is acquired
        :param float|int interval: interval to query lock (if locked by others)

        :returns:
          On success:  string - secret token that shall be used to unlock
                                the resource when calling unlock()
          On failure:  boolean False - Lock couldn't be acquired
        """

    @abc.abstractmethod
    def lock(
        self,
        lock_name: str,
        ttl: float = None,
        block: float | bool = True,
        interval: float = None,
    ):
        """Refer to docstring for async lock() above"""

    @abc.abstractmethod
    async def unlock(self, unlock_secret_token: str) -> bool:
        """Unlock a resource

        :param str lock_name: the name of the lock
        :param str unlock_secret_token: the secret token for the unlock

        :returns: boolean (True for success, False otherwise)
        """

    @abc.abstractmethod
    def unlock(self, unlock_secret_token: str) -> bool:
        """Refer to docstring for async unlock() above"""
