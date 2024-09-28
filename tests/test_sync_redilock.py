import unittest.mock
import sys
import os
import time

import redis

_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _parent_dir)

import redilock.sync_redilock as redilock


class TestRediScriptSync(unittest.TestCase):

    def test_rediscript_run_script_not_found(self):
        script = redilock._RediScript("X=1")
        keys = ()
        args = []
        mock_redis = unittest.mock.MagicMock()

        # mock evalsha: first run throw NoScriptError and then return OK
        mock_redis.evalsha.side_effect = [redis.exceptions.NoScriptError, "OK"]
        result = script.run(mock_redis, keys, args)
        mock_redis.evalsha.assert_has_calls(
            [
                unittest.mock.call(script._script_sha1, 0),
                unittest.mock.call(script._script_sha1, 0),
            ]
        )

        mock_redis.script_load.assert_called_with("X=1")
        self.assertEqual(result, "OK")

    def test_rediscript_run_script_found(self):
        script = redilock._RediScript("X=1")
        keys = ()
        args = []
        mock_redis = unittest.mock.MagicMock()

        # mock evalsha: first run throw NoScriptError and then return OK
        mock_redis.evalsha.return_value = "OK"
        result = script.run(mock_redis, keys, args)
        mock_redis.evalsha.assert_called_with(script._script_sha1, 0)
        mock_redis.script_load.assert_not_called()
        self.assertEqual(result, "OK")


class TestRediLockSync(unittest.TestCase):

    @unittest.mock.patch.object(redis, "StrictRedis")
    def test_connect(self, mock_redis):
        lock = redilock.DistributedLock("host", 6379, 2)
        self.assertIsNone(lock._redis)
        lock._connect()
        self.assertEqual(lock._redis, mock_redis.return_value)
        mock_redis.assert_called_once_with(host="host", port=6379, db=2)

        # Make sure that we dont connect twice
        lock._connect()
        mock_redis.assert_called_once()

    @unittest.mock.patch.object(redis, "StrictRedis")
    def test_lock_success_on_1st_attempt(self, mock_redis):
        mock_redis.return_value.set.return_value = 1
        lock = redilock.DistributedLock()
        secret_token = lock.lock("mylock", 1000)
        mock_redis.return_value.set.assert_called_once_with(
            "mylock", secret_token, px=1000000, nx=True
        )

    @unittest.mock.patch.object(redis, "StrictRedis")
    @unittest.mock.patch.object(time, "sleep")
    def test_lock_success_on_2nd_attempt(self, mock_sleep, mock_redis):
        mock_redis.return_value.set.side_effect = [0, 1]
        lock = redilock.DistributedLock()
        secret_token = lock.lock("mylock", 1000, True, 0.33)
        mock_sleep.assert_called_once_with(0.33)
        mock_redis.return_value.set.asserrt_has_calls(
            [
                unittest.mock.call("mylock", secret_token, px=1000000, nx=True),
                unittest.mock.call("mylock", secret_token, px=1000000, nx=True),
            ]
        )

    def test_unlock(self):
        lock = redilock.DistributedLock()
        lock._redis = unittest.mock.MagicMock()
        lock._unlock_script = unittest.mock.MagicMock()
        lock.unlock("mylock", "my_secret_token")
        lock._unlock_script.run.assert_called_once_with(
            lock._redis, ("mylock",), ["my_secret_token"]
        )

    def test_with_lock(self):
        mylock = redilock.DistributedLock()

        with unittest.mock.patch.object(mylock, "lock") as mock_lock, \
            unittest.mock.patch.object(mylock, "unlock") as mock_unlock:

            with mylock("myresource"):
                mock_lock.assert_called_once_with("myresource", None)
                mock_unlock.assert_not_called()
            mock_unlock.assert_called_once_with("myresource", unittest.mock.ANY)
