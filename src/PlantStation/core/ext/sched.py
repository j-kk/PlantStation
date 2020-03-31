import threading
import datetime
from threading import Condition, RLock
from typing import Callable
import queue


class Event(object):
    _time: datetime.datetime
    _func: Callable
    _args: []
    _kwargs: {}
    cancel = False

    def __init__(self, time: datetime, func: Callable, args, kwargs):
        self._time = time
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def __eq__(self, other):
        return self.time == other.time

    def __lt__(self, other):
        return self.time < other.time

    def __le__(self, other):
        return self.time <= other.time

    def __gt__(self, other):
        return self.time > other.time

    def __ge__(self, other):
        return self.time >= other.time

    @property
    def time(self):
        return self._time

    def run(self):
        if not self.cancel:
            self._func(*self._args, **self._kwargs)


class MultithreadSched(object):
    """Multithread implementation of scheduler.

    The main difference is that tasks are run in seperate threads.
    Implementation is thread safe.

    Priority is skipped, because tasks are executed independently

    """
    running: bool = False
    _lock = RLock()
    _new_job = Condition(_lock)
    _threads: [threading.Thread] = []
    _queue = queue.PriorityQueue()

    @property
    def threads(self):
        """List of all active running task threads

        Returns
        -------
        List of threads,
        """
        with self._lock:
            return self._threads

    def _add_thread(self, thread):
        with self._lock:
            self._threads.append(thread)

    def _pack_job(self, func):
        def __packed_job(*args, **kwargs):
            with self._lock:
                self.threads.append(threading.current_thread())
            func(*args, **kwargs)
            with self._lock:
                self.threads.remove(threading.current_thread())

        return __packed_job

    def enterabs(self, time: datetime.datetime, action: Callable, args=[], kwargs={}):
        """Schedules new task

        Parameters
        ----------
        time : datetime.datetime
            Scheduled time of execution
        action : () -> None
            function to execute
        args: []
            list of arguments to pass
        kwargs: {}
            dict of named arguments to pass
        """
        action = self._pack_job(action)
        new_event = Event(time, action, args, kwargs)
        with self._lock:
            self._queue.put(new_event)
            self._new_job.notify()

    def enter(self, delay: datetime.timedelta, action: Callable, args=[], kwargs={}):
        """Schedules new task

        Parameters
        ----------
        delay : datetime.timedelta
            delay time
        action : () -> None
            function to execute
        args: []
            list of arguments to pass
        kwargs: {}
            dict of named arguments to pass
        """
        time = datetime.datetime.now() + delay
        return self.enterabs(time, action, args, kwargs)

    def stop(self) -> None:
        """
            Stops scheduler without removing pending tasks
        """
        with self._lock:
            self.running = False
            self._new_job.notify()

    def run(self):
        """
            Execute events until the scheduler is stopped
            If there are no tasks waiting, it hangs until new appears
            or it's stopped by stop()

        """
        self.running = True
        with self._lock:
            while self.running:
                if self._queue.empty():
                    self._new_job.wait()
                event = self._queue.get()  # TODO peek
                if datetime.datetime.now() < event.time:
                    self._queue.put(event)
                    diff = datetime.datetime.now() - event.time
                    self._new_job.wait(timeout=diff.total_seconds())
                else:
                    thread = threading.Thread(target=event.run)
                    thread.run()
