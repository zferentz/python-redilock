"""Async version of loadtest.py - refer to loadtest.py for more info

In a nutshell - this script simulates an asynchronous operation  on a shared
resource (file).

Run this script with one of the 3 locks:
LOCK=None : no locking at all . multiple tasks access the file concurrently.
            file is corrupted or in "INVALID STATE" 
LOCK=asyncio_mutex : standard asyncio.Lock() 
            no errors when running a single instance of this tester but file
            is corrupted (or INVALID STATE) when running multipel instances
LOCK=redilock_mutex : using redilock
            no errors whether running sinlge or multiple instances

for more information - refer to the non-async file loadtest.py
"""
import asyncio
import aiofiles
import random
import time
import redilock.async_redilock as redilock

TASKS_COUNT = 4
TASK_ITERATIONS = 50

shared_resource_filename = "/tmp/share_resource.txt"

redilock_mutex = redilock.DistributedLock(ttl=10)
asyncio_mutex = asyncio.Lock()

# LOCK = None
# LOCK = redilock_mutex
LOCK = asyncio_mutex

# Global array to count number of errors from all tasks
total_errors = []


async def _update_shared_file() -> int:
    errors = 0
    try:
        async with aiofiles.open(shared_resource_filename, "r") as f:
            data = await f.read()
            if data != "VALID STATE":
                errors += 1

        async with aiofiles.open(shared_resource_filename, "w") as f:
            await f.write("INVALID STATE")
        time.sleep(random.random() % 0.25)

        async with aiofiles.open(shared_resource_filename, "w") as f:
            await f.write("VALID STATE")
    except Exception as e:
        errors += 1

    return errors


async def taskfunction(task_index):
    for i in range(0, TASK_ITERATIONS):

        if not LOCK:
            errors = await _update_shared_file()
        elif LOCK == asyncio_mutex:
            async with asyncio_mutex:
                errors = await _update_shared_file()
        elif LOCK == redilock_mutex:
            async with redilock_mutex("my_lock"):
                errors = await _update_shared_file()
        else:
            assert False, "Unknown LOCK"

        if errors:
            print("x", end="")
        else:
            print(".", end="")

        total_errors[task_index] += errors


async def main():
    with open(shared_resource_filename, "w") as f:
        f.write("VALID STATE")
    tasks = []
    for i in range(0, TASKS_COUNT):
        tasks.append(taskfunction(i))
        total_errors.append(0)
    await asyncio.gather(*tasks)
    print(f"\nTotal Errors: {sum(total_errors)}")


asyncio.run(main())
