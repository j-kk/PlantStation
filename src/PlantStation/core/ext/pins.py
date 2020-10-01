from datetime import datetime, timedelta, date, time
from threading import Lock, Condition

from gpiozero import DigitalOutputDevice
from gpiozero.pins import mock, native, local

DEFAULT_ACTIVE_LIMIT = 1
#TODO sigint interrupt -> turn off all devices


class SilentHoursException(Exception):
    pass


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

    def on(self, force= False):
        """
        Turns on device. Respects to working hours scheduled by pin_manager
        Parameters
        ----------
        force: ignores working hours schedule

        Returns
        -------
        None if working hours
        """
        if not force:
            if self._manager.calc_working_hours() is not None:
                raise SilentHoursException()
        self._manager.acquire_lock()
        super().on()
        return None


    def off(self):
        super().off()
        self._manager.release_lock()


class PinManager(object):
    """
    Manages pin IO and responds for parallel working pump limit
    """
    _factory: local.LocalPiFactory

    _active_limit : int
    _working_pumps : int
    _pump_lock: Lock
    _wait_for_pump: Condition
    _devices : []
    _working_hours : (time, time) = None

    def __init__(self, active_limit: int = DEFAULT_ACTIVE_LIMIT, dry_run: bool = False, working_hours = None):
        # create lock & condition
        self._pump_lock = Lock()
        self._wait_for_pump = Condition(self._pump_lock)
        #set attributes
        self._active_limit = active_limit
        self._devices = []
        self._working_pumps = 0
        self.working_hours = working_hours
        # create pin factory
        self._pin_factory = native.NativeFactory() if not dry_run else mock.MockFactory()


    @property
    def pin_factory(self):
        """
        Returns pin factory
        """
        return self._pin_factory

    @property
    def working_hours(self):
        with self._pump_lock:
            return self._working_hours

    @working_hours.setter
    def working_hours(self, value: (time, time)):
        with self._pump_lock:
            if value is None:
                return
            if value[1] < value [0]:
                raise ValueError(f'Working hours begin after they ends')
            self._working_hours[0] = value[0]
            self._working_hours[1] = value[1]

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

    def calc_working_hours(self):
        if self._working_hours is not None:
            if datetime.now().time() < self.working_hours[0]:
                return datetime.combine(date.today(), self.working_hours[0]) - datetime.now()
            if self.working_hours[1] <= datetime.now().time():
                return datetime.combine(date.today() + timedelta(days=1), self.working_hours[1]) - datetime.now()
        return timedelta(0)

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
