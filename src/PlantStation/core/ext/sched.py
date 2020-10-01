import functools
import asyncio
from concurrent.futures import Future

from threading import Thread, current_thread


class B(Thread):

    loop: asyncio.AbstractEventLoop
    tid: Thread

    def __init__(self):
        Thread.__init__(self)

    def run(self):
        self.loop = asyncio.get_event_loop()
        self.tid = current_thread()
        self.loop.run_forever()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)

    def add_task(self, coro):
        """this method should return a task object, that I
          can cancel, not a handle"""
        def _async_add(func, fut):
            try:
                ret = func()
                fut.set_result(ret)
            except Exception as e:
                fut.set_exception(e)

        f = functools.partial(asyncio.ensure_future, coro, loop=self.loop)
        if current_thread() == self.tid:
            return f() # We can call directly if we're not going between threads.
        else:
            # We're in a non-event loop thread so we use a Future
            # to get the task from the event loop thread once
            # it's ready.
            fut = Future()
            self.loop.call_soon_threadsafe(_async_add, f, fut)
            return fut.result()

    def cancel_task(self, task):
        self.loop.call_soon_threadsafe(task.cancel)

