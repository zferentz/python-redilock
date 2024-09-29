"""Tester to validate the redilock vs. no-lock vs. threading.Lock

In order to prove that redilock is working as expected, we can use this super
simple program that simulates a "shared resource".

Our shared-resource is a file that can have only 2 states:
  "VALID STATE"  or "INVALID STATE"

This test program runs multiple threads, each one has a simple loop :
  - read the shared-resource file. if state is "INVALID STATE" count as an error
  - validate that it is in "VALID STATE"
  - writes "INVALID STATE" to the file to simulate resource is busy
  - sleep random time (less than 250ms)
  - validate that it is in "VALID STATE"

At the end of the program we cound the total number of errors (from all threads).

The global variable LOCK  can point to one of 3 locks:
- None: no locking at all
- threading_mutex:  standard threading.Lock() mutex
- redilock_mutex:  redilock mutex

By running the script with different LOCK options, we can see that :
- Without lock  - we usually see multiple errors
- With threading-mutex we dont see error when running single instance of this
  script but when running multiple instances of this script we see errors
- With redilock-mutex we dont see errors at all
"""
import random
import time
import threading
import redilock.sync_redilock as redilock

THREAD_COUNT = 4
THREAD_ITERATIONS = 50

shared_resource_filename = "/tmp/share_resource.txt"

threading_mutex = threading.Lock()
redilock_mutex = redilock.DistributedLock(ttl=10)

# To test different scenarios - uncomment ONE of the lines below
LOCK = redilock_mutex
#LOCK = threading_mutex
#LOCK = None

# Global array to count number of errors from all threads
total_errors = []

def _update_shared_file() -> int:
    errors = 0
    try:
        with open(shared_resource_filename, "r") as f:
            data = f.read()
            if data != "VALID STATE":
                errors += 1

        with open(shared_resource_filename, "w") as f:
            f.write("INVALID STATE")
        time.sleep(random.random() % 0.25)

        with open(shared_resource_filename, "w") as f:
            f.write("VALID STATE")
    except Exception as e:
        errors += 1

    return errors


def threadfunction(thread_index):
    for i in range(0, THREAD_ITERATIONS):
        errors = 0

        if not LOCK:
            errors += _update_shared_file()
        elif LOCK is threading_mutex:
            with threading_mutex:
                errors += _update_shared_file()
        elif LOCK is redilock_mutex:
            with redilock_mutex("my_lock"):
                errors += _update_shared_file()
        else:
            assert "Unexpected LOCK value"
        if errors:
            print("x", end="")
        else:
            print(".", end="")

        total_errors[thread_index] += errors


with open(shared_resource_filename, "w") as f:
    f.write("VALID STATE")
threads = []
for i in range(0, THREAD_COUNT):
    t = threading.Thread(target=threadfunction, args=(i,))
    threads.append(t)
    total_errors.append(0)
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"\nTotal Errors: {sum(total_errors)}")
