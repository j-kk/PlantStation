from datetime import datetime, timedelta, time, date
from threading import Lock, Condition
from typing import Optional, List, Tuple

from gpiozero import DigitalOutputDevice
from gpiozero.pins import mock, native, local

from core import EnvironmentConfig

DEFAULT_ACTIVE_LIMIT = 1


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

    def on(self, force: bool = False) -> None:
        """Turns on the device. Respects to working hours scheduled by pin_manager

        Args:
            force (bool): ignores working hours schedule
        """
        if not force:
            if self._manager.calc_working_hours() is not None:
                raise SilentHoursException()
        self._manager.acquire_lock()
        super().on()

    def off(self):
        """Turns off the device"""
        super().off()
        self._manager.release_lock()


class PinManager(object):
    """Manages pin IO and responds for parallel working pump limit"""
    _factory: local.LocalPiFactory

    _active_limit: int
    _working_pumps: int
    _pump_lock: Lock
    _wait_for_pump: Condition
    _devices: List[LimitedDigitalOutputDevice]
    _working_hours: Optional[Tuple[time, time]]

    def __init__(self,
                 active_limit: int = DEFAULT_ACTIVE_LIMIT,
                 dry_run: bool = False,
                 working_hours: Optional[Tuple[time, time]] = None,
                 config: Optional[EnvironmentConfig] = None):
        # create lock & condition
        self._pump_lock = Lock()
        self._wait_for_pump = Condition(self._pump_lock)
        # set attributes
        self._config = config
        self._active_limit = active_limit
        self._devices = []
        self._working_pumps = 0
        self.working_hours = working_hours
        # create pin factory
        self._pin_factory = native.NativeFactory() if not dry_run else mock.MockFactory()

    @property
    def pin_factory(self) -> local.PiFactory:
        """Returns pin factory"""
        return self._pin_factory

    @property
    def working_hours(self) -> Optional[Tuple[time, time]]:
        """Returns set working hours"""
        with self._pump_lock:
            if self._config:
                return self._config.silent_hours
            else:
                return self._working_hours

    @working_hours.setter
    def working_hours(self, value: (time, time)) -> None:
        assert self._config is None
        with self._pump_lock:
            if value is None:
                return
            if value[1] < value[0]:
                raise ValueError(f'Working hours begin after they ends')
            self._working_hours = value

    @property
    def active_limit(self):
        """Limit of parallel working pumps"""
        with self._pump_lock:
            if self._config:
                return self._config.active_limit
            else:
                return self._active_limit

    @active_limit.setter
    def active_limit(self, value) -> None:
        assert self._config is None
        with self._pump_lock:
            self._active_limit = value

    @property
    def working_pumps(self) -> int:
        """Number of working pumps"""
        with self._pump_lock:
            return self._working_pumps

    def calc_working_hours(self) -> timedelta:
        """Calculates time to next watering

        Returns:
            (timedelta): time to next watering
        """
        if self._working_hours is not None:
            if datetime.now().time() < self.working_hours[0]:
                return datetime.combine(date.today(), self.working_hours[0]) - datetime.now()
            if self.working_hours[1] <= datetime.now().time():
                return datetime.combine(date.today() + timedelta(days=1), self.working_hours[1]) - datetime.now()
        return timedelta(0)

    def acquire_lock(self) -> None:
        """Acquires pump lock"""
        with self._pump_lock:
            while self._working_pumps >= self._active_limit:
                self._wait_for_pump.wait()
            else:
                self._working_pumps += 1

    def release_lock(self) -> None:
        """
        Releases pump lock
        """
        with self._pump_lock:
            self._working_pumps -= 1
            self._wait_for_pump.notify()

    def create_pump(self, pin_number: str) -> LimitedDigitalOutputDevice:
        """Creates Digital output device, which stick to the limit of parallel working pumps

        Args:
            pin_number (str): pin number

        Returns
            LimitedDigitalOutputDevice
        """
        device = LimitedDigitalOutputDevice(self, pin=pin_number, pin_factory=self.pin_factory)
        self._devices.append(device)
        return device
