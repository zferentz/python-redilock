# redilock :  Redis Distributed Lock

### Introduction - what is a Lock / Mutex?

In multithreaded/asynchronous programs, multiple "tasks" run in parallel.
One challenge with such parallel tasks is that sometimes there is a need to make sure that only one task will call a
function or access a resource.

A lock (a.k.a Mutex) is a code facility that acts as a gatekeeper and allows only one task to access a resource.

Python provides `threading.Lock()` and `asyncio.Lock()` exactly for this purpose.

### Distributed Locks

When working with multiple processes or multiple services/hosts - we also need a lock but now we need a “distributed
lock” which is similar to the standard lock except that it is available to other programs/services/hosts.

As Redis is a storage/caching system, we can use it to act as a distributed lock.

**Redilock** is a simple python package that acts as a simple distributed lock and allows you to add locking capabilites
to any cloud/distributed environment.

**Redilock** main features:

* Simple to use:
    * Context manager (`with statement`)
    * Only 2 api calls `lock()` and `unlock()`
* Supports both synchronous implementation and an async implementation
* Safe:
    * Caller must specify the lock-expiration (TTL - time to lock) so even if the program/host crashes - the lock will
      be eventually released
    * Unlocking the lock can be performed only by the party who put the lock

### Installation
```pip install python-redilock```
  
### Usage & Examples

_(for synchronous code, async is identical and straightforward. check out the examples directory for more examples)_:

The easiest way - using `with statement`

```
import redilock.sync_redilock as redilock
mylock = redilock.DistributedLock(ttl=30)  # max lock for 30 seconds

with mylock("my_lock"):
  print("I've got the lock !!")
```

Directly using `lock` and `unlock`

```
import redilock.sync_redilock as redilock

lock = redilock.DistributedLock(ttl=300)  # lock for maximum 5min

unlock_secret_token = lock.lock("my_lock")  # Acquire the lock
lock.unlock("my_lock", unlock_secret_token)  # Release the lock
```

By default, if you try to acquire a lock - your program will be blocked until the lock is acquired.
you can specify non-blocking mode which can be useful in many cases, for example:

```
import redilock.sync_redilock as redilock

lock = redilock.DistributedLock(ttl=10)  # lock for 10s

lock.lock("my_lock")  
if not lock.lock("my_lock", block=False):  # try to lock again but do't block  
  print("Couldnt acquire the lock")
```

### Good to know and best practices
* The TTL is super important. it dictates when to auto-release the lock if your code doesnt release it
  (in case of a bug or a crash). You should not rely on it for unlocking as your code should either unlock
  using the `unlock` function or via `with statement`.
  As so, a large value (e.g 30-60 seconds) is probably fine.
* you can specify TTL when instantiating the class or when performing the lock operation itself.  
* When using blocking lock there is a background loop that checks redis periodically if the lock is still acquired.
  The system uses check-interval of 0.25. You can modify this value if needed via the `interval` parameter.
```
mylock = redilock.DistributedLock(interval=2)
```
  
* The lock is not re-entrant. it means that if a task (thread/coroutine) owns it and tries to lock again - it will be blocked until the lock expires (ttl). 
For example
```
with mylock("my_lock", ttl=5):
  print("I've got the lock, let's lock again")
  with mylock("my_lock", ttl=5):  # <------------- will block for 5s
    print("I've got the lock again")
```
Technically, it is possible to create a re-entrant distributed lock but i tend to believe
that if you need such facility - you're probably using the wrong architecture or you don't need this redilock :) .

* using a `with-statement` for locking is indeed the easiest way however there is one big tricky "gotcha" with this approach.
if your TTL is too short  - the lock will expire while you're still in the "with"
Consider the following code:
```
import time
import redilock.sync_redilock as redilock

mylock = redilock.DistributedLock(ttl=2)  # lock that will autoexpire after 2s

with mylock("my_lock"):
    print("I've got the lock !!")
    time.sleep(3)
    print("Hmm...i dont have the lock anymore :( ")
```
