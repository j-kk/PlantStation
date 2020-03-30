import heapq
import threading
from sched import scheduler, _sentinel
from threading import Condition, Lock
from time import monotonic as _time



class MultithreadSched(scheduler):

    _new_job: Condition

    def __init__(self, timefunc=_time):
        super().__init__(timefunc=_time)
        self._new_job = Condition(self._lock)

    def enterabs(self, time, priority, action, argument=(), kwargs=_sentinel):
        with self._lock:
            super().enterabs(time, priority, action, argument, _sentinel)
            self._new_job.notify()

    def enter(self, delay, priority, action, argument=(), kwargs=_sentinel):
        with self._lock:
            super().enter(delay, priority, action, argument, _sentinel)
            self._new_job.notify()

    def cancel(self, event):
        with self._lock:
            super().cancel(event)
            self._new_job.notify()


    def run(self):
        """Execute events until the queue is empty.
        If blocking is False executes the scheduled events due to
        expire soonest (if any) and then return the deadline of the
        next scheduled call in the scheduler.

        When there is a positive delay until the first event, the
        delay function is called and the event is left in the queue;
        otherwise, the event is removed from the queue and executed
        (its action function is called, passing it the argument).  If
        the delay function returns prematurely, it is simply
        restarted.

        It is legal for both the delay function and the action
        function to modify the queue or to raise an exception;
        exceptions are not caught but the scheduler's state remains
        well-defined so run() may be called again.

        A questionable hack is added to allow other threads to run:
        just after an event is executed, a delay of 0 is executed, to
        avoid monopolizing the CPU when other threads are also
        runnable.

        """
        # localize variable access to minimize overhead
        # and to improve thread safety
        lock = self._lock
        q = self._queue
        timefunc = self.timefunc
        pop = heapq.heappop
        with lock:
            while True:
                if not q:
                    self._new_job.wait()
                time, priority, action, argument, kwargs = q[0]
                now = timefunc()
                if time > now:
                    self._new_job.wait(timeout=time-now)
                else:
                    pop(q) #FUTURE store info about threads
                    thread = threading.Thread(target=action, args=argument)
                    thread.run()






