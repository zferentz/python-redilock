import asyncio
import random
import redilock.async_redilock as redilock


async def main():
    # Define lock with 2 seconds maximum lock time
    lock = redilock.DistributedLock(ttl=2)

    lock_name = f"my_lock_{random.randint(0, 1000)}"

    # Lock for 5 minutes (override the default 2s lock)
    print("Step1: Lock for 5min...")
    unlock_secret_token = await lock.lock(lock_name, ttl=300)
    assert unlock_secret_token

    print("Step2: Trying to lock again without waiting for the lock")
    result = await lock.lock(lock_name, block=False)
    print(f"Got {result}")
    assert result is False

    print("Step3: Trying to lock again with 1s  wait")
    result = await lock.lock(lock_name, block=1)
    print(f"Got {result}")
    assert result is False

    print("Step4: Unlocking the lock with the wrong key...")
    result = await lock.unlock(lock_name, "wrong-key")
    print(f"Got {result}")
    assert result is False

    print("Step5: Unlocking the lock with the correct key...")
    result = await lock.unlock(lock_name, unlock_secret_token)
    print(f"Got {result}")
    assert result is True

    print("Step6: Trying to lock (after unlock)...")
    unlock_secret_token = await lock.lock(lock_name)
    assert unlock_secret_token
    print("Done")


if __name__ == "__main__":
    asyncio.run(main())
