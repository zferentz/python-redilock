"""Async Distributed Lock  (using redis)"""
import asyncio
import aioredis
import hashlib
import uuid
import time

_redis: aioredis.Redis = None


_REDIS_HOST = None
_REDIS_POST = None
_REDIS_DB = None

async def initialize():
    global _redis
    _redis = await aioredis.from_url(
        url=f"redis://{_REDIS_HOST}:{REDIS_PORT}",
        db=_REDIS_DB,
        password=None,
        encoding="utf-8",
        decode_responses=True
    )

    await _redis.ping()


class _RediScript:
    def __init__(self, script: str):
        self._script = script
        self._script_sha1 = hashlib.sha1(script.encode("utf-8")).hexdigest()  # nosec

    async def run(self, keys: tuple, args: list):
        try:
            result = await _redis.evalsha(self._script_sha1, len(keys), *keys, *args)

        except aioredis.exceptions.NoScriptError:
            await _redis.script_load(self._script)
            result = await _redis.evalsha(self._script_sha1, len(keys), *keys, *args)

        return result


_UNLOCK_SCRIPT = _RediScript("""
    local lock_name = KEYS[1]
    local lock_secret_token = ARGV[1] 
    if redis.call("get", lock_name) == lock_secret_token
    then
        return redis.call("del", lock_name)
    else
        return 0
    end
""")


class DistributedLock:
    """Distributed Lock"""

    @classmethod
    async def lock(
            cls,
            lock_name: str,
            ttl: float,
            max_wait: float = None,
            interval: float = 0.25
    ):
        """Lock a resource (by lock name).  Wait until lock is owned.

        :param str lock_name: the name of the lock  (e.g. resource to lock)
        :param float|int ttl: Time To Leave (or Time To Lock) in seconds
        :param float|int max_wait: Max time to lock  (lock expiration)
        :param float|int interval: interval to query lock (if locked by others)

        :returns:
          string (token to unlock) - if lock was successfully acquired
          False (boolean) - on failure (couldn't lock the resource)

        Notes:
        * This function is simply a loop around try_lock(). We will try to lock
          the resource (lock_name) until the lock is owned by us or max_time
          reached.
        * The default behavior is max_wait=None and interval=0.25 which means
          that the function will block until it owns the lock and will try to
          lock every 0.25 seconds  (250ms)
        * When using this function - consider the `ttl` parameter - for how long
          the lock is required. This will make sure that in case of a crash or
          system error the lock will be auto-released.
        """

        assert isinstance(interval, (int, float)) and interval > 0, \
            "interval must be >0"
        if max_wait is not None:
            assert isinstance(max_wait, (int, float)) and max_wait > 0, \
                "max_wait must be >0"
            end_wait = time.time() + max_wait
        else:
            end_wait = None

        while True:
            # Try to acquire lock
            unlock_secret = await cls.try_lock(lock_name, ttl)

            # If we got it - return the "secret" for unlock
            if unlock_secret:
                return unlock_secret

            # If did not acquire lock - check if max_time has been exceeded
            if end_wait and time.time() >= end_wait:
                return False

            # Sleep before retrying to obtain the lock again
            await asyncio.sleep(interval)

        assert False, "Can never be here"

    @classmethod
    async def try_lock(cls, lock_name: str, ttl: float):
        """Lock a resource (by lock name).  return False if lock wasn't acquired

        :param str lock_name: the name of the lock  (e.g. resource to lock)
        :param float|int ttl: Time To Leave (or Time To Lock) in seconds

        :returns: string (token to unlock) or False for failure (couldn't lock)
        """
        assert isinstance(ttl, (int, float)) and ttl > 0, "ttl must be >0"
        unlock_secret = f"_LOCK_{lock_name}_{uuid.uuid4().hex}"
        ret = await _redis.set(
            lock_name, unlock_secret, px=int(ttl * 1000), nx=True
        )
        assert ret in (True, None)
        if not ret:
            return False
        return unlock_secret

    @classmethod
    async def unlock(cls, lock_name: str, unlock_secret: str) -> bool:

        # Run the unlock-script with lock_name as key and unlock_secret as argv
        return await _UNLOCK_SCRIPT.run((lock_name,), [unlock_secret, ]) == 1
