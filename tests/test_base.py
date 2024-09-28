import hashlib
import time
import unittest.mock
import uuid

import sys
import os

_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _parent_dir)

import redilock.base as base


class TestRedisLuaScriptBase(unittest.TestCase):

    def test_redis_script_direct_inheritance(self):
        with self.assertRaises(TypeError):
            base.RedisLuaScriptBase("X=1")

    def test_redis_script_sync(self):
        class RedisLuaScriptBaseSync(base.RedisLuaScriptBase):
            def run(self):
                pass

        lua_script = "X=1"
        script_object = RedisLuaScriptBaseSync(lua_script)
        self.assertEqual(script_object._script, lua_script)
        self.assertEqual(
            script_object._script_sha1,
            hashlib.sha1(lua_script.encode("utf-8")).hexdigest(),
        )

    def test_redis_script_async(self):
        class RedisLuaScriptBaseSync(base.RedisLuaScriptBase):
            async def run(self):
                pass

        lua_script = "X=1"
        script_object = RedisLuaScriptBaseSync(lua_script)
        self.assertEqual(script_object._script, lua_script)
        self.assertEqual(
            script_object._script_sha1,
            hashlib.sha1(lua_script.encode("utf-8")).hexdigest(),
        )


class TestDistributedLockBase(unittest.TestCase):

    def test_distributed_lock_sync_default(self):
        class MyDistributedLock(base.DistributedLockBase):
            def lock(self):
                pass

            def unlock(self):
                pass

        lock = MyDistributedLock()
        self.assertEqual(lock._redis, None)
        self.assertEqual(lock._redis_host, base._DEFAULT_REDIS_HOST)
        self.assertEqual(lock._redis_port, base._DEFAULT_REDIS_PORT)
        self.assertEqual(lock._redis_db, base._DEFAULT_REDIS_DB)

        lock = MyDistributedLock("host", 666, 12)
        self.assertEqual(lock._redis, None)
        self.assertEqual(lock._redis_host, "host")
        self.assertEqual(lock._redis_port, 666)
        self.assertEqual(lock._redis_db, 12)

    def test_distributed_lock_async(self):
        class MyDistributedLock(base.DistributedLockBase):
            async def lock(self):
                pass

            async def unlock(self):
                pass

        lock = MyDistributedLock()
        self.assertEqual(lock._redis, None)
        self.assertEqual(lock._redis_host, base._DEFAULT_REDIS_HOST)
        self.assertEqual(lock._redis_port, base._DEFAULT_REDIS_PORT)
        self.assertEqual(lock._redis_db, base._DEFAULT_REDIS_DB)

        lock = MyDistributedLock("host", 666, 12)
        self.assertEqual(lock._redis, None)
        self.assertEqual(lock._redis_host, "host")
        self.assertEqual(lock._redis_port, 666)
        self.assertEqual(lock._redis_db, 12)

    def test_prepare_lock_validation(self):
        class MyTestDistributedLock(base.DistributedLockBase):
            def run(self):
                pass

        mylock = MyTestDistributedLock()  # Missing ttl
        with self.assertRaises(AssertionError):
            mylock._prepare_lock("mylock", None, True, None)

        mylock = MyTestDistributedLock(interval=2)  # Missing ttl
        with self.assertRaises(AssertionError):
            mylock._prepare_lock("mylock", None, True, None)

        mylock = MyTestDistributedLock(ttl=1)
        _, ttl, end_wait, interval = mylock._prepare_lock("mylock", None, True, None)
        self.assertEqual(ttl, 1)
        self.assertEqual(interval, base._DEFAULT_INTERVAL)

        mylock = MyTestDistributedLock(ttl=1, interval=2)
        _, ttl, end_wait, interval = mylock._prepare_lock("mylock", None, True, None)
        self.assertEqual(ttl, 1)
        self.assertEqual(interval, 2)

    @unittest.mock.patch.object(uuid, "uuid4")
    def test_prepare_lock(self, mock_uuid4):

        class MyTestDistributedLock(base.DistributedLockBase):
            def run(self):
                pass

        mock_uuid4.return_value.hex = "AAAA-BBBB-CCCC-DDDD"

        # test with block=True
        mylock = MyTestDistributedLock(ttl=14, interval=0.66)
        unlock_secret_token, ttl, end_wait, interval = mylock._prepare_lock(
            "mylock", None, True, None
        )

        self.assertEqual(end_wait, None)
        self.assertEqual(unlock_secret_token, "_LOCK_mylock_AAAA-BBBB-CCCC-DDDD")
        self.assertEqual(ttl, 14)
        self.assertEqual(interval, 0.66)

    def test_prepare_lock_with_timed_block(self):

        class MyTestDistributedLock(base.DistributedLockBase):
            async def run(self):
                pass

        now = time.time()
        with unittest.mock.patch.object(time, "time") as mock_time:
            mock_time.return_value = now
            # test with block=1.23
            _, ttl, end_wait, interval = MyTestDistributedLock()._prepare_lock(
                "my_lock_name", 123, 1.23, 666
            )

        self.assertEqual(end_wait, now + 1.23)
        self.assertEqual(ttl, 123)
        self.assertEqual(interval, 666)
