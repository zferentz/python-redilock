"""Async Distributed Lock  (using redis)"""
import asyncio
import aioredis
import hashlib
import uuid
import time


class _RediScript:
    def __init__(self, script: str):
        self._script = script
        self._script_sha1 = hashlib.sha1(script.encode("utf-8")).hexdigest()

    async def run(self, _redis: aioredis.Redis, keys: tuple, args: list):
        try:
            result = await _redis.evalsha(self._script_sha1, len(keys), *keys,
                                          *args)

        except aioredis.exceptions.NoScriptError:
            await _redis.script_load(self._script)
            result = await _redis.evalsha(self._script_sha1, len(keys), *keys,
                                          *args)

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

    def __init__(self, redis_host: str, redis_port: int, redis_db: int):
        self._redis: aioredis.Redis = None
        self._redis_host: str = redis_host
        self._redis_port: int = redis_port
        self._redis_db: int = redis_db

    async def _connect(self):

        self._redis = await aioredis.from_url(
            url=f"redis://{self._redis_host}:{self._redis_port}/{self}",
            db=self._redis_db,
            password=None,
            encoding="utf-8",
            decode_responses=True
        )

        await self._redis.ping()

    async def lock(
            self,
            lock_name: str,
            ttl: float,
            block: float | bool = True,
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

        if not self._redis:
            await self._connect()

        assert isinstance(ttl, (int, float)) and ttl > 0, "ttl must be >0"
        assert isinstance(interval, (int, float)) and interval > 0, \
            "interval must be >0"
        if block not in (True, False):
            assert isinstance(block, (int, float)) and block > 0, \
                "max_wait must be >0"
            end_wait = time.time() + block
        else:
            end_wait = None

        unlock_secret = f"_LOCK_{lock_name}_{uuid.uuid4().hex}"

        while True:
            # Try to acquire lock
            ret = await self._redis.set(
                lock_name, unlock_secret, px=int(ttl * 1000), nx=True
            )
            if ret:
                return unlock_secret

            # If did not acquire lock - check if max_time has been exceeded
            if not block or (end_wait and time.time() >= end_wait):
                return False

            # Sleep before retrying to obtain the lock again
            await asyncio.sleep(interval)

        assert False, "Can never be here"

    async def unlock(self, lock_name: str, unlock_secret: str) -> bool:
        if not self._redis:
            await self._connect()

        # Run the unlock-script with lock_name as key and unlock_secret as argv
        return 1 == await _UNLOCK_SCRIPT.run(
            self._redis, (lock_name,), [unlock_secret, ]
        )

async def main():
    dl = DistributedLock("127.0.0.1", 6379, 5)
    lock = await dl.lock("zvika1", 5)
    print(lock)
    await dl.unlock("zvika1", lock)
    print(await dl.lock("zvika1", 5, block=False))
    lock = await dl.lock("zvika1", 5)
    print(lock)


asyncio.run(main())