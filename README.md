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


**Redilock** is a simple python package that acts as a simple distributed lock and  allows you to add locking capabilites to any cloud/distributed environment.

**Redilock** main features:
* Simple to use - only 2 api calls `lock()` and `unlock()` 
* Supports both synchronous implementation and an async implementation  
* Safe: 
  * When acquiring a lock, one must specify the lock-expiration (TTL - time to lock) so even if the program/host crashes - the lock eventually will be released
  * unlocking the lock can be performed only by the party who put the lock

Examples:
```
import redilock.sync_redilock as redilock

lock = redilock.DistributedLock()

unlock_secret_token = lock.lock("my_lock", 300)  # lock for 5min
lock.unlock("my_lock", unlock_secret_token)  # release the lock
```

By default, if you try to acquire a lock - your program will be blocked until the lock is acquired.
you can specify non-blocking mode which can be useful in my cases, for example:
```
import redilock.sync_redilock as redilock

lock = redilock.DistributedLock()

lock.lock("my_lock", 10)  # lock for 10s
if not lock.lock("my_lock", 1, False):  # try to lock again (for 1s) but do't block  
  print("Couldnt acquire the lock")

```

