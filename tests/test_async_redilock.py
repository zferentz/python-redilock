import asyncio
import unittest.mock
import sys
import os

import aioredis

_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _parent_dir)

import redilock.async_redilock as redilock


class TestRediScriptAsync(unittest.IsolatedAsyncioTestCase):

    async def test_rediscript_run_script_not_found(self):
        script = redilock._RediScript("X=1")
        keys = ()
        args = []
        mock_redis = unittest.mock.AsyncMock()

        # mock evalsha: first run throw NoScriptError and then return OK
        mock_redis.evalsha.side_effect = [aioredis.exceptions.NoScriptError,
                                          "OK"]
        result = await script.run(mock_redis, keys, args)
        mock_redis.evalsha.assert_has_calls(
            [
                unittest.mock.call(script._script_sha1, 0),
                unittest.mock.call(script._script_sha1, 0),
            ]
        )

        mock_redis.script_load.assert_called_with("X=1")
        self.assertEqual(result, "OK")

    async def test_rediscript_run_script_found(self):
        script = redilock._RediScript("X=1")
        keys = ()
        args = []
        mock_redis = unittest.mock.AsyncMock()

        # mock evalsha: first run throw NoScriptError and then return OK
        mock_redis.evalsha.return_value = "OK"
        result = await script.run(mock_redis, keys, args)
        mock_redis.evalsha.assert_called_with(script._script_sha1, 0)
        mock_redis.script_load.assert_not_called()
        self.assertEqual(result, "OK")


class TestRediLockAsync(unittest.IsolatedAsyncioTestCase):

    @unittest.mock.patch.object(
        aioredis, "from_url", new_callable=unittest.mock.AsyncMock
    )
    async def test_connect(self, mock_redis):
        lock = redilock.DistributedLock("host", 6379, 2)
        self.assertIsNone(lock._redis)
        await lock._connect()
        self.assertEqual(lock._redis, mock_redis.return_value)
        mock_redis.assert_called_once_with(
            url="redis://host:6379/", db=2, password=None, encoding="utf-8"
        )

        # Make sure that we dont connect twice
        await lock._connect()
        mock_redis.assert_called_once()

    @unittest.mock.patch.object(
        aioredis, "from_url", new_callable=unittest.mock.AsyncMock
    )
    async def test_lock_success_on_1st_attempt(self, mock_redis):
        mock_redis.return_value.set.return_value = 1
        lock = redilock.DistributedLock()
        secret_token = await lock.lock("mylock", 1000)
        mock_redis.return_value.set.assert_called_once_with(
            "mylock", secret_token, px=1000000, nx=True
        )

    @unittest.mock.patch.object(
        aioredis, "from_url", new_callable=unittest.mock.AsyncMock
    )
    @unittest.mock.patch.object(asyncio, "sleep")
    async def test_lock_success_on_2nd_attempt(self, mock_sleep, mock_redis):
        mock_redis.return_value.set.side_effect = [0, 1]
        lock = redilock.DistributedLock()
        secret_token = await lock.lock("mylock", 1000, True, 0.33)
        mock_sleep.assert_called_once_with(0.33)
        mock_redis.return_value.set.asserrt_has_calls(
            [
                unittest.mock.call("mylock", secret_token, px=1000000, nx=True),
                unittest.mock.call("mylock", secret_token, px=1000000, nx=True),
            ]
        )

    async def test_unlock(self):
        lock = redilock.DistributedLock()
        lock._redis = unittest.mock.AsyncMock()
        lock._unlock_script = unittest.mock.AsyncMock()
        await lock.unlock("mylock", "my_secret_token")
        lock._unlock_script.run.assert_called_once_with(
            lock._redis, ("mylock",), ["my_secret_token"]
        )

    async def test_with_lock(self):
        mylock = redilock.DistributedLock()

        with unittest.mock.patch.object(mylock, "lock") as mock_lock, \
                unittest.mock.patch.object(mylock, "unlock") as mock_unlock:
            async with mylock("myresource"):
                mock_lock.assert_called_once_with("myresource", None)
                mock_unlock.assert_not_called()
            mock_unlock.assert_called_once_with("myresource", unittest.mock.ANY)
