import asyncio
import logging
import threading
from asyncio import Future
from datetime import timedelta, datetime
from functools import wraps
from typing import Callable, Optional

from gpiozero import GPIOZeroError

from .config import EnvironmentConfig
from .ext import Interval, Duration
from .ext.pins import LimitedDigitalOutputDevice
from .helpers.format_validators import is_gpio


def _update_config(propertySetter: Callable):
    @wraps(propertySetter)
    def _property_modifier(self, *args, **kwargs):
        with self._infoLock:
            propertySetter(self, *args, **kwargs)
            self._envConfig.update_plant_section(self)

    return _property_modifier


class Plant:
    """Representation of a plant

    Stores basic information about plant.
    """
    _plantName: str
    _wateringDuration: Duration
    _wateringInterval: Interval
    _lastTimeWatered: datetime

    _envConfig: EnvironmentConfig
    _logger: logging.Logger
    _gpioPinNumber: str
    _pumpSwitch: LimitedDigitalOutputDevice
    _infoLock: threading.RLock

    _isActive: bool
    _waterLock: threading.Lock
    _waterCondition: threading.Condition
    _waterInside: int
    _relatedTask: Optional[Future]
    _watering_event: Optional[asyncio.Event]

    def __init__(self,
                 plantName: str,
                 envConfig: EnvironmentConfig,
                 gpioPinNumber: str,
                 wateringDuration: timedelta,
                 wateringInterval: timedelta,
                 lastTimeWatered: datetime = datetime.min,
                 isActive=True):
        """
        Args:
            plantName (str): Plant name
            envConfig (EnvironmentConfig): Environment configuration
            gpioPinNumber (str): GPIO number, either BOARDXX or GPIOXX where
                XX is a pin number
            wateringDuration (timedelta): How long should the plant be watered?
            wateringInterval (timedelta): Time between watering
            lastTimeWatered (datetime): When plant was watered last time?
        """
        # Check if data is correct
        if None in [plantName, envConfig, gpioPinNumber, wateringDuration, wateringInterval]:
            raise KeyError()
        if plantName == '':
            raise ValueError()
        if datetime.now() < lastTimeWatered:
            raise ValueError('Last time watered is in future')
        if wateringDuration <= timedelta():
            raise ValueError("Watering duration is negative or equal to 0")
        if wateringInterval <= timedelta():
            raise ValueError("Watering interval is negative or equal to 0")
        if not is_gpio(gpioPinNumber):
            raise ValueError('Wrong GPIO value')

        # set all attributes
        self._infoLock = threading.RLock()
        self._envConfig = envConfig

        self._plantName = plantName
        self._lastTimeWatered: datetime = lastTimeWatered
        self._wateringDuration = Duration.convert_to_duration(wateringDuration)
        self._wateringInterval = Interval.convert_to_interval(wateringInterval)

        self._gpioPinNumber = gpioPinNumber
        self._logger = self._envConfig.logger.getChild(self._plantName)
        # activates pump
        self.isActive = isActive
        self._pumpSwitch = self._envConfig.pin_manager.create_pump(self._gpioPinNumber)
        self._waterLock = threading.Lock()
        self._waterCondition = threading.Condition(self._waterLock)
        self._waterInside = 0

        self._envConfig.logger.debug(
            f'Creating successful. Last time watered: {self._lastTimeWatered}. Interval: {self._wateringInterval}. '
            f'Pin: {self._gpioPinNumber}')

    def __del__(self):
        self._pumpSwitch.close()

    @property
    def plantName(self) -> str:
        """Plant's name"""
        with self._infoLock:
            return self._plantName

    @plantName.setter
    @_update_config
    def plantName(self, plantName: str) -> None:
        with self._infoLock:
            self.plantName = plantName

    @property
    def wateringDuration(self) -> timedelta:
        """Duration between waterings"""
        with self._infoLock:
            return self._wateringDuration

    @wateringDuration.setter
    @_update_config
    def wateringDuration(self, value: timedelta) -> None:
        with self._infoLock:
            self._wateringDuration = Duration.convert_to_duration(value)

    @property
    def wateringInterval(self) -> timedelta:
        """Interval between waterings"""
        with self._infoLock:
            return self._wateringInterval

    @wateringInterval.setter
    @_update_config
    def wateringInterval(self, value: timedelta):
        with self._infoLock:
            self.wateringInterval = Interval.convert_to_interval(value)
            self._watering_event.set()

    @property
    def lastTimeWatered(self) -> datetime:
        """Last time of watering"""
        with self._infoLock:
            return self._lastTimeWatered

    @property
    def gpioPinNumber(self):
        """GpioPinNumber"""
        with self._infoLock:
            return self._gpioPinNumber

    @property
    def isActive(self):
        """Is watering active?"""
        with self._infoLock:
            return self._isActive

    @isActive.setter
    @_update_config
    def isActive(self, value: bool):
        with self._infoLock:
            if self._isActive == value:
                return
            elif value:
                self._relatedTask = self._envConfig.env_loop.add_task(self.plant_task_loop())
                self._envConfig.logger.info(f'Auto watering activated')
            else:
                self._envConfig.env_loop.cancel_task(self._relatedTask)
                self._envConfig.logger.info(f'Auto watering deactivated')
                self._relatedTask = None
            self._isActive = value

    def manual_water(self, wateringDuration: timedelta = None, force: bool = False) -> None:
        with self._waterLock:
            self._envConfig.env_loop.add_task(self._water(wateringDuration, force)).result()

    async def plant_task_loop(self) -> None:
        while True:
            while not self.should_water():
                try:
                    await asyncio.wait_for(self._watering_event.wait(), self.time_to_next_watering().total_seconds())
                except asyncio.TimeoutError:
                    pass
                if self._watering_event:
                    self._watering_event.clear()
                    break
            with self._waterLock:
                if self.should_water():
                    await asyncio.shield(self._water())

    async def _water(self, wateringDuration: timedelta = None, force: bool = False) -> None:
        """Waters plant.

        Obtains pump lock (EnvironmentConfig specifies max number of simultanously working pumps).
        Blocks thread until plant is watered
        """
        try:
            self._logger.info(f'{self._plantName}: Started watering')
            self._pumpSwitch.on(force)
            if wateringDuration is None:
                await asyncio.sleep(self.wateringDuration.total_seconds())
            else:
                await asyncio.sleep(wateringDuration.total_seconds())
        except GPIOZeroError as exc:
            self._logger.error(f'{self._plantName}: GPIO error')
            raise exc
        finally:
            self._pumpSwitch.off()
            with self._infoLock:
                self._lastTimeWatered = datetime.now()
            self._logger.info(f'{self._plantName}: Stopped watering')

    def should_water(self) -> bool:
        """Checks if it is right to water plant now"""
        self._logger.debug(
            f'Time now: {datetime.now()}. Planned watering: {self._lastTimeWatered + self._wateringInterval}')
        if datetime.now() >= self._lastTimeWatered + self._wateringInterval:
            self._logger.info(f'{self._plantName}: It\'s right to water me now!')
            return True
        else:
            self._logger.info(f'{self._plantName}: Give me some time, water me later')
            return False

    def calc_next_watering(self) -> datetime:
        """Calculate next watering date

        Returns:
            (datetime) watering datetime
        """
        return self._lastTimeWatered + self._wateringInterval

    def time_to_next_watering(self) -> timedelta:
        return self.calc_next_watering() - datetime.now()
