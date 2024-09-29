"""Async Distributed Lock  (using redis)"""

import asyncio
import contextlib
import time

import redis
import redis.asyncio

import redilock.base as base


class _RediScript(base.RedisLuaScriptBase):
    """Helper to store and run Redis Lua scripts - async implementation"""

    async def run(self, _redis: redis.Redis, keys: tuple, args: list):
        try:
            result = await _redis.evalsha(self._script_sha1, len(keys), *keys,
                                          *args)

        except redis.exceptions.NoScriptError:
            await _redis.script_load(self._script)
            result = await _redis.evalsha(self._script_sha1, len(keys), *keys,
                                          *args)

        return result


class DistributedLock(base.DistributedLockBase):
    """Distributed Lock"""

    _unlock_script = _RediScript(base.UNLOCK_SCRIPT)
    _connect_mutex = asyncio.Lock()

    async def _connect(self):
        async with self._connect_mutex:
            if self._redis:
                return

            self._redis = await redis.asyncio.from_url(
                url=f"redis://{self._redis_host}:{self._redis_port}/",
                db=self._redis_db,
                password=None,
                encoding="utf-8",
            )

        await self._redis.ping()

    async def lock(
            self,
            lock_name: str,
            ttl: float = None,
            block: bool | float | int = True,
            interval: float | int = None,
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

        if not self._redis:
            await self._connect()

        unlock_secret_token, ttl, end_wait, interval = self._prepare_lock(
            lock_name, ttl, block, interval
        )

        while True:
            # Try to acquire lock
            ret = await self._redis.set(
                lock_name, unlock_secret_token, px=int(ttl * 1000), nx=True
            )
            if ret:
                return unlock_secret_token

            # If did not acquire lock - check if max_time has been exceeded
            if not block or (end_wait and time.time() >= end_wait):
                return False

            # Sleep before retrying to obtain the lock again
            await asyncio.sleep(interval)

        assert False, "Can never be here"

    async def unlock(self, unlock_secret_token: str) -> bool:
        lock_name = self._token2lockname(unlock_secret_token)
        if not lock_name:
            return False

        if not self._redis:
            await self._connect()

        # Run the unlock-script with lock_name & unlock_secret_token
        return 1 == await self._unlock_script.run(
            self._redis,
            (lock_name,),
            [
                unlock_secret_token,
            ],
        )

    @contextlib.asynccontextmanager
    async def __call__(self, lock_name: str, ttl: float = None):
        unlock_secret_token = await self.lock(lock_name, ttl)
        try:
            yield self
        finally:
            await self.unlock(unlock_secret_token)
