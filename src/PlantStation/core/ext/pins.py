import asyncio
import logging
from datetime import timedelta, time
from typing import Optional, Tuple

from gpiozero import DigitalOutputDevice
from gpiozero.pins import mock, native, local

from PlantStation.core import EnvironmentConfig
from PlantStation.core.ext import EventLoop, Duration

DEFAULT_ACTIVE_LIMIT = 1


class SilentHoursException(Exception):
    """Exception thrown when pump is ordered to work during silent hours"""
    pass


class LimitedDigitalOutputDevice(DigitalOutputDevice):
    """
    DigitalOutputDevice extended with limitation of maximum number
    of active pins at once. Requires :class: PinManager which grants
    permission
    """
    _manager: "PinManager"
    _logger: logging.Logger

    def __init__(self, manager, config: EnvironmentConfig, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(__name__ + ':gpio')
        self._manager = manager
        self._config = config

    async def manual_on(self, force: bool = False) -> None:  # FixMe mutual exclusion with activate_for
        """Turns on the device. Respects to working hours scheduled by pin_manager

        Args:
            force (bool): ignores working hours schedule
        """
        if self._config.calc_working_hours().total_seconds() > 0 and not force:
            raise SilentHoursException()

        await self._manager.acquire_lock()
        super().on()

    async def manual_off(self) -> None:
        """Turns off the device"""
        super().off()
        await self._manager.release_lock()

    async def activate_for(self, duration: Duration, force: bool = False) -> None:
        """Activates pump for given time. Use force to override silent hours.

        Args:
            duration (timedelta): time to water
            force (bool): override silent hours rule
        """
        if self._config.calc_working_hours().total_seconds() > 0 and not force:
            raise SilentHoursException
        try:
            await self._manager.acquire_lock()
            self.on()
            self._logger.debug(f'Pin {self._pin} is on')
            await asyncio.sleep(duration.total_seconds())
        finally:
            self.off()
            self._logger.debug(f'Pin {self._pin} is off')
            await asyncio.shield(self._manager.release_lock())


class PinManager(object):
    """Manages pin IO and responds for parallel working pump limit"""
    _factory: local.LocalPiFactory

    _config: Optional[EnvironmentConfig]
    _active_limit: int
    _working_pumps: int
    _pump_lock: asyncio.Lock
    _wait_for_pump: asyncio.Condition
    _working_hours: Optional[Tuple[time, time]]

    def __init__(self,
                 event_loop: EventLoop,
                 config: EnvironmentConfig,
                 active_limit: int = DEFAULT_ACTIVE_LIMIT,
                 dry_run: bool = False):

        # create lock & condition
        self._pump_lock = asyncio.Lock(loop=event_loop.async_loop)
        self._wait_for_pump = asyncio.Condition(self._pump_lock, loop=event_loop.async_loop)
        # set attributes
        self._config = config
        self._active_limit = active_limit
        self._working_pumps = 0
        # create pin factory
        self._pin_factory = native.NativeFactory() if not dry_run else mock.MockFactory()
        # logger
        if config is not None:
            self._logger = logging.getLogger(config.env_name)

    @property
    def pin_factory(self) -> local.PiFactory:
        """Returns pin factory"""
        return self._pin_factory

    @property
    def silent_hours(self) -> Optional[Tuple[time, time]]:
        """Returns set working hours"""
        with self._pump_lock:
            if self._config:
                return self._config.silent_hours
            else:
                return None

    @property
    def active_limit(self) -> int:
        """Limit of parallel working pumps"""
        if self._config:
            return self._config.active_limit
        else:
            return self._active_limit

    async def acquire_lock(self) -> None:
        """Acquires pump lock"""
        async with self._pump_lock:
            if self._working_pumps >= self.active_limit:
                await self._wait_for_pump.wait()
            self._working_pumps += 1

    async def release_lock(self) -> None:
        """Releases pump lock"""
        async with self._pump_lock:
            self._working_pumps -= 1
            self._wait_for_pump.notify()

    def create_pump(self, pin_number: str) -> LimitedDigitalOutputDevice:
        """Creates Digital output device, which stick to the limit of parallel working pumps

        Args:
            pin_number (str): pin number

        Returns
            LimitedDigitalOutputDevice
        """
        device = LimitedDigitalOutputDevice(self, pin=pin_number, pin_factory=self.pin_factory, config=self._config)
        return device
