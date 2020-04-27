import datetime
import logging
import threading
import time
from datetime import timedelta, datetime
from functools import wraps
from typing import Callable

from gpiozero import DigitalOutputDevice, GPIOZeroError

from .config import EnvironmentConfig
from .ext import Interval, Duration
from .ext.pins import LimitedDigitalOutputDevice
from .helpers.format_validators import is_gpio


class Plant(object):
    """Representation of a plant

    Stores basic information about plant.

    Attributes:
    -----------

    plantName  : str
        Name of the plant


    Methods:
    --------

    water()
        Waters plant. Obtains pump lock (EnvironmentConfig specifies max number of simultanously working pumps).
        Blocks thread until plant is watered

    should_water()
        Checks if it is right time to water now, returns appropriate actions to do in kwargs (new scheduler event)
    """
    _plantName: str
    _wateringDuration: Duration
    _wateringInterval: Interval
    _lastTimeWatered: datetime

    _envConfig: EnvironmentConfig
    _logger: logging.Logger
    _gpioPinNumber: str
    _pumpSwitch: LimitedDigitalOutputDevice
    _relatedTask = None
    _isActive = False

    _infoLock: threading.RLock

    def __init__(self, plantName: str, envConfig: EnvironmentConfig, gpioPinNumber: str, wateringDuration: timedelta,
                 wateringInterval: timedelta, lastTimeWatered: datetime = datetime.min, isActive=True):
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
        self._lastTimeWatered: datetime.datetime = lastTimeWatered
        self._wateringDuration = Duration.convert_to_duration(wateringDuration)
        self._wateringInterval = Interval.convert_to_interval(wateringInterval)

        self._gpioPinNumber = gpioPinNumber
        self._logger = self._envConfig.logger.getChild(self._plantName)
        #activates pump
        self.isActive = isActive

        self._envConfig.logger.debug(
            f'Creating successful. Last time watered: {self._lastTimeWatered}. Interval: {self._wateringInterval}. '
            f'Pin: {self._gpioPinNumber}')

    def __del__(self):
        self._pumpSwitch.close()

    def __dir__(self):
        packed = [
            'plantName',
            'wateringDuration',
            'wateringInterval',
            'lastTimeWatered',
            'gpioPinNumber',
            'isActive'
        ]
        return packed

    def _update_config(propertySetter: Callable):
        @wraps(propertySetter)
        def _property_modifier(self, *args, **kwargs):
            with self._infoLock:
                propertySetter(self, *args, **kwargs)
                self._envConfig.update_plant_section(self)

        return _property_modifier

    @property
    def plantName(self) -> str:
        """
        Plant's name
        """
        with self._infoLock:
            return self._plantName

    @plantName.setter
    @_update_config
    def plantName(self, plantName: str) -> None:
        with self._infoLock:
            self.plantName = plantName

    @property
    def wateringDuration(self) -> timedelta:
        """
        Duration between waterings
        """
        with self._infoLock:
            return self._wateringDuration

    @wateringDuration.setter
    @_update_config
    def wateringDuration(self, value: timedelta) -> None:
        with self._infoLock:
            self._wateringDuration = Duration.convert_to_duration(value)

    @property
    def wateringInterval(self) -> timedelta:
        """Interval between waterings

        """
        with self._infoLock:
            return self._wateringInterval

    @wateringInterval.setter
    @_update_config
    def wateringInterval(self, value: timedelta):
        with self._infoLock:
            self.wateringInterval = Interval.convert_to_interval(value)

    @property
    def lastTimeWatered(self) -> datetime:
        """
        Last time of watering
        """
        with self._infoLock:
            return self._lastTimeWatered

    @property
    def gpioPinNumber(self):
        with self._infoLock:
            return self._gpioPinNumber

    @property
    def isActive(self):
        with self._infoLock:
            return self._isActive

    @isActive.setter
    @_update_config
    def isActive(self, value: bool):
        with self._infoLock:
            if self._isActive == value:
                return
            elif value:
                # define pump
                try:
                    self._pumpSwitch = self._envConfig.pin_manager.create_pump(self._gpioPinNumber)
                    self._envConfig.logger.info(f'Pump activated')
                    self._isActive = value
                except GPIOZeroError as exc:
                    self._envConfig.logger.error(f'Couldn\'t set up gpio pin: {self._gpioPinNumber}')
                    raise exc
            else:
                self._pumpSwitch.close()
                self._envConfig.logger.info(f'Pump deactivated')

    @property
    def relatedTask(self):
        with self._infoLock:
            return self._relatedTask

    @relatedTask.setter
    def relatedTask(self, value):
        with self._infoLock:
            self._relatedTask = value

    def water(self, force=False) -> None:
        """
            Waters plant. Obtains pump lock (EnvironmentConfig specifies max number of simultanously working pumps).
            Blocks thread until plant is watered
        """
        if self.isActive:
            try:
                self._logger.info(f'{self._plantName}: Started watering')
                self._pumpSwitch.on(force)
                time.sleep(self.wateringDuration.total_seconds())
            except GPIOZeroError as exc:
                self._logger.error(f'{self._plantName}: GPIO error')
                raise exc
            finally:
                self._pumpSwitch.off()
                with self._infoLock:
                    self._lastTimeWatered = datetime.now()
                self._logger.info(f'{self._plantName}: Stopped watering')
        else:
            self._logger.info(f'Water: Pump is not active')

    def should_water(self) -> bool:
        """Checks if it is right to water plant now

        """
        self._logger.debug(
            f'Time now: {datetime.now()}. Planned watering: {self._lastTimeWatered + self._wateringInterval}')
        if datetime.now() >= self._lastTimeWatered + self._wateringInterval:
            self._logger.info("%s: It's right to water me now!", self._plantName)
            return True
        else:
            self._logger.info("%s: Give me some time, water me later", self._plantName)
            return False



    def calc_next_watering(self) -> datetime:
        """Calculate next watering date

        :return: watering datetime
        """
        return self._lastTimeWatered + self._wateringInterval
