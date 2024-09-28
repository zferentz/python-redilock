import asyncio
import random
import redilock.async_redilock as redilock


async def main():
    # Define lock with 2 seconds maximum lock time
    lock = redilock.DistributedLock(ttl=5)

    lock_name = f"my_lock_{random.randint(0, 1000)}"

    async with lock(lock_name):
        print("Acquired lock  for 5s. will try to acquire again...")
        async with lock(lock_name):  # Note - non re-entrant lock  (5s wait...)
            print("Acquired again")


if __name__ == "__main__":
    asyncio.run(main())
