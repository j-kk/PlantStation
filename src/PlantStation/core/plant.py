import asyncio
import configparser
import logging
import threading
from asyncio import Future
from datetime import timedelta, datetime
from typing import Callable, Optional

from .config import EnvironmentConfig
from .ext import Interval, Duration, EventLoop
from .ext.pins import LimitedDigitalOutputDevice, PinManager, SilentHoursException
from .helpers.format_validators import is_gpio, parse_time


def update_config(propertySetter: Callable):
    def wrapper(self, value, *args, **kwargs):
        propertySetter(self, value, *args, **kwargs)
        if isinstance(value, datetime):
            self._envConfig.update_section(self._plantName, propertySetter.__name__, value.strftime('%Y-%m-%d %X'))
        else:
            self._envConfig.update_section(self._plantName, propertySetter.__name__, str(value))

    return wrapper


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
    _pumpSwitch: Optional[LimitedDigitalOutputDevice]
    _infoLock: threading.Lock

    _isActive: bool
    _waterLock: threading.Lock
    _relatedTask: Optional[Future]

    _env_loop: Optional[EventLoop]

    def __init__(self,
                 plantName: str,
                 envConfig: EnvironmentConfig,
                 gpioPinNumber: str,
                 wateringDuration: timedelta,
                 wateringInterval: timedelta,
                 env_loop: Optional[EventLoop] = None,
                 pin_manager: Optional[PinManager] = None,
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

        self._infoLock = threading.Lock()
        self._waterLock = threading.Lock()
        assert type(envConfig) is EnvironmentConfig
        self._envConfig = envConfig

        self.plantName = plantName
        self._logger = logging.getLogger(self._envConfig.env_name).getChild(self.plantName)

        if env_loop:
            assert type(env_loop) is EventLoop
            self._env_loop = env_loop
        else:
            self._env_loop = None

        assert is_gpio(gpioPinNumber), 'Wrong GPIO value'
        self.gpioPinNumber = gpioPinNumber
        # activates pump
        self._isActive = False
        self.isActive = isActive

        if pin_manager:
            self._pumpSwitch = pin_manager.create_pump(self.gpioPinNumber)
        else:
            self._pumpSwitch = None

        assert isinstance(lastTimeWatered, datetime)
        assert lastTimeWatered <= datetime.now(), 'Last time watered is in future'
        self.lastTimeWatered = lastTimeWatered

        self.wateringDuration = Duration.convert_to_duration(wateringDuration)
        self.wateringInterval = Interval.convert_to_interval(wateringInterval)

        self._logger.debug(
            f'Creating successful. Last time watered: {self.lastTimeWatered}. Interval: {self.wateringInterval}. '
            f'Pin: {self.gpioPinNumber}')

    @property
    def plantName(self) -> str:
        """Plant's name"""
        with self._infoLock:
            return self._plantName

    @plantName.setter
    @update_config
    def plantName(self, plantName: str) -> None:
        assert isinstance(plantName, str)
        assert len(plantName) > 0
        with self._infoLock:
            self._plantName = plantName

    @property
    def wateringDuration(self) -> Duration:
        """Duration between waterings"""
        with self._infoLock:
            return self._wateringDuration

    @wateringDuration.setter
    @update_config
    def wateringDuration(self, value: Duration) -> None:
        assert isinstance(value, Duration)
        assert not value <= timedelta(), "Watering duration is negative or equal to 0"
        with self._infoLock:
            self._wateringDuration = value

    @property
    def wateringInterval(self) -> Interval:
        """Interval between waterings"""
        with self._infoLock:
            return self._wateringInterval

    @wateringInterval.setter
    @update_config
    def wateringInterval(self, value: Interval):
        assert isinstance(value, Interval)
        assert not value <= timedelta(), "Watering interval is negative or equal to 0"
        with self._infoLock:
            self._wateringInterval = value
            # TODO update time

    @property
    def lastTimeWatered(self) -> datetime:
        """Last time of watering"""
        with self._infoLock:
            return self._lastTimeWatered

    @lastTimeWatered.setter
    @update_config
    def lastTimeWatered(self, value: datetime) -> None:
        assert isinstance(value, datetime)
        with self._infoLock:
            self._lastTimeWatered = value

    @property
    def gpioPinNumber(self) -> str:
        """GpioPinNumber"""
        with self._infoLock:
            return self._gpioPinNumber

    @gpioPinNumber.setter
    @update_config
    def gpioPinNumber(self, value: str) -> None:
        with self._infoLock:
            self._gpioPinNumber = value

    @property
    def isActive(self) -> bool:
        """Is watering active?"""
        with self._infoLock:
            return self._isActive

    @isActive.setter
    @update_config
    def isActive(self, value: bool) -> None:
        assert type(value) is bool
        with self._infoLock:
            if self._isActive == value:
                return
            self._isActive = value
            if self._env_loop:
                if self._isActive:
                    self._relatedTask = self._env_loop.add_task(self.plant_task_loop())
                    self._logger.info(f'Auto watering activated')
                else:
                    self._env_loop.cancel_task(self._relatedTask)
                    self._logger.info(f'Auto watering deactivated')
                    self._relatedTask = None

    async def plant_task_loop(self) -> None:
        while True:
            await asyncio.sleep(self.time_to_next_watering().total_seconds())
            await asyncio.sleep(self._envConfig.calc_working_hours().total_seconds())
            with self._waterLock:
                await asyncio.shield(self._water())

    async def _water(self, wateringDuration: Optional[timedelta] = None) -> None:
        """Waters plant.

        Obtains pump lock (EnvironmentConfig specifies max number of simultanously working pumps).
        Blocks thread until plant is watered
        """
        try:
            self._logger.info(f'{self._plantName}: Started watering.')
            if wateringDuration is None:
                wateringDuration = self.wateringDuration
            await self._pumpSwitch.activate_for(wateringDuration)
            self.lastTimeWatered = datetime.now()
            self._logger.info(f'{self._plantName}: Stopped watering.')
        except SilentHoursException:
            self._logger.info(f'{self._plantName}: Watering canceled. Silent hours are active.')

    def should_water(self) -> bool:
        """Checks if it is right to water plant now"""
        self._logger.debug(
            f'Time now: {datetime.now()}. Planned watering: {self.lastTimeWatered + self.wateringInterval}')
        if datetime.now() >= self.lastTimeWatered + self.wateringInterval:
            self._logger.info(f'{self.plantName}: It\'s right to water me now!')
            return True
        else:
            self._logger.info(f'{self.plantName}: Give me some time, water me later')
            return False

    def time_to_next_watering(self) -> timedelta:
        """Calculate time to next watering

        Returns:
            (timedelta) remaining time
        """
        with self._infoLock:
            return self._lastTimeWatered + self._wateringInterval - datetime.now()

    @classmethod
    def from_config(cls,
                    env_config: EnvironmentConfig,
                    section: configparser.SectionProxy,
                    env_loop: EventLoop,
                    pin_manager: PinManager) -> "Plant":

        return cls(env_loop=env_loop,
                   pin_manager=pin_manager,
                   plantName=section.name,
                   envConfig=env_config,
                   gpioPinNumber=section['gpioPinNumber'],
                   wateringDuration=timedelta(seconds=float(section['wateringDuration'])),
                   wateringInterval=parse_time(section['wateringInterval']),
                   lastTimeWatered=datetime.strptime(section['lastTimeWatered'], '%Y-%m-%d %X'),
                   isActive=bool(section['isActive'])
                   )
