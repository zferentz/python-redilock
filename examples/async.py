import asyncio
import random
import redilock.async_redilock as redilock

# Define lock
lock = redilock.DistributedLock()

lock_name = f"my_lock_{random.randint(0, 1000)}"


async def main():
    print("Step1: Locking for 5min...")
    unlock_secret_token = await lock.lock(lock_name, 300)
    assert unlock_secret_token

    print("Step2: Trying to lock again without waiting for the lock")
    result = await lock.lock(lock_name, 5, False)
    print(f"Got {result}")
    assert result is False

    print("Step3: Trying to lock again with 1s  wait")
    result = await lock.lock(lock_name, 5, 1)
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

    print("Step6: Locking for 5s...")
    unlock_secret_token = await lock.lock(
        lock_name,
        5,
    )
    assert unlock_secret_token
    print("Done")


asyncio.run(main())
