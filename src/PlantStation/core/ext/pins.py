from threading import Lock, Condition

from gpiozero import DigitalOutputDevice
from gpiozero.pins import mock, native, local

DEFAULT_ACTIVE_LIMIT = 1


class LimitedDigitalOutputDevice(DigitalOutputDevice):
    """
    DigitalOutputDevice extended with limitation of maximum number
    of active pins at once. Requires :class: PinManager which grants
    permission
    """
    _manager = None

    def __init__(self, manager, **kwargs):
        super().__init__(**kwargs)
        self._manager = manager

    def on(self):
        self._manager.acquire_lock()
        super(self).on()

    def off(self):
        super(self).off()
        self._manager.release_lock()


class PinManager(object):
    """
    Manages pin IO and responds for parallel working pump limit
    """
    _factory: local.LocalPiFactory

    _active_limit : int
    _working_pumps = 0
    _pump_lock: Lock
    _wait_for_pump: Condition
    _devices = []

    def __init__(self, active_limit: int = DEFAULT_ACTIVE_LIMIT, dry_run: bool = False):
        self._active_limit = active_limit

        # create pin factory
        self._pin_factory = native.NativeFactory() if not dry_run else mock.MockFactory()

        # create lock & condition
        self._pump_lock = Lock()
        self._wait_for_pump = Condition(self._pump_lock)

    @property
    def pin_factory(self):
        """
        Returns pin factory
        """
        return self._pin_factory

    @property
    def active_limit(self):
        """
        Limit of parallel working pumps
        """
        with self._pump_lock:
            return self._active_limit

    @active_limit.setter
    def active_limit(self, value):
        with self._pump_lock:
            self._active_limit = value

    @property
    def working_pumps(self) -> int:
        """
        Number of working pumps
        """
        with self._pump_lock:
            return self._working_pumps

    def acquire_lock(self):
        """
        Acquires pump lock
        """
        with self._pump_lock:
            while self._working_pumps >= self._active_limit:
                self._wait_for_pump.wait()
            else:
                self._working_pumps += 1

    def release_lock(self):
        """
        Releases pump lock
        """
        with self._pump_lock:
            self._working_pumps -= 1
            self._wait_for_pump.notify()

    def create_pump(self, pin_number: str) -> LimitedDigitalOutputDevice:
        """
        Creates Digital output device, which stick to the limit of parallel working pumps
        Parameters
        ----------
        pin_number: pin number

        Returns
        -------
        LimitedDigitalOutputDevice
        """
        device = LimitedDigitalOutputDevice(self, pin=pin_number, pin_factory=self.pin_factory)
        self._devices.append(device)
        return device
