import asyncio
import logging
import threading
from concurrent.futures import Future


class EventLoop(threading.Thread):
    """Asyncio event loop in standalone thread."""
    _loop: asyncio.AbstractEventLoop

    _logger: logging.Logger

    _exit_lock: threading.Lock
    _exit_cond: threading.Condition
    _canceled: int

    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._loop = asyncio.new_event_loop()

        self._exit_lock = threading.Lock()
        self._exit_cond = threading.Condition(self._exit_lock)
        self._canceled = 0

    @property
    def async_loop(self):
        """Async loop"""
        return self._loop

    def run(self) -> None:
        """Implementation of Thread run() method. Runs event loop"""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def stop(self) -> None:
        """Stops event loop and waits for thread termination"""
        # TODO grateful cancelation

        all_tasks = asyncio.all_tasks(self._loop)

        with self._exit_lock:
            self._canceled = len(all_tasks)
            for task in all_tasks:
                self._loop.call_soon_threadsafe(lambda: task.add_done_callback(lambda _: self._rm_task()))
                self._loop.call_soon_threadsafe(task.cancel)

            if self._canceled > 0:
                self._exit_cond.wait()
        for task in all_tasks:
            try:
                task.result()
            except asyncio.CancelledError:
                pass

        self._loop.call_soon_threadsafe(self._loop.stop)
        self.join()

    def _rm_task(self):
        with self._exit_lock:
            self._canceled -= 1
            if self._canceled == 0:
                self._exit_cond.notify()

    def add_task(self, coro) -> Future:
        """this method should return a task object, that I
          can cancel, not a handle"""

        task = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return task
