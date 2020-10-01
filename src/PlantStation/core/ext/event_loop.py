import asyncio
from concurrent.futures import Future

from threading import Thread, current_thread
from typing import Optional


class EventLoop(Thread):
    """Asyncio event loop in standalone thread."""
    _loop: asyncio.AbstractEventLoop
    _tid: Optional[Thread]

    def __init__(self):
        Thread.__init__(self)
        self._loop = asyncio.new_event_loop()

    def run(self) -> None:
        """Implementation of Thread run() method. Runs event loop"""
        asyncio.set_event_loop(self._loop)
        self._tid = current_thread()
        self._loop.run_forever()

    def stop(self) -> None:
        """Stops event loop and waits for thread termination"""
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._tid.join()
        self._tid = None

    def add_task(self, coro) -> Future:
        """this method should return a task object, that I
          can cancel, not a handle"""
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def cancel_task(self, task: Future) -> None:
        """Cancels task execution"""
        self._loop.call_soon_threadsafe(task.cancel)
